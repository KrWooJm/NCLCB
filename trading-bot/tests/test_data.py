from datetime import date, datetime, time, timedelta

import pandas as pd
import pytest

from core.broker.kis_common import frame_from_bars
from core.config import load_strategy
from core.data.collector import collect
from core.data.resample import resample_minutes
from core.data.store import CandleStore
from core.data.validate import clean_minutes
from core.data.watchlist import load_watchlist, merge_extra, save_watchlist
from core.models import Market, WatchItem
from core.timeutil import KST, NEW_YORK, last_completed_session, recent_weekdays

STRATEGY = load_strategy()
KR = STRATEGY.markets.domestic
US = STRATEGY.markets.us


def bars(day: date, start: time, n: int, tz, *, price: float = 100.0) -> pd.DataFrame:
    t0 = datetime.combine(day, start, tz)
    return frame_from_bars(
        {t0 + timedelta(minutes=i): (price + i, price + i + 1, price + i - 1, price + i + 0.5, 10.0) for i in range(n)}
    )


# ---------------------------------------------------------------- store


def test_store_roundtrip_keeps_timezone(tmp_path):
    store = CandleStore(tmp_path)
    day = date(2026, 10, 6)
    df = bars(day, time(9, 30), 5, NEW_YORK)
    store.write(Market.US, "NAS:AAPL", day, df)
    assert store.has(Market.US, "NAS:AAPL", day)
    back = store.read(Market.US, "NAS:AAPL", day, day)
    pd.testing.assert_frame_equal(back, df, check_freq=False)
    assert str(back.index.tz) == "America/New_York"


def test_store_rejects_naive_index(tmp_path):
    df = bars(date(2026, 10, 6), time(9, 0), 3, KST)
    df.index = df.index.tz_localize(None)
    with pytest.raises(ValueError):
        CandleStore(tmp_path).write(Market.DOMESTIC, "005930", date(2026, 10, 6), df)


def test_store_empty_marker_and_overwrite(tmp_path):
    store = CandleStore(tmp_path)
    day = date(2026, 10, 6)
    store.mark_empty(Market.DOMESTIC, "005930", day)
    assert store.has(Market.DOMESTIC, "005930", day)
    assert store.read(Market.DOMESTIC, "005930", day, day).empty
    store.write(Market.DOMESTIC, "005930", day, bars(day, time(9, 0), 3, KST))
    store.write(Market.DOMESTIC, "005930", day, bars(day, time(9, 0), 2, KST))  # 덮어쓰기
    assert len(store.read(Market.DOMESTIC, "005930", day, day)) == 2
    assert not list(tmp_path.rglob("*.empty")) and not list(tmp_path.rglob("*.tmp"))


# ---------------------------------------------------------------- validate


def test_clean_minutes_drops_duplicates_and_out_of_session():
    day = date(2026, 10, 6)
    df = pd.concat([bars(day, time(8, 58), 400, KST), bars(day, time(9, 0), 1, KST)])
    clean, issues = clean_minutes(df, day, KR.session)
    assert clean.index.min().time() == time(9, 0)
    assert clean.index.max().time() <= time(15, 30)
    assert clean.index.is_unique
    assert any("중복" in m for m in issues) and any("밖" in m for m in issues)


def test_clean_minutes_flags_bad_ohlc_and_partial_day():
    day = date(2026, 10, 6)
    df = bars(day, time(9, 0), 10, KST)
    df.iloc[3, df.columns.get_loc("high")] = 1.0
    _, issues = clean_minutes(df, day, KR.session)
    assert any("OHLC" in m for m in issues)
    assert any("절반 미만" in m for m in issues)


# ---------------------------------------------------------------- resample


def test_resample_to_5m_aligned_to_session_open():
    day = date(2026, 10, 6)
    df = bars(day, time(9, 30), 12, NEW_YORK)  # 09:30~09:41
    out = resample_minutes(df, 5, US.session.open)
    assert [t.strftime("%H:%M") for t in out.index] == ["09:30", "09:35", "09:40"]
    first = out.iloc[0]
    assert first["open"] == df.iloc[0]["open"]
    assert first["close"] == df.iloc[4]["close"]
    assert first["high"] == df.iloc[0:5]["high"].max()
    assert first["low"] == df.iloc[0:5]["low"].min()
    assert first["volume"] == 50
    assert out.iloc[2]["volume"] == 20  # 09:40, 09:41 두 개
    assert str(out.index.tz) == "America/New_York"


def test_resample_handles_multiple_days():
    d1, d2 = date(2026, 10, 5), date(2026, 10, 6)
    df = pd.concat([bars(d1, time(9, 0), 10, KST), bars(d2, time(9, 0), 10, KST)])
    out = resample_minutes(df, 5, KR.session.open)
    assert len(out) == 4


# ---------------------------------------------------------------- session dates


