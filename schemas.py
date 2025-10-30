from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    phone_number: str
    country: str
    age: int

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    country: str
    age: int
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    balance: float = 0.0
    total_won: float = 0.0
    participations: int = 0
    win_rate: float = 0.0
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Payment Schemas
class DepositRequest(BaseModel):
    amount: float
    currency: str = "NGN"
    payment_method: str = "card"

class DepositResponse(BaseModel):
    deposit_id: int
    amount: float
    currency: str
    status: str
    payment_url: str
    
    class Config:
        from_attributes = True

class WithdrawalRequest(BaseModel):
    amount: float
    currency: str = "NGN"
    bank_code: str
    account_number: str
    account_name: str

class WithdrawalResponse(BaseModel):
    withdrawal_id: int
    amount: float
    currency: str
    status: str
    flutterwave_transfer_id: Optional[str] = None
    
    class Config:
        from_attributes = True

# Transaction Schemas
class TransactionResponse(BaseModel):
    transaction_id: int
    transaction_type: str
    amount: float
    currency: str
    status: str
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class BalanceResponse(BaseModel):
    available_balance: float
    total_deposits: float
    total_withdrawals: float
    pending_withdrawals: float
    net_available: float

# Group Schemas
class GroupCreate(BaseModel):
    name: str
    type: str
    min_contribution: float = 10.0
    hierarchy_type: str = "equal"
    currency: str = "USD"

class GroupResponse(BaseModel):
    group_id: int
    name: str
    type: str
    members_count: int = 0
    current_jackpot: float = 0.0
    min_contribution: float
    hierarchy_type: str = "equal"
    currency: str = "USD"
    
    class Config:
        from_attributes = True

class GroupJoinRequest(BaseModel):
    contribution_amount: float

# Shuffle Schemas
class ShuffleParticipantResponse(BaseModel):
    username: str
    avatar: str
    country: str

class ShuffleJoinRequest(BaseModel):
    jackpot_type: str = "global"
    group_id: Optional[int] = None

# Winner Schemas
class WinnerResponse(BaseModel):
    username: str
    message: str
    avatar: str
    country: str
    
    class Config:
        from_attributes = True

# Jackpot Schemas
class GlobalJackpotResponse(BaseModel):
    jackpot_id: int
    current_amount: float
    currency: str
    updated_at: datetime
    
    class Config:
        from_attributes = True