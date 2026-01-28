from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.concurrency import asynccontextmanager
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from api import router as api_router
from api.health import router as health_router
from api.services.monitor_service import MonitorService
from api.services.user_service import UserService
from db.engine import SessionLocal
from db.repositories.monitor_repository import MonitorRepository
from db.repositories.user_repository import UserRepository
from db.repositories.settings_repository import SettingsRepository
import logging
import os
import secrets
from ui import router as ui_router
from ui.utils import render_template


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    filename="log.txt",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def ensure_jwt_secret():
    """Ensure JWT_SECRET exists and is secure"""
    jwt_secret = os.getenv("JWT_SECRET")
    
    # Check for insecure defaults
    insecure_defaults = [
        "change-me-in-production",
        "change-me-to-random-string",
        "your-secret-key-here",
    ]
    
    if not jwt_secret or jwt_secret in insecure_defaults:
        # Generate a secure random secret
        new_secret = secrets.token_hex(32)
        logger.warning(
            "JWT_SECRET not set or insecure! Generated secure random secret. "
            "Please set JWT_SECRET in your environment for production."
        )
        
        # Try to save to settings database
        try:
            db = SessionLocal()
            settings_repo = SettingsRepository(db)
            settings_repo.set_setting("JWT_SECRET", new_secret, is_secret=True)
            logger.info("Generated JWT_SECRET saved to database")
            db.close()
        except Exception as e:
            logger.error(f"Failed to save JWT_SECRET to database: {e}")
        
        os.environ["JWT_SECRET"] = new_secret
        return new_secret
    
    return jwt_secret


def initialize_admin_user():
    """Create admin user from environment variables if no users exist"""
    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        user_service = UserService(user_repo)
        
        # Check if any users exist
        existing_users = user_repo.list_users(limit=1)
        if existing_users:
            logger.info(f"Users already exist ({len(existing_users)} found), skipping admin creation")
            return
        
        # Check for admin credentials in environment
        admin_email = os.getenv("ADMIN_EMAIL")
        admin_password = os.getenv("ADMIN_PASSWORD")
        
        if admin_email and admin_password:
            logger.info(f"Creating admin user from environment variables: {admin_email}")
            user = user_service.signup(admin_email, admin_password)
            # Mark as admin
            user_repo.update_user(user.id, {"is_admin": True})
            logger.info(f"Admin user created successfully: {admin_email}")
        else:
            logger.info("No admin credentials in environment. First-run setup will be required.")
    except Exception as e:
        logger.error(f"Error initializing admin user: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("adding lifespan events")
    # Startup code
    ensure_jwt_secret()
    initialize_admin_user()
    start_scheduler()
    yield
    # Shutdown code (if needed)
    # scheduler.shutdown()  # if you want to stop the scheduler gracefully


app = FastAPI(lifespan=lifespan)

# Rate limiting setup
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration - Allow same-origin by default, customize for production
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
if allowed_origins == ["*"]:
    logger.warning(
        "CORS is set to allow all origins (*). "
        "Set CORS_ORIGINS environment variable to restrict origins in production."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=600,
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.include_router(health_router)
app.include_router(api_router, prefix="/api")
app.include_router(ui_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


scheduler = None


def check_missed_pings(monitor_service: MonitorService):
    def check():
        logger.info("Checking for missed pings...")
        monitor_service.check_missed_pings()

    return check


# Initialize scheduler with MonitorService
def init_scheduler(monitor_service: MonitorService):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_missed_pings(monitor_service=monitor_service),
        "interval",
        seconds=30,
        id="check_missed_pings_job",
    )
    return scheduler


def start_scheduler():
    global scheduler
    print("Starting scheduler...")  # Debug print
    db = SessionLocal()
    monitor_repo = MonitorRepository(db)
    user_repo = UserRepository(db)
    
    # Import here to avoid circular dependency
    from db.repositories.settings_repository import SettingsRepository
    settings_repo = SettingsRepository(db)
    
    monitor_service = MonitorService(monitor_repo, user_repo, settings_repo)
    scheduler = init_scheduler(monitor_service)
    from apscheduler.events import EVENT_JOB_ERROR

    def job_error_listener(event):
        print(f"Job crashed: {event}")

    scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)
    scheduler.start()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    context = {"error": exc.detail, "status_code": exc.status_code}
    return render_template(request, "error.html", context, status_code=exc.status_code)


print(app.routes)
