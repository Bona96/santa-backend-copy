from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from controllers.jackpot import get_global_jackpot

router = APIRouter(prefix="/jackpot")


@router.get("/global")
async def global_jackpot(db: Session = Depends(get_db)):
    return get_global_jackpot(db)
