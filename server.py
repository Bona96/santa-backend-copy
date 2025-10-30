from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, status
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from database import engine, get_db
from models import Base, User, Deposit, Withdrawal, Transaction, Group, GroupMember, ShuffleParticipant, GlobalJackpot, Winner
from schemas import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    DepositRequest, DepositResponse, WithdrawalRequest, WithdrawalResponse,
    TransactionResponse, BalanceResponse, GroupCreate, GroupResponse,
    ShuffleJoinRequest, ShuffleParticipantResponse, WinnerResponse, GroupJoinRequest
)
from auth import get_password_hash, verify_password, create_access_token, get_current_user
from payment_service import flutterwave_service
from helpers import calculate_user_balance, calculate_user_stats, validate_withdrawal_eligibility

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create all database tables
Base.metadata.create_all(bind=engine)

# Create the main app
app = FastAPI(title="Santa Daily Win Universe API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Root endpoint
@api_router.get("/")
async def root():
    return {"message": "Santa Daily Win Universe API"}

# ========== Authentication Endpoints ==========

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hashed_password,
            phone_number=user_data.phone_number,
            country=user_data.country,
            age=user_data.age,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create access token
        access_token = create_access_token(data={"user_id": new_user.user_id})
        
        # Calculate user stats
        stats = calculate_user_stats(new_user.user_id, db)
        
        # Create user response
        user_response = UserResponse(
            user_id=new_user.user_id,
            username=new_user.username,
            email=new_user.email,
            country=new_user.country,
            age=new_user.age,
            phone_number=new_user.phone_number,
            profile_picture=new_user.profile_picture,
            **stats
        )
        
        return TokenResponse(access_token=access_token, user=user_response)
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user."""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == user_data.email).first()
        if not user or not verify_password(user_data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Create access token
        access_token = create_access_token(data={"user_id": user.user_id})
        
        # Calculate user stats
        stats = calculate_user_stats(user.user_id, db)
        
        # Create user response
        user_response = UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            country=user.country,
            age=user.age,
            phone_number=user.phone_number,
            profile_picture=user.profile_picture,
            **stats
        )
        
        return TokenResponse(access_token=access_token, user=user_response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== User Endpoints ==========

@api_router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user information."""
    stats = calculate_user_stats(current_user.user_id, db)
    
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        country=current_user.country,
        age=current_user.age,
        phone_number=current_user.phone_number,
        profile_picture=current_user.profile_picture,
        **stats
    )

