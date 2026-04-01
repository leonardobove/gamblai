from datetime import datetime
from pydantic import BaseModel, Field


class Portfolio(BaseModel):
    model_config = {"frozen": True}

    bankroll: float
    total_trades: int = 0
    winning_trades: int = 0
    total_pnl: float = 0.0
    open_positions: list[str] = Field(default_factory=list)  # market_ids
    peak_bankroll: float = 0.0
    current_drawdown: float = 0.0

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    @property
    def available_capital(self) -> float:
        return self.bankroll

    def apply_trade_result(self, pnl: float, market_id: str) -> "Portfolio":
        new_bankroll = self.bankroll + pnl
        new_total = self.total_trades + 1
        new_winning = self.winning_trades + (1 if pnl > 0 else 0)
        new_total_pnl = self.total_pnl + pnl
        new_peak = max(self.peak_bankroll, new_bankroll)
        new_drawdown = (new_peak - new_bankroll) / new_peak if new_peak > 0 else 0.0
        new_positions = [p for p in self.open_positions if p != market_id]
        return self.model_copy(update={
            "bankroll": round(new_bankroll, 4),
            "total_trades": new_total,
            "winning_trades": new_winning,
            "total_pnl": round(new_total_pnl, 4),
            "open_positions": new_positions,
            "peak_bankroll": round(new_peak, 4),
            "current_drawdown": round(new_drawdown, 6),
        })

    def add_position(self, market_id: str) -> "Portfolio":
        return self.model_copy(update={"open_positions": [*self.open_positions, market_id]})


class PortfolioSnapshot(BaseModel):
    model_config = {"frozen": True}

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    bankroll: float
    open_position_count: int
    total_trades: int
    win_rate: float
    total_pnl: float
    current_drawdown: float
