"""Historical base rates by category. Used by the Bayesian predictor as an anchor."""

BASE_RATES: dict[str, dict[str, float]] = {
    "politics": {
        "default": 0.45,
        "incumbent_wins": 0.62,
        "bill_passes": 0.35,
        "resignation": 0.15,
        "rate_hike": 0.40,
        "trade_deal": 0.38,
    },
    "weather": {
        "default": 0.50,
        "above_average_rainfall": 0.50,
        "hurricane_category3": 0.60,
        "temperature_record": 0.20,
        "heavy_snowfall": 0.30,
    },
    "sports": {
        "default": 0.50,
        "favorite_wins": 0.58,
        "underdog_wins": 0.30,
        "player_scores": 0.45,
        "team_qualifies": 0.50,
        "record_broken": 0.18,
    },
    "crypto": {
        "default": 0.45,
        "btc_above_target": 0.42,
        "eth_outperforms": 0.40,
        "market_cap_target": 0.38,
        "exchange_listing": 0.35,
        "etf_inflows": 0.40,
    },
    "entertainment": {
        "default": 0.50,
        "box_office_hit": 0.45,
        "award_win": 0.33,
        "renewal": 0.55,
        "tour_announced": 0.38,
    },
}


def get_base_rate(category: str, sub_type: str = "default") -> float:
    cat_rates = BASE_RATES.get(category, {})
    return cat_rates.get(sub_type, cat_rates.get("default", 0.50))
