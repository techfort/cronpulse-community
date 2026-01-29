from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.base import Base
from db.models import User, Monitor, ApiKey  # noqa: F401
import os

# SQLite database setup
# Use environment variable or default to local file
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/monitors.db")

# Create data directory if it doesn't exist
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# Use check_same_thread only for SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(engine)
print("Tables created:", Base.metadata.tables.keys())
