from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from controllers.auth import register_user, login_user
from schemas import UserRegister, UserLogin, TokenResponse

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    return register_user(user_data, db)


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    return login_user(user_data, db)
