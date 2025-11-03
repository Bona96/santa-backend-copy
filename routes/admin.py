from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from db.database import get_db
from auth import require_admin
from controllers.admin import list_pending_withdrawals, approve_withdrawal, reject_withdrawal

router = APIRouter(prefix="/admin")


@router.get("/withdrawals")
async def get_pending_withdrawals(current_admin=Depends(require_admin), db: Session = Depends(get_db)):
    return list_pending_withdrawals(db)


@router.post("/withdrawals/{withdrawal_id}/approve")
async def approve(withdrawal_id: int, current_admin=Depends(require_admin), db: Session = Depends(get_db)):
    return await approve_withdrawal(withdrawal_id, db)


@router.post("/withdrawals/{withdrawal_id}/reject")
async def reject(withdrawal_id: int, reason: str = Body(None), current_admin=Depends(require_admin), db: Session = Depends(get_db)):
    return reject_withdrawal(withdrawal_id, reason, db)
