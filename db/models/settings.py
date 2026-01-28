from sqlalchemy import Column, Integer, String, Boolean
from db.base import Base


class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(String, nullable=True)
    is_secret = Column(Boolean, default=False)  # Don't expose in API
