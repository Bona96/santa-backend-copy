from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from db.models import Group, GroupMember
from schemas import GroupCreate, GroupResponse


def get_groups(current_user, db: Session):
    try:
        groups = db.query(Group).filter(
            (Group.creator_user_id == current_user.user_id) |
            (Group.group_id.in_(
                db.query(GroupMember.group_id).filter(
                    GroupMember.user_id == current_user.user_id
                )
            ))
        ).all()

        result = []
        for group in groups:
            members_count = db.query(GroupMember).filter(
                GroupMember.group_id == group.group_id
            ).count()

            result.append(GroupResponse(
                group_id=group.group_id,
                name=group.name,
                type=group.type,
                members_count=members_count,
                current_jackpot=group.current_jackpot,
                min_contribution=group.min_contribution,
                hierarchy_type=group.hierarchy_type or "equal",
                currency=group.currency or "USD"
            ))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_group(group_data: GroupCreate, current_user, db: Session):
    try:
        new_group = Group(
            name=group_data.name,
            type=group_data.type,
            creator_user_id=current_user.user_id,
            min_contribution=group_data.min_contribution,
            hierarchy_type=group_data.hierarchy_type,
            currency=group_data.currency,
            current_jackpot=0.0,
            created_at=datetime.utcnow()
        )
        db.add(new_group)
        db.commit()
        db.refresh(new_group)

        member = GroupMember(
            group_id=new_group.group_id,
            user_id=current_user.user_id,
            contribution_amount=0.0,
            joined_at=datetime.utcnow()
        )
        db.add(member)
        db.commit()

        return GroupResponse(
            group_id=new_group.group_id,
            name=new_group.name,
            type=new_group.type,
            members_count=1,
            current_jackpot=new_group.current_jackpot,
            min_contribution=new_group.min_contribution,
            hierarchy_type=new_group.hierarchy_type,
            currency=new_group.currency
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def join_group(group_id: int, join_data, current_user, db: Session):
    try:
        group = db.query(Group).filter(Group.group_id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        existing_member = db.query(GroupMember).filter(
            (GroupMember.group_id == group_id) &
            (GroupMember.user_id == current_user.user_id)
        ).first()

        if existing_member:
            existing_member.contribution_amount += join_data.contribution_amount
        else:
            member = GroupMember(
                group_id=group_id,
                user_id=current_user.user_id,
                contribution_amount=join_data.contribution_amount,
                joined_at=datetime.utcnow()
            )
            db.add(member)

        group.current_jackpot += join_data.contribution_amount
        db.commit()

        return {
            "success": True,
            "message": f"Contributed ${join_data.contribution_amount} to {group.name}",
            "group_jackpot": group.current_jackpot
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
