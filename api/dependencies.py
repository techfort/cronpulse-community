# api/dependencies.py
from fastapi import Depends, Request, HTTPException, status
from db.engine import SessionLocal
from sqlalchemy.orm import Session
from db.repositories.monitor_repository import MonitorRepository
from db.repositories.user_repository import UserRepository
from db.repositories.settings_repository import SettingsRepository
from api.services.monitor_service import MonitorService
from api.services.user_service import UserService, UserServiceException


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_monitor_service(db: Session = Depends(get_db)):
    monitor_repo = MonitorRepository(db)
    user_repo = UserRepository(db)
    settings_repo = SettingsRepository(db)
    return MonitorService(monitor_repo, user_repo, settings_repo)


def get_user_service(db: Session = Depends(get_db)):
    user_repo = UserRepository(db)
    return UserService(user_repo)


async def get_current_user(
    request: Request,
    user_service: UserService = Depends(get_user_service),
):
    try:
        user = await user_service.get_current_user_from_request(request)
        return user
    except UserServiceException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
