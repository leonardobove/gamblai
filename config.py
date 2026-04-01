from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    tavily_api_key: str = Field(default="", env="TAVILY_API_KEY")

    mirofish_enabled: bool = Field(default=False, env="MIROFISH_ENABLED")
    mirofish_url: str = Field(default="http://localhost:5001", env="MIROFISH_URL")
    mirofish_timeout: float = Field(default=30.0, env="MIROFISH_TIMEOUT")

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
