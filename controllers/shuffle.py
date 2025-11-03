from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from db.models import ShuffleParticipant, User
from schemas import ShuffleParticipantResponse


def get_shuffle_participants(db: Session):
    try:
        today = datetime.utcnow().date()
        participants = db.query(ShuffleParticipant, User).join(
            User, ShuffleParticipant.user_id == User.user_id
        ).filter(ShuffleParticipant.shuffle_date >= today).all()

        result = []
        for participant, user in participants:
            result.append(ShuffleParticipantResponse(
                username=user.username,
                avatar=user.username[0].upper(),
                country=user.country
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def join_shuffle(shuffle_data, current_user, db: Session):
    try:
        today = datetime.utcnow().date()
        existing = db.query(ShuffleParticipant).filter(
            (ShuffleParticipant.user_id == current_user.user_id) &
            (ShuffleParticipant.shuffle_date >= today) &
            (ShuffleParticipant.jackpot_type == shuffle_data.jackpot_type)
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Already joined today's shuffle")

        participant = ShuffleParticipant(
            user_id=current_user.user_id,
            shuffle_date=datetime.utcnow(),
            jackpot_type=shuffle_data.jackpot_type,
            group_id=shuffle_data.group_id,
            created_at=datetime.utcnow()
        )
        db.add(participant)
        db.commit()

        return {"success": True, "message": "Successfully joined the shuffle!", "jackpot_type": shuffle_data.jackpot_type}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
