from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from api.services.monitor_service import MonitorService
from api.services.user_service import UserService
from api.dependencies import get_monitor_service, get_user_service, get_current_user
from db.models.user import User
from .utils import render_template, require_auth

router = APIRouter()


@router.get("/dashboard/ui", response_class=HTMLResponse)
@require_auth
async def dashboard_ui(
    request: Request,
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
    user_service: UserService = Depends(get_user_service),
):
    monitors = monitor_service.count_active_monitors(current_user.id)
    api_keys = user_service.count_api_keys(current_user.id)
    user = user_service.get_by_id(current_user.id)
    return render_template(
        request,
        "dashboard.html",
        {
            "current_user": user,
            "monitors": monitors,
            "api_keys": api_keys,
        },
    )
