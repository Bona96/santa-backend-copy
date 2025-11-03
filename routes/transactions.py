from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from auth import get_current_user
from controllers.transactions import get_transactions

router = APIRouter(prefix="/transactions")


@router.get("/")
async def list_transactions(limit: int = 50, offset: int = 0, transaction_type: str = None, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_transactions(limit, offset, transaction_type, current_user, db)
