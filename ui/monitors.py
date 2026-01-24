from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from api.services.monitor_service import MonitorService
from api.dependencies import get_monitor_service, get_current_user
from db.models.user import User
from .utils import render_template, require_auth
from datetime import datetime, timezone

router = APIRouter()


@router.get("/monitors/ui", response_class=HTMLResponse)
@require_auth
async def monitors_ui(
    request: Request,
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
):
    monitors = monitor_service.list_monitors(current_user.id)
    return render_template(
        request,
        "monitors.html",
        {
            "current_user": current_user,
            "monitors": monitors,
            "now": datetime.now(timezone.utc),
        },
    )


@router.post("/monitors/ui", response_class=HTMLResponse)
@require_auth
async def create_monitor_ui(
    request: Request,
    name: str = Form(...),
    interval: float = Form(...),
    email_recipient: str = Form(None),
    webhook_url: str = Form(None),
    expires_at: str = Form(None),
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
):
    try:
        monitor_service.create_monitor(
            name=name,
            interval=interval,
            user_id=current_user.id,
            email_recipient=email_recipient,
            webhook_url=webhook_url,
            expires_at=expires_at,
        )

        # If request came from HTMX, return the monitors list fragment only
        is_htmx = request.headers.get("HX-Request", "").lower() == "true"
        if is_htmx:
            monitors = monitor_service.list_monitors(current_user.id)
            return render_template(
                request,
                "partials/monitor_list.html",
                {
                    "current_user": current_user,
                    "monitors": monitors,
                    "now": datetime.now(timezone.utc),
                },
            )

        # Non-HTMX: full-page redirect
        return RedirectResponse(
            url="/monitors/ui", status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        return render_template(
            request,
            "monitors.html",
            {
                "current_user": current_user,
                "monitors": monitor_service.list_monitors(current_user.id),
                "error": str(e),
            },
        )


@router.post("/monitors/{monitor_id}/delete/ui", response_class=HTMLResponse)
@require_auth
async def delete_monitor_ui(
    request: Request,
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
):
    try:
        monitor_service.delete_monitor(monitor_id, current_user.id)

        is_htmx = request.headers.get("HX-Request", "").lower() == "true"
        if is_htmx:
            monitors = monitor_service.list_monitors(current_user.id)
            return render_template(
                request,
                "partials/monitor_list.html",
                {
                    "current_user": current_user,
                    "monitors": monitors,
                    "now": datetime.now(timezone.utc),
                },
            )

        return RedirectResponse(
            url="/monitors/ui", status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        return render_template(
            request,
            "monitors.html",
            {
                "current_user": current_user,
                "monitors": monitor_service.list_monitors(current_user.id),
                "error": str(e),
                "error_details": e.args[0] if e.args else "Unknown error",
            },
        )
    finally:
        # Ensure the monitors list is always updated
        monitor_service.list_monitors(current_user.id)


@router.get("/monitors/{monitor_id}/edit/ui", response_class=HTMLResponse)
@require_auth
async def edit_monitor_ui_get(
    request: Request,
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
):
    monitor = monitor_service.get_monitor(monitor_id, current_user.id)
    if not monitor:
        return render_template(
            request,
            "monitors.html",
            {
                "current_user": current_user,
                "monitors": monitor_service.list_monitors(current_user.id),
                "error": "Monitor not found or you are not authorized",
            },
        )
    return render_template(
        request,
        "edit_monitor.html",
        {"current_user": current_user, "monitor": monitor},
    )


@router.post("/monitors/{monitor_id}/edit/ui", response_class=HTMLResponse)
@require_auth
async def edit_monitor_ui_post(
    request: Request,
    monitor_id: int,
    name: str = Form(None),
    interval: float = Form(None),
    email_recipient: str = Form(None),
    webhook_url: str = Form(None),
    expires_at: str = Form(None),
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
):
    try:
        # Use provided values; if a field is left empty, pass None so service can decide
        monitor_service.update_monitor(
            monitor_id=monitor_id,
            user_id=current_user.id,
            name=name,
            interval=interval,
            email_recipient=email_recipient,
            webhook_url=webhook_url,
            expires_at=expires_at,
        )

        is_htmx = request.headers.get("HX-Request", "").lower() == "true"
        if is_htmx:
            monitors = monitor_service.list_monitors(current_user.id)
            return render_template(
                request,
                "partials/monitor_list.html",
                {
                    "current_user": current_user,
                    "monitors": monitors,
                    "now": datetime.now(timezone.utc),
                },
            )

        return RedirectResponse(
            url="/monitors/ui", status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        return render_template(
            request,
            "edit_monitor.html",
            {
                "current_user": current_user,
                "monitor": monitor_service.get_monitor(monitor_id, current_user.id),
                "error": str(e),
            },
        )
