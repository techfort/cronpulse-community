# ui/admin.py
from fastapi import APIRouter, Request, Form, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from .utils import render_template
from api.services.user_service import UserService, UserServiceException
from api.dependencies import get_user_service, get_current_user
from db.repositories.user_repository import UserRepository
from db.repositories.monitor_repository import MonitorRepository
from db.engine import SessionLocal
from db.models.user import User

router = APIRouter()


async def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency to ensure user is an admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required"
        )
    return current_user


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_ui(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """Admin page to manage users"""
    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        monitor_repo = MonitorRepository(db)
        
        users = user_repo.list_users()
        
        # Add counts for each user
        for user in users:
            user.monitor_count = len(monitor_repo.list_monitors(user.id))
            user.api_key_count = user_repo.count_api_keys(user.id)
        
        return render_template(request, "admin_users.html", {"users": users})
    finally:
        db.close()


@router.post("/admin/users/create", response_class=HTMLResponse)
async def admin_create_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    is_admin: str = Form(None),
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """Create a new user (admin only)"""
    try:
        # Create the user
        new_user = user_service.signup(email, password)
        
        # Set admin flag if requested
        if is_admin == "true":
            db = SessionLocal()
            try:
                user_repo = UserRepository(db)
                user_repo.update_user(new_user.id, {"is_admin": True})
            finally:
                db.close()
        
        return RedirectResponse(
            url="/admin/users?message=User created successfully",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except UserServiceException as e:
        db = SessionLocal()
        try:
            user_repo = UserRepository(db)
            users = user_repo.list_users()
            return render_template(
                request,
                "admin_users.html",
                {"users": users, "error": str(e)}
            )
        finally:
            db.close()


@router.post("/admin/users/{user_id}/delete")
async def admin_delete_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_admin)
):
    """Delete a user (admin only)"""
    if user_id == current_user.id:
        return RedirectResponse(
            url="/admin/users?error=Cannot delete your own account",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        monitor_repo = MonitorRepository(db)
        
        # Delete user's monitors and API keys first
        monitors = monitor_repo.list_monitors(user_id)
        for monitor in monitors:
            monitor_repo.delete_monitor(monitor.id)
        
        api_keys = user_repo.list_api_keys(user_id)
        for api_key in api_keys:
            user_repo.delete_api_key(api_key.id)
        
        # Delete the user
        user_repo.delete_user(user_id)
        
        return RedirectResponse(
            url="/admin/users?message=User deleted successfully",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/users?error={str(e)}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    finally:
        db.close()
