from datetime import date, datetime, time, timedelta

import pytest

from core.broker import kis_domestic, kis_overseas
from core.broker.kis_domestic import KisDomesticBroker
from core.broker.kis_overseas import KisOverseasBroker
from core.config import load_strategy
from core.timeutil import KST, NEW_YORK
from tests.kis_fake import FakeKis, make_client, ok

STRATEGY = load_strategy()
KR = STRATEGY.markets.domestic
US = STRATEGY.markets.us


def krx_minutes(day: date) -> list[datetime]:
    """KRX 정규장 1분봉 시각: 09:00~15:19 연속 + 15:30 종가 단일가."""
    t = datetime.combine(day, time(9, 0))
    out = []
    while t.time() < time(15, 20):
        out.append(t)
        t += timedelta(minutes=1)
    return out + [datetime.combine(day, time(15, 30))]


def domestic_minute_handler(days: dict[date, list[datetime]]):
    def handler(req):
        p = req.url.params
        day = datetime.strptime(p["FID_INPUT_DATE_1"], "%Y%m%d").date()
        until = datetime.combine(day, datetime.strptime(p["FID_INPUT_HOUR_1"], "%H%M%S").time())
        bars = sorted((t for t in days.get(day, []) if t <= until), reverse=True)[:120]
        return ok(
            {
                "output1": {"hts_kor_isnm": "테스트"},
                "output2": [
                    {
                        "stck_bsop_date": t.strftime("%Y%m%d"),
                        "stck_cntg_hour": t.strftime("%H%M%S"),
                        "stck_prpr": "10100",
                        "stck_oprc": "10000",
                        "stck_hgpr": "10200",
                        "stck_lwpr": "9900",
                        "cntg_vol": "150",
                        "acml_tr_pbmn": "999",
                    }
                    for t in bars
                ],
            }
        )

    return handler


def test_domestic_fetches_full_day_across_pages(tmp_path):
    day = date(2026, 10, 6)
    fake = FakeKis()
    fake.route(kis_domestic.MINUTE_PATH, domestic_minute_handler({day: krx_minutes(day)}))
    broker = KisDomesticBroker(make_client(fake, tmp_path), KR.session)

    df = broker.fetch_minutes("005930", [day])[day]

    assert len(df) == len(krx_minutes(day)) == 381
    assert df.index.is_monotonic_increasing and df.index.is_unique
    assert str(df.index.tz) == "Asia/Seoul"
    assert df.index[0] == datetime(2026, 10, 6, 9, 0, tzinfo=KST)
    assert df.iloc[0].to_dict() == {"open": 10000, "high": 10200, "low": 9900, "close": 10100, "volume": 150}
    calls = fake.api_calls(kis_domestic.MINUTE_PATH)
    assert len(calls) == 4  # 120건씩
    assert calls[0].headers["tr_id"] == "FHKST03010230"
    assert calls[0].url.params["FID_COND_MRKT_DIV_CODE"] == "J"


def test_domestic_empty_day_returns_empty_frame(tmp_path):
    fake = FakeKis()
    fake.route(kis_domestic.MINUTE_PATH, domestic_minute_handler({}))
    df = KisDomesticBroker(make_client(fake, tmp_path), KR.session).fetch_minutes("005930", [date(2026, 10, 3)])
    assert df[date(2026, 10, 3)].empty
    assert len(fake.api_calls(kis_domestic.MINUTE_PATH)) == 1


def test_domestic_get_candles_filters_range(tmp_path):
    day = date(2026, 10, 6)
    fake = FakeKis()
    fake.route(kis_domestic.MINUTE_PATH, domestic_minute_handler({day: krx_minutes(day)}))
    broker = KisDomesticBroker(make_client(fake, tmp_path), KR.session)
    df = broker.get_candles("005930", "1m", datetime(2026, 10, 6, 9, 0, tzinfo=KST), datetime(2026, 10, 6, 9, 15, tzinfo=KST))
    assert len(df) == 15
    with pytest.raises(ValueError):
        broker.get_candles("005930", "5m", datetime(2026, 10, 6, tzinfo=KST), datetime(2026, 10, 7, tzinfo=KST))


