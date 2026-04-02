"""Simple session-based auth for the GamblAI dashboard settings page."""

import hashlib
import os
import secrets
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

from db.repositories import SettingsRepository

_REPO = SettingsRepository


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def is_setup_complete() -> bool:
    """Return True if admin credentials have been created."""
    repo = _REPO()
    return bool(repo.get("admin_username") and repo.get("admin_password_hash"))


def create_admin(username: str, password: str) -> None:
    repo = _REPO()
    repo.set("admin_username", username.strip(), is_secret=False)
    repo.set("admin_password_hash", _hash(password), is_secret=True)


def check_credentials(username: str, password: str) -> bool:
    repo = _REPO()
    stored_user = repo.get("admin_username") or ""
    stored_hash = repo.get("admin_password_hash") or ""
    return (
        secrets.compare_digest(stored_user, username.strip())
        and secrets.compare_digest(stored_hash, _hash(password))
    )


def get_session_user(request: Request) -> Optional[str]:
    return request.session.get("admin_user")


def require_auth(request: Request) -> Optional[RedirectResponse]:
    """Return a redirect if not authenticated, else None."""
    if not is_setup_complete():
        if request.url.path != "/setup":
            return RedirectResponse(url="/setup", status_code=303)
        return None
    if not get_session_user(request):
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
    return None
