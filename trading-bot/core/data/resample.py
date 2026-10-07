"""1분봉 → N분봉. 구간은 장 시작 시각 기준 [시작, 시작+N분), 라벨은 구간 시작 시각.

KIS 1분봉의 시각은 해당 1분 구간의 시작으로 본다 (예: 09:00 봉 = 09:00:00~09:00:59).
"""

from __future__ import annotations

from datetime import datetime, time

import pandas as pd

from core.models import CANDLE_COLUMNS

_AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}


def resample_minutes(df: pd.DataFrame, minutes: int, session_open: time) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    if df.index.tz is None:
        raise ValueError("timezone-naive 분봉")
    tz = df.index.tz
    parts = []
    for day, part in df.groupby(df.index.date):
        origin = pd.Timestamp(datetime.combine(day, session_open)).tz_localize(tz)
        r = part.resample(f"{minutes}min", origin=origin, label="left", closed="left").agg(_AGG)
        parts.append(r.dropna(subset=["open"]))
    out = pd.concat(parts)[CANDLE_COLUMNS]
    out.index.name = "ts"
    return out