def test_domestic_rank_applies_universe_filters(tmp_path):
    rows = [
        # 코드, 이름, 가격, 상장주식수, 거래대금
        ("000001", "통과-작은대금", "50000", "10000000", "20000000000"),
        ("000002", "통과-큰대금", "30000", "10000000", "90000000000"),
        ("000003", "시총미달", "5000", "1000000", "50000000000"),  # 시총 50억
        ("000004", "대금미달", "50000", "10000000", "5000000000"),
        ("000005", "가격초과", "150000", "10000000", "90000000000"),
    ]
    fake = FakeKis()
    fake.route(
        kis_domestic.RANK_PATH,
        lambda r: ok(
            {"output": [{"mksc_shrn_iscd": c, "hts_kor_isnm": n, "stck_prpr": p, "lstn_stcn": s, "acml_tr_pbmn": t} for c, n, p, s, t in rows]}
        ),
    )
    items = KisDomesticBroker(make_client(fake, tmp_path), KR.session).rank_by_turnover(KR.universe, 30)
    assert [w.symbol for w in items] == ["000002", "000001"]
    p = fake.api_calls(kis_domestic.RANK_PATH)[0].url.params
    assert p["FID_BLNG_CLS_CODE"] == "3" and p["FID_TRGT_EXLS_CLS_CODE"] == "1111111101"
    assert (p["FID_INPUT_PRICE_1"], p["FID_INPUT_PRICE_2"]) == ("2000", "100000")


def test_brokers_require_quote_only_client(tmp_path):
    client = make_client(FakeKis(), tmp_path, quote_only=False)
    with pytest.raises(ValueError):
        KisDomesticBroker(client, KR.session)
    with pytest.raises(ValueError):
        KisOverseasBroker(client)


def test_order_methods_not_implemented(tmp_path):
    broker = KisDomesticBroker(make_client(FakeKis(), tmp_path), KR.session)
    with pytest.raises(NotImplementedError):
        broker.place_order("005930", None, 1, None)


# ---------------------------------------------------------------- overseas


def nyse_minutes(day: date) -> list[datetime]:
    t = datetime.combine(day, time(9, 30))
    out = []
    while t.time() < time(16, 0):
        out.append(t)
        t += timedelta(minutes=1)
    return out


def overseas_minute_handler(all_bars: list[datetime]):
    def handler(req):
        p = req.url.params
        if p["KEYB"]:
            until = datetime.strptime(p["KEYB"], "%Y%m%d%H%M%S")
            assert p["NEXT"] == "1"
        else:
            until = datetime.max
        bars = sorted((t for t in all_bars if t <= until), reverse=True)[:120]
        return ok(
            {
                "output1": {"rsym": "DNASAAPL", "next": "1", "more": "1"},
                "output2": [
                    {
                        "xymd": t.strftime("%Y%m%d"),
                        "xhms": t.strftime("%H%M%S"),
                        "kymd": "",
                        "khms": "",
                        "open": "10.00",
                        "high": "10.50",
                        "low": "9.90",
                        "last": "10.20",
                        "evol": "1000",
                        "eamt": "10200",
                    }
                    for t in bars
                ],
            }
        )

    return handler


def test_overseas_walks_back_until_oldest_requested_day(tmp_path):
    d1, d2, d3 = date(2026, 10, 2), date(2026, 10, 5), date(2026, 10, 6)
    fake = FakeKis()
    fake.route(kis_overseas.MINUTE_PATH, overseas_minute_handler(nyse_minutes(d1) + nyse_minutes(d2) + nyse_minutes(d3)))
    broker = KisOverseasBroker(make_client(fake, tmp_path), today=d3)

    out = broker.fetch_minutes("NAS:AAPL", [d2, d3])

    assert set(out) == {d2, d3}
    assert len(out[d2]) == len(out[d3]) == 390
    assert str(out[d3].index.tz) == "America/New_York"
    assert out[d3].index[0] == datetime(2026, 10, 6, 9, 30, tzinfo=NEW_YORK)
    calls = fake.api_calls(kis_overseas.MINUTE_PATH)
    assert calls[0].url.params["EXCD"] == "NAS" and calls[0].url.params["SYMB"] == "AAPL"
    assert calls[0].url.params["KEYB"] == ""
    # d1 데이터에 닿은 페이지에서 멈춘다 (d1 전체를 받지 않음)
    assert len(calls) <= 8


def test_overseas_requires_exchange_prefix(tmp_path):
    broker = KisOverseasBroker(make_client(FakeKis(), tmp_path), today=date(2026, 10, 6))
    with pytest.raises(ValueError):
        broker.fetch_minutes("AAPL", [date(2026, 10, 6)])


def test_overseas_rank_merges_exchanges(tmp_path):
    data = {
        "NAS": [("AAPL", "50", "900"), ("CHEAP", "2", "999999")],
        "NYS": [("F", "12", "500"), ("AAPL", "50", "1")],
    }
    fake = FakeKis()
    fake.route(
        kis_overseas.RANK_PATH,
        lambda r: ok({"output1": {}, "output2": [{"symb": s, "name": s, "last": p, "tamt": t} for s, p, t in data[r.url.params["EXCD"]]]}),
    )
    items = KisOverseasBroker(make_client(fake, tmp_path), today=date(2026, 10, 6)).rank_by_turnover(US.universe, ["NAS", "NYS"], 10)
    assert [w.symbol for w in items] == ["NAS:AAPL", "NYS:F", "NYS:AAPL"]
