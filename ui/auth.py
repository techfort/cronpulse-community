from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from .utils import render_template
from api.services.user_service import UserService, UserServiceException
from api.dependencies import get_user_service
from db.repositories.user_repository import UserRepository
from db.repositories.settings_repository import SettingsRepository
from db.engine import SessionLocal
from typing import Optional

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


@router.get("/setup", response_class=HTMLResponse)
async def setup_ui(request: Request):
    """First-run setup page"""
    if not check_setup_required():
        return RedirectResponse(url="/login/ui", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(request, "setup.html")


@router.post("/setup", response_class=HTMLResponse)
async def setup_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    smtp_host: Optional[str] = Form(None),
    smtp_port: Optional[str] = Form(None),
    smtp_user: Optional[str] = Form(None),
    smtp_password: Optional[str] = Form(None),
    sender_email: Optional[str] = Form(None),
    sender_name: Optional[str] = Form(None),
    smtp_use_tls: Optional[str] = Form(None),
    user_service: UserService = Depends(get_user_service),
):
    """Process first-run setup"""
    if not check_setup_required():
        return RedirectResponse(url="/login/ui", status_code=status.HTTP_303_SEE_OTHER)
    
    # Validate passwords match
    if password != confirm_password:
        return render_template(
            request,
            "setup.html",
            {"error": "Passwords do not match"},
        )
    
    # Validate password strength
    if len(password) < 8:
        return render_template(
            request,
            "setup.html",
            {"error": "Password must be at least 8 characters"},
        )
    
    try:
        db = SessionLocal()
        try:
            # Create admin user
            user = user_service.signup(email, password)
            
            # Mark as admin
            user_repo = UserRepository(db)
            user_repo.update_user(user.id, {"is_admin": True})
            
            # Save SMTP settings if provided
            if smtp_host and smtp_port and smtp_user and smtp_password and sender_email:
                settings_repo = SettingsRepository(db)
                settings_repo.set_setting("SMTP_HOST", smtp_host)
                settings_repo.set_setting("SMTP_PORT", smtp_port)
                settings_repo.set_setting("SMTP_USER", smtp_user)
                settings_repo.set_setting("SMTP_PASSWORD", smtp_password, is_secret=True)
                settings_repo.set_setting("SENDER_EMAIL", sender_email)
                settings_repo.set_setting("SENDER_NAME", sender_name or "CronPulse")
                settings_repo.set_setting("SMTP_USE_TLS", "true" if smtp_use_tls else "false")
        finally:
            db.close()
        
        # Redirect to login with success message
        return RedirectResponse(url="/login/ui?setup=complete", status_code=status.HTTP_303_SEE_OTHER)
    except UserServiceException as e:
        return render_template(
            request,
            "setup.html",
            {"error": str(e)},
        )


@router.get("/signup/ui", response_class=HTMLResponse)
async def signup_ui(request: Request):
    # Redirect to setup if no users exist
    if check_setup_required():
        return RedirectResponse(url="/setup", status_code=status.HTTP_303_SEE_OTHER)
    
    # Otherwise show error - signup disabled after setup
    return render_template(
        request,
        "error.html",
        {"error": "Public signup is disabled. Please contact your administrator for an account."},
    )


@router.post("/signup/ui", response_class=HTMLResponse)
async def signup_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    user_service: UserService = Depends(get_user_service),
):
    # Block signup if setup is complete
    if not check_setup_required():
        return render_template(
            request,
            "error.html",
            {"error": "Public signup is disabled. Please contact your administrator for an account."},
        )
    
    try:
        user_service.signup(email, password)
        # Show a message or redirect to login
        return render_template(
            request,
            "login.html",
            {"message": "Signup successful, please log in"},
        )
    except UserServiceException as e:
        return render_template(
            request,
            "signup.html",
            {"error": str(e)},
        )


@router.get("/login/ui", response_class=HTMLResponse)
async def login_ui(request: Request):
    # Redirect to setup if no users exist
    if check_setup_required():
        return RedirectResponse(url="/setup", status_code=status.HTTP_303_SEE_OTHER)
    
    # Check for setup complete message
    setup = request.query_params.get("setup")
    context = {}
    if setup == "complete":
        context["message"] = "Setup complete! Please login with your admin credentials."
    
    return render_template(request, "login.html", context)


@router.post("/login/ui", response_class=HTMLResponse)
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    user_service: UserService = Depends(get_user_service),
):
    try:
        token = user_service.login(email, password)  # may be string or dict
        # If service returned a dict like {"access_token": "..."} extract the string
        if isinstance(token, dict):
            token = token.get("access_token") or token.get("token") or token.get("jwt")
        if not isinstance(token, str):
            raise UserServiceException("Invalid token returned from login")
        response = RedirectResponse(
            url="/dashboard/ui", status_code=status.HTTP_303_SEE_OTHER
        )
        # store only the raw JWT string
        response.set_cookie("access_token", token, httponly=True, samesite="lax")
        return response
    except UserServiceException as e:
        return render_template(
            request,
            "login.html",
            {"error": str(e)},
        )


@router.get("/logout/ui")
async def logout_ui():
    return RedirectResponse(url="/login/ui", status_code=status.HTTP_303_SEE_OTHER)
