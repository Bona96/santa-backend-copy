from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, status, Body
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from db.database import engine, get_db
from db.models import Base, User, Deposit, Withdrawal, Transaction, Group, GroupMember, ShuffleParticipant, GlobalJackpot, Winner
from schemas import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    DepositRequest, DepositResponse, WithdrawalRequest, WithdrawalResponse,
    TransactionResponse, BalanceResponse, GroupCreate, GroupResponse,
    ShuffleJoinRequest, ShuffleParticipantResponse, WinnerResponse, GroupJoinRequest
)
from auth import get_password_hash, verify_password, create_access_token, get_current_user
from payment_service import flutterwave_service
from auth import require_admin
from db.mongo_client import get_mongo_db
from helpers import calculate_user_balance, calculate_user_stats, validate_withdrawal_eligibility
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create all database tables
Base.metadata.create_all(bind=engine)

# Create the main app
# Enable debug if DEBUG env var is set to 'True' (useful in development)
DEBUG_MODE = os.getenv("DEBUG", "False").lower() in ("1", "true", "yes")
app = FastAPI(title="Santa Daily Win Universe API", debug=DEBUG_MODE)

# Import and include modular routers from the routes package
from routes import (
    auth_router, users_router, payments_router, admin_router,
    groups_router, transactions_router, shuffle_router, winners_router, jackpot_router
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(payments_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(groups_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(shuffle_router, prefix="/api")
app.include_router(winners_router, prefix="/api")
app.include_router(jackpot_router, prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global exception handlers to log full tracebacks for easier debugging.
from fastapi.exception_handlers import http_exception_handler as fastapi_http_exception_handler
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def log_unhandled_exceptions(request: Request, exc: Exception):
    # Log full traceback to console/file
    logger.error("Unhandled exception caught:", exc_info=exc)
    # In debug mode return the exception detail in the response (useful for local dev).
    if DEBUG_MODE:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    # Otherwise return a generic 500 response so we don't leak internals in production.
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # Log server errors (5xx) with stack information where available
    if exc.status_code >= 500:
        logger.error(f"HTTPException {exc.status_code}: {exc.detail}", exc_info=exc)
        # In debug mode include the detail in the response body
        if DEBUG_MODE:
            return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})
    # Delegate to FastAPI's default handler for proper client response
    return await fastapi_http_exception_handler(request, exc)

@app.get("/api/")
async def root():
    return {"message": "Santa Daily Win Universe API"}

# Note: individual routers are included above from the `routes` package.

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.getenv("FRONTEND_URL"),
        "https://*.emergent.host",  # Production domain pattern
        "*"  # Allow all origins for development (remove in strict production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")

if __name__ == "__main__":
    import uvicorn
    # Respect the PORT environment variable provided by hosting platforms (e.g., Railway)
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
