from abc import ABC, abstractmethod
from models.market import Market
from models.research import ResearchReport


class BaseResearchProvider(ABC):
    @abstractmethod
    def search(self, market: Market) -> list[dict]:
        """Return a list of raw news item dicts with title, snippet, source, url."""
        ...
