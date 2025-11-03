from fastapi import HTTPException
from sqlalchemy.orm import Session
from auth import get_current_user
from db.models import User
from helpers import calculate_user_stats, calculate_user_balance
from schemas import UserResponse, BalanceResponse


def get_user_info(current_user: User, db: Session) -> UserResponse:
    stats = calculate_user_stats(current_user.user_id, db)
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        country=current_user.country,
        age=current_user.age,
        phone_number=current_user.phone_number,
        profile_picture=current_user.profile_picture,
        **stats
    )


def get_balance(current_user: User, db: Session) -> BalanceResponse:
    # Prefer Mongo when possible; the routes will call the helper that uses Mongo if available.
    # Here we delegate to helpers.calculate_user_balance for fallback.
    try:
        from db.mongo_client import get_mongo_db
        from payment_service import flutterwave_service
        import asyncio

        mongo_db = get_mongo_db()
        mongo_balance = mongo_db.balances.find_one({"user_id": current_user.user_id})
        if mongo_balance:
            # Keep behavior simple here: return mongo-stored balance
            return BalanceResponse(
                available_balance=float(mongo_balance.get("available_balance", 0.0)),
                total_deposits=float(mongo_balance.get("total_deposits", 0.0)),
                total_withdrawals=float(mongo_balance.get("total_withdrawals", 0.0)),
                pending_withdrawals=float(mongo_balance.get("pending_withdrawals", 0.0)),
                net_available=float(mongo_balance.get("available_balance", 0.0)) - float(mongo_balance.get("pending_withdrawals", 0.0))
            )
    except Exception:
        # Fall back to SQL calculation
        pass

    return calculate_user_balance(current_user.user_id, db)


def update_profile(current_user: User, db: Session, profile_picture: str = None) -> UserResponse:
    try:
        if profile_picture:
            current_user.profile_picture = profile_picture
        db.commit()
        db.refresh(current_user)
        stats = calculate_user_stats(current_user.user_id, db)
        return UserResponse(
            user_id=current_user.user_id,
            username=current_user.username,
            email=current_user.email,
            country=current_user.country,
            age=current_user.age,
            phone_number=current_user.phone_number,
            profile_picture=current_user.profile_picture,
            **stats
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
