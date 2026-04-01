import json
import uuid
from datetime import datetime
from typing import Optional

from db.connection import get_connection
from models.market import Market, MarketCategory
from models.trade import Trade, TradeAction
from models.portfolio import Portfolio, PortfolioSnapshot
from models.research import ResearchReport, NewsItem
from models.prediction import Prediction, PredictorSource


class MarketRepository:
    def save(self, market: Market) -> None:
        with get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO markets
                   (id, question, category, market_price, resolution_date, resolved, outcome, metadata_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    market.id,
                    market.question,
                    market.category.value,
                    market.market_price,
                    market.resolution_date.isoformat(),
                    1 if market.resolved else 0,
                    (1 if market.outcome else 0) if market.outcome is not None else None,
                    json.dumps(market.metadata),
                    market.created_at.isoformat(),
                ),
            )

    def find_by_id(self, market_id: str) -> Optional[Market]:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM markets WHERE id = ?", (market_id,)).fetchone()
        return self._row_to_market(row) if row else None

    def find_unresolved(self) -> list[Market]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM markets WHERE resolved = 0").fetchall()
        return [self._row_to_market(r) for r in rows]

    def find_expired_unresolved(self) -> list[Market]:
        now = datetime.utcnow().isoformat()
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM markets WHERE resolved = 0 AND resolution_date <= ?", (now,)
            ).fetchall()
        return [self._row_to_market(r) for r in rows]

    def _row_to_market(self, row) -> Market:
        return Market(
            id=row["id"],
            question=row["question"],
            category=MarketCategory(row["category"]),
            market_price=row["market_price"],
            resolution_date=datetime.fromisoformat(row["resolution_date"]),
            resolved=bool(row["resolved"]),
            outcome=bool(row["outcome"]) if row["outcome"] is not None else None,
            metadata=json.loads(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


class TradeRepository:
    def save(self, trade: Trade) -> None:
        with get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO trades
                   (id, market_id, action, entry_price, position_size, predicted_probability,
                    edge, kelly_fraction, timestamp, resolved, pnl, failure_category)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trade.id,
                    trade.market_id,
                    trade.action.value,
                    trade.entry_price,
                    trade.position_size,
                    trade.predicted_probability,
                    trade.edge,
                    trade.kelly_fraction,
                    trade.timestamp.isoformat(),
                    1 if trade.resolved else 0,
                    trade.pnl,
                    trade.failure_category,
                ),
            )

    def find_by_market(self, market_id: str) -> list[Trade]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM trades WHERE market_id = ?", (market_id,)).fetchall()
        return [self._row_to_trade(r) for r in rows]

    def find_open(self) -> list[Trade]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM trades WHERE resolved = 0 AND action != 'skip'").fetchall()
        return [self._row_to_trade(r) for r in rows]

    def find_resolved(self, limit: int = 100) -> list[Trade]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE resolved = 1 ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_trade(r) for r in rows]

    def find_recent_pnls(self, limit: int = 50) -> list[float]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT pnl FROM trades WHERE resolved = 1 AND pnl IS NOT NULL ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [r["pnl"] for r in rows]

    def _row_to_trade(self, row) -> Trade:
        return Trade(
            id=row["id"],
            market_id=row["market_id"],
            action=TradeAction(row["action"]),
            entry_price=row["entry_price"],
            position_size=row["position_size"],
            predicted_probability=row["predicted_probability"],
            edge=row["edge"],
            kelly_fraction=row["kelly_fraction"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            resolved=bool(row["resolved"]),
            pnl=row["pnl"],
            failure_category=row["failure_category"],
        )


class PortfolioRepository:
    def save_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO portfolio_snapshots
                   (timestamp, bankroll, open_position_count, total_trades, win_rate, total_pnl, current_drawdown)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    snapshot.timestamp.isoformat(),
                    snapshot.bankroll,
                    snapshot.open_position_count,
                    snapshot.total_trades,
                    snapshot.win_rate,
                    snapshot.total_pnl,
                    snapshot.current_drawdown,
                ),
            )

    def get_history(self, limit: int = 200) -> list[PortfolioSnapshot]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            PortfolioSnapshot(
                timestamp=datetime.fromisoformat(r["timestamp"]),
                bankroll=r["bankroll"],
                open_position_count=r["open_position_count"],
                total_trades=r["total_trades"],
                win_rate=r["win_rate"],
                total_pnl=r["total_pnl"],
                current_drawdown=r["current_drawdown"],
            )
            for r in reversed(rows)
        ]


class ResearchCacheRepository:
    def save(self, report: ResearchReport) -> None:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO research_cache (market_id, report_json, gathered_at) VALUES (?, ?, ?)",
                (report.market_id, report.model_dump_json(), report.gathered_at.isoformat()),
            )

    def find_by_market(self, market_id: str, max_age_minutes: int = 60) -> Optional[ResearchReport]:
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(minutes=max_age_minutes)).isoformat()
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM research_cache WHERE market_id = ? AND gathered_at > ?",
                (market_id, cutoff),
            ).fetchone()
        if not row:
            return None
        data = json.loads(row["report_json"])
        return ResearchReport(**data)


class KnowledgeRepository:
    def save_insight(self, category: str, insight: str, trade_id: Optional[str] = None) -> None:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO knowledge_base (category, insight, trade_id, created_at) VALUES (?, ?, ?, ?)",
                (category, insight, trade_id, datetime.utcnow().isoformat()),
            )

    def get_insights(self, category: Optional[str] = None, limit: int = 20) -> list[dict]:
        with get_connection() as conn:
            if category:
                rows = conn.execute(
                    "SELECT * FROM knowledge_base WHERE category = ? ORDER BY created_at DESC LIMIT ?",
                    (category, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM knowledge_base ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        return [dict(r) for r in rows]

    def save_calibration(self, predicted_prob: float, actual_outcome: bool, trade_id: Optional[str] = None) -> None:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO calibration_log (predicted_probability, actual_outcome, trade_id, timestamp) VALUES (?, ?, ?, ?)",
                (predicted_prob, 1 if actual_outcome else 0, trade_id, datetime.utcnow().isoformat()),
            )

    def get_calibration_data(self, limit: int = 500) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM calibration_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
