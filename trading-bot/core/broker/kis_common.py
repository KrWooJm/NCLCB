"""국내·해외 KIS 구현체가 같이 쓰는 도우미."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.models import CANDLE_COLUMNS


def to_float(v: object) -> float:
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return float("nan")


def frame_from_bars(bars: dict[datetime, tuple[float, float, float, float, float]]) -> pd.DataFrame:
    """{ts: (open, high, low, close, volume)} → ts 오름차순 DataFrame (tz-aware index)."""
    if not bars:
        idx = pd.DatetimeIndex([], tz="UTC", name="ts")
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in CANDLE_COLUMNS}, index=idx)
    df = pd.DataFrame.from_dict(bars, orient="index", columns=CANDLE_COLUMNS).sort_index()
    df.index = pd.DatetimeIndex(df.index, name="ts")
    return df.astype("float64")


def unsupported(what: str, stage: int) -> NotImplementedError:
    return NotImplementedError(f"{what}는 {stage}단계에서 구현됩니다")
