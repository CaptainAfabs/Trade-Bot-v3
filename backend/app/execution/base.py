"""Pluggable execution interface. v1 only ships ManualAdapter (no real orders).
Adding IBKR later: subclass ExecutionAdapter, implement the three methods, register
in the factory below. The rest of the system never sees the broker."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass
class Order:
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float
    order_type: Literal["market", "limit"] = "market"
    limit_price: float | None = None


@dataclass
class OrderResult:
    accepted: bool
    broker_order_id: str | None
    message: str


class ExecutionAdapter(ABC):
    name: str

    @abstractmethod
    async def submit(self, order: Order) -> OrderResult: ...

    @abstractmethod
    async def positions(self) -> list[dict]: ...

    @abstractmethod
    async def cash_balance(self) -> float: ...
