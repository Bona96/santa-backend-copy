from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from auth import get_current_user
from controllers.shuffle import get_shuffle_participants, join_shuffle
from schemas import ShuffleJoinRequest

router = APIRouter(prefix="/shuffle")


@router.get("/participants")
async def participants(db: Session = Depends(get_db)):
    return get_shuffle_participants(db)


@router.post("/join")
async def join(shuffle_data: ShuffleJoinRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return join_shuffle(shuffle_data, current_user, db)
