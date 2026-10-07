"""Broker 인터페이스. 전략 엔진·리스크 가드는 이것만 사용한다.

증권사별 코드는 구현체(kis_domestic.py, kis_overseas.py — 2단계) 안에만 둔다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

import pandas as pd

from core.models import Balance, OrderId, OrderSide, OrderType, Position, Quote


@runtime_checkable
class Broker(Protocol):
    def get_candles(
        self, symbol: str, interval: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """OHLCV. index는 timezone-aware DatetimeIndex."""
        ...

    def get_quote(self, symbol: str) -> Quote: ...

    def get_balance(self) -> Balance: ...

    def get_positions(self) -> list[Position]: ...

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: int,
        order_type: OrderType,
        price: float | None = None,
    ) -> OrderId: ...

    def cancel_order(self, order_id: OrderId) -> None: ...
