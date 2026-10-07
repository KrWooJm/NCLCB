"""1분봉 Parquet 저장소.

data/candles/{market}/1m/{symbol}/{YYYY-MM-DD}.parquet
같은 날을 다시 받으면 덮어쓴다. 데이터가 없던 날(휴장·거래정지·제공 범위 밖)은
{YYYY-MM-DD}.empty 표시 파일을 남겨 매번 다시 조회하지 않게 한다.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd

from core.models import CANDLE_COLUMNS, Market


class CandleStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _dir(self, market: Market, symbol: str) -> Path:
        safe = symbol.replace(":", "_").replace("/", "_")
        return self.root / "candles" / market.value / "1m" / safe

    def path(self, market: Market, symbol: str, day: date) -> Path:
        return self._dir(market, symbol) / f"{day.isoformat()}.parquet"

    def _empty_marker(self, market: Market, symbol: str, day: date) -> Path:
        return self._dir(market, symbol) / f"{day.isoformat()}.empty"

    def has(self, market: Market, symbol: str, day: date) -> bool:
        return self.path(market, symbol, day).exists() or self._empty_marker(market, symbol, day).exists()

    def write(self, market: Market, symbol: str, day: date, df: pd.DataFrame) -> Path:
        if df.index.tz is None:
            raise ValueError("timezone-naive 인덱스는 저장하지 않습니다")
        if list(df.columns) != CANDLE_COLUMNS:
            raise ValueError(f"컬럼은 {CANDLE_COLUMNS} 이어야 합니다: {list(df.columns)}")
        p = self.path(market, symbol, day)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".parquet.tmp")
        df.to_parquet(tmp)
        os.replace(tmp, p)  # 중간에 끊겨도 반쯤 쓴 파일이 남지 않게
        self._empty_marker(market, symbol, day).unlink(missing_ok=True)
        return p

    def mark_empty(self, market: Market, symbol: str, day: date) -> None:
        m = self._empty_marker(market, symbol, day)
        m.parent.mkdir(parents=True, exist_ok=True)
        m.touch()

    def read(self, market: Market, symbol: str, start: date, end: date) -> pd.DataFrame:
        """start~end(포함) 날짜의 1분봉을 이어 붙인다."""
        frames = [
            pd.read_parquet(p)
            for p in sorted(self._dir(market, symbol).glob("*.parquet"))
            if start <= date.fromisoformat(p.stem) <= end
        ]
        if not frames:
            return pd.DataFrame(columns=CANDLE_COLUMNS)
        return pd.concat(frames).sort_index()
