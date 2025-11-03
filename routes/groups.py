from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from auth import get_current_user
from controllers.groups import get_groups, create_group, join_group
from schemas import GroupCreate, GroupJoinRequest

router = APIRouter(prefix="/groups")


@router.get("/")
async def list_groups(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_groups(current_user, db)


@router.post("/", response_model=GroupCreate)
async def post_group(group_data: GroupCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return create_group(group_data, current_user, db)


@router.post("/{group_id}/join")
async def post_join(group_id: int, join_data: GroupJoinRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return join_group(group_id, join_data, current_user, db)
