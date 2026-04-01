from datetime import datetime
from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    model_config = {"frozen": True}

    title: str
    snippet: str
    source: str
    url: str
    published_at: datetime | None = None


class ResearchReport(BaseModel):
    model_config = {"frozen": True}

    market_id: str
    news_items: list[NewsItem]
    summary: str
    sentiment_score: float  # -1.0 to 1.0
    gathered_at: datetime = Field(default_factory=datetime.utcnow)
