"""수집한 1분봉 정리·검증. 문제는 고칠 수 있으면 고치고, 전부 문자열로 보고한다."""

from __future__ import annotations

from datetime import date, datetime

import logging

import pandas as pd

from core.config import SessionConfig

logger = logging.getLogger(__name__)


def clean_minutes(
    df: pd.DataFrame, day: date, keep: SessionConfig, core: SessionConfig
) -> tuple[pd.DataFrame, list[str]]:
    """keep(수집 범위) 밖의 봉은 버리고, core(전략 시간)에 봉이 절반도 없으면 경고한다.

    NXT에서 거래되지 않는 종목은 08:00~09:00, 15:30~20:00 봉이 원래 없으므로 core 기준으로만 센다.
    """
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
    outside = (t < keep.open) | (t > keep.close)
    drop = wrong_day | outside
    if drop.any():
        # 미국 분봉 API는 프리·애프터마켓과 앞뒤 날짜 봉도 함께 주므로 정상 동작 — 경고로 세지 않는다
        logger.debug("%s: 수집 시간·해당일 밖 %d건 제거", day, int(drop.sum()))
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
    core_minutes = (datetime.combine(day, core.close, tz) - datetime.combine(day, core.open, tz)).seconds // 60
    t = df.index.time
    in_core = int(((t >= core.open) & (t < core.close)).sum())
    if in_core < core_minutes * 0.5:
        issues.append(f"전략 시간 분봉 {in_core}개 — {core_minutes}분의 절반 미만 (일부만 받았을 수 있음)")
    return df, issues
