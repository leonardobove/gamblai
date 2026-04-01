import random
from datetime import datetime, timedelta

from config import settings
from models.market import Market, MarketCategory

_TEMPLATES: dict[MarketCategory, list[dict]] = {
    MarketCategory.POLITICS: [
        {"question": "Will the incumbent party win the upcoming by-election in {region}?", "base_prob": 0.52},
        {"question": "Will {politician} approve the {policy} bill before {deadline}?", "base_prob": 0.45},
        {"question": "Will unemployment fall below {threshold}% by end of Q{quarter}?", "base_prob": 0.40},
        {"question": "Will the central bank raise interest rates at their next meeting?", "base_prob": 0.35},
        {"question": "Will the trade deal between {country_a} and {country_b} be signed this month?", "base_prob": 0.38},
        {"question": "Will the prime minister resign before the end of the year?", "base_prob": 0.22},
    ],
    MarketCategory.WEATHER: [
        {"question": "Will {city} experience above-average rainfall this month?", "base_prob": 0.50},
        {"question": "Will there be a Category 3+ hurricane in the Atlantic this season?", "base_prob": 0.60},
        {"question": "Will {city} break a temperature record this week?", "base_prob": 0.25},
        {"question": "Will snowfall exceed 10cm in {city} before the end of the month?", "base_prob": 0.33},
    ],
    MarketCategory.SPORTS: [
        {"question": "Will {team_a} beat {team_b} in their next match?", "base_prob": 0.55},
        {"question": "Will {player} score in their next appearance?", "base_prob": 0.45},
        {"question": "Will {team} qualify for the playoffs this season?", "base_prob": 0.48},
        {"question": "Will the underdog win the upcoming {tournament} final?", "base_prob": 0.30},
        {"question": "Will {athlete} break the world record at the upcoming championship?", "base_prob": 0.20},
    ],
    MarketCategory.CRYPTO: [
        {"question": "Will Bitcoin close above ${price}k this week?", "base_prob": 0.45},
        {"question": "Will Ethereum outperform Bitcoin over the next 30 days?", "base_prob": 0.42},
        {"question": "Will the total crypto market cap exceed ${cap}T by month end?", "base_prob": 0.40},
        {"question": "Will a major exchange list {token} before the end of Q{quarter}?", "base_prob": 0.35},
        {"question": "Will Bitcoin ETF daily inflows exceed $500M this week?", "base_prob": 0.38},
    ],
    MarketCategory.ENTERTAINMENT: [
        {"question": "Will {movie} gross over ${amount}M in its opening weekend?", "base_prob": 0.50},
        {"question": "Will {artist} announce a world tour before end of year?", "base_prob": 0.40},
        {"question": "Will {show} be renewed for another season?", "base_prob": 0.55},
        {"question": "Will {celebrity} win the award at the upcoming {ceremony}?", "base_prob": 0.35},
    ],
}

_FILLERS = {
    "region": ["Kent", "Yorkshire", "Bristol", "Birmingham", "Manchester"],
    "politician": ["the President", "the Governor", "the Chancellor", "the PM"],
    "policy": ["infrastructure", "climate", "healthcare", "education", "tax reform"],
    "deadline": ["March", "April", "June", "September"],
    "threshold": ["4.5", "5.0", "5.5", "6.0"],
    "quarter": ["1", "2", "3", "4"],
    "country_a": ["the US", "the EU", "China", "India", "Japan"],
    "country_b": ["the UK", "Canada", "Brazil", "South Korea", "Mexico"],
    "city": ["London", "New York", "Tokyo", "Sydney", "Paris", "Berlin"],
    "team_a": ["Arsenal", "Bayern", "Real Madrid", "Liverpool", "PSG"],
    "team_b": ["Chelsea", "Dortmund", "Barcelona", "Man City", "Juventus"],
    "team": ["the home side", "the favorites", "the top-seeded team"],
    "player": ["the team captain", "the leading scorer", "the MVP candidate"],
    "athlete": ["the world #1", "the defending champion", "the rising star"],
    "tournament": ["Champions League", "Grand Slam", "World Cup", "Olympics"],
    "price": ["80", "85", "90", "95", "100"],
    "cap": ["2.5", "3", "3.5", "4"],
    "token": ["a new L2 token", "a major DeFi protocol", "a privacy coin"],
    "movie": ["the anticipated sequel", "the summer blockbuster", "the indie hit"],
    "amount": ["50", "100", "200", "300"],
    "artist": ["the pop superstar", "the Grammy winner", "the comeback act"],
    "show": ["the hit drama", "the acclaimed comedy", "the documentary series"],
    "celebrity": ["the frontrunner", "the dark horse", "the veteran"],
    "ceremony": ["Oscars", "BAFTAs", "Golden Globes", "Grammy Awards"],
}


def _fill_template(question: str) -> str:
    import re
    placeholders = re.findall(r"\{(\w+)\}", question)
    for ph in placeholders:
        if ph in _FILLERS:
            question = question.replace(f"{{{ph}}}", random.choice(_FILLERS[ph]), 1)
    return question


class MarketGenerator:
    def generate(self, count: int = 3) -> list[Market]:
        markets = []
        categories = list(_TEMPLATES.keys())
        for _ in range(count):
            category = random.choice(categories)
            template = random.choice(_TEMPLATES[category])
            question = _fill_template(template["question"])
            base_prob = template["base_prob"]
            # Add market noise: ±15 percentage points
            market_price = max(0.10, min(0.90, base_prob + random.uniform(-0.15, 0.15)))

            # Fast simulation: resolve in minutes for quick testing
            if settings.fast_simulation:
                resolution_minutes = random.randint(
                    settings.fast_simulation_minutes_min,
                    settings.fast_simulation_minutes_max,
                )
                resolution_date = datetime.utcnow() + timedelta(minutes=resolution_minutes)
            else:
                resolution_days = random.randint(1, 21)
                resolution_date = datetime.utcnow() + timedelta(days=resolution_days)

            market = Market(
                question=question,
                category=category,
                market_price=round(market_price, 3),
                resolution_date=resolution_date,
                metadata={"base_prob": base_prob, "template": template["question"]},
            )
            markets.append(market)
        return markets
