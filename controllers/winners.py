from fastapi import HTTPException
from sqlalchemy.orm import Session
from db.models import Winner, User
from schemas import WinnerResponse


def get_recent_winners(limit: int, db: Session):
    try:
        winners = db.query(Winner, User).join(User, Winner.user_id == User.user_id).order_by(Winner.won_at.desc()).limit(limit).all()
        result = []
        for winner, user in winners:
            result.append(WinnerResponse(
                username=user.username,
                message=f"Won ${winner.amount_won}!",
                avatar=user.username[0].upper(),
                country=user.country
            ))
        return result
    except Exception as e:
        # Return empty list on error to avoid exposing internals
        raise HTTPException(status_code=500, detail=str(e))
