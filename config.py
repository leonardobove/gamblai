import atexit
import tempfile
import os
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


# Keys configurable via the Settings page (DB overrides .env for these)
CONFIGURABLE_KEYS: list[dict] = [
    {"key": "anthropic_api_key",   "label": "Anthropic API Key",            "is_secret": True},
    {"key": "tavily_api_key",      "label": "Tavily API Key (optional)",     "is_secret": True},
    {"key": "kalshi_api_key_id",   "label": "Kalshi API Key ID",             "is_secret": True},
    {"key": "kalshi_private_key",  "label": "Kalshi Private Key (PEM text)", "is_secret": True, "multiline": True},
    {"key": "kalshi_enabled",      "label": "Kalshi Enabled",                "is_secret": False, "type": "bool"},
    {"key": "kalshi_execute_trades","label": "Kalshi Execute Trades",        "is_secret": False, "type": "bool"},
]

_kalshi_pem_tmpfile: Optional[str] = None


class Settings(BaseSettings):
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    tavily_api_key: str = Field(default="", env="TAVILY_API_KEY")

    mirofish_enabled: bool = Field(default=False, env="MIROFISH_ENABLED")
    mirofish_url: str = Field(default="http://localhost:5001", env="MIROFISH_URL")
    mirofish_timeout: float = Field(default=30.0, env="MIROFISH_TIMEOUT")

    # Kalshi integration (optional — leave blank to use simulation mode)
    kalshi_enabled: bool = Field(default=False, env="KALSHI_ENABLED")
    kalshi_demo: bool = Field(default=True, env="KALSHI_DEMO")  # True = demo, False = live
    kalshi_api_key_id: str = Field(default="", env="KALSHI_API_KEY_ID")
    kalshi_private_key_path: str = Field(default="kalshi_private.pem", env="KALSHI_PRIVATE_KEY_PATH")
    kalshi_execute_trades: bool = Field(default=False, env="KALSHI_EXECUTE_TRADES")  # extra safety gate

    starting_bankroll: float = Field(default=10000.0, env="STARTING_BANKROLL")
    edge_threshold: float = Field(default=0.04, env="EDGE_THRESHOLD")
    kelly_fraction: float = Field(default=0.25, env="KELLY_FRACTION")
    max_position_pct: float = Field(default=0.05, env="MAX_POSITION_PCT")
    max_drawdown_pct: float = Field(default=0.08, env="MAX_DRAWDOWN_PCT")
    max_concurrent_positions: int = Field(default=15, env="MAX_CONCURRENT_POSITIONS")
    min_var_trades: int = Field(default=20, env="MIN_VAR_TRADES")

    claude_model: str = Field(default="claude-sonnet-4-6", env="CLAUDE_MODEL")
    db_path: str = Field(default="data/gamblai.db", env="DB_PATH")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    markets_per_cycle: int = Field(default=3, env="MARKETS_PER_CYCLE")
    research_cache_minutes: int = Field(default=60, env="RESEARCH_CACHE_MINUTES")

    # Fast simulation: markets resolve in minutes instead of days (great for testing)
    fast_simulation: bool = Field(default=False, env="FAST_SIMULATION")
    fast_simulation_minutes_min: int = Field(default=2, env="FAST_SIM_MINUTES_MIN")
    fast_simulation_minutes_max: int = Field(default=10, env="FAST_SIM_MINUTES_MAX")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "env_ignore_empty": True,  # .env values win over empty OS env vars (e.g. set by Claude Code)
    }


settings = Settings()


def get_setting(key: str) -> str:
    """Return the value for a setting, preferring the DB over .env / env vars."""
    try:
        from db.repositories import SettingsRepository
        db_val = SettingsRepository().get(key)
        if db_val is not None and db_val.strip():
            return db_val
    except Exception:
        pass
    return str(getattr(settings, key, "") or "")


def get_bool_setting(key: str) -> bool:
    """Return a boolean setting, preferring the DB over .env / env vars."""
    val = get_setting(key)
    if val.lower() in ("true", "1", "yes"):
        return True
    if val.lower() in ("false", "0", "no"):
        return False
    return bool(getattr(settings, key, False))


def get_kalshi_private_key_path() -> str:
    """Return path to Kalshi private key PEM file.

    If the PEM *content* was saved via the Settings page it is written to a
    temporary file (created once per process).  Otherwise fall back to the
    file path from .env / env vars.
    """
    global _kalshi_pem_tmpfile

    pem_content = get_setting("kalshi_private_key")
    if pem_content and "BEGIN" in pem_content:
        if _kalshi_pem_tmpfile and os.path.exists(_kalshi_pem_tmpfile):
            return _kalshi_pem_tmpfile
        tmp = tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="w")
        tmp.write(pem_content)
        tmp.close()
        _kalshi_pem_tmpfile = tmp.name
        atexit.register(lambda: os.unlink(_kalshi_pem_tmpfile) if os.path.exists(_kalshi_pem_tmpfile) else None)
        return _kalshi_pem_tmpfile

    return settings.kalshi_private_key_path
