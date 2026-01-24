from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from db.base import Base


class Monitor(Base):
    __tablename__ = "monitors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    interval = Column(Float)
    last_ping = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id"))
    email_recipient = Column(String, nullable=True)  # Added
    webhook_url = Column(String, nullable=True)  # Added
    expires_at = Column(DateTime, nullable=True)  # Added
