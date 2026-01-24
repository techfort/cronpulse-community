from fastapi import APIRouter
from .auth import router as auth_router
from .dashboard import router as dashboard_router
from .monitors import router as monitors_router
from .api_keys import router as api_keys_router
from .landing import router as landing_router
from .docs import router as docs_router
from .admin import router as admin_router

router = APIRouter()
router.include_router(landing_router)
router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(monitors_router)
router.include_router(api_keys_router)
router.include_router(admin_router)
router.include_router(docs_router)
