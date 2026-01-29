from fastapi import APIRouter, Depends, status
from api.dependencies import get_monitor_service, get_current_user
from api.models import MonitorCreate, MonitorUpdate, MonitorResponse
from api.services.monitor_service import MonitorService
from db.models.user import User

router = APIRouter()


@router.get("/monitors", response_model=list[MonitorResponse])
def list_monitors(
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
):
    return monitor_service.list_monitors(current_user.id)


@router.post("/monitors", response_model=MonitorResponse)
def create_monitor(
    monitor: MonitorCreate,
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
):
    # Convert Pydantic HttpUrl to string for database storage
    webhook_url_str = str(monitor.webhook_url) if monitor.webhook_url else None
    
    return monitor_service.create_monitor(
        monitor.name,
        monitor.interval,
        current_user.id,
        monitor.email_recipient,
        webhook_url_str,
        monitor.expires_at,
    )


@router.put("/monitors/{monitor_id}", response_model=MonitorResponse)
def update_monitor(
    monitor_id: int,
    monitor: MonitorUpdate,
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
):
    # Convert Pydantic HttpUrl to string for database storage
    webhook_url_str = str(monitor.webhook_url) if monitor.webhook_url else None
    
    return monitor_service.update_monitor(
        monitor_id,
        current_user.id,
        monitor.name,
        monitor.interval,
        monitor.email_recipient,
        webhook_url_str,
        monitor.expires_at,
    )


@router.delete("/monitors/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
):
    monitor_service.delete_monitor(monitor_id, current_user.id)


@router.get("/ping/{monitor_id}")
def ping_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
):
    return monitor_service.ping_monitor(monitor_id, current_user.id)


@router.post("/ping/{monitor_id}")
def ping_monitor_post(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    monitor_service: MonitorService = Depends(get_monitor_service),
):
    return monitor_service.ping_monitor(monitor_id, current_user.id)
