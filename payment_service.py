import httpx
import os
import uuid
import hmac
import hashlib
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from db.models import Deposit, Withdrawal, Transaction, User
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
        # Lightweight runtime check: collect missing keys for diagnostics
        self._missing_keys = [
            name for name, val in (
                ("FLUTTERWAVE_PUBLIC_KEY", self.public_key),
                ("FLUTTERWAVE_SECRET_KEY", self.secret_key),
                ("FLUTTERWAVE_ENCRYPTION_KEY", self.encryption_key),
            ) if not val
        ]
    
    async def initiate_deposit(
        self,
        user: User,
        amount: float,
        currency: str,
        payment_method: str,
        db: Session
    ) -> DepositResponse:
        """Initiate a deposit transaction through Flutterwave."""
        # Fail early if required keys are missing to avoid creating DB rows
        if self._missing_keys:
            raise Exception(f"Missing Flutterwave configuration: {', '.join(self._missing_keys)}")

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
            # Use FRONTEND_URL if configured; default to port 3000 (frontend dev server)
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
                payment_url=payment_link,
                tx_ref=tx_ref
            )
        
        except Exception as e:
            db.rollback()
            # Re-raise with context so caller can see it's specific to deposit initiation
            raise Exception(f"Error initiating deposit: {str(e)}")
    
    async def verify_transaction(
        self,
        transaction_id: str
    ) -> dict:
        """Verify a transaction with Flutterwave."""
        if not self.secret_key:
            raise Exception("Missing FLUTTERWAVE_SECRET_KEY for transaction verification")
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

    async def verify_transaction_safe(self, identifier: str) -> dict:
        """Try to verify a transaction using either transaction id or tx_ref.

        Flutterwave verification endpoint may accept different identifier forms depending
        on what you stored. Try by id first, then by tx_ref.
        """
        # Try by id first
        try:
            return await self.verify_transaction(identifier)
        except Exception:
            # If that fails, try using the identifier as tx_ref (Fluterwave may accept it)
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.BASE_URL}/transactions/verify_by_txref?tx_ref={identifier}",
                        headers={"Authorization": f"Bearer {self.secret_key}"},
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        return response.json().get("data", {})
                    else:
                        # Fall back to raising an error similar to verify_transaction
                        raise Exception(f"Failed to verify by tx_ref: {response.text}")
            except Exception as e:
                raise Exception(f"Error verifying transaction safely: {str(e)}")
    
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
        # Fail early if required keys are missing to avoid creating DB rows
        if self._missing_keys:
            raise Exception(f"Missing Flutterwave configuration: {', '.join(self._missing_keys)}")

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

    async def execute_withdrawal(self, withdrawal: Withdrawal, user: User, db: Session) -> WithdrawalResponse:
        """Execute a transfer for an existing withdrawal record using Flutterwave.

        This avoids creating duplicate withdrawal records and updates the provided
        withdrawal instance with the transfer id and status.
        """
        if self._missing_keys:
            raise Exception(f"Missing Flutterwave configuration: {', '.join(self._missing_keys)}")

        transfer_payload = {
            "account_bank": withdrawal.bank_code,
            "account_number": withdrawal.account_number,
            "amount": int(withdrawal.amount),
            "currency": withdrawal.currency,
            "beneficiary_name": withdrawal.account_name,
            "reference": f"WDR_{withdrawal.withdrawal_id}_{datetime.utcnow().timestamp()}",
            "narration": "Santa Daily Win Universe Withdrawal",
            "debit_currency": withdrawal.currency
        }

        try:
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

                # Update withdrawal with Flutterwave transfer ID and mark processing
                withdrawal.flutterwave_transfer_id = str(transfer_id)
                withdrawal.status = "processing"
                db.commit()

                # Create transaction record
                transaction = Transaction(
                    user_id=user.user_id,
                    transaction_type="withdrawal",
                    amount=withdrawal.amount,
                    currency=withdrawal.currency,
                    status="processing",
                    description=f"Withdrawal to {withdrawal.account_number}",
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
            raise Exception(f"Error executing withdrawal: {str(e)}")
    
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
