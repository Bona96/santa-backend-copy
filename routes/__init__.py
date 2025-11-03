"""Routes package: combine and expose routers for the FastAPI app."""

from .auth import router as auth_router
from .users import router as users_router
from .payments import router as payments_router
from .admin import router as admin_router
from .groups import router as groups_router
from .transactions import router as transactions_router
from .shuffle import router as shuffle_router
from .winners import router as winners_router
from .jackpot import router as jackpot_router

__all__ = [
	"auth_router", "users_router", "payments_router", "admin_router",
	"groups_router", "transactions_router", "shuffle_router", "winners_router", "jackpot_router"
]
