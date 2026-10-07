from datetime import time

import pytest
from pydantic import ValidationError

from core.config import load_app_config, load_secrets, load_strategy


def test_strategy_yaml_loads_documented_values():
    s = load_strategy()

    kr, us = s.markets.domestic, s.markets.us
    assert kr.timezone == "Asia/Seoul" and us.timezone == "America/New_York"
    assert kr.capital == 1_000_000 and us.capital == 1_000_000
    assert (kr.entry_window.start, kr.entry_window.end) == (time(9, 15), time(11, 0))
    assert (us.entry_window.start, us.entry_window.end) == (time(9, 45), time(11, 30))
    assert (kr.session.open, kr.session.close) == (time(9, 0), time(15, 20))
    assert (kr.data_session.open, kr.data_session.close) == (time(8, 0), time(20, 0))
    assert kr.max_price_vs_limit_up == 0.9 and us.max_price_vs_limit_up is None
    assert kr.universe.watchlist_size == 30 and us.universe.watchlist_size == 20
    assert kr.costs.slippage_rate == 0.001 and us.costs.slippage_rate == 0.001

    assert s.entry.bar_minutes == 5
    assert s.entry.opening_range_minutes == 15
    assert s.entry.relative_volume.multiplier == 2.0
    assert (s.entry.gap.min, s.entry.gap.max) == (0.0, 0.08)

    assert s.exit.stop_loss_pct == 0.02
    assert s.exit.take_profit_1.pct == 0.03 and s.exit.take_profit_1.fraction == 0.5
    assert s.exit.take_profit_2.pct == 0.05
    assert s.exit.flatten_before_close_minutes == 15
    assert s.exit.max_holding_days == 3

    assert s.sizing.risk_per_trade == 0.01
    assert s.sizing.max_position_fraction == 0.5
    assert s.sizing.min_qty == 2

    assert s.risk.max_drawdown == 0.10
    assert s.risk.daily_loss_limit == 0.03
    assert s.risk.max_consecutive_stop_losses == 4
    assert s.risk.max_positions == 2


def test_missing_field_fails(strategy_dict, write_yaml):
    del strategy_dict["risk"]["max_drawdown"]
    with pytest.raises(ValidationError, match="max_drawdown"):
        load_strategy(write_yaml(strategy_dict))


def test_unknown_field_fails(strategy_dict, write_yaml):
    strategy_dict["sizing"]["risk_per_trad"] = 0.01  # 오타
    with pytest.raises(ValidationError, match="risk_per_trad"):
        load_strategy(write_yaml(strategy_dict))


@pytest.mark.parametrize(
    "section, key, value",
    [
        (("risk",), "max_drawdown", 1.5),
        (("sizing",), "min_qty", 0),
        (("exit", "take_profit_2"), "pct", 0.01),  # 1차 익절보다 낮음
        (("entry", "gap"), "max", -0.01),  # min보다 작음
        (("markets", "us"), "timezone", "Mars/Olympus"),
        (("markets", "domestic"), "max_price_vs_limit_up", 1.5),
        (("markets", "domestic", "entry_window"), "end", "09:00"),  # start보다 앞
        (("markets", "domestic", "data_session"), "close", "15:00"),  # session(15:20)을 포함하지 않음
        (("markets", "domestic", "entry_window"), "end", "15:30"),  # session 밖
    ],
)
def test_invalid_values_fail(strategy_dict, write_yaml, section, key, value):
    node = strategy_dict
    for k in section:
        node = node[k]
    node[key] = value
    with pytest.raises(ValidationError):
        load_strategy(write_yaml(strategy_dict))


def test_app_yaml_defaults_to_notify():
    assert load_app_config().executor == "notify"


def test_secrets_are_not_exposed_in_repr(tmp_path, monkeypatch):
    monkeypatch.delenv("KIS_QUOTE_APP_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("KIS_QUOTE_APP_KEY=super-secret-key-123\n", encoding="utf-8")
    secrets = load_secrets(env)
    assert secrets.kis_quote_app_key.get_secret_value() == "super-secret-key-123"
    assert "super-secret-key-123" not in repr(secrets)
    assert secrets.values() == ["super-secret-key-123"]


def test_app_yaml_collect_settings():
    app = load_app_config()
    assert app.collect.domestic.candidates <= 30
    assert set(app.collect.us.exchanges) <= {"NAS", "NYS", "AMS"}
    assert app.data_dir.is_absolute()


@pytest.mark.parametrize("field, value", [("extra_symbols", ["AAPL"]), ("symbols", ["NASDAQ:AAPL"])])
def test_us_symbols_need_exchange(app_dict, write_yaml, field, value):
    app_dict["collect"]["us"][field] = value
    with pytest.raises(ValidationError, match="거래소:티커"):
        load_app_config(write_yaml(app_dict))


def test_us_list_mode_needs_symbols(app_dict, write_yaml):
    app_dict["collect"]["us"]["use_ranking"] = False
    app_dict["collect"]["us"]["symbols"] = []
    with pytest.raises(ValidationError, match="symbols"):
        load_app_config(write_yaml(app_dict))


def test_default_us_watchlist_is_symbol_list():
    us = load_app_config().collect.us
    assert us.use_ranking is False and len(us.symbols) > 0
