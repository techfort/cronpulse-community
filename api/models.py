from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional


class MonitorCreate(BaseModel):
    name: str
    interval: float
    email_recipient: Optional[str] = None
    webhook_url: Optional[str] = None
    expires_at: Optional[datetime] = None

    @field_validator("email_recipient")
    def check_alert_destination(cls, email_recipient, values):
        webhook_url = values.get("webhook_url")
        if not email_recipient and not webhook_url:
            raise ValueError(
                "At least one of email_recipient or webhook_url must be provided"
            )
        return email_recipient

    @field_validator("expires_at")
    def check_expires_at(cls, expires_at):
        if expires_at and expires_at < datetime.utcnow():
            raise ValueError("expires_at must be in the future")
        return expires_at


class MonitorUpdate(BaseModel):
    name: Optional[str] = None
    interval: Optional[float] = None
    email_recipient: Optional[str] = None
    webhook_url: Optional[str] = None
    expires_at: Optional[datetime] = None

    @field_validator("email_recipient")
    def check_alert_destination(cls, email_recipient, values):
        webhook_url = values.get("webhook_url")
        if (
            (email_recipient is not None or webhook_url is not None)
            and not email_recipient
            and not webhook_url
        ):
            raise ValueError(
                "At least one of email_recipient or "
                "webhook_url must be provided if updating alert settings"
            )
        return email_recipient


class MonitorResponse(BaseModel):
    id: int
    name: str
    interval: float
    last_ping: Optional[datetime]
    user_id: int
    email_recipient: Optional[str]
    webhook_url: Optional[str]
    expires_at: Optional[datetime]


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str


class ApiKeyResponse(BaseModel):
    id: int
    name: Optional[str]
    created_at: datetime
