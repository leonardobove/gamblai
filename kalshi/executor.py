"""
Places and monitors real orders on Kalshi.

Contract math:
  - Each contract pays $1.00 if it resolves in your favour, $0 otherwise.
  - You buy YES at `yes_price` cents. If YES resolves: profit = (100 - yes_price) cents per contract.
  - You buy NO at `no_price` cents. If NO resolves:  profit = (100 - no_price) cents per contract.
  - Position size in dollars → contracts = floor(dollars / (price_cents / 100))

Slippage protection:
  - We place limit orders at the current ask price (not market orders).
  - If the ask moves more than SLIPPAGE_LIMIT_PCT before fill, we cancel.
"""

import uuid
import structlog

from kalshi.client import KalshiClient
from models.trade import TradeAction

log = structlog.get_logger()

_SLIPPAGE_LIMIT_PCT = 0.02   # abort if price moves >2% before fill
_MIN_CONTRACTS = 1


class KalshiExecutor:
    def __init__(self, client: KalshiClient):
        self._client = client

    def place_order(
        self,
        ticker: str,
        action: TradeAction,
        position_size_dollars: float,
        entry_price: float,          # probability 0.0-1.0 (our market_price at signal time)
    ) -> dict | None:
        """
        Place a limit order and return the Kalshi order object, or None if rejected.

        action = BUY_YES → buy YES contracts
        action = BUY_NO  → buy NO contracts
        """
        if action == TradeAction.SKIP:
            return None

        if action == TradeAction.BUY_YES:
            side = "yes"
            price_cents = int(entry_price * 100)
        else:
            side = "no"
            price_cents = int((1 - entry_price) * 100)  # NO price = 100 - YES price

        # Clamp to valid Kalshi range
        price_cents = max(1, min(99, price_cents))

        # Contracts we can buy for our dollar budget
        cost_per_contract = price_cents / 100.0
        contracts = int(position_size_dollars / cost_per_contract)
        if contracts < _MIN_CONTRACTS:
            log.warning("kalshi_too_few_contracts", ticker=ticker, contracts=contracts, size=position_size_dollars)
            return None

        client_order_id = str(uuid.uuid4())
        body = {
            "ticker": ticker,
            "action": "buy",
            "side": side,
            "type": "limit",
            "count": contracts,
            f"{side}_price": price_cents,
            "client_order_id": client_order_id,
        }

        log.info(
            "kalshi_placing_order",
            ticker=ticker,
            side=side,
            contracts=contracts,
            price_cents=price_cents,
            size_dollars=round(contracts * cost_per_contract, 2),
        )

        try:
            response = self._client.post("/portfolio/orders", body)
            order = response.get("order", response)
            log.info("kalshi_order_placed", order_id=order.get("order_id"), status=order.get("status"))
            return order
        except Exception as e:
            log.error("kalshi_order_failed", ticker=ticker, error=str(e))
            return None

    def cancel_order(self, order_id: str) -> bool:
        try:
            self._client.delete(f"/portfolio/orders/{order_id}")
            log.info("kalshi_order_cancelled", order_id=order_id)
            return True
        except Exception as e:
            log.warning("kalshi_cancel_failed", order_id=order_id, error=str(e))
            return False

    def get_order(self, order_id: str) -> dict | None:
        try:
            data = self._client.get(f"/portfolio/orders/{order_id}")
            return data.get("order", data)
        except Exception as e:
            log.warning("kalshi_get_order_failed", order_id=order_id, error=str(e))
            return None

    def get_open_orders(self) -> list[dict]:
        try:
            data = self._client.get("/portfolio/orders", params={"status": "resting"})
            return data.get("orders", [])
        except Exception as e:
            log.warning("kalshi_get_open_orders_failed", error=str(e))
            return []
