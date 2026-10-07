"""scripts/collect.py 전체 흐름: 순위 → 감시목록 저장 → 분봉 수집 → Parquet (가짜 KIS 서버)."""

import importlib.util
from datetime import date
from pathlib import Path

import httpx

import core.broker.kis_client as kis_client
from core.broker import kis_domestic
from core.config import load_app_config
from core.data.store import CandleStore
from core.models import Market
from tests.kis_fake import FakeKis, ok
from tests.test_kis_brokers import domestic_minute_handler, krx_minutes

ROOT = Path(__file__).resolve().parents[1]


def load_cli():
    spec = importlib.util.spec_from_file_location("collect_cli", ROOT / "scripts" / "collect.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_collect_cli_end_to_end(tmp_path, monkeypatch):
    day = date(2026, 10, 6)
    fake = FakeKis()
    fake.route(
        kis_domestic.RANK_PATH,
        lambda r: ok({"output": [{"mksc_shrn_iscd": "005930", "hts_kor_isnm": "삼성전자", "stck_prpr": "70000", "lstn_stcn": "5969782550", "acml_tr_pbmn": "900000000000"}]}),
    )
    fake.route(kis_domestic.MINUTE_PATH, domestic_minute_handler({day: krx_minutes(day)}))

    real_client = httpx.Client
    monkeypatch.setattr(kis_client.httpx, "Client", lambda **kw: real_client(base_url="https://kis.test", transport=httpx.MockTransport(fake)))
    monkeypatch.setenv("KIS_QUOTE_APP_KEY", "K-TEST")
    monkeypatch.setenv("KIS_QUOTE_APP_SECRET", "S-TEST")

    cli = load_cli()
    app = load_app_config()
    app = app.model_copy(
        update={
            "data": app.data.model_copy(update={"dir": str(tmp_path / "data"), "backfill_days": 0}),
            "log": app.log.model_copy(update={"dir": str(tmp_path / "logs")}),
        }
    )
    monkeypatch.setattr(cli, "load_app_config", lambda: app)
    monkeypatch.setattr(cli, "setup_logging", lambda *a, **k: None)

    assert cli.main(["--market", "domestic", "--date", "2026-10-06"]) == 0

    store = CandleStore(tmp_path / "data")
    df = store.read(Market.DOMESTIC, "005930", day, day)
    assert len(df) == 381
    assert (tmp_path / "data" / "watchlists" / "domestic" / "2026-10-06.json").exists()
    assert (tmp_path / "data" / ".kis_token_quote.json").exists()
    # 조회 전용 클라이언트는 시세·순위 경로만 호출했다
    assert all("/quotations/" in c.url.path or c.url.path == "/oauth2/tokenP" for c in fake.calls)
