from pydantic import BaseModel, EmailStr, field_validator, model_validator, HttpUrl, constr, confloat
from datetime import datetime
from typing import Optional
import re


class MonitorCreate(BaseModel):
    name: constr(min_length=1, max_length=200, strip_whitespace=True)  # type: ignore
    interval: confloat(gt=0, le=43200)  # Max 30 days in minutes  # type: ignore
    email_recipient: Optional[EmailStr] = None
    webhook_url: Optional[HttpUrl] = None
    expires_at: Optional[datetime] = None

    @model_validator(mode='after')
    def check_alert_destination(self):
        if not self.email_recipient and not self.webhook_url:
            raise ValueError(
                "At least one of email_recipient or webhook_url must be provided"
            )
        return self

    @field_validator("expires_at")
    @classmethod
    def check_expires_at(cls, expires_at):
        if expires_at and expires_at < datetime.utcnow():
            raise ValueError("expires_at must be in the future")
        return expires_at
    
    @field_validator("name")
    @classmethod
    def sanitize_name(cls, name):
        # Remove any HTML/script tags
        name = re.sub(r'<[^>]+>', '', name)
        return name.strip()


class MonitorUpdate(BaseModel):
    name: Optional[constr(min_length=1, max_length=200, strip_whitespace=True)] = None  # type: ignore
    interval: Optional[confloat(gt=0, le=43200)] = None  # type: ignore
    email_recipient: Optional[EmailStr] = None
    webhook_url: Optional[HttpUrl] = None
    expires_at: Optional[datetime] = None

    @model_validator(mode='after')
    def check_alert_destination(self):
        if (
            (self.email_recipient is not None or self.webhook_url is not None)
            and not self.email_recipient
            and not self.webhook_url
        ):
            raise ValueError(
                "At least one of email_recipient or "
                "webhook_url must be provided if updating alert settings"
            )
        return self
    
    @field_validator("name")
    @classmethod
    def sanitize_name(cls, name):
        if name:
            # Remove any HTML/script tags
            name = re.sub(r'<[^>]+>', '', name)
            return name.strip()
        return name


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
    password: constr(min_length=8, max_length=100)  # type: ignore
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return password


class UserResponse(BaseModel):
    id: int
    email: str


class ApiKeyCreate(BaseModel):
    name: Optional[constr(min_length=1, max_length=100, strip_whitespace=True)] = None  # type: ignore
    
    @field_validator("name")
    @classmethod
    def sanitize_name(cls, name):
        if name:
            # Remove any HTML/script tags
            name = re.sub(r'<[^>]+>', '', name)
            return name.strip()
        return name


class ApiKeyResponse(BaseModel):
    id: int
    name: Optional[str]
    created_at: datetime
