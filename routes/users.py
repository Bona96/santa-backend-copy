from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from auth import get_current_user
from controllers.users import get_user_info, get_balance, update_profile
from schemas import UserResponse, BalanceResponse

router = APIRouter(prefix="/users")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_user_info(current_user, db)


@router.get("/balance", response_model=BalanceResponse)
async def balance(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_balance(current_user, db)


@router.put("/me", response_model=UserResponse)
async def update_me(profile_picture: str = None, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return update_profile(current_user, db, profile_picture)
