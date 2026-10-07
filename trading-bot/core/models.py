"""코어 전반에서 쓰는 도메인 타입."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NewType

from core.timeutil import ensure_aware

OrderId = NewType("OrderId", str)


class Market(str, Enum):
    DOMESTIC = "domestic"
    US = "us"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    LIMIT = "limit"
    MARKET = "market"


@dataclass(frozen=True)
class Quote:
    symbol: str
    last: float
    bid: float
    ask: float
    ts: datetime

    def __post_init__(self) -> None:
        ensure_aware(self.ts)


@dataclass(frozen=True)
class Balance:
    currency: str
    cash: float
    equity: float  # 평가금 (현금 + 보유 평가액)


@dataclass(frozen=True)
class Position:
    symbol: str
    qty: int
    avg_price: float


@dataclass(frozen=True)
class Signal:
    market: Market
    symbol: str
    side: OrderSide
    qty: int
    price: float | None  # None이면 시장가
    order_type: OrderType
    reason: str
    ts: datetime

    def __post_init__(self) -> None:
        ensure_aware(self.ts)
        if self.qty <= 0:
            raise ValueError(f"qty는 양수여야 합니다: {self.qty}")
        if self.order_type is OrderType.LIMIT and self.price is None:
            raise ValueError("지정가 신호에는 price가 필요합니다")
