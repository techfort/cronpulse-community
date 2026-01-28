from db.repositories.monitor_repository import MonitorRepository
from db.repositories.user_repository import UserRepository
from db.repositories.settings_repository import SettingsRepository
from db.models import Monitor
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import os
import requests
import logging
from api.services.email_service import EmailService

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
    def __init__(self, monitor_repo: MonitorRepository, user_repo: UserRepository, settings_repo: Optional[SettingsRepository] = None):
        self.monitor_repo = monitor_repo
        self.user_repo = user_repo
        self.settings_repo = settings_repo
        
        # Initialize EmailService if SMTP is configured
        self.email_service = None
        self._init_email_service()
    
    def _init_email_service(self):
        """Initialize email service from settings (env vars or database)"""
        # Helper to get setting value
        def get_setting(key: str) -> Optional[str]:
            if self.settings_repo:
                return self.settings_repo.get_setting(key)
            return os.getenv(key)
        
        smtp_config = {
            "SMTP_HOST": get_setting("SMTP_HOST"),
            "SMTP_PORT": get_setting("SMTP_PORT"),
            "SMTP_USER": get_setting("SMTP_USER"),
            "SMTP_PASSWORD": get_setting("SMTP_PASSWORD"),
            "SENDER_EMAIL": get_setting("SENDER_EMAIL"),
            "SENDER_NAME": get_setting("SENDER_NAME") or "CronPulse",
            "SMTP_USE_TLS": get_setting("SMTP_USE_TLS") or "true",
        }
        
        if all(smtp_config.get(k) for k in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SENDER_EMAIL"]):
            try:
                self.email_service = EmailService(smtp_config)
                logger.info("Email service initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize email service: {e}")
        else:
            logger.info("SMTP not configured, email alerts disabled")

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
        
        if not self.email_service:
            logger.warning("Email service not configured, skipping email alert")
            return
        
        if not monitor.email_recipient:
            logger.warning(f"No email recipient configured for monitor {monitor.name}")
            return
        
        subject = f"⚠️ CronPulse Alert: {monitor.name} missed ping"
        html_content = f"""
        <h2>⚠️ Monitor Alert</h2>
        <p>The monitor <strong>{monitor.name}</strong> has not received a ping within the expected interval.</p>
        
        <h3>Details:</h3>
        <ul>
            <li><strong>Monitor:</strong> {monitor.name}</li>
            <li><strong>Expected Interval:</strong> {monitor.interval} minutes</li>
            <li><strong>Last Ping:</strong> {monitor.last_ping.isoformat() if monitor.last_ping else 'Never'}</li>
            <li><strong>Alert Time:</strong> {datetime.utcnow().isoformat()}</li>
        </ul>
        
        <p>Please check your cron job or scheduled task to ensure it's running correctly.</p>
        
        <hr>
        <p style="color: #666; font-size: 12px;">
            This alert was sent by CronPulse Community Edition. 
            <a href="http://localhost:8000/monitors">View Monitor</a>
        </p>
        """
        
        success, message = self.email_service.send_alert(
            to_email=monitor.email_recipient,
            to_name=monitor.email_recipient,
            subject=subject,
            html_content=html_content,
        )
        
        if success:
            logger.info(f"Email alert sent successfully for monitor {monitor.name}")
        else:
            logger.error(f"Failed to send email alert for monitor {monitor.name}: {message}")

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
