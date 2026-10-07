from datetime import datetime

import pytest

from core.broker.base import Broker
from core.config import load_app_config
from core.execution.base import Executor
from core.execution.factory import LiveExecutorNotAvailable, build_executor
from core.execution.notify import NotifyExecutor
from core.execution.paper import PaperExecutor
from core.models import Market, OrderSide, OrderType, Signal
from core.timeutil import KST


def _signal() -> Signal:
    return Signal(
        market=Market.DOMESTIC,
        symbol="005930",
        side=OrderSide.BUY,
        qty=3,
        price=70000,
        order_type=OrderType.LIMIT,
        reason="ORB breakout",
        ts=datetime(2026, 10, 7, 9, 20, tzinfo=KST),
    )


class DummyBroker:
    def get_candles(self, symbol, interval, start, end): ...
    def get_quote(self, symbol): ...
    def get_balance(self): ...
    def get_positions(self): ...
    def place_order(self, symbol, side, qty, order_type, price=None): ...
    def cancel_order(self, order_id): ...


def test_default_executor_is_notify():
    ex = build_executor(load_app_config())
    assert isinstance(ex, NotifyExecutor)
    assert isinstance(ex, Executor)


def test_live_executor_is_refused():
    app = load_app_config().model_copy(update={"executor": "live"})
    with pytest.raises(LiveExecutorNotAvailable):
        build_executor(app, broker=DummyBroker())


def test_paper_requires_broker():
    app = load_app_config().model_copy(update={"executor": "paper"})
    with pytest.raises(ValueError):
        build_executor(app)
    broker = DummyBroker()
    assert isinstance(broker, Broker)
    assert isinstance(build_executor(app, broker=broker), PaperExecutor)


def test_notify_executor_sends_formatted_signal():
    sent: list[str] = []
    NotifyExecutor(sender=sent.append).execute(_signal())
    assert len(sent) == 1
    assert "005930" in sent[0] and "BUY" in sent[0] and "x3" in sent[0] and "+09:00" in sent[0]
