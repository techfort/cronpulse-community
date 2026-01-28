from fastapi import APIRouter
from slowapi import Limiter
from slowapi.util import get_remote_address
from .auth import router as auth_router
from .monitors import router as monitors_router
from .api_keys import router as api_keys_router

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()
router.include_router(auth_router)
router.include_router(monitors_router)
router.include_router(api_keys_router)
