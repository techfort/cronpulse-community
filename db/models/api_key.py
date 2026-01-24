from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from db.base import Base
from datetime import datetime


class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    api_key = Column(String, unique=True, nullable=False)  # Plaintext key for display
    key_hash = Column(String, unique=True, nullable=False)  # Hashed key for validation
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
