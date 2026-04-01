from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class MarketCategory(str, Enum):
    POLITICS = "politics"
    WEATHER = "weather"
    SPORTS = "sports"
    CRYPTO = "crypto"
    ENTERTAINMENT = "entertainment"


class Market(BaseModel):
    model_config = {"frozen": True}

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    category: MarketCategory
    market_price: float  # Implied probability 0.0-1.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolution_date: datetime
    resolved: bool = False
    outcome: bool | None = None
    metadata: dict = Field(default_factory=dict)

    def with_price(self, new_price: float) -> "Market":
        return self.model_copy(update={"market_price": new_price})

    def resolve(self, outcome: bool) -> "Market":
        return self.model_copy(update={"resolved": True, "outcome": outcome})
