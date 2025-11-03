from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from controllers.winners import get_recent_winners

router = APIRouter(prefix="/winners")


@router.get("/recent")
async def recent(limit: int = 10, db: Session = Depends(get_db)):
    return get_recent_winners(limit, db)
