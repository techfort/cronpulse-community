from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from .utils import render_template, require_auth
from db.engine import SessionLocal
from db.repositories.settings_repository import SettingsRepository
from api.dependencies import get_current_user
from db.models.user import User
from typing import Optional

router = APIRouter()


@router.get("/settings/ui", response_class=HTMLResponse)
@require_auth
async def settings_ui(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Display settings page"""
    db = SessionLocal()
    try:
        settings_repo = SettingsRepository(db)
        
        # Get current SMTP settings (from env or database)
        smtp_settings = {
            "smtp_host": settings_repo.get_setting("SMTP_HOST") or "",
            "smtp_port": settings_repo.get_setting("SMTP_PORT") or "587",
            "smtp_user": settings_repo.get_setting("SMTP_USER") or "",
            "sender_email": settings_repo.get_setting("SENDER_EMAIL") or "",
            "sender_name": settings_repo.get_setting("SENDER_NAME") or "CronPulse",
            "smtp_use_tls": settings_repo.get_setting("SMTP_USE_TLS") or "true",
        }
        
        # Check if email is configured
        email_configured = all([
            smtp_settings["smtp_host"],
            smtp_settings["smtp_port"],
            smtp_settings["smtp_user"],
            smtp_settings["sender_email"]
        ])
        
        return render_template(
            request,
            "settings.html",
            {
                "current_user": current_user,
                "smtp_settings": smtp_settings,
                "email_configured": email_configured,
            },
        )
    finally:
        db.close()


@router.post("/settings/smtp", response_class=HTMLResponse)
@require_auth
async def update_smtp_settings(
    request: Request,
    smtp_host: str = Form(...),
    smtp_port: str = Form(...),
    smtp_user: str = Form(...),
    smtp_password: Optional[str] = Form(None),
    sender_email: str = Form(...),
    sender_name: str = Form("CronPulse"),
    smtp_use_tls: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """Update SMTP settings"""
    db = SessionLocal()
    try:
        settings_repo = SettingsRepository(db)
        
        # Save settings to database
        settings_repo.set_setting("SMTP_HOST", smtp_host)
        settings_repo.set_setting("SMTP_PORT", smtp_port)
        settings_repo.set_setting("SMTP_USER", smtp_user)
        if smtp_password:  # Only update password if provided
            settings_repo.set_setting("SMTP_PASSWORD", smtp_password, is_secret=True)
        settings_repo.set_setting("SENDER_EMAIL", sender_email)
        settings_repo.set_setting("SENDER_NAME", sender_name)
        settings_repo.set_setting("SMTP_USE_TLS", "true" if smtp_use_tls else "false")
        
        # Get updated settings
        smtp_settings = {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_user": smtp_user,
            "sender_email": sender_email,
            "sender_name": sender_name,
            "smtp_use_tls": "true" if smtp_use_tls else "false",
        }
        
        return render_template(
            request,
            "settings.html",
            {
                "current_user": current_user,
                "smtp_settings": smtp_settings,
                "email_configured": True,
                "success": "SMTP settings saved successfully! Email alerts are now enabled.",
            },
        )
    except Exception as e:
        return render_template(
            request,
            "settings.html",
            {
                "current_user": current_user,
                "error": f"Failed to save settings: {str(e)}",
            },
        )
    finally:
        db.close()


@router.post("/settings/test-email", response_class=HTMLResponse)
@require_auth
async def test_email(
    request: Request,
    test_email_address: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    """Send a test email"""
    db = SessionLocal()
    try:
        settings_repo = SettingsRepository(db)
        
        # Get SMTP settings
        smtp_config = {
            "SMTP_HOST": settings_repo.get_setting("SMTP_HOST"),
            "SMTP_PORT": settings_repo.get_setting("SMTP_PORT"),
            "SMTP_USER": settings_repo.get_setting("SMTP_USER"),
            "SMTP_PASSWORD": settings_repo.get_setting("SMTP_PASSWORD"),
            "SENDER_EMAIL": settings_repo.get_setting("SENDER_EMAIL"),
            "SENDER_NAME": settings_repo.get_setting("SENDER_NAME") or "CronPulse",
            "SMTP_USE_TLS": settings_repo.get_setting("SMTP_USE_TLS") or "true",
        }
        
        # Check if all required settings are present
        if not all(smtp_config.get(k) for k in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SENDER_EMAIL"]):
            smtp_settings = {
                "smtp_host": smtp_config.get("SMTP_HOST", ""),
                "smtp_port": smtp_config.get("SMTP_PORT", "587"),
                "smtp_user": smtp_config.get("SMTP_USER", ""),
                "sender_email": smtp_config.get("SENDER_EMAIL", ""),
                "sender_name": smtp_config.get("SENDER_NAME", "CronPulse"),
                "smtp_use_tls": smtp_config.get("SMTP_USE_TLS", "true"),
            }
            return render_template(
                request,
                "settings.html",
                {
                    "current_user": current_user,
                    "smtp_settings": smtp_settings,
                    "email_configured": False,
                    "error": "SMTP settings are incomplete. Please configure all required fields first.",
                },
            )
        
        # Try to send test email
        from api.services.email_service import EmailService
        
        email_service = EmailService(smtp_config)
        success, message = email_service.send_alert(
            to_email=test_email_address,
            to_name=test_email_address,
            subject="✅ CronPulse Test Email",
            html_content="""
                <h2>✅ Email Configuration Test</h2>
                <p>Congratulations! Your CronPulse email configuration is working correctly.</p>
                <p>You will now receive email alerts when your monitors miss pings.</p>
                <hr>
                <p style="color: #666; font-size: 12px;">
                    This is a test email from CronPulse Community Edition
                </p>
            """
        )
        
        smtp_settings = {
            "smtp_host": smtp_config["SMTP_HOST"],
            "smtp_port": smtp_config["SMTP_PORT"],
            "smtp_user": smtp_config["SMTP_USER"],
            "sender_email": smtp_config["SENDER_EMAIL"],
            "sender_name": smtp_config["SENDER_NAME"],
            "smtp_use_tls": smtp_config["SMTP_USE_TLS"],
        }
        
        if success:
            return render_template(
                request,
                "settings.html",
                {
                    "current_user": current_user,
                    "smtp_settings": smtp_settings,
                    "email_configured": True,
                    "success": f"Test email sent successfully to {test_email_address}! Check your inbox.",
                },
            )
        else:
            return render_template(
                request,
                "settings.html",
                {
                    "current_user": current_user,
                    "smtp_settings": smtp_settings,
                    "email_configured": True,
                    "error": f"Failed to send test email: {message}",
                },
            )
    except Exception as e:
        return render_template(
            request,
            "settings.html",
            {
                "current_user": current_user,
                "error": f"Failed to send test email: {str(e)}",
            },
        )
    finally:
        db.close()
