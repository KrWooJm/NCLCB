"""한국투자증권 해외(미국)주식 구현체 (2단계: 분봉·거래대금 순위 조회).

종목 표기는 '거래소:티커' (NAS:AAPL, NYS:F, AMS:...).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import pandas as pd

from core.broker.kis_client import KisClient
from core.broker.kis_common import frame_from_bars, to_float, unsupported
from core.config import UniverseConfig
from core.models import Balance, OrderId, OrderSide, OrderType, Position, Quote, WatchItem, split_us_symbol
from core.timeutil import NEW_YORK, ensure_aware, weekdays_between

logger = logging.getLogger(__name__)

# [v1_해외주식-030] 해외주식분봉조회: 호출당 최대 120건, 최신부터 거슬러 올라가며 페이지 조회
MINUTE_PATH = "/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice"
MINUTE_TR = "HHDFS76950200"
# 해외주식 거래대금순위
RANK_PATH = "/uapi/overseas-stock/v1/ranking/trade-pbmn"
RANK_TR = "HHDFS76320010"

PAGES_PER_WEEKDAY = 8  # 정규장 390분 / 120건 ≈ 4 페이지 + 여유


class KisOverseasBroker:
    def __init__(self, quote: KisClient, *, today: date | None = None) -> None:
        if not quote.quote_only:
            raise ValueError("시세 조회에는 조회 전용(quote_only) 클라이언트를 넘겨야 합니다")
        self._q = quote
        self._today = today  # 테스트용 고정값

    # ------------------------------------------------------------ candles

    def fetch_minutes(self, symbol: str, days: list[date]) -> dict[date, pd.DataFrame]:
        """최신 분봉부터 거슬러 올라가며 days 중 가장 이른 날까지 받는다."""
        if not days:
            return {}
        excd, ticker = split_us_symbol(symbol)
        oldest = min(days)
        today = self._today or datetime.now(NEW_YORK).date()
        max_pages = PAGES_PER_WEEKDAY * (len(weekdays_between(oldest, today)) + 1)

        bars: dict[datetime, tuple] = {}
        keyb, nxt = "", ""
        prev_earliest: datetime | None = None
        for _ in range(max_pages):
            res = self._q.get(
                MINUTE_PATH,
                MINUTE_TR,
                {
                    "AUTH": "",
                    "EXCD": excd,
                    "SYMB": ticker,
                    "NMIN": "1",
                    "PINC": "1",  # 전일 포함
                    "NEXT": nxt,
                    "NREC": "120",
                    "FILL": "",
                    "KEYB": keyb,
                },
            )
            stamps = []
            for r in res.body.get("output2") or []:
                if not r.get("xymd") or not r.get("xhms"):
                    continue
                # xymd/xhms: 현지(뉴욕) 기준 일자·시각
                ts = datetime.strptime(r["xymd"] + r["xhms"], "%Y%m%d%H%M%S").replace(tzinfo=NEW_YORK)
                bars[ts] = (
                    to_float(r.get("open")),
                    to_float(r.get("high")),
                    to_float(r.get("low")),
                    to_float(r.get("last")),
                    to_float(r.get("evol")),
                )
                stamps.append(ts)
            if not stamps:
                break
            earliest = min(stamps)
            if earliest.date() < oldest or (prev_earliest is not None and earliest >= prev_earliest):
                break
            prev_earliest = earliest
            keyb, nxt = (earliest - timedelta(minutes=1)).strftime("%Y%m%d%H%M%S"), "1"
        else:
            logger.warning("%s: 페이지 한도(%d) 도달", symbol, max_pages)

        df = frame_from_bars(bars)
        wanted = set(days)
        out: dict[date, pd.DataFrame] = {d: df.iloc[0:0] for d in days}
        for d, part in df.groupby(df.index.date):
            if d in wanted:
                out[d] = part
        return out

    def get_candles(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
        if interval != "1m":
            raise ValueError("KIS 원본은 1분봉만 지원합니다. 5분봉은 core.data.resample로 만든다")
        start, end = ensure_aware(start).astimezone(NEW_YORK), ensure_aware(end).astimezone(NEW_YORK)
        frames = [f for f in self.fetch_minutes(symbol, weekdays_between(start.date(), end.date())).values() if len(f)]
        if not frames:
            return frame_from_bars({})
        df = pd.concat(frames).sort_index()
        return df[(df.index >= start) & (df.index < end)]

    # ------------------------------------------------------------ ranking

    def rank_by_turnover(self, universe: UniverseConfig, exchanges: list[str], size: int) -> list[WatchItem]:
        """거래소별 당일 거래대금 순위를 합쳐 상위 size개. ETF·ADR 구분은 3단계 유니버스에서 거른다."""
        seen: dict[str, WatchItem] = {}
        for excd in exchanges:
            res = self._q.get(
                RANK_PATH,
                RANK_TR,
                {
                    "EXCD": excd,
                    "NDAY": "0",  # 당일
                    "VOL_RANG": "0",
                    "AUTH": "",
                    "KEYB": "",
                    "PRC1": f"{universe.min_price:g}",  # 5.0 → "5"
                    "PRC2": f"{universe.max_price:g}",
                },
            )
            rows = res.body.get("output2") or []
            kept = 0
            for r in rows:
                ticker = (r.get("symb") or "").strip()
                price = to_float(r.get("last"))
                if not ticker or not (universe.min_price <= price <= universe.max_price):
                    continue
                item = WatchItem(f"{excd}:{ticker}", (r.get("name") or r.get("ename") or "").strip(), price, to_float(r.get("tamt")))
                seen.setdefault(item.symbol, item)
                kept += 1
            if rows:
                logger.info("%s 거래대금 순위: 응답 %d행, 가격 필터 후 %d개", excd, len(rows), kept)
            else:
                # 장 시작 전·휴장 등으로 '당일' 순위가 비어 있을 수 있다 — 원인 파악용으로 응답 요약을 남긴다
                logger.warning(
                    "%s 거래대금 순위가 비었습니다: msg=%s output1=%s",
                    excd,
                    str(res.body.get("msg1", "")).strip(),
                    res.body.get("output1"),
                )
        items = sorted(seen.values(), key=lambda w: w.turnover if w.turnover == w.turnover else -1, reverse=True)
        return items[:size]

    # ------------------------------------------------------------ 이후 단계

    def get_quote(self, symbol: str) -> Quote:
        raise unsupported("get_quote", 5)

    def get_balance(self) -> Balance:
        raise unsupported("get_balance", 6)

    def get_positions(self) -> list[Position]:
        raise unsupported("get_positions", 6)

    def place_order(self, symbol: str, side: OrderSide, qty: int, order_type: OrderType, price: float | None = None) -> OrderId:
        raise unsupported("place_order", 6)

    def cancel_order(self, order_id: OrderId) -> None:
        raise unsupported("cancel_order", 6)
