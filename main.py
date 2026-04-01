"""
GamblAI — AI Prediction Market Trading Simulator
Usage:
  python main.py init              Initialize the database
  python main.py run               Run a single pipeline cycle
  python main.py loop [--interval] Run pipeline continuously
  python main.py dashboard         Start the web dashboard
  python main.py status            Print portfolio summary
  python main.py resolve           Force-resolve all expired markets
"""

import argparse
import sys
import time
import structlog
import logging

from config import settings

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
log = structlog.get_logger()


def cmd_init():
    from db.connection import init_db
    init_db()
    print("Database initialized at", settings.db_path)


def cmd_run():
    from db.connection import init_db
    from pipeline.runner import PipelineRunner
    init_db()
    runner = PipelineRunner()
    portfolio = runner.run_cycle()
    _print_portfolio(portfolio)


def cmd_loop(interval: int):
    from db.connection import init_db
    from pipeline.runner import PipelineRunner
    init_db()
    runner = PipelineRunner()
    print(f"Starting continuous loop (interval: {interval}s). Press Ctrl+C to stop.")
    cycle = 0
    while True:
        cycle += 1
        print(f"\n--- Cycle {cycle} ---")
        try:
            portfolio = runner.run_cycle()
            _print_portfolio(portfolio)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            log.error("cycle_failed", error=str(e))
        time.sleep(interval)


def cmd_dashboard(host: str, port: int):
    import uvicorn
    from db.connection import init_db
    init_db()
    print(f"Starting dashboard at http://{host}:{port}")
    uvicorn.run("api.server:app", host=host, port=port, reload=False, log_level="warning")


def cmd_status():
    from db.repositories import PortfolioRepository, TradeRepository
    from knowledge.calibration import CalibrationTracker

    repo = PortfolioRepository()
    history = repo.get_history(limit=1)
    if not history:
        print("No portfolio data yet. Run: python main.py run")
        return

    snap = history[-1]
    trades_repo = TradeRepository()
    open_trades = trades_repo.find_open()
    calibration = CalibrationTracker()
    brier = calibration.brier_score()

    print("\n=== GamblAI Portfolio Status ===")
    print(f"  Bankroll:      ${snap.bankroll:,.2f}")
    print(f"  Total P&L:     ${snap.total_pnl:+,.2f}")
    print(f"  Total Trades:  {snap.total_trades}")
    print(f"  Win Rate:      {snap.win_rate:.1%}")
    print(f"  Open Positions:{snap.open_position_count}")
    print(f"  Drawdown:      {snap.current_drawdown:.1%}")
    print(f"  Brier Score:   {brier if brier else 'N/A (need 5+ resolved trades)'}")
    print(f"  Last updated:  {snap.timestamp}")
    print()


def cmd_resolve():
    from db.connection import init_db
    from db.repositories import PortfolioRepository
    from pipeline.compound import CompoundStep
    from pipeline.runner import _load_portfolio

    init_db()
    portfolio_repo = PortfolioRepository()
    portfolio = _load_portfolio(portfolio_repo)
    compound = CompoundStep()
    portfolio = compound.process_resolved_markets(portfolio)
    snapshot = compound.snapshot(portfolio)
    portfolio_repo.save_snapshot(snapshot)
    print("Resolved expired markets.")
    _print_portfolio(portfolio)


def _print_portfolio(portfolio):
    from models.portfolio import Portfolio
    print(f"\n  Bankroll: ${portfolio.bankroll:,.2f} | "
          f"P&L: ${portfolio.total_pnl:+,.2f} | "
          f"Trades: {portfolio.total_trades} | "
          f"Win Rate: {portfolio.win_rate:.1%} | "
          f"Open: {len(portfolio.open_positions)}")


def main():
    parser = argparse.ArgumentParser(description="GamblAI — Prediction Market Simulator")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Initialize the database")
    sub.add_parser("run", help="Run one pipeline cycle")

    loop_p = sub.add_parser("loop", help="Run pipeline continuously")
    loop_p.add_argument("--interval", type=int, default=300, help="Seconds between cycles (default: 300)")

    dash_p = sub.add_parser("dashboard", help="Start the web dashboard")
    dash_p.add_argument("--host", default="127.0.0.1")
    dash_p.add_argument("--port", type=int, default=8000)

    sub.add_parser("status", help="Print portfolio summary")
    sub.add_parser("resolve", help="Force-resolve expired markets")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init()
    elif args.command == "run":
        cmd_run()
    elif args.command == "loop":
        cmd_loop(args.interval)
    elif args.command == "dashboard":
        cmd_dashboard(args.host, args.port)
    elif args.command == "status":
        cmd_status()
    elif args.command == "resolve":
        cmd_resolve()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
