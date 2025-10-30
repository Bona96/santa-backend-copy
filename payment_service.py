import httpx
import os
import uuid
import hmac
import hashlib
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from models import Deposit, Withdrawal, Transaction, User
from schemas import DepositResponse, WithdrawalResponse

load_dotenv()

FLUTTERWAVE_PUBLIC_KEY = os.getenv("FLUTTERWAVE_PUBLIC_KEY", "")
FLUTTERWAVE_SECRET_KEY = os.getenv("FLUTTERWAVE_SECRET_KEY", "")
FLUTTERWAVE_ENCRYPTION_KEY = os.getenv("FLUTTERWAVE_ENCRYPTION_KEY", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

class FlutterwaveService:
    """Service for Flutterwave payment integration."""
    
    BASE_URL = "https://api.flutterwave.com/v3"
    
    def __init__(self):
        self.public_key = FLUTTERWAVE_PUBLIC_KEY
        self.secret_key = FLUTTERWAVE_SECRET_KEY
        self.encryption_key = FLUTTERWAVE_ENCRYPTION_KEY
    
    async def initiate_deposit(
        self,
        user: User,
        amount: float,
        currency: str,
        payment_method: str,
        db: Session
    ) -> DepositResponse:
        """Initiate a deposit transaction through Flutterwave."""
        
        # Generate unique transaction reference
        tx_ref = f"DEP_{user.user_id}_{datetime.utcnow().timestamp()}_{uuid.uuid4().hex[:8]}"
        
        # Create deposit record in database
        deposit = Deposit(
            user_id=user.user_id,
            amount=amount,
            currency=currency,
            flutterwave_tx_ref=tx_ref,
            status="pending",
            payment_method=payment_method,
            created_at=datetime.utcnow()
        )
        db.add(deposit)
        db.commit()
        db.refresh(deposit)
        
        # Prepare Flutterwave payment payload
        payload = {
            "tx_ref": tx_ref,
            "amount": str(int(amount)),
            "currency": currency,
            "redirect_url": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/payment-callback",
            "payment_options": payment_method,
            "customer": {
                "email": user.email,
                "phonenumber": user.phone_number or "",
                "name": user.username
            },
            "customizations": {
                "title": "Santa Daily Win Universe",
                "description": f"Deposit {currency} {amount}",
                "logo": "https://yourdomain.com/logo.png"
            },
            "meta": {
                "deposit_id": deposit.deposit_id,
                "user_id": user.user_id
            }
        }
        
        try:
            # Call Flutterwave API to get payment URL
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/payments",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code not in [200, 201]:
                    db.delete(deposit)
                    db.commit()
                    raise Exception(f"Failed to create Flutterwave payment: {response.text}")
                
                flutterwave_response = response.json()
                payment_link = flutterwave_response.get("data", {}).get("link")
                
                if not payment_link:
                    db.delete(deposit)
                    db.commit()
                    raise Exception("No payment link returned from Flutterwave")
            
            return DepositResponse(
                deposit_id=deposit.deposit_id,
                amount=deposit.amount,
                currency=deposit.currency,
                status=deposit.status,
                payment_url=payment_link
            )
        
        except Exception as e:
            db.rollback()
            raise Exception(f"Error initiating deposit: {str(e)}")
    
    async def verify_transaction(
        self,
        transaction_id: str
    ) -> dict:
        """Verify a transaction with Flutterwave."""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/transactions/{transaction_id}/verify",
                    headers={"Authorization": f"Bearer {self.secret_key}"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json().get("data", {})
                else:
                    raise Exception(f"Failed to verify transaction: {response.text}")
        
        except Exception as e:
            raise Exception(f"Error verifying transaction: {str(e)}")
    
    async def initiate_withdrawal(
        self,
        user: User,
        amount: float,
        currency: str,
        bank_code: str,
        account_number: str,
        account_name: str,
        db: Session
    ) -> WithdrawalResponse:
        """Initiate a withdrawal/transfer through Flutterwave."""
        
        # Create withdrawal record
        withdrawal = Withdrawal(
            user_id=user.user_id,
            amount=amount,
            currency=currency,
            bank_code=bank_code,
            account_number=account_number,
            account_name=account_name,
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(withdrawal)
        db.commit()
        db.refresh(withdrawal)
        
        # Prepare Flutterwave transfer payload
        transfer_payload = {
            "account_bank": bank_code,
            "account_number": account_number,
            "amount": int(amount),
            "currency": currency,
            "beneficiary_name": account_name,
            "reference": f"WDR_{withdrawal.withdrawal_id}_{datetime.utcnow().timestamp()}",
            "narration": "Santa Daily Win Universe Withdrawal",
            "debit_currency": currency
        }
        
        try:
            # Execute transfer through Flutterwave API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/transfers",
                    json=transfer_payload,
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code not in [200, 201]:
                    withdrawal.status = "failed"
                    db.commit()
                    error_data = response.json()
                    raise Exception(f"Transfer failed: {error_data.get('message', 'Unknown error')}")
                
                transfer_response = response.json()
                transfer_id = transfer_response.get("data", {}).get("id")
                
                if not transfer_id:
                    withdrawal.status = "failed"
                    db.commit()
                    raise Exception("No transfer ID returned from Flutterwave")
                
                # Update withdrawal with Flutterwave transfer ID
                withdrawal.flutterwave_transfer_id = str(transfer_id)
                withdrawal.status = "processing"
                
                # Create transaction record
                transaction = Transaction(
                    user_id=user.user_id,
                    transaction_type="withdrawal",
                    amount=amount,
                    currency=currency,
                    status="processing",
                    description=f"Withdrawal to {account_number}",
                    created_at=datetime.utcnow()
                )
                
                db.add(transaction)
                db.commit()
            
            return WithdrawalResponse(
                withdrawal_id=withdrawal.withdrawal_id,
                amount=withdrawal.amount,
                currency=withdrawal.currency,
                status=withdrawal.status,
                flutterwave_transfer_id=transfer_id
            )
        
        except Exception as e:
            db.rollback()
            raise Exception(f"Error initiating withdrawal: {str(e)}")
    
    def verify_webhook_signature(self, request_body: str, signature: str) -> bool:
        """Verify that incoming webhook is genuinely from Flutterwave."""
        expected_signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            request_body.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)

# Create singleton instance
flutterwave_service = FlutterwaveService()
