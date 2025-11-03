from sqlalchemy.orm import Session
from fastapi import HTTPException
from db.models import Transaction
from schemas import TransactionResponse


def get_transactions(limit: int, offset: int, transaction_type: str, current_user, db: Session):
    try:
        query = db.query(Transaction).filter(Transaction.user_id == current_user.user_id)
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)

        transactions = query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
