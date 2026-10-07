"""시간대 헬퍼. 모든 시각은 timezone-aware로 다룬다."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, tzinfo
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


def last_completed_session(now_: datetime, tz: tzinfo, close: time, grace: timedelta) -> date:
    """now_ 시점에 마감(+grace)까지 끝난 가장 최근 평일 거래일. 공휴일은 알지 못한다."""
    local = to_tz(now_, tz)
    d = local.date()
    if local.weekday() >= 5 or local < datetime.combine(d, close, tz) + grace:
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def recent_weekdays(end: date, n: int) -> list[date]:
    """end를 포함해 거슬러 올라간 평일 n개 (오래된 순)."""
    out: list[date] = []
    d = end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return out[::-1]


def weekdays_between(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out
