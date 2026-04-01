from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class TradeAction(str, Enum):
    BUY_YES = "buy_yes"
    BUY_NO = "buy_no"
    SKIP = "skip"


class Trade(BaseModel):
    model_config = {"frozen": True}

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    market_id: str
    action: TradeAction
    entry_price: float
    position_size: float  # Dollar amount wagered
    predicted_probability: float
    edge: float
    kelly_fraction: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    pnl: float | None = None
    failure_category: str | None = None  # bad_prediction, bad_timing, bad_execution, external_shock

    def resolve(self, outcome: bool) -> "Trade":
        if self.action == TradeAction.BUY_YES:
            pnl = self.position_size * (1 / self.entry_price - 1) if outcome else -self.position_size
        else:  # BUY_NO
            pnl = self.position_size * (1 / (1 - self.entry_price) - 1) if not outcome else -self.position_size
        return self.model_copy(update={"resolved": True, "pnl": round(pnl, 4)})
