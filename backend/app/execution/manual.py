from app.execution.base import ExecutionAdapter, Order, OrderResult


class ManualAdapter(ExecutionAdapter):
    """No-op adapter: prints what a real broker WOULD do. User executes by hand."""
    name = "manual"

    async def submit(self, order: Order) -> OrderResult:
        return OrderResult(
            accepted=True,
            broker_order_id=None,
            message=(
                f"[MANUAL] {order.side.upper()} {order.quantity} {order.ticker} "
                f"({order.order_type}{f' @ {order.limit_price}' if order.limit_price else ''}). "
                "Place this trade in your broker."
            ),
        )

    async def positions(self) -> list[dict]:
        return []

    async def cash_balance(self) -> float:
        return 0.0


def get_adapter(name: str = "manual") -> ExecutionAdapter:
    if name == "manual":
        return ManualAdapter()
    raise ValueError(f"Unknown execution adapter: {name}")
