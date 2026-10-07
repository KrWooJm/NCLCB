"""분봉 수집 실행.

    python scripts/collect.py --market domestic
    python scripts/collect.py --market us --dry-run --limit 2
    python scripts/collect.py --market domestic --date 2026-10-06

--date를 생략하면 지금 시각 기준으로 마감된 가장 최근 거래일을 수집한다.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.broker.kis_client import KisClient  # noqa: E402
from core.broker.kis_domestic import KisDomesticBroker  # noqa: E402
from core.broker.kis_overseas import KisOverseasBroker  # noqa: E402
from core.config import load_app_config, load_secrets, load_strategy  # noqa: E402
from core.data.collector import collect  # noqa: E402
from core.data.store import CandleStore  # noqa: E402
from core.data.watchlist import latest_watchlist, merge_extra, save_watchlist  # noqa: E402
from core.logging_setup import setup_logging  # noqa: E402
from core.models import Market, WatchItem  # noqa: E402
from core.timeutil import last_completed_session  # noqa: E402

logger = logging.getLogger("collect")

CLOSE_GRACE = timedelta(minutes=5)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="KIS 1분봉 수집")
    ap.add_argument("--market", choices=[m.value for m in Market], required=True)
    ap.add_argument("--date", type=date.fromisoformat, help="수집 거래일 (현지 날짜, 기본: 마감된 최근 거래일)")
    ap.add_argument("--dry-run", action="store_true", help="조회만 하고 저장하지 않음")
    ap.add_argument("--limit", type=int, help="감시목록 앞에서 N개만 (연결 확인용)")
    ap.add_argument("--no-backfill", action="store_true", help="과거 빈 날 채우기 생략")
    ap.add_argument("--symbols", help="순위 조회 대신 이 종목만 수집 (쉼표 구분, 미국은 거래소:티커. 예: NAS:AAPL,NYS:F)")
    args = ap.parse_args(argv)

    app, strategy, secrets = load_app_config(), load_strategy(), load_secrets()
    setup_logging(app.log, secrets.values())

    if secrets.kis_quote_app_key is None or secrets.kis_quote_app_secret is None:
        logger.error(".env에 KIS_QUOTE_APP_KEY / KIS_QUOTE_APP_SECRET 이 없습니다")
        return 2

    market = Market(args.market)
    mcfg = getattr(strategy.markets, market.value)
    day = args.date or last_completed_session(datetime.now(mcfg.tz), mcfg.tz, mcfg.data_session.close, CLOSE_GRACE)

    root = app.data_dir
    client = KisClient(
        "real",
        secrets.kis_quote_app_key,
        secrets.kis_quote_app_secret,
        root / ".kis_token_quote.json",
        quote_only=True,
        requests_per_second=app.kis.requests_per_second,
        max_retries=app.kis.max_retries,
        timeout_seconds=app.kis.timeout_seconds,
    )

    if market is Market.DOMESTIC:
        broker = KisDomesticBroker(client, mcfg.data_session)
        extra = app.collect.domestic.extra_symbols
    else:
        broker = KisOverseasBroker(client)
        extra = app.collect.us.extra_symbols

    def as_items(symbols: list[str]) -> list[WatchItem]:
        return [WatchItem(s.strip(), "", float("nan"), float("nan")) for s in symbols if s.strip()]

    from_ranking = False
    if args.symbols:
        items = as_items(args.symbols.split(","))
    elif market is Market.US and not app.collect.us.use_ranking:
        items = as_items(app.collect.us.symbols)
        logger.info("미국 감시목록: config/app.yaml의 collect.us.symbols %d종목", len(items))
    elif market is Market.DOMESTIC:
        items, from_ranking = broker.rank_by_turnover(mcfg.universe, app.collect.domestic.candidates), True
    else:
        items, from_ranking = broker.rank_by_turnover(mcfg.universe, app.collect.us.exchanges, app.collect.us.candidates), True

    if from_ranking and not items:
        prev = latest_watchlist(root, market, day)
        if prev:
            logger.warning("순위 결과가 비어 %s에 저장된 감시목록 %d종목을 대신 씁니다", prev[0], len(prev[1]))
            items, from_ranking = prev[1], False
        else:
            logger.warning(
                "순위 결과가 비었고 저장된 감시목록도 없습니다. 수집 마감 직후(국내 20:10, 미국 한국시각 06:15)에 "
                "다시 실행하거나 --symbols 로 종목을 지정하세요"
            )
    items = merge_extra(items, extra)

    if args.limit:
        items = items[: args.limit]
    logger.info("수집 대상 %s %s: %d종목 %s", market.value, day, len(items), [w.symbol for w in items])
    if not items:
        logger.error("감시목록이 비었습니다")
        return 1
    if not args.dry_run and not args.symbols:
        save_watchlist(root, market, day, items)

    summary = collect(
        market,
        day,
        items,
        broker,
        CandleStore(root),
        mcfg.data_session,
        mcfg.session,
        backfill_days=0 if args.no_backfill else app.data.backfill_days,
        dry_run=args.dry_run,
    )
    print(summary)
    return 1 if summary.failed and len(summary.failed) == summary.symbols else 0


def run() -> int:
    try:
        return main()
    except Exception:
        logger.exception("수집 중단")
        return 1


if __name__ == "__main__":
    sys.exit(run())
