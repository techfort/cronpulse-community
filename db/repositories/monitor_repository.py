from operator import or_
from sqlalchemy.orm import Session
from db.models import Monitor
from datetime import datetime


class MonitorRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, monitor: Monitor) -> Monitor:
        self.db.add(monitor)
        self.db.commit()
        self.db.refresh(monitor)
        return monitor

    def get_by_id(self, monitor_id: int, user_id: int) -> Monitor | None:
        return (
            self.db.query(Monitor)
            .filter(Monitor.id == monitor_id, Monitor.user_id == user_id)
            .first()
        )

    def get_by_token(self, token: str) -> Monitor | None:
        return self.db.query(Monitor).filter(Monitor.token == token).first()

    def list_by_user(self, user_id: int) -> list[Monitor]:
        return self.db.query(Monitor).filter(Monitor.user_id == user_id).all()

    def get_all(self) -> list[Monitor]:
        return self.db.query(Monitor).all()

    def update(self, updated_monitor: Monitor) -> Monitor:
        monitor = self.get_by_id(updated_monitor.id, updated_monitor.user_id)
        if not monitor:
            raise ValueError("Monitor not found or not authorized")
        # Update fields if provided in updated_monitor (and not None)
        if updated_monitor.name is not None:
            monitor.name = updated_monitor.name
        if updated_monitor.interval is not None:
            monitor.interval = updated_monitor.interval
        if updated_monitor.email_recipient is not None:
            monitor.email_recipient = updated_monitor.email_recipient
        if updated_monitor.webhook_url is not None:
            monitor.webhook_url = updated_monitor.webhook_url
        if updated_monitor.expires_at is not None:
            monitor.expires_at = updated_monitor.expires_at
        self.db.commit()
        self.db.refresh(monitor)
        return monitor

    def update_last_ping(
        self, monitor: Monitor, last_ping: datetime = datetime.now()
    ) -> Monitor:
        monitor.last_ping = last_ping
        self.db.commit()
        self.db.refresh(monitor)
        return monitor

    def delete(self, monitor_id: int, user_id: int) -> None:
        monitor = self.get_by_id(monitor_id, user_id)
        if not monitor:
            raise ValueError("Monitor not found or not authorized")
        self.db.delete(monitor)
        self.db.commit()

    def count_active_by_user(self, user_id: int) -> int:
        now = datetime.now()
        return (
            self.db.query(Monitor)
            .filter(
                Monitor.user_id == user_id,
                or_(Monitor.expires_at.is_(None), Monitor.expires_at > now),
            )
            .count()
        )
