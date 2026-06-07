from dotenv import load_dotenv
load_dotenv()
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
import os
import json
import tempfile
import PIL.Image
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
import datetime
from app.database import SessionLocal
from app.models import Expense, User, Family
from app.routers.auth import get_current_user, get_db

router = APIRouter(prefix="/api/expenses", tags=["expenses"])

class ExpenseCreate(BaseModel):
    amount: float
    description: str
    category: str
    date: Optional[str] = None
    location: Optional[str] = None

class ExpenseResponse(BaseModel):
    id: int
    amount: float
    description: str
    category: str
    date: datetime.datetime
    is_anomaly: bool
    owner_name: Optional[str] = None
    location: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ExpenseResponse])
async def get_expenses(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    if user.family_id:
        family_members = db.query(User).filter(User.family_id == user.family_id).all()
        user_map = {m.id: m.full_name for m in family_members}
        member_ids = list(user_map.keys())
        expenses = db.query(Expense).filter(Expense.owner_id.in_(member_ids)).order_by(Expense.date.desc()).all()
        for e in expenses:
            setattr(e, "owner_name", user_map.get(e.owner_id, "Unknown"))
    else:
        expenses = db.query(Expense).filter(Expense.owner_id == user.id).order_by(Expense.date.desc()).all()
        for e in expenses:
            setattr(e, "owner_name", user.full_name)
    return expenses

@router.post("/", response_model=ExpenseResponse)
async def create_expense(expense: ExpenseCreate, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    # Anomaly Detection Logic
    is_anomaly = False
    past_expenses = db.query(Expense).filter(Expense.owner_id == user.id, Expense.category == expense.category).all()
    if len(past_expenses) >= 1:
        avg_spend = sum(e.amount for e in past_expenses) / len(past_expenses)
        if expense.amount > (avg_spend * 3.0) and expense.amount > 100: # 3x the normal category spend!
            is_anomaly = True
    elif expense.amount > 5000: # Absolute high threshold fallback
        is_anomaly = True
        
    expense_date = datetime.datetime.utcnow()
    if expense.date:
        try:
            expense_date = datetime.datetime.strptime(expense.date, "%Y-%m-%d")
        except:
            pass
            
    # Prevent future dates
    if expense_date > datetime.datetime.utcnow():
        expense_date = datetime.datetime.utcnow()

    new_expense = Expense(
        amount=expense.amount,
        description=expense.description,
        category=expense.category,
        owner_id=user.id,
        is_anomaly=is_anomaly,
        date=expense_date,
        location=expense.location
    )
    db.add(new_expense)
    
    now = datetime.datetime.utcnow().date()
    if user.last_expense_date:
        last_date = user.last_expense_date.date()
        if last_date == now - datetime.timedelta(days=1):
            user.current_streak += 1
        elif last_date < now - datetime.timedelta(days=1):
            user.current_streak = 1
    else:
        user.current_streak = 1
    user.last_expense_date = datetime.datetime.utcnow()

    db.commit()
    db.refresh(new_expense)
    return new_expense

@router.delete("/{expense_id}")
async def delete_expense(expense_id: int, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.owner_id == user.id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found or unauthorized")
    
    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted"}

@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(expense_id: int, expense_data: ExpenseCreate, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.owner_id == user.id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found or unauthorized")
        
    expense.amount = expense_data.amount
    expense.description = expense_data.description
    expense.category = expense_data.category
    expense.location = expense_data.location
    if expense_data.date:
        try:
            parsed_date = datetime.datetime.strptime(expense_data.date, "%Y-%m-%d")
            # Prevent future dates
            if parsed_date > datetime.datetime.utcnow():
                parsed_date = datetime.datetime.utcnow()
            expense.date = parsed_date
        except:
            pass
            
    is_anomaly = False
    past_expenses = db.query(Expense).filter(Expense.owner_id == user.id, Expense.category == expense.category, Expense.id != expense.id).all()
    if len(past_expenses) >= 1:
        avg_spend = sum(e.amount for e in past_expenses) / len(past_expenses)
        if expense.amount > (avg_spend * 3.0) and expense.amount > 100:
            is_anomaly = True
    elif expense.amount > 5000:
        is_anomaly = True
    expense.is_anomaly = is_anomaly

    db.commit()
    db.refresh(expense)
    return expense

@router.get("/summary")
async def get_summary(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    member_totals = {}
    if user.family_id:
        family_members = db.query(User).filter(User.family_id == user.family_id).all()
        user_map = {m.id: m.full_name for m in family_members}
        member_ids = list(user_map.keys())
        expenses = db.query(Expense).filter(Expense.owner_id.in_(member_ids)).all()
        member_totals = {m.full_name: 0.0 for m in family_members}
        for e in expenses:
            if e.owner_id in user_map:
                member_totals[user_map[e.owner_id]] += e.amount
    else:
        expenses = db.query(Expense).filter(Expense.owner_id == user.id).all()
        member_totals = {user.full_name: sum(e.amount for e in expenses)}
        
    total_balance = sum(e.amount for e in expenses)
    monthly_spending = sum(e.amount for e in expenses if e.date.month == datetime.datetime.utcnow().month)
    anomalies = sum(1 for e in expenses if e.is_anomaly)
    
    locations = {}
    categories = {}
    for e in expenses:
        categories[e.category] = categories.get(e.category, 0) + e.amount
        if e.location:
            locations[e.location] = locations.get(e.location, 0) + e.amount
            
    top_location = None
    if locations:
        top_location = max(locations, key=locations.get)
        
    import json
    try:
        user_badges = json.loads(user.badges or "[]")
    except:
        user_badges = []
        
    if user.current_streak >= 3 and "Consistent Tracker" not in user_badges:
        user_badges.append("Consistent Tracker")
    if user.budget_goal > 0 and monthly_spending <= user.budget_goal * 0.8 and "Budget Master" not in user_badges:
        user_badges.append("Budget Master")
        
    user.badges = json.dumps(user_badges)
    db.commit()

    smart_alerts = []
    
    # Advanced Anomaly Alerts
    for e in expenses:
        if e.is_anomaly and e.date >= datetime.datetime.utcnow() - datetime.timedelta(days=7):
            smart_alerts.append(f"Unusual expense detected in {e.category} (₹{e.amount:.0f}, which is significantly higher than your average).")

    # Budget Limits
    try:
        cat_budgets = json.loads(user.category_budgets or "{}")
        for cat, spend in categories.items():
            budget = float(cat_budgets.get(cat, 0))
            if budget > 0 and spend > budget * 0.9:
                excess = spend - budget
                if excess > 0:
                    smart_alerts.append(f"Reduce {cat} spending by ₹{excess:.0f} to stay within budget.")
                else:
                    smart_alerts.append(f"Approaching limit for {cat}.")
    except Exception as e:
        print("Smart Alerts Error:", e)
        
    # Context-Aware Insights
    now = datetime.datetime.utcnow()
    current_week = []
    last_week = []
    for e in expenses:
        if now - datetime.timedelta(days=7) <= e.date <= now:
            current_week.append(e)
        elif now - datetime.timedelta(days=14) <= e.date < now - datetime.timedelta(days=7):
            last_week.append(e)
            
    # Merchant Frequency
    merchants = {}
    for e in current_week:
        # Ignore basic descriptions
        if len(e.description) > 3 and "ocr" not in e.description.lower():
            merchants[e.description] = merchants.get(e.description, 0) + 1
    for m, count in merchants.items():
        if count >= 3:
            smart_alerts.append(f"You ordered from {m} {count} times this week.")

    # Category Trends
    curr_cat_spend = {}
    for e in current_week:
        curr_cat_spend[e.category] = curr_cat_spend.get(e.category, 0) + e.amount
    last_cat_spend = {}
    for e in last_week:
        last_cat_spend[e.category] = last_cat_spend.get(e.category, 0) + e.amount

    for cat, c_spend in curr_cat_spend.items():
        l_spend = last_cat_spend.get(cat, 0)
        if l_spend > 0 and c_spend > 500: # non-trivial spending
            increase_pct = ((c_spend - l_spend) / l_spend) * 100
            if increase_pct >= 40:
                smart_alerts.append(f"{cat} spending increased by {increase_pct:.0f}% compared to last week.")
        
    predicted_spend = 0.0
    from collections import defaultdict
    months_data = defaultdict(float)
    for e in expenses:
        m_key = e.date.year * 12 + e.date.month
        months_data[m_key] += e.amount
    
    if len(months_data) >= 2:
        sorted_months = sorted(months_data.keys())
        x_vals = list(range(len(sorted_months)))
        y_vals = [months_data[m] for m in sorted_months]
        
        n = len(x_vals)
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x*y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x*x for x in x_vals)
        
        denominator = (n * sum_x2 - sum_x**2)
        if denominator != 0:
            m = (n * sum_xy - sum_x * sum_y) / denominator
            b = (sum_y - m * sum_x) / n
            next_x = n
            predicted_spend = m * next_x + b
    elif len(months_data) == 1:
        predicted_spend = list(months_data.values())[0]
        
    return {
        "total_balance": total_balance,
        "monthly_spending": monthly_spending,
        "anomalies": anomalies,
        "categories": categories,
        "member_totals": member_totals,
        "budget_goal": user.budget_goal,
        "top_location": top_location,
        "current_streak": user.current_streak,
        "badges": user_badges,
        "smart_alerts": smart_alerts,
        "predicted_spend": predicted_spend if predicted_spend > 0 else 0
    }

@router.post("/upload")
async def extract_receipt(file: UploadFile = File(...), request: Request = None, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    import tempfile
    import PIL.Image
    import pytesseract
    import re
    import os
    import json
    
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
            
        img = PIL.Image.open(tmp_path)
        img.thumbnail((1024, 1024))
        
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                prompt = """Analyze this receipt image. Extract the total amount, a short description (like merchant name), the location (like store name or city if available), the date of the receipt (in YYYY-MM-DD format), and categorize the expense into one of: Food & Dining, Transportation, Housing, Entertainment, Bills & Utilities, Shopping, Healthcare/Medicines, or Other.
Return ONLY a valid JSON object in this exact format space, with no code fences or backticks:
{"amount": 12.34, "description": "Starbucks", "category": "Food & Dining", "location": "New York", "date": "2023-10-27"}"""
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[img, prompt]
                )
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:-3].strip()
                elif text.startswith("```"):
                    text = text[3:-3].strip()
                res_data = json.loads(text)
                return {
                    "amount": float(res_data.get("amount", 0)),
                    "description": str(res_data.get("description", "Unknown Merchant"))[:40],
                    "category": res_data.get("category", "Other"),
                    "location": res_data.get("location", None),
                    "date": res_data.get("date", None),
                    "confidence": 0.95
                }
            except Exception as e:
                print(f"⚠️ Gemini OCR Failed (Falling back to local): {str(e)}")
                pass # Fall through to local fallback

        # Fallback Local OCR
        raw_text = pytesseract.image_to_string(img)
        amount = 0.0
        # More flexible regex to catch "Total Amt", "Net Amt", etc. with optional punctuation/parentheses
        total_match = re.search(r"(?i)(?:total|net)[\s\w\.\(\)/]*[:=]+\s*(?:Rs\.?|INR|\$|£|€)?\s*([\d,\.]+)", raw_text)
        if total_match:
            try:
                amount = float(total_match.group(1).replace(",", "").rstrip("."))
            except:
                pass
        else:
            numbers = re.findall(r"\d+\.\d+", raw_text)
            if not numbers:
                # Be conservative if defaulting to max integer to avoid capturing phone numbers
                numbers = [n for n in re.findall(r"\d+", raw_text) if len(n) < 7]
            if numbers:
                valid_numbers = [float(n) for n in numbers if not (1900 <= float(n) <= 2100)]
                if valid_numbers:
                    amount = max(valid_numbers)
            
        desc = "Local OCR Bill"
        words = [w.strip() for w in raw_text.splitlines() if len(w.strip()) > 4]
        for w in words:
            w_lower = w.lower()
            if any(stop in w_lower for stop in ["total", "amount", "tax", "cash", "change", "composition", "dealer", "memo"]):
                continue
            # Avoid lines with too many numbers (like addresses, phone numbers)
            if sum(c.isdigit() for c in w) < 3:
                desc = w[:40]
                break
                
        cat = "Other"
        lower_text = raw_text.lower()
        if any(x in lower_text for x in ["food", "restaurant", "cafe", "coffee", "eatery"]):
            cat = "Food & Dining"
        elif any(x in lower_text for x in ["uber", "ola", "taxi", "cab", "train", "flight"]):
            cat = "Transportation"
        elif any(x in lower_text for x in ["hospital", "clinic", "pharmacy", "medicine"]):
            cat = "Healthcare/Medicines"
        elif any(x in lower_text for x in ["mart", "supermarket", "store", "retail"]):
            cat = "Shopping"

        date_str = None
        date_match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", raw_text)
        if date_match:
            try:
                day, month, year = date_match.groups()
                if len(year) == 2:
                    year = "20" + year
                import datetime
                dt = datetime.datetime(int(year), int(month), int(day))
                date_str = dt.strftime("%Y-%m-%d")
            except:
                pass
            
        return {"amount": amount, "description": desc, "category": cat, "location": None, "date": date_str, "confidence": 0.70}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR Failed: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

class ChatMessage(BaseModel):
    message: str

@router.post("/chatbot")
async def chat_with_advisor(msg: ChatMessage, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
        
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"reply": "Please export your GEMINI_API_KEY in the terminal to activate my AI!"}

    if user.family_id:
        family_members = db.query(User).filter(User.family_id == user.family_id).all()
        user_map = {m.id: m.full_name for m in family_members}
        member_ids = list(user_map.keys())
        expenses = db.query(Expense).filter(Expense.owner_id.in_(member_ids)).all()
        
        member_totals = {m.full_name: 0.0 for m in family_members}
        for e in expenses:
            if e.owner_id in user_map:
                member_totals[user_map[e.owner_id]] += e.amount
                
        context = f"User is {user.full_name}. Overall Family spending is Rs {sum(e.amount for e in expenses)}. Family member totals: {member_totals}. Spend by category: "
    else:
        expenses = db.query(Expense).filter(Expense.owner_id == user.id).all()
        context = f"User {user.full_name} has spent Rs {sum(e.amount for e in expenses)} total. Spend by category: "
        
    cats = {}
    for e in expenses:
        cats[e.category] = cats.get(e.category, 0) + e.amount
        
    context += f"{cats}."
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Act as a professional, friendly AI financial advisor for a Smart Expense Analyzer app. Be very brief (1-2 sentences). Context: {context}. User asks: {msg.message}"
        )
        return {"reply": response.text}
    except Exception as e:
        print(f"Chatbot error: {str(e)}")
        total_spent = sum(e.amount for e in expenses)
        return {"reply": f"I'm having trouble connecting to my AI engine right now. Based on your data, you've spent ₹{total_spent:.0f} total. Please try again in a moment!"}
