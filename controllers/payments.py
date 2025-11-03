from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
from db.models import Deposit, Transaction
from schemas import DepositRequest, DepositResponse
from payment_service import flutterwave_service
from db.mongo_client import get_mongo_db


async def initiate_deposit(user, deposit_request: DepositRequest, db: Session) -> DepositResponse:
    try:
        if deposit_request.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        if deposit_request.amount > 50000000:
            raise HTTPException(status_code=400, detail="Maximum deposit amount exceeded")

        result = await flutterwave_service.initiate_deposit(
            user=user,
            amount=deposit_request.amount,
            currency=deposit_request.currency,
            payment_method=deposit_request.payment_method,
            db=db
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def verify_deposit_status(deposit_id: int, current_user, db: Session):
    try:
        deposit = db.query(Deposit).filter(Deposit.deposit_id == deposit_id, Deposit.user_id == current_user.user_id).first()
        if not deposit:
            raise HTTPException(status_code=404, detail="Deposit not found")
        if deposit.status == "completed":
            return {
                "deposit_id": deposit.deposit_id,
                "status": deposit.status,
                "amount": deposit.amount,
                "currency": deposit.currency,
                "tx_ref": deposit.flutterwave_tx_ref
            }

        identifier = deposit.flutterwave_transaction_id or deposit.flutterwave_tx_ref
        if not identifier:
            return {"deposit_id": deposit.deposit_id, "status": deposit.status, "message": "No external identifier to verify"}

        try:
            fw_data = await flutterwave_service.verify_transaction(identifier)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

        fw_status = fw_data.get("status") or fw_data.get("chargecode") or fw_data.get("tx_ref")
        if str(fw_status).lower() in ("successful", "success", "completed", "charge.completed"):
            deposit.status = "completed"
            deposit.flutterwave_transaction_id = str(fw_data.get("id") or fw_data.get("tx_id") or deposit.flutterwave_transaction_id)
            deposit.completed_at = datetime.utcnow()
            db.commit()

            tx_exists = db.query(Transaction).filter(
                Transaction.user_id == deposit.user_id,
                Transaction.amount == deposit.amount,
                Transaction.transaction_type == "deposit",
                Transaction.created_at >= deposit.created_at
            ).first()
            if not tx_exists:
                transaction = Transaction(
                    user_id=deposit.user_id,
                    transaction_type="deposit",
                    amount=deposit.amount,
                    currency=deposit.currency,
                    status="completed",
                    description=f"Deposit via Flutterwave (ref: {deposit.flutterwave_tx_ref})",
                    created_at=datetime.utcnow()
                )
                db.add(transaction)
                db.commit()

            try:
                mongo_db = get_mongo_db()
                mongo_db.transactions.insert_one({
                    "user_id": deposit.user_id,
                    "deposit_id": deposit.deposit_id,
                    "tx_ref": deposit.flutterwave_tx_ref,
                    "flutterwave_tx_id": deposit.flutterwave_transaction_id,
                    "amount": float(deposit.amount),
                    "currency": deposit.currency,
                    "status": "completed",
                    "created_at": deposit.created_at.isoformat(),
                    "completed_at": deposit.completed_at.isoformat()
                })
                mongo_db.balances.update_one(
                    {"user_id": deposit.user_id},
                    {"$inc": {"available_balance": float(deposit.amount), "total_deposits": float(deposit.amount)}, "$setOnInsert": {"user_id": deposit.user_id}},
                    upsert=True
                )
            except Exception:
                pass

        return {"deposit_id": deposit.deposit_id, "status": deposit.status}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_webhook(request: Request, db: Session):
    try:
        raw_body = await request.body()
        body_text = raw_body.decode()
        from payment_service import flutterwave_service as fw

        signature = request.headers.get("verif-hash") or request.headers.get("x-flutterwave-signature")

        if not signature or not fw.verify_webhook_signature(body_text, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

        payload = await request.json()
        data = payload.get("data", {})
        status = data.get("status") or payload.get("event")

        if str(status).lower() not in ("successful", "success", "completed", "charge.completed"):
            try:
                mongo_db = get_mongo_db()
                mongo_db.webhook_events.insert_one({"payload": payload, "received_at": datetime.utcnow().isoformat()})
            except Exception:
                pass
            return {"success": True, "message": "Ignored non-successful webhook event"}

        tx_ref = data.get("tx_ref") or data.get("reference") or data.get("flw_ref")
        flutterwave_tx_id = data.get("id") or data.get("tx_id") or data.get("flw_ref")

        if not tx_ref:
            raise HTTPException(status_code=400, detail="tx_ref missing in webhook payload")

        deposit = db.query(Deposit).filter(Deposit.flutterwave_tx_ref == tx_ref).first()
        mongo_db = get_mongo_db()

        if deposit:
            deposit.status = "completed"
            deposit.flutterwave_transaction_id = str(flutterwave_tx_id)
            deposit.completed_at = datetime.utcnow()
            db.commit()

            transaction = Transaction(
                user_id=deposit.user_id,
                transaction_type="deposit",
                amount=deposit.amount,
                currency=deposit.currency,
                status="completed",
                description=f"Deposit via Flutterwave (ref: {tx_ref})",
                created_at=datetime.utcnow()
            )
            db.add(transaction)
            db.commit()

            try:
                mongo_tx = {
                    "user_id": deposit.user_id,
                    "deposit_id": deposit.deposit_id,
                    "tx_ref": tx_ref,
                    "flutterwave_tx_id": str(flutterwave_tx_id),
                    "amount": float(deposit.amount),
                    "currency": deposit.currency,
                    "status": "completed",
                    "created_at": deposit.created_at.isoformat(),
                    "completed_at": deposit.completed_at.isoformat()
                }
                mongo_db.transactions.insert_one(mongo_tx)
                mongo_db.balances.update_one(
                    {"user_id": deposit.user_id},
                    {
                        "$inc": {"available_balance": float(deposit.amount), "total_deposits": float(deposit.amount)},
                        "$setOnInsert": {"user_id": deposit.user_id}
                    },
                    upsert=True
                )
            except Exception:
                pass

            return {"success": True, "message": "Processed deposit webhook"}

        else:
            try:
                mongo_db.webhook_events.insert_one({"payload": payload, "received_at": datetime.utcnow().isoformat()})
            except Exception:
                pass
            return {"success": True, "message": "No matching deposit found; event stored"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
