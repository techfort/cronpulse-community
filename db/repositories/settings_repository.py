from db.models.settings import Settings
from sqlalchemy.orm import Session
from typing import Optional, Dict
import os


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value, preferring environment variable over database"""
        # Check environment first
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        
        # Fall back to database
        setting = self.db.query(Settings).filter(Settings.key == key).first()
        return setting.value if setting else None

    def set_setting(self, key: str, value: Optional[str], is_secret: bool = False):
        """Set a setting value in database"""
        setting = self.db.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = value
            setting.is_secret = is_secret
        else:
            setting = Settings(key=key, value=value, is_secret=is_secret)
            self.db.add(setting)
        self.db.commit()

    def get_all_settings(self, include_secrets: bool = False) -> Dict[str, str]:
        """Get all settings as a dictionary"""
        query = self.db.query(Settings)
        if not include_secrets:
            query = query.filter(Settings.is_secret == False)
        
        settings = query.all()
        result = {}
        for setting in settings:
            # Prefer environment variable
            env_value = os.getenv(setting.key)
            result[setting.key] = env_value if env_value is not None else setting.value
        
        return result

    def is_smtp_configured(self) -> bool:
        """Check if SMTP is configured (either env vars or database)"""
        required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SENDER_EMAIL"]
        return all(self.get_setting(key) for key in required)
