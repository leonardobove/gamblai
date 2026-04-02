import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from api.routes.dashboard import router as dashboard_router
from api.routes.markets import router as markets_router
from api.routes.trades import router as trades_router
from api.routes.portfolio import router as portfolio_router
from api.routes.settings import router as settings_router
from api.routes.auth import router as auth_router

app = FastAPI(title="GamblAI", description="AI Prediction Market Trading Simulator")

# Session middleware — secret rotates on each deploy (sessions invalidated), which is fine
_session_secret = os.environ.get("SESSION_SECRET") or os.urandom(32).hex()
app.add_middleware(SessionMiddleware, secret_key=_session_secret, https_only=False)

_base = Path(__file__).parent
templates = Jinja2Templates(directory=str(_base / "templates"))
app.mount("/static", StaticFiles(directory=str(_base / "static")), name="static")

app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(markets_router, prefix="/api/markets")
app.include_router(trades_router, prefix="/api/trades")
app.include_router(portfolio_router, prefix="/api/portfolio")
