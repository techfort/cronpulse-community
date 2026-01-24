from fastapi import APIRouter
from .auth import router as auth_router
from .monitors import router as monitors_router
from .api_keys import router as api_keys_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(monitors_router)
router.include_router(api_keys_router)
