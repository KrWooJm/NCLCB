"""시간대 헬퍼. 모든 시각은 timezone-aware로 다룬다."""

from __future__ import annotations

from datetime import datetime, tzinfo
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
NEW_YORK = ZoneInfo("America/New_York")  # 서머타임은 zoneinfo가 자동 반영


def ensure_aware(dt: datetime) -> datetime:
    """naive datetime이면 예외. 시간대 추정은 하지 않는다."""
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"timezone-naive datetime은 허용되지 않습니다: {dt!r}")
    return dt


def now(tz: tzinfo) -> datetime:
    return datetime.now(tz)


def to_tz(dt: datetime, tz: tzinfo) -> datetime:
    return ensure_aware(dt).astimezone(tz)
