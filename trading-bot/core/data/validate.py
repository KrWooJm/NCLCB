"""수집한 1분봉 정리·검증. 문제는 고칠 수 있으면 고치고, 전부 문자열로 보고한다."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from core.config import SessionConfig


def clean_minutes(df: pd.DataFrame, day: date, session: SessionConfig) -> tuple[pd.DataFrame, list[str]]:
    issues: list[str] = []
    if df.empty:
        return df, issues
    if df.index.tz is None:
        raise ValueError("timezone-naive 분봉")

    dup = df.index.duplicated(keep="last")
    if dup.any():
        issues.append(f"중복 시각 {int(dup.sum())}건 제거")
        df = df[~dup]

    wrong_day = df.index.date != day
    t = df.index.time
    outside = (t < session.open) | (t > session.close)
    drop = wrong_day | outside
    if drop.any():
        issues.append(f"정규장·해당일 밖 {int(drop.sum())}건 제거")
        df = df[~drop]

    df = df.sort_index()
    bad_price = (df[["open", "high", "low", "close"]] <= 0).any(axis=1) | df[["open", "high", "low", "close"]].isna().any(axis=1)
    if bad_price.any():
        issues.append(f"가격 0 이하·누락 {int(bad_price.sum())}건")
    bad_ohlc = (df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1))
    if bad_ohlc.any():
        issues.append(f"OHLC 순서 오류 {int(bad_ohlc.sum())}건")
    if (df["volume"] < 0).any():
        issues.append(f"음수 거래량 {int((df['volume'] < 0).sum())}건")

    tz = df.index.tz
    session_minutes = (datetime.combine(day, session.close, tz) - datetime.combine(day, session.open, tz)).seconds // 60
    if len(df) < session_minutes * 0.5:
        issues.append(f"분봉 {len(df)}개 — 정규장 {session_minutes}분의 절반 미만 (일부만 받았을 수 있음)")
    return df, issues
