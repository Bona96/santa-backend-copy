from fastapi import HTTPException
from sqlalchemy.orm import Session
from db.models import Withdrawal, User
from payment_service import flutterwave_service


def list_pending_withdrawals(db: Session):
    try:
        pending = db.query(Withdrawal).filter(Withdrawal.status == "pending").all()
        result = [
            {
                "withdrawal_id": w.withdrawal_id,
                "user_id": w.user_id,
                "amount": w.amount,
                "currency": w.currency,
                "bank_code": w.bank_code,
                "account_number": w.account_number,
                "account_name": w.account_name,
                "created_at": w.created_at.isoformat()
            }
            for w in pending
        ]
        return {"pending_withdrawals": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def approve_withdrawal(withdrawal_id: int, db: Session):
    try:
        withdrawal = db.query(Withdrawal).filter(Withdrawal.withdrawal_id == withdrawal_id).first()
        if not withdrawal:
            raise HTTPException(status_code=404, detail="Withdrawal not found")

        if withdrawal.status != "pending":
            raise HTTPException(status_code=400, detail="Withdrawal is not pending")

        user = db.query(User).filter(User.user_id == withdrawal.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Associated user not found")

        try:
            result = await flutterwave_service.execute_withdrawal(withdrawal, user, db)
            return {"success": True, "result": result}
        except Exception as e:
            withdrawal.status = "failed"
            db.commit()
            raise HTTPException(status_code=500, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def reject_withdrawal(withdrawal_id: int, reason: str, db: Session):
    try:
        withdrawal = db.query(Withdrawal).filter(Withdrawal.withdrawal_id == withdrawal_id).first()
        if not withdrawal:
            raise HTTPException(status_code=404, detail="Withdrawal not found")

        if withdrawal.status != "pending":
            raise HTTPException(status_code=400, detail="Withdrawal is not pending")

        withdrawal.status = "rejected"
        db.commit()
        return {"success": True, "withdrawal_id": withdrawal_id, "status": "rejected", "reason": reason}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
