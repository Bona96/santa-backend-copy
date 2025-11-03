from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
from auth import get_password_hash, verify_password, create_access_token
from db.models import User
from helpers import calculate_user_stats
from schemas import UserRegister, UserLogin, TokenResponse, UserResponse


def register_user(user_data: UserRegister, db: Session) -> TokenResponse:
    try:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hashed_password,
            phone_number=user_data.phone_number,
            country=user_data.country,
            age=user_data.age,
            created_at=datetime.utcnow()
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        access_token = create_access_token(data={"user_id": new_user.user_id})

        stats = calculate_user_stats(new_user.user_id, db)

        user_response = UserResponse(
            user_id=new_user.user_id,
            username=new_user.username,
            email=new_user.email,
            country=new_user.country,
            age=new_user.age,
            phone_number=new_user.phone_number,
            profile_picture=new_user.profile_picture,
            **stats
        )

        return TokenResponse(access_token=access_token, user=user_response)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def login_user(user_data: UserLogin, db: Session) -> TokenResponse:
    try:
        user = db.query(User).filter(User.email == user_data.email).first()
        if not user or not verify_password(user_data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        access_token = create_access_token(data={"user_id": user.user_id})
        stats = calculate_user_stats(user.user_id, db)

        user_response = UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            country=user.country,
            age=user.age,
            phone_number=user.phone_number,
            profile_picture=user.profile_picture,
            **stats
        )

        return TokenResponse(access_token=access_token, user=user_response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
