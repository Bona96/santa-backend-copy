from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date
from typing import Dict

from models import User, Deposit, Withdrawal, Transaction, ShuffleParticipant, Winner
from schemas import BalanceResponse

def calculate_user_balance(user_id: int, db: Session) -> BalanceResponse:
    """
    Calculate user's current balance across all currencies.
    Returns balance details including available, pending, and total amounts.
    """
    # Get all completed deposits
    total_deposits = db.query(func.sum(Deposit.amount)).filter(
        and_(Deposit.user_id == user_id, Deposit.status == "completed")
    ).scalar() or 0.0
    
    # Get all completed withdrawals
    total_withdrawals = db.query(func.sum(Withdrawal.amount)).filter(
        and_(
            Withdrawal.user_id == user_id,
            Withdrawal.status.in_(["completed", "processing"])
        )
    ).scalar() or 0.0
    
    # Get pending withdrawals
    pending_withdrawals = db.query(func.sum(Withdrawal.amount)).filter(
        and_(Withdrawal.user_id == user_id, Withdrawal.status == "pending")
    ).scalar() or 0.0
    
    # Calculate available balance
    available_balance = total_deposits - total_withdrawals
    
    return BalanceResponse(
        available_balance=available_balance,
        total_deposits=total_deposits,
        total_withdrawals=total_withdrawals,
        pending_withdrawals=pending_withdrawals,
        net_available=available_balance - pending_withdrawals
    )

def calculate_user_stats(user_id: int, db: Session) -> Dict:
    """Calculate user statistics including participations and win rate."""
    
    # Count total participations
    participations = db.query(ShuffleParticipant).filter(
        ShuffleParticipant.user_id == user_id
    ).count()
    
    # Count wins
    wins = db.query(Winner).filter(Winner.user_id == user_id).count()
    
    # Calculate total won amount
    total_won = db.query(func.sum(Winner.amount_won)).filter(
        Winner.user_id == user_id
    ).scalar() or 0.0
    
    # Calculate win rate
    win_rate = (wins / participations * 100) if participations > 0 else 0.0
    
    # Get balance
    balance_info = calculate_user_balance(user_id, db)
    
    return {
        "balance": balance_info.available_balance,
        "total_won": total_won,
        "participations": participations,
        "win_rate": round(win_rate, 1)
    }

def validate_withdrawal_eligibility(
    user_id: int,
    requested_amount: float,
    db: Session
) -> tuple:
    """
    Validate that user has sufficient balance for withdrawal.
    Returns (is_eligible, reason_if_not).
    """
    balance_info = calculate_user_balance(user_id, db)
    
    if requested_amount > balance_info.net_available:
        return False, f"Insufficient balance. Available: ${balance_info.net_available:.2f}"
    
    # Check for minimum withdrawal
    if requested_amount < 500:
        return False, "Minimum withdrawal amount is $500"
    
    # Check withdrawal limits per day
    today_withdrawals = db.query(func.sum(Withdrawal.amount)).filter(
        and_(
            Withdrawal.user_id == user_id,
            Withdrawal.status.in_(["pending", "processing", "completed"]),
            func.date(Withdrawal.created_at) == date.today()
        )
    ).scalar() or 0
    
    daily_limit = 1000000
    if today_withdrawals + requested_amount > daily_limit:
        remaining = daily_limit - today_withdrawals
        return False, f"Daily withdrawal limit exceeded. Remaining: ${remaining:.2f}"
    
    return True, ""
