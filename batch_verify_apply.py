#!/usr/bin/env python3
"""Batch verify pending deposits against Flutterwave and optionally apply updates.

This script will *dry-run* by default: it prints which deposits would be marked completed
based on Flutterwave verification. Use --apply to actually update the SQL DB and Mongo.

Usage:
  python batch_verify_apply.py [--apply] [--limit N]

Notes:
 - Requires FLUTTERWAVE_SECRET_KEY set in .env and httpx installed.
 - If --apply is used, pymongo should be available and MongoDB reachable (MONGO_URI env).
"""
import asyncio
import argparse
import os
import sys
from datetime import datetime

from db.database import SessionLocal
from db.models import Deposit, Transaction
from db.mongo_client import get_mongo_db
from payment_service import flutterwave_service


async def verify_identifier(identifier: str):
    try:
        res = await flutterwave_service.verify_transaction_safe(identifier)
        return res
    except Exception as e:
        return e


def apply_updates(db, deposit: Deposit, fw_data: dict):
    # Mark deposit as completed, create transaction, update mongo
    try:
        deposit.status = "completed"
        deposit.flutterwave_transaction_id = str(fw_data.get("id") or fw_data.get("tx_id") or deposit.flutterwave_transaction_id)
        deposit.completed_at = datetime.utcnow()
        db.commit()

        # Create transaction record if none exists
        tx_exists = db.query(Transaction).filter(
            Transaction.user_id == deposit.user_id,
            Transaction.amount == deposit.amount,
            Transaction.transaction_type == "deposit",
            Transaction.created_at >= deposit.created_at
        ).first()
        if not tx_exists:
            tx = Transaction(
                user_id=deposit.user_id,
                transaction_type="deposit",
                amount=deposit.amount,
                currency=deposit.currency,
                status="completed",
                description=f"Deposit via Flutterwave (ref: {deposit.flutterwave_tx_ref})",
                created_at=datetime.utcnow()
            )
            db.add(tx)
            db.commit()

        # Update Mongo if available
        try:
            mongo_db = get_mongo_db()
            mongo_tx = {
                "user_id": deposit.user_id,
                "deposit_id": deposit.deposit_id,
                "tx_ref": deposit.flutterwave_tx_ref,
                "flutterwave_tx_id": deposit.flutterwave_transaction_id,
                "amount": float(deposit.amount),
                "currency": deposit.currency,
                "status": "completed",
                "created_at": deposit.created_at.isoformat(),
                "completed_at": deposit.completed_at.isoformat()
            }
            mongo_db.transactions.insert_one(mongo_tx)
            mongo_db.balances.update_one(
                {"user_id": deposit.user_id},
                {"$inc": {"available_balance": float(deposit.amount), "total_deposits": float(deposit.amount)}, "$setOnInsert": {"user_id": deposit.user_id}},
                upsert=True
            )
        except Exception:
            # Non-fatal if Mongo unavailable
            pass

        return True
    except Exception as e:
        db.rollback()
        raise


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply updates to DB and Mongo (default is dry-run)")
    parser.add_argument("--limit", type=int, default=50, help="Max pending deposits to process")
    args = parser.parse_args()

    db = SessionLocal()

    pending = db.query(Deposit).filter(Deposit.status == "pending").limit(args.limit).all()
    if not pending:
        print("No pending deposits found.")
        return

    print(f"Found {len(pending)} pending deposits; processing up to {args.limit} (apply={args.apply})")

    coros = []
    identifiers = []
    mapping = {}
    for d in pending:
        identifier = d.flutterwave_transaction_id or d.flutterwave_tx_ref
        if not identifier:
            continue
        identifiers.append(identifier)
        mapping[identifier] = d
        coros.append(verify_identifier(identifier))

    results = await asyncio.gather(*coros, return_exceptions=True)

    for ident, res in zip(identifiers, results):
        deposit = mapping[ident]
        print("---")
        print(f"Deposit {deposit.deposit_id} user={deposit.user_id} ident={ident} amount={deposit.amount} currency={deposit.currency}")

        if isinstance(res, Exception):
            print(f"Verification error: {res}")
            continue

        fw_status = res.get("status") or res.get("chargecode")
        fw_amount = res.get("amount") or res.get("charged_amount") or res.get("settlement_amount")
        print(f"Flutterwave status: {fw_status}; amount: {fw_amount}")

        if str(fw_status).lower() in ("successful", "success", "completed", "charge.completed"):
            print("Would mark as completed")
            if args.apply:
                try:
                    apply_updates(db, deposit, res)
                    print("Applied updates: deposit marked completed and Mongo updated (if available)")
                except Exception as e:
                    print("Failed to apply updates:", e)
        else:
            print("Not successful; skipping")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
