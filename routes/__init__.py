"""Routes package: combine and expose routers for the FastAPI app."""

from .auth import router as auth_router
from .users import router as users_router
from .payments import router as payments_router
from .admin import router as admin_router

__all__ = ["auth_router", "users_router", "payments_router", "admin_router"]
