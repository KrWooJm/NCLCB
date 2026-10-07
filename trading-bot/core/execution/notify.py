"""NotifyExecutor: 주문 없이 신호만 알린다 (기본값).

텔레그램 전송은 5단계에서 sender로 주입한다. 지금은 로그로만 남긴다.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from core.models import Signal

logger = logging.getLogger(__name__)


def format_signal(signal: Signal) -> str:
    price = "시장가" if signal.price is None else f"{signal.price:,}"
    return (
        f"[{signal.market.value}] {signal.side.value.upper()} {signal.symbol} "
        f"x{signal.qty} @ {price} ({signal.reason}) {signal.ts.isoformat()}"
    )


class NotifyExecutor:
    def __init__(self, sender: Callable[[str], None] | None = None) -> None:
        self._send = sender or logger.info

    def execute(self, signal: Signal) -> None:
        self._send(format_signal(signal))
