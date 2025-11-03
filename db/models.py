from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone_number = Column(String(20))
    country = Column(String(10))
    age = Column(Integer)
    profile_picture = Column(String(500), nullable=True)  # URL or base64
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    # Role flag to mark administrative users. Default False for regular users.
    is_admin = Column(Boolean, default=False, nullable=False)
    
    deposits = relationship("Deposit", back_populates="user")
    withdrawals = relationship("Withdrawal", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    group_memberships = relationship("GroupMember", back_populates="user")
    created_groups = relationship("Group", back_populates="creator")
    shuffle_participations = relationship("ShuffleParticipant", back_populates="user")

class Deposit(Base):
    __tablename__ = "deposits"
    
    deposit_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    flutterwave_tx_ref = Column(String(255), unique=True, index=True)
    flutterwave_transaction_id = Column(String(255), unique=True, index=True, nullable=True)
    status = Column(String(20), default="pending")  # pending, completed, failed
    payment_method = Column(String(50))  # card, bank_transfer, mobile_money, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="deposits")

class Withdrawal(Base):
    __tablename__ = "withdrawals"
    
    withdrawal_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    bank_code = Column(String(20))
    account_number = Column(String(50))
    account_name = Column(String(255))
    flutterwave_transfer_id = Column(String(255), unique=True, index=True, nullable=True)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="withdrawals")

class Transaction(Base):
    __tablename__ = "transactions"
    
    transaction_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    transaction_type = Column(String(50), nullable=False)  # deposit, withdrawal, shuffle_participation, shuffle_win
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(String(20), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")

class Group(Base):
    __tablename__ = "groups"
    
    group_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # family, friends, work, custom
    creator_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    min_contribution = Column(Float, default=10.0)
    current_jackpot = Column(Float, default=0.0)
    hierarchy_type = Column(String(50), default="equal")  # equal, winner_takes_all, top_3, proportional
    currency = Column(String(10), default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    creator = relationship("User", back_populates="created_groups")
    members = relationship("GroupMember", back_populates="group")

class GroupMember(Base):
    __tablename__ = "group_members"
    
    member_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    contribution_amount = Column(Float, default=0.0)
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")

class ShuffleParticipant(Base):
    __tablename__ = "shuffle_participants"
    
    participant_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    shuffle_date = Column(DateTime, default=datetime.utcnow)
    jackpot_type = Column(String(20), default="global")  # global, group
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="shuffle_participations")

class GlobalJackpot(Base):
    __tablename__ = "global_jackpot"
    
    jackpot_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    current_amount = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    last_winner_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    last_winner_amount = Column(Float, nullable=True)
    last_winner_date = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Winner(Base):
    __tablename__ = "winners"
    
    winner_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    username = Column(String(100))
    country = Column(String(10))
    amount_won = Column(Float)
    jackpot_type = Column(String(20))  # global, group
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=True)
    won_at = Column(DateTime, default=datetime.utcnow)
