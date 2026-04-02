from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from api.auth import check_credentials, create_admin, is_setup_complete

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    if is_setup_complete():
        return RedirectResponse(url="/settings", status_code=303)
    return _templates.TemplateResponse(request, "setup.html", {"error": ""})


@router.post("/setup", response_class=HTMLResponse)
async def setup_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    if is_setup_complete():
        return RedirectResponse(url="/settings", status_code=303)
    if not username.strip():
        return _templates.TemplateResponse(request, "setup.html", {"error": "Username cannot be empty."})
    if len(password) < 8:
        return _templates.TemplateResponse(request, "setup.html", {"error": "Password must be at least 8 characters."})
    if password != password_confirm:
        return _templates.TemplateResponse(request, "setup.html", {"error": "Passwords do not match."})
    create_admin(username, password)
    request.session["admin_user"] = username.strip()
    return RedirectResponse(url="/settings?saved=1", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/settings"):
    if not is_setup_complete():
        return RedirectResponse(url="/setup", status_code=303)
    return _templates.TemplateResponse(request, "login.html", {"error": "", "next": next})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/settings"),
):
    if check_credentials(username, password):
        request.session["admin_user"] = username.strip()
        return RedirectResponse(url=next, status_code=303)
    return _templates.TemplateResponse(request, "login.html", {"error": "Invalid username or password.", "next": next})


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
