from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import SessionLocal
from app.models import User
from app.auth_utils import get_password_hash, verify_password, create_access_token, decode_access_token
from typing import Optional
from datetime import timedelta

router = APIRouter(prefix="/api/auth", tags=["auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class PasswordResetRequest(BaseModel):
    email: str
    new_password: str

class BudgetUpdate(BaseModel):
    budget_goal: float
    category_budgets: Optional[dict] = None

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        return None
    email: str = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    return user

@router.post("/signup")
def signup(user: UserCreate, response: Response, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password, full_name=user.full_name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.email}, expires_delta=timedelta(days=7))
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return {"message": "User created successfully", "user_id": new_user.id}

@router.post("/login")
def login(user: UserLogin, response: Response, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": db_user.email}, expires_delta=timedelta(days=7))
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return {"message": "Login successful"}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}

@router.post("/reset-password")
def reset_password(req: PasswordResetRequest, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == req.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Email not found")
    
    db_user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

@router.post("/set-budget")
async def set_budget(req: BudgetUpdate, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
        
    user.budget_goal = req.budget_goal
    if req.category_budgets is not None:
        import json
        user.category_budgets = json.dumps(req.category_budgets)
    db.commit()
    return {"message": "Budget updated", "budget_goal": user.budget_goal}

class FamilyCreate(BaseModel):
    name: str

class FamilyJoin(BaseModel):
    family_id: int

@router.post("/family/create")
async def create_family(family: FamilyCreate, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
        
    from app.models import Family
    new_family = Family(name=family.name)
    db.add(new_family)
    db.commit()
    db.refresh(new_family)
    
    user.family_id = new_family.id
    db.commit()
    return {"message": "Family created successfully", "family_id": new_family.id, "name": new_family.name}

@router.post("/family/join")
async def join_family(family: FamilyJoin, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
        
    from app.models import Family
    existing_family = db.query(Family).filter(Family.id == family.family_id).first()
    if not existing_family:
        raise HTTPException(status_code=404, detail="Family not found")
        
    user.family_id = existing_family.id
    db.commit()
    return {"message": "Joined family successfully", "family_id": existing_family.id, "name": existing_family.name}

@router.post("/family/leave")
async def leave_family(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
        
    user.family_id = None
    db.commit()
    return {"message": "Left family successfully"}
