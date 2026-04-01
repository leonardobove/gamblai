import random
from models.market import Market, MarketCategory
from research_providers.base import BaseResearchProvider

_MOCK_NEWS: dict[MarketCategory, list[dict]] = {
    MarketCategory.POLITICS: [
        {"title": "Polls show tight race ahead of vote", "snippet": "Recent surveys indicate a close contest with margins within the error range.", "source": "reuters.com", "url": "https://reuters.com/mock/1"},
        {"title": "Economic indicators strengthen incumbent's position", "snippet": "GDP growth and low unemployment may boost the ruling party's prospects.", "source": "bbc.com", "url": "https://bbc.com/mock/2"},
        {"title": "Opposition rallies energize supporters", "snippet": "Large turnout at opposition events signals growing momentum.", "source": "guardian.com", "url": "https://guardian.com/mock/3"},
    ],
    MarketCategory.WEATHER: [
        {"title": "Meteorologists forecast above-normal precipitation", "snippet": "Models consistently show wetter-than-average conditions through the period.", "source": "weather.gov", "url": "https://weather.gov/mock/1"},
        {"title": "High pressure system expected to dominate", "snippet": "A stable high-pressure ridge should keep conditions dry and warm.", "source": "accuweather.com", "url": "https://accuweather.com/mock/2"},
        {"title": "Climate data suggests trend continues", "snippet": "Historical patterns indicate a 55% probability of the current anomaly persisting.", "source": "noaa.gov", "url": "https://noaa.gov/mock/3"},
    ],
    MarketCategory.SPORTS: [
        {"title": "Team announces full squad for upcoming fixture", "snippet": "Key players return from injury, boosting the side's chances significantly.", "source": "bbc-sport.com", "url": "https://bbc-sport.com/mock/1"},
        {"title": "Injury doubts cloud selection ahead of match", "snippet": "The manager confirmed three first-team players are uncertain for selection.", "source": "sky-sports.com", "url": "https://sky-sports.com/mock/2"},
        {"title": "Historical head-to-head favors home side", "snippet": "The home team has won 7 of the last 10 encounters at this venue.", "source": "espn.com", "url": "https://espn.com/mock/3"},
    ],
    MarketCategory.CRYPTO: [
        {"title": "Institutional inflows reach monthly high", "snippet": "Bitcoin ETFs recorded their largest single-day inflows in three months.", "source": "coindesk.com", "url": "https://coindesk.com/mock/1"},
        {"title": "Market sentiment turns cautious amid macro uncertainty", "snippet": "The fear and greed index slipped to 'Fear' territory as Fed speculation mounts.", "source": "cryptonews.com", "url": "https://cryptonews.com/mock/2"},
        {"title": "On-chain metrics suggest accumulation phase", "snippet": "Whale wallets increased holdings by 12% over the past week.", "source": "glassnode.com", "url": "https://glassnode.com/mock/3"},
    ],
    MarketCategory.ENTERTAINMENT: [
        {"title": "Early tracking data looks strong for release", "snippet": "Pre-sales and audience interest point to a solid opening weekend performance.", "source": "variety.com", "url": "https://variety.com/mock/1"},
        {"title": "Critics weigh in with mixed-to-positive reviews", "snippet": "A 72% Rotten Tomatoes score suggests mainstream appeal without breakout status.", "source": "hollywoodreporter.com", "url": "https://hollywoodreporter.com/mock/2"},
        {"title": "Streaming competition may dampen theatrical turnout", "snippet": "The title faces stiff competition from major streaming releases this weekend.", "source": "deadline.com", "url": "https://deadline.com/mock/3"},
    ],
}


class MockResearchProvider(BaseResearchProvider):
    """Returns synthetic news for offline development and testing."""

    def search(self, market: Market) -> list[dict]:
        items = _MOCK_NEWS.get(market.category, [])
        # Shuffle to add variety between cycles
        shuffled = list(items)
        random.shuffle(shuffled)
        return shuffled
