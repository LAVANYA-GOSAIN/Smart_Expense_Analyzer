from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    budget_goal = Column(Float, default=0.0)
    category_budgets = Column(String, default="{}")
    current_streak = Column(Integer, default=0)
    last_expense_date = Column(DateTime, nullable=True)
    badges = Column(String, default="[]")
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)

    family = relationship("Family", back_populates="members")
    expenses = relationship("Expense", back_populates="owner")

class Family(Base):
    __tablename__ = "families"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    
    members = relationship("User", back_populates="family")

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, index=True)
    category = Column(String, index=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    is_anomaly = Column(Boolean, default=False)
    location = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="expenses")
