"""수집 대상 종목 목록. 매일 순위 API로 뽑은 결과를 data/watchlists/에 남긴다."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from core.models import Market, WatchItem


def merge_extra(items: list[WatchItem], extra_symbols: list[str]) -> list[WatchItem]:
    have = {w.symbol for w in items}
    return items + [WatchItem(s, "", float("nan"), float("nan")) for s in extra_symbols if s not in have]


def save_watchlist(root: Path, market: Market, day: date, items: list[WatchItem]) -> Path:
    p = root / "watchlists" / market.value / f"{day.isoformat()}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([asdict(w) for w in items], ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def load_watchlist(root: Path, market: Market, day: date) -> list[WatchItem]:
    p = root / "watchlists" / market.value / f"{day.isoformat()}.json"
    return [WatchItem(**d) for d in json.loads(p.read_text(encoding="utf-8"))]


def latest_watchlist(root: Path, market: Market, before: date) -> tuple[date, list[WatchItem]] | None:
    """before 이전(포함)에 저장된 가장 최근 감시목록."""
    d = root / "watchlists" / market.value
    days = sorted(date.fromisoformat(p.stem) for p in d.glob("*.json") if date.fromisoformat(p.stem) <= before)
    if not days:
        return None
    return days[-1], load_watchlist(root, market, days[-1])
