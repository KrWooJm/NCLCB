"""한국투자증권 국내주식 구현체 (2단계: 분봉·거래대금 순위 조회)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import pandas as pd

from core.broker.kis_client import KisClient
from core.broker.kis_common import frame_from_bars, to_float, unsupported
from core.config import SessionConfig, UniverseConfig
from core.models import Balance, OrderId, OrderSide, OrderType, Position, Quote, WatchItem
from core.timeutil import KST, ensure_aware, weekdays_between

logger = logging.getLogger(__name__)

# [국내주식-213] 주식일별분봉조회: 과거 일자 분봉, 호출당 최대 120건 (실전 서버)
MINUTE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice"
MINUTE_TR = "FHKST03010230"
# [v1_국내주식-047] 거래량순위
RANK_PATH = "/uapi/domestic-stock/v1/quotations/volume-rank"
RANK_TR = "FHPST01710000"

# 시장 구분: UN = KRX + NXT 통합 (NXT 프리·애프터마켓 08:00~20:00 포함)
MARKET_CODE = "UN"

# 순위 조회 대상 제외 (10자리, 순서: 투자위험/경고/주의, 관리종목, 정리매매, 불성실공시,
# 우선주, 거래정지, ETF, ETN, 신용주문불가, SPAC)
RANK_EXCLUDE = "1111111101"


class KisDomesticBroker:
    def __init__(self, quote: KisClient, data_session: SessionConfig, *, max_pages_per_day: int = 12) -> None:
        if not quote.quote_only:
            raise ValueError("시세 조회에는 조회 전용(quote_only) 클라이언트를 넘겨야 합니다")
        self._q = quote
        self._session = data_session  # 08:00~20:00 = 720분 / 120건 = 6페이지 + 여유
        self._max_pages = max_pages_per_day

    # ------------------------------------------------------------ candles

    def fetch_minutes(self, symbol: str, days: list[date]) -> dict[date, pd.DataFrame]:
        return {d: self._fetch_day(symbol, d) for d in days}

    def _fetch_day(self, symbol: str, day: date) -> pd.DataFrame:
        ds = day.strftime("%Y%m%d")
        open_hms = self._session.open.strftime("%H%M%S")
        hour = self._session.close.strftime("%H%M%S")  # 수집 범위 끝에서부터 거슬러 올라간다
        bars: dict[datetime, tuple] = {}
        for _ in range(self._max_pages):
            res = self._q.get(
                MINUTE_PATH,
                MINUTE_TR,
                {
                    "FID_COND_MRKT_DIV_CODE": MARKET_CODE,
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_HOUR_1": hour,
                    "FID_INPUT_DATE_1": ds,
                    "FID_PW_DATA_INCU_YN": "N",
                    "FID_FAKE_TICK_INCU_YN": "",
                },
            )
            hours = []
            for r in res.body.get("output2") or []:
                if r.get("stck_bsop_date") != ds or not r.get("stck_cntg_hour"):
                    continue
                h = r["stck_cntg_hour"]
                ts = datetime.strptime(ds + h, "%Y%m%d%H%M%S").replace(tzinfo=KST)
                bars[ts] = (
                    to_float(r.get("stck_oprc")),
                    to_float(r.get("stck_hgpr")),
                    to_float(r.get("stck_lwpr")),
                    to_float(r.get("stck_prpr")),
                    to_float(r.get("cntg_vol")),
                )
                hours.append(h)
            if not hours:
                break
            earliest = min(hours)
            if earliest <= open_hms or earliest >= hour:
                break
            hour = (datetime.strptime(earliest, "%H%M%S") - timedelta(minutes=1)).strftime("%H%M%S")
        else:
            logger.warning("%s %s: 페이지 한도(%d) 도달", symbol, ds, self._max_pages)
        return frame_from_bars(bars)

    def get_candles(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
        if interval != "1m":
            raise ValueError("KIS 원본은 1분봉만 지원합니다. 5분봉은 core.data.resample로 만든다")
        start, end = ensure_aware(start).astimezone(KST), ensure_aware(end).astimezone(KST)
        frames = [f for f in self.fetch_minutes(symbol, weekdays_between(start.date(), end.date())).values() if len(f)]
        if not frames:
            return frame_from_bars({})
        df = pd.concat(frames).sort_index()
        return df[(df.index >= start) & (df.index < end)]

    # ------------------------------------------------------------ ranking

    def rank_by_turnover(self, universe: UniverseConfig, size: int) -> list[WatchItem]:
        """거래대금 상위 종목 (장 마감 후 호출하면 당일 기준 = 다음 거래일의 '전일 거래대금')."""
        res = self._q.get(
            RANK_PATH,
            RANK_TR,
            {
                "FID_COND_MRKT_DIV_CODE": MARKET_CODE,
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "0000",
                "FID_DIV_CLS_CODE": "1",  # 보통주
                "FID_BLNG_CLS_CODE": "3",  # 거래금액순
                "FID_TRGT_CLS_CODE": "111111111",
                "FID_TRGT_EXLS_CLS_CODE": RANK_EXCLUDE,
                "FID_INPUT_PRICE_1": str(int(universe.min_price)),
                "FID_INPUT_PRICE_2": str(int(universe.max_price)),
                "FID_VOL_CNT": "",
                "FID_INPUT_DATE_1": "",
            },
        )
        items = []
        for r in res.body.get("output") or []:
            code = (r.get("mksc_shrn_iscd") or "").strip()
            price = to_float(r.get("stck_prpr"))
            turnover = to_float(r.get("acml_tr_pbmn"))
            mcap = to_float(r.get("lstn_stcn")) * price
            if not code or not (universe.min_price <= price <= universe.max_price):
                continue
            if universe.min_market_cap is not None and not mcap >= universe.min_market_cap:
                continue
            if universe.min_prev_turnover is not None and not turnover >= universe.min_prev_turnover:
                continue
            items.append(WatchItem(code, (r.get("hts_kor_isnm") or "").strip(), price, turnover))
        items.sort(key=lambda w: w.turnover, reverse=True)
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
