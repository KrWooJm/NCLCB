from datetime import datetime, timedelta

import pytest

from core.models import Market, OrderSide, OrderType, Signal
from core.timeutil import KST, NEW_YORK, ensure_aware, to_tz


def test_new_york_dst_is_applied():
    winter = datetime(2026, 1, 15, 9, 30, tzinfo=NEW_YORK)
    summer = datetime(2026, 7, 15, 9, 30, tzinfo=NEW_YORK)
    assert winter.utcoffset() == timedelta(hours=-5)
    assert summer.utcoffset() == timedelta(hours=-4)
    # 미국 정규장 개장은 한국 시각으로 겨울 23:30, 여름 22:30
    assert to_tz(winter, KST).hour == 23
    assert to_tz(summer, KST).hour == 22


def test_naive_datetime_rejected():
    with pytest.raises(ValueError):
        ensure_aware(datetime(2026, 1, 1, 9, 0))


def test_signal_requires_aware_ts():
    with pytest.raises(ValueError):
        Signal(Market.DOMESTIC, "005930", OrderSide.BUY, 2, 70000, OrderType.LIMIT, "orb", datetime(2026, 1, 1))
