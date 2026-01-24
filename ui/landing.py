# ui/landing.py
from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from .utils import render_template
from db.repositories.user_repository import UserRepository
from db.engine import SessionLocal

router = APIRouter()


def check_setup_required():
    """Check if initial setup is required (no users exist)"""
    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        users = user_repo.list_users(limit=1)
        return len(users) == 0
    finally:
        db.close()


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    # Redirect to setup if no users exist
    if check_setup_required():
        return RedirectResponse(url="/setup", status_code=status.HTTP_303_SEE_OTHER)
    
    return render_template(request, "index.html")
