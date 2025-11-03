from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from db.models import Deposit, GlobalJackpot


def get_global_jackpot(db: Session):
    try:
        total_deposits = db.query(func.sum(Deposit.amount)).filter(Deposit.status == "completed").scalar() or 0.0

        jackpot = db.query(GlobalJackpot).first()
        if not jackpot:
            jackpot = GlobalJackpot(current_amount=total_deposits, currency="USD", updated_at=datetime.utcnow())
            db.add(jackpot)
            db.commit()
            db.refresh(jackpot)
        else:
            jackpot.current_amount = total_deposits
            jackpot.updated_at = datetime.utcnow()
            db.commit()

        return {"jackpot_id": jackpot.jackpot_id, "current_amount": total_deposits, "currency": "Multi-Currency", "updated_at": jackpot.updated_at}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
