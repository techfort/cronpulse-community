from db.repositories.monitor_repository import MonitorRepository
from db.repositories.user_repository import UserRepository
from db.models import Monitor
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import os
import requests
import logging

logger = logging.getLogger(__name__)


def _parse_datetime(value: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Parse a string into a timezone-aware datetime (UTC), or return the datetime as-is.
    Accepts ISO 8601 and common formats. Returns None for empty/invalid input.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        v = value.strip()
        if not v:
            return None
        # Try ISO first
        try:
            dt = datetime.fromisoformat(v)
        except Exception:
            dt = None
        # Try common formats
        if dt is None:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(v, fmt)
                    break
                except Exception:
                    dt = None
        # Try dateutil if available for more flexible parsing
        if dt is None:
            try:
                from dateutil.parser import parse as _dateutil_parse

                dt = _dateutil_parse(v)
            except Exception:
                dt = None
    else:
        return None

    if dt is None:
        return None

    # If parsed datetime is naive, assume it's in local time? prefer treat as UTC.
    # Convert naive -> timezone-aware in UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # normalize to UTC
        dt = dt.astimezone(timezone.utc)
    return dt


class MonitorService:
    def __init__(self, monitor_repo: MonitorRepository, user_repo: UserRepository):
        self.monitor_repo = monitor_repo
        self.user_repo = user_repo
        self.mailgun_api_key = os.getenv("MAILGUN_API_KEY")
        self.mailgun_domain = os.getenv("MAILGUN_DOMAIN")

    def create_monitor(
        self,
        name: str,
        interval: float,
        user_id: int,
        email_recipient: Optional[str] = None,
        webhook_url: Optional[str] = None,
        expires_at: Optional[Union[str, datetime]] = None,
    ) -> Monitor:
        # Parse expires_at if provided as a string
        parsed_expires = _parse_datetime(expires_at)
        monitor = Monitor(
            name=name,
            interval=interval,
            user_id=user_id,
            email_recipient=email_recipient,
            webhook_url=webhook_url,
            expires_at=parsed_expires,
        )
        return self.monitor_repo.create(monitor)

    def update_monitor(
        self,
        monitor_id: int,
        user_id: int,
        name: Optional[str] = None,
        interval: Optional[float] = None,
        email_recipient: Optional[str] = None,
        webhook_url: Optional[str] = None,
        expires_at: Optional[Union[str, datetime]] = None,
    ) -> Monitor:
        # Parse expires_at if provided as a string
        parsed_expires = _parse_datetime(expires_at)
        monitor = Monitor(
            id=monitor_id,
            user_id=user_id,
            name=name,
            interval=interval,
            email_recipient=email_recipient,
            webhook_url=webhook_url,
            expires_at=parsed_expires,
        )
        return self.monitor_repo.update(monitor)

    def get_monitor(self, monitor_id: int, user_id: int) -> Monitor | None:
        return self.monitor_repo.get_by_id(monitor_id, user_id)

    def delete_monitor(self, monitor_id: int, user_id: int) -> None:
        self.monitor_repo.delete(monitor_id, user_id)

    def ping_monitor(self, monitor_id: int, user_id: int) -> dict:
        monitor = self.monitor_repo.get_by_id(monitor_id, user_id)
        if not monitor:
            raise ValueError("Monitor not found or not authorized")
        self.monitor_repo.update_last_ping(monitor, datetime.now())
        return {"status": "success", "monitor_id": monitor_id}

    def list_monitors(self, user_id: int) -> list[Monitor]:
        monitors = self.monitor_repo.list_by_user(user_id)
        # Ensure expires_at on returned monitors is timezone-aware (UTC)
        #  so templates can compare with now
        for m in monitors:
            if getattr(m, "expires_at", None) is not None:
                if m.expires_at.tzinfo is None:
                    m.expires_at = m.expires_at.replace(tzinfo=timezone.utc)
                else:
                    m.expires_at = m.expires_at.astimezone(timezone.utc)
        return monitors

    def update_last_ping(self, monitor_id: int, user_id: int) -> Monitor | None:
        monitor = self.monitor_repo.get_by_id(monitor_id, user_id)
        if not monitor:
            return None
        return self.monitor_repo.update_last_ping(monitor, datetime.now())

    def check_missed_pings(self) -> None:
        monitors = self.monitor_repo.get_all()
        now = datetime.now()
        for monitor in monitors:
            if monitor.last_ping is None:
                continue
            if monitor.expires_at and now > monitor.expires_at:
                logger.info(f"Monitor {monitor.name} has expired, skipping ping check")
                continue
            expected_time = monitor.last_ping + timedelta(minutes=monitor.interval)
            if now > expected_time:
                logger.info(f"Monitor {monitor.name} is overdue")
                if monitor.email_recipient:
                    self.send_alert_email(monitor)
                if monitor.webhook_url:
                    self.send_webhook_alert(monitor)
                self.monitor_repo.update_last_ping(monitor, now)

    def send_alert_email(self, monitor: Monitor) -> None:
        if monitor.expires_at and datetime.utcnow() > monitor.expires_at:
            logger.info(f"Skipping email alert for expired monitor {monitor.name}")
            return
        if not self.mailgun_api_key or not self.mailgun_domain:
            logger.warning("Mailgun configuration missing, skipping email alert")
            return
        response = requests.post(
            f"https://api.mailgun.net/v3/{self.mailgun_domain}/messages",
            auth=("api", self.mailgun_api_key),
            data={
                "from": f"no-reply@{self.mailgun_domain}",
                "to": monitor.email_recipient,
                "subject": (f"Alert: Monitor {monitor.name} missed ping"),
                "text": (
                    f"The monitor '{monitor.name}' has not received a ping within the "
                    f"expected interval of {monitor.interval} minutes."
                ),
            },
        )
        if response.status_code == 200:
            logger.info(f"Email alert sent for monitor {monitor.name}")
        else:
            logger.error(
                "Failed to send email alert for monitor %s: %s",
                monitor.name,
                response.text,
            )

    def send_webhook_alert(self, monitor: Monitor) -> None:
        if monitor.expires_at and datetime.utcnow() > monitor.expires_at:
            logger.info(f"Skipping webhook alert for expired monitor {monitor.name}")
            return
        payload = {
            "event": "monitor_missed_ping",
            "monitor_name": monitor.name,
            "interval_minutes": monitor.interval,
            "last_ping": monitor.last_ping.isoformat() if monitor.last_ping else None,
            "message": "Monitor missed its expected ping interval.",
        }
        try:
            response = requests.post(monitor.webhook_url, json=payload, timeout=5)
            if response.status_code == 200:
                logger.info(f"Webhook alert sent for monitor {monitor.name}")
            else:
                logger.error(
                    "Failed to send webhook alert for monitor %s: %s %s",
                    monitor.name,
                    response.status_code,
                    response.text,
                )
        except requests.RequestException as e:
            logger.error(f"Webhook alert failed for monitor {monitor.name}: {str(e)}")

    def count_active_monitors(self, user_id: int) -> int:
        return self.monitor_repo.count_active_by_user(user_id)