@pytest.mark.parametrize(
    "now, expected",
    [
        (datetime(2026, 10, 7, 15, 0, tzinfo=KST), date(2026, 10, 6)),  # 수 장중 → 화
        (datetime(2026, 10, 7, 15, 40, tzinfo=KST), date(2026, 10, 7)),  # 수 마감 후
        (datetime(2026, 10, 10, 12, 0, tzinfo=KST), date(2026, 10, 9)),  # 토 → 금
        (datetime(2026, 10, 12, 8, 0, tzinfo=KST), date(2026, 10, 9)),  # 월 장전 → 금
    ],
)
def test_last_completed_session_domestic(now, expected):
    assert last_completed_session(now, KST, KR.session.close, timedelta(minutes=5)) == expected


def test_last_completed_session_us_from_korean_morning():
    # 한국 수요일 06:15 = 뉴욕 화요일 17:15 (서머타임) → 화요일 세션
    now = datetime(2026, 10, 7, 6, 15, tzinfo=KST)
    assert last_completed_session(now, NEW_YORK, US.session.close, timedelta(minutes=5)) == date(2026, 10, 6)


def test_recent_weekdays_skips_weekend():
    assert recent_weekdays(date(2026, 10, 12), 3) == [date(2026, 10, 8), date(2026, 10, 9), date(2026, 10, 12)]


# ---------------------------------------------------------------- watchlist


def test_watchlist_roundtrip_and_extra(tmp_path):
    items = merge_extra([WatchItem("005930", "삼성전자", 70000, 1e12)], ["005930", "000660"])
    assert [w.symbol for w in items] == ["005930", "000660"]
    save_watchlist(tmp_path, Market.DOMESTIC, date(2026, 10, 6), items[:1])
    assert load_watchlist(tmp_path, Market.DOMESTIC, date(2026, 10, 6)) == items[:1]


# ---------------------------------------------------------------- collector


class FakeSource:
    def __init__(self, available: dict[tuple[str, date], pd.DataFrame], fail: set[str] = frozenset()):
        self.available = available
        self.fail = fail
        self.requests: list[tuple[str, list[date]]] = []

    def fetch_minutes(self, symbol, days):
        self.requests.append((symbol, list(days)))
        if symbol in self.fail:
            raise RuntimeError("down")
        return {d: self.available.get((symbol, d), frame_from_bars({})) for d in days}


def full_day(day: date) -> pd.DataFrame:
    return bars(day, time(9, 0), 381, KST)


def test_collect_saves_target_and_backfills_only_missing(tmp_path):
    store = CandleStore(tmp_path)
    target = date(2026, 10, 7)
    history = recent_weekdays(target, 4)[:-1]  # 10/2, 10/5, 10/6
    store.write(Market.DOMESTIC, "A", history[0], full_day(history[0]))  # 이미 있음
    src = FakeSource({("A", d): full_day(d) for d in history + [target]})

    s = collect(Market.DOMESTIC, target, [WatchItem("A", "", 1, 1)], src, store, KR.session, backfill_days=3)

    assert src.requests == [("A", history[1:] + [target])]
    assert s.days_saved == 3 and s.days_empty == 0 and not s.failed
    for d in history + [target]:
        assert store.path(Market.DOMESTIC, "A", d).exists()


def test_collect_marks_empty_days_and_does_not_refetch_them(tmp_path):
    store = CandleStore(tmp_path)
    target = date(2026, 10, 7)
    src = FakeSource({("A", target): full_day(target)})  # 10/6은 휴장이라고 가정
    collect(Market.DOMESTIC, target, [WatchItem("A", "", 1, 1)], src, store, KR.session, backfill_days=1)
    collect(Market.DOMESTIC, target, [WatchItem("A", "", 1, 1)], src, store, KR.session, backfill_days=1)
    assert src.requests[1] == ("A", [target])  # 표시된 빈 날은 다시 묻지 않는다


def test_collect_continues_after_symbol_failure(tmp_path):
    store = CandleStore(tmp_path)
    target = date(2026, 10, 7)
    src = FakeSource({("B", target): full_day(target)}, fail={"A"})
    s = collect(Market.DOMESTIC, target, [WatchItem("A", "", 1, 1), WatchItem("B", "", 1, 1)], src, store, KR.session, backfill_days=0)
    assert s.failed == ["A"] and s.days_saved == 1


def test_collect_dry_run_writes_nothing(tmp_path):
    target = date(2026, 10, 7)
    src = FakeSource({("A", target): full_day(target)})
    s = collect(Market.DOMESTIC, target, [WatchItem("A", "", 1, 1)], src, CandleStore(tmp_path), KR.session, backfill_days=2, dry_run=True)
    assert s.days_saved == 1 and s.days_empty == 2
    assert not any(tmp_path.rglob("*"))
