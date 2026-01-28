from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.engine import SessionLocal
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint for monitoring and load balancers.
    Returns 200 OK if the application is healthy.
    """
    try:
        # Test database connectivity
        db.execute(text("SELECT 1"))
        
        # Check if scheduler is running (imported from main)
        from main import scheduler
        scheduler_status = "running" if scheduler and scheduler.running else "stopped"
        
        return {
            "status": "healthy",
            "database": "connected",
            "scheduler": scheduler_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
