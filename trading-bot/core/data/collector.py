"""감시목록 → 1분봉 조회 → 정리·검증 → Parquet 저장."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

import pandas as pd

from core.config import SessionConfig
from core.data.store import CandleStore
from core.data.validate import clean_minutes
from core.models import Market, WatchItem
from core.timeutil import recent_weekdays

logger = logging.getLogger(__name__)


class MinuteSource(Protocol):
    def fetch_minutes(self, symbol: str, days: list[date]) -> dict[date, pd.DataFrame]: ...


@dataclass
class CollectSummary:
    market: Market
    day: date
    symbols: int = 0
    days_saved: int = 0
    days_empty: int = 0
    bars_saved: int = 0
    warnings: int = 0
    failed: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"[{self.market.value} {self.day}] 종목 {self.symbols}개, 저장 {self.days_saved}일치 "
            f"({self.bars_saved}봉), 빈 날 {self.days_empty}, 경고 {self.warnings}, 실패 {len(self.failed)}"
            + (f" {self.failed}" if self.failed else "")
        )


def collect(
    market: Market,
    day: date,
    watchlist: list[WatchItem],
    source: MinuteSource,
    store: CandleStore,
    session: SessionConfig,
    *,
    backfill_days: int,
    dry_run: bool = False,
) -> CollectSummary:
    """day는 항상 다시 받고(덮어쓰기), 그 이전 backfill_days 평일 중 저장 안 된 날만 채운다."""
    summary = CollectSummary(market, day, symbols=len(watchlist))
    history = recent_weekdays(day, backfill_days + 1)[:-1]

    for item in watchlist:
        sym = item.symbol
        days = [d for d in history if not store.has(market, sym, d)] + [day]
        try:
            fetched = source.fetch_minutes(sym, days)
        except Exception:
            logger.exception("%s 조회 실패", sym)
            summary.failed.append(sym)
            continue

        for d in days:
            raw = fetched.get(d)
            df, issues = clean_minutes(raw, d, session) if raw is not None else (None, [])
            for msg in issues:
                logger.warning("%s %s: %s", sym, d, msg)
            summary.warnings += len(issues)
            if df is None or df.empty:
                summary.days_empty += 1
                if not dry_run:
                    store.mark_empty(market, sym, d)
                continue
            summary.days_saved += 1
            summary.bars_saved += len(df)
            if not dry_run:
                store.write(market, sym, d, df)
        logger.info("%s: %d일 조회", sym, len(days))

    logger.info("%s", summary)
    return summary
