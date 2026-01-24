from sqlalchemy import Column, Integer, String, Boolean
from db.base import Base

# Subscription status constants
SUBSCRIPTION_ACTIVE = "active"
SUBSCRIPTION_INACTIVE = "inactive"
SUBSCRIPTION_TRIALING = "trialing"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    pricing_plan_id = Column(Integer, nullable=True)
    subscription_status = Column(String, default=SUBSCRIPTION_INACTIVE)
