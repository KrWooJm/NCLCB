import httpx
import pytest

from core.broker.kis_client import KisApiError, QuoteOnlyViolation
from tests.kis_fake import FakeKis, fail, make_client, ok

QUOTE = "/uapi/domestic-stock/v1/quotations/inquire-price"
ORDER = "/uapi/domestic-stock/v1/trading/order-cash"


def test_token_is_issued_once_and_cached_across_clients(tmp_path):
    fake = FakeKis()
    fake.route(QUOTE, lambda r: ok({"output": {}}))
    c1 = make_client(fake, tmp_path)
    c1.get(QUOTE, "TR", {})
    c1.get(QUOTE, "TR", {})
    make_client(fake, tmp_path).get(QUOTE, "TR", {})  # 새 프로세스라고 가정
    assert fake.token_count == 1
    assert fake.api_calls(QUOTE)[0].headers["authorization"] == "Bearer tok1"
    assert fake.api_calls(QUOTE)[0].headers["tr_id"] == "TR"


def test_cached_token_near_expiry_is_reissued(tmp_path):
    fake = FakeKis()
    fake.route(QUOTE, lambda r: ok({}))
    fake.token_expires = "2026-10-07 16:05:00"  # now(16:00) + 5분 < 갱신 여유 10분
    make_client(fake, tmp_path).get(QUOTE, "TR", {})
    make_client(fake, tmp_path).get(QUOTE, "TR", {})
    assert fake.token_count >= 2


def test_token_file_does_not_contain_app_secret(tmp_path):
    fake = FakeKis()
    fake.route(QUOTE, lambda r: ok({}))
    make_client(fake, tmp_path).get(QUOTE, "TR", {})
    text = (tmp_path / "token.json").read_text()
    assert "APPKEY-TEST-1234" not in text and "APPSECRET-TEST-5678" not in text


def test_quote_only_client_refuses_order_paths(tmp_path):
    fake = FakeKis()
    with pytest.raises(QuoteOnlyViolation):
        make_client(fake, tmp_path).get(ORDER, "TTTC0802U", {})
    assert fake.calls == []  # 토큰 발급조차 하지 않는다


def test_api_error_raises(tmp_path):
    fake = FakeKis()
    fake.route(QUOTE, lambda r: fail("OPSQ0001", "잘못된 종목코드"))
    with pytest.raises(KisApiError, match="OPSQ0001"):
        make_client(fake, tmp_path).get(QUOTE, "TR", {})


def test_rate_limit_is_retried_then_succeeds(tmp_path):
    fake = FakeKis()
    responses = iter([fail("EGW00201", "초당 거래건수를 초과하였습니다.", status=500), ok({"output": 1})])
    fake.route(QUOTE, lambda r: next(responses))
    sleeps: list[float] = []
    res = make_client(fake, tmp_path, sleep=sleeps.append).get(QUOTE, "TR", {})
    assert res.body["output"] == 1
    assert sleeps  # 백오프 대기


def test_rate_limit_gives_up_after_max_retries(tmp_path):
    fake = FakeKis()
    fake.route(QUOTE, lambda r: fail("EGW00201", status=500))
    with pytest.raises(KisApiError, match="EGW00201"):
        make_client(fake, tmp_path, max_retries=2).get(QUOTE, "TR", {})
    assert len(fake.api_calls(QUOTE)) == 3


def test_expired_token_response_triggers_reissue(tmp_path):
    fake = FakeKis()
    responses = iter([fail("EGW00123", "기간이 만료된 token 입니다."), ok({})])
    fake.route(QUOTE, lambda r: next(responses))
    make_client(fake, tmp_path).get(QUOTE, "TR", {})
    assert fake.token_count == 2
    assert fake.api_calls(QUOTE)[1].headers["authorization"] == "Bearer tok2"


def test_transport_error_retried(tmp_path):
    fake = FakeKis()
    state = {"n": 0}

    def flaky(r):
        state["n"] += 1
        if state["n"] == 1:
            raise httpx.ConnectError("boom")
        return ok({})

    fake.route(QUOTE, flaky)
    make_client(fake, tmp_path).get(QUOTE, "TR", {})
    assert state["n"] == 2


def test_requests_are_spaced_by_rate_limit(tmp_path):
    fake = FakeKis()
    fake.route(QUOTE, lambda r: ok({}))
    clock = {"t": 0.0}
    sleeps: list[float] = []

    def sleep(s):
        sleeps.append(s)
        clock["t"] += s

    c = make_client(fake, tmp_path, rps=2, sleep=sleep, monotonic=lambda: clock["t"])
    for _ in range(3):
        c.get(QUOTE, "TR", {})
    # 토큰 발급 1회 + 조회 3회 = 4회 호출, 각 간격 0.5초
    assert sleeps == [0.5, 0.5, 0.5]


def test_empty_app_key_rejected(tmp_path):
    from pydantic import SecretStr

    from core.broker.kis_client import KisClient

    with pytest.raises(ValueError):
        KisClient("real", SecretStr(""), SecretStr("x"), tmp_path / "t.json", quote_only=True, requests_per_second=1, max_retries=0)
