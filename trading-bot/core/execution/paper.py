"""PaperExecutor: 모의투자 계좌 주문. 6단계에서 구현한다."""

from __future__ import annotations

from core.broker.base import Broker
from core.models import Signal


class PaperExecutor:
    def __init__(self, broker: Broker) -> None:
        self._broker = broker

    def execute(self, signal: Signal) -> None:
        raise NotImplementedError("PaperExecutor는 6단계에서 구현됩니다")
