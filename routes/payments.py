from fastapi import APIRouter, Depends, Request, Body
from sqlalchemy.orm import Session
from db.database import get_db
from auth import get_current_user
from controllers.payments import initiate_deposit, verify_deposit_status, handle_webhook
from schemas import DepositRequest, DepositResponse

router = APIRouter(prefix="/payments")


@router.post("/deposit/initiate", response_model=DepositResponse)
async def deposit_initiate(deposit_request: DepositRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return await initiate_deposit(current_user, deposit_request, db)


@router.get("/deposit/{deposit_id}/verify")
async def deposit_verify(deposit_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return await verify_deposit_status(deposit_id, current_user, db)


@router.post("/webhook")
async def webhook_endpoint(request: Request, db: Session = Depends(get_db)):
    return await handle_webhook(request, db)


class ManualConfirmPayload:
    pass
