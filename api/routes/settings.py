from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from api.auth import require_auth, create_admin, check_credentials
from config import CONFIGURABLE_KEYS
from db.repositories import SettingsRepository

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, saved: int = 0, error: str = ""):
    redirect = require_auth(request)
    if redirect:
        return redirect

    repo = SettingsRepository()
    stored = repo.get_all()

    fields = []
    for cfg in CONFIGURABLE_KEYS:
        key = cfg["key"]
        entry = stored.get(key)
        is_configured = bool(entry and entry["value"].strip())
        fields.append({
            **cfg,
            "is_configured": is_configured,
            # Only pass value for non-secret fields (e.g. boolean toggles)
            "current_value": entry["value"] if entry and not cfg.get("is_secret") else "",
            "updated_at": entry["updated_at"] if entry else None,
        })

    return _templates.TemplateResponse(request, "settings.html", {
        "fields": fields,
        "saved": bool(saved),
        "error": error,
        "user": request.session.get("admin_user"),
    })


@router.post("/settings", response_class=HTMLResponse)
async def save_settings(
    request: Request,
    anthropic_api_key: Optional[str] = Form(default=None),
    tavily_api_key: Optional[str] = Form(default=None),
    newsapi_api_key: Optional[str] = Form(default=None),
    kalshi_api_key_id: Optional[str] = Form(default=None),
    kalshi_private_key: Optional[str] = Form(default=None),
    kalshi_enabled: Optional[str] = Form(default=None),
    kalshi_execute_trades: Optional[str] = Form(default=None),
    # Password change fields
    new_username: Optional[str] = Form(default=None),
    new_password: Optional[str] = Form(default=None),
    new_password_confirm: Optional[str] = Form(default=None),
    current_password: Optional[str] = Form(default=None),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    repo = SettingsRepository()

    # --- API key fields ---
    field_map = {
        "anthropic_api_key":     (anthropic_api_key,    True),
        "tavily_api_key":        (tavily_api_key,        True),
        "newsapi_api_key":       (newsapi_api_key,       True),
        "kalshi_api_key_id":     (kalshi_api_key_id,     True),
        "kalshi_private_key":    (kalshi_private_key,    True),
        "kalshi_enabled":        (kalshi_enabled,        False),
        "kalshi_execute_trades": (kalshi_execute_trades, False),
    }

    for key, (value, is_secret) in field_map.items():
        cfg = next((c for c in CONFIGURABLE_KEYS if c["key"] == key), {})
        if cfg.get("type") == "bool":
            repo.set(key, "true" if value else "false", is_secret=False)
        elif value is not None and value.strip():
            repo.set(key, value.strip(), is_secret=is_secret)

    # --- Password / username change ---
    if new_password and new_password.strip():
        error = _handle_password_change(request, current_password, new_username, new_password, new_password_confirm)
        if error:
            stored = repo.get_all()
            fields = _build_fields(stored)
            return _templates.TemplateResponse(request, "settings.html", {
                "fields": fields, "saved": False, "error": error,
                "user": request.session.get("admin_user"),
            })

    return RedirectResponse(url="/settings?saved=1", status_code=303)


def _handle_password_change(
    request: Request,
    current_password: Optional[str],
    new_username: Optional[str],
    new_password: Optional[str],
    new_password_confirm: Optional[str],
) -> str:
    """Validate and apply a password change. Returns error string or empty string."""
    current_user = request.session.get("admin_user", "")
    if not check_credentials(current_user, current_password or ""):
        return "Current password is incorrect."
    if new_password != new_password_confirm:
        return "New passwords do not match."
    if len(new_password) < 8:
        return "New password must be at least 8 characters."
    username = (new_username or "").strip() or current_user
    create_admin(username, new_password)
    request.session["admin_user"] = username
    return ""


def _build_fields(stored: dict) -> list:
    fields = []
    for cfg in CONFIGURABLE_KEYS:
        key = cfg["key"]
        entry = stored.get(key)
        is_configured = bool(entry and entry["value"].strip())
        fields.append({
            **cfg,
            "is_configured": is_configured,
            "current_value": entry["value"] if entry and not cfg.get("is_secret") else "",
            "updated_at": entry["updated_at"] if entry else None,
        })
    return fields
