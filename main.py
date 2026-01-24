from fastapi import FastAPI, Request, HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.concurrency import asynccontextmanager
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from api import router as api_router
from api.services.monitor_service import MonitorService
from api.services.user_service import UserService
from db.engine import SessionLocal
from db.repositories.monitor_repository import MonitorRepository
from db.repositories.user_repository import UserRepository
import logging
import os
from ui import router as ui_router
from ui.utils import render_template


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    filename="log.txt",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
    initialize_admin_user()
    start_scheduler()
    yield
    # Shutdown code (if needed)
    # scheduler.shutdown()  # if you want to stop the scheduler gracefully


app = FastAPI(lifespan=lifespan)
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
    monitor_service = MonitorService(monitor_repo, user_repo)
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