@api_router.get("/users/balance", response_model=BalanceResponse)
async def get_user_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user balance."""
    return calculate_user_balance(current_user.user_id, db)

@api_router.put("/users/me")
async def update_user_profile(
    profile_picture: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile including profile picture."""
    try:
        if profile_picture:
            current_user.profile_picture = profile_picture
        
        db.commit()
        db.refresh(current_user)
        
        stats = calculate_user_stats(current_user.user_id, db)
        
        return UserResponse(
            user_id=current_user.user_id,
            username=current_user.username,
            email=current_user.email,
            country=current_user.country,
            age=current_user.age,
            phone_number=current_user.phone_number,
            profile_picture=current_user.profile_picture,
            **stats
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ========== Transaction Endpoints ==========

@api_router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    transaction_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve transaction history for current user."""
    query = db.query(Transaction).filter(Transaction.user_id == current_user.user_id)
    
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    transactions = query.order_by(
        Transaction.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return transactions

# ========== Payment Endpoints ==========

@api_router.post("/payments/deposit/initiate", response_model=DepositResponse)
async def initiate_deposit(
    deposit_request: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate a deposit transaction through Flutterwave - accepts any currency."""
    try:
        # Validate deposit amount (flexible for any currency)
        if deposit_request.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        if deposit_request.amount > 50000000:
            raise HTTPException(status_code=400, detail="Maximum deposit amount exceeded")
        
        # Call Flutterwave service
        result = await flutterwave_service.initiate_deposit(
            user=current_user,
            amount=deposit_request.amount,
            currency=deposit_request.currency,
            payment_method=deposit_request.payment_method,
            db=db
        )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== Group Endpoints ==========

@api_router.get("/groups", response_model=List[GroupResponse])
async def get_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all groups for current user."""
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

@api_router.post("/groups", response_model=GroupResponse)
async def create_group(
    group_data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new group."""
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
        
        # Add creator as first member
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

@api_router.post("/groups/{group_id}/join")
async def join_group(
    group_id: int,
    join_data: GroupJoinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a group and contribute to its jackpot."""
    try:
        # Check if group exists
        group = db.query(Group).filter(Group.group_id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Check if user already a member
        existing_member = db.query(GroupMember).filter(
            (GroupMember.group_id == group_id) &
            (GroupMember.user_id == current_user.user_id)
        ).first()
        
        if existing_member:
            # Update contribution
            existing_member.contribution_amount += join_data.contribution_amount
        else:
            # Add as new member
            member = GroupMember(
                group_id=group_id,
                user_id=current_user.user_id,
                contribution_amount=join_data.contribution_amount,
                joined_at=datetime.utcnow()
            )
            db.add(member)
        
        # Update group jackpot
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

# ========== Shuffle Endpoints ==========

@api_router.get("/shuffle/participants", response_model=List[ShuffleParticipantResponse])
async def get_shuffle_participants(db: Session = Depends(get_db)):
    """Get all participants for today's shuffle."""
    today = datetime.utcnow().date()
    
    participants = db.query(ShuffleParticipant, User).join(
        User, ShuffleParticipant.user_id == User.user_id
    ).filter(
        ShuffleParticipant.shuffle_date >= today
    ).all()
    
    result = []
    for participant, user in participants:
        result.append(ShuffleParticipantResponse(
            username=user.username,
            avatar=user.username[0].upper(),
            country=user.country
        ))
    
    return result

@api_router.post("/shuffle/join")
async def join_shuffle(
    shuffle_data: ShuffleJoinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join the daily shuffle."""
    try:
        today = datetime.utcnow().date()
        
        # Check if user already joined today
        existing = db.query(ShuffleParticipant).filter(
            (ShuffleParticipant.user_id == current_user.user_id) &
            (ShuffleParticipant.shuffle_date >= today) &
            (ShuffleParticipant.jackpot_type == shuffle_data.jackpot_type)
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Already joined today's shuffle")
        
        # Add participant
        participant = ShuffleParticipant(
            user_id=current_user.user_id,
            shuffle_date=datetime.utcnow(),
            jackpot_type=shuffle_data.jackpot_type,
            group_id=shuffle_data.group_id,
            created_at=datetime.utcnow()
        )
        
        db.add(participant)
        db.commit()
        
        return {
            "success": True,
            "message": "Successfully joined the shuffle!",
            "jackpot_type": shuffle_data.jackpot_type
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ========== Winner Endpoints ==========

@api_router.get("/winners/recent", response_model=List[WinnerResponse])
async def get_recent_winners(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent winners."""
    try:
        winners = db.query(Winner, User).join(
            User, Winner.user_id == User.user_id
        ).order_by(Winner.won_at.desc()).limit(limit).all()
        
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
        # Return empty list if table doesn't exist yet
        logger.error(f"Error fetching winners: {str(e)}")
        return []

# ========== Jackpot Endpoints ==========

@api_router.get("/jackpot/global")
async def get_global_jackpot(db: Session = Depends(get_db)):
    """Get current global jackpot from actual completed deposits."""
    
    # Calculate total from all completed deposits
    total_deposits = db.query(func.sum(Deposit.amount)).filter(
        Deposit.status == "completed"
    ).scalar() or 0.0
    
    # Get or create global jackpot record
    jackpot = db.query(GlobalJackpot).first()
    
    if not jackpot:
        jackpot = GlobalJackpot(
            current_amount=total_deposits,
            currency="USD",
            updated_at=datetime.utcnow()
        )
        db.add(jackpot)
        db.commit()
        db.refresh(jackpot)
    else:
        # Update with actual deposits
        jackpot.current_amount = total_deposits
        jackpot.updated_at = datetime.utcnow()
        db.commit()
    
    return {
        "jackpot_id": jackpot.jackpot_id,
        "current_amount": total_deposits,
        "currency": "Multi-Currency",
        "updated_at": jackpot.updated_at
    }

# Include the router in the main app
app.include_router(api_router)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "https://*.emergent.host",  # Production domain pattern
        "*"  # Allow all origins for development (remove in strict production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
