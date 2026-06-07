from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from app.database import Base, engine
from app.routers import auth, expenses
from app.routers.auth import get_current_user, SessionLocal

# Initialize Database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Expense Analyzer", description="AI-Based Smart Expense Tracker API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Routers
app.include_router(auth.router)
app.include_router(expenses.router)

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html")

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="reset_password.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    db = SessionLocal()
    user = await get_current_user(request, db)
    db.close()
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user})

@app.get("/health")
def health_check():
    return {"status": "ok"}
