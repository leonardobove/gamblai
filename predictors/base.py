from abc import ABC, abstractmethod
from models.market import Market
from models.prediction import Prediction
from models.research import ResearchReport


class BasePredictor(ABC):
    @abstractmethod
    def predict(self, market: Market, research: ResearchReport) -> Prediction:
        """Return a probability prediction for the market resolving YES."""
        ...
