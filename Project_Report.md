# Project Report: Smart Expense Analyzer (Trackr.ai)

## 1. Project Overview
Smart Expense Analyzer (Trackr.ai) is a full-stack, AI-powered personal finance management application. It evolves the traditional expense tracker into an intelligent financial assistant. By leveraging Machine Learning (ML) and Generative AI (Google Gemini), the platform offers automated receipt scanning, natural language expense logging, predictive spending forecasts, and highly sensitive anomaly detection to prevent budget runaway.

## 2. Technology Stack & Installed Libraries
The project avoids bulky front-end frameworks to maintain speed and uses a modern Python backend.

### **Frontend**
- **HTML5 & Vanilla JavaScript**: For semantic structure and dynamic asynchronous API calls.
- **Vanilla CSS3**: Utilized for the premium **Glassmorphism** aesthetic, CSS variables for dynamic Light/Dark mode toggling, and responsive flex/grid layouts.
- **Chart.js (CDN)**: For rendering the interactive category distribution pie chart.
- **FontAwesome (CDN)**: For crisp vector icons used throughout the UI.

### **Backend & Database**
- **FastAPI**: High-performance asynchronous web framework for Python.
- **Uvicorn**: ASGI web server implementation for FastAPI.
- **SQLAlchemy**: ORM (Object Relational Mapper) for database interactions.
- **SQLite3**: Lightweight, file-based relational database (`sql_app.db`).
- **Pydantic**: For data validation and strictly typed API schemas.

### **Security & Authentication**
- **Passlib & bcrypt**: For secure password hashing.
- **Python-JOSE**: For generating and decoding secure JWT (JSON Web Tokens) for session management.
- **Python-Multipart**: For handling form data during authentication.

### **AI & Machine Learning**
- **Google Generative AI SDK (`google-genai` / `google-generativeai`)**: Powers the receipt OCR data extraction, voice-to-text natural language processing, and the AI Chatbot assistant using the `gemini-2.5-flash` model.

---

## 3. Core Features Developed

1. **Intelligent Dashboard & Theming**: A glassmorphic UI featuring a toggleable Light/Dark mode that uses CSS custom properties (`var(--bg-color)`) for instant switching without reloading.
2. **AI Receipt Scanner (OCR)**: Users can upload images of receipts. The Gemini API analyzes the image and returns a structured JSON payload containing the merchant name, total amount, category, and location.
3. **Natural Language Logging**: Users can type or speak sentences like *"I spent 500 on Starbucks in Delhi"* and the AI automatically categorizes and logs it.
4. **Smart Budgets & Alerts**: Users define custom budgets per category. The system actively warns users when they approach 90% of their limit.
5. **Gamification Engine**: Tracks consecutive logging days to build "Streaks" and awards badges like "Consistent Tracker" and "Budget Master" to motivate financial health.
6. **Family / Group Mode**: Allows users to create or join a shared Family ID to pool and track household expenses together.

---

## 4. Key Logic & Code Snapshots

### A. Context-Aware Anomaly Detection
The system actively tracks spending habits. If an expense is significantly larger (3x) than the historical average for that specific category, it is flagged as an anomaly.

```python
# Snapshot from app/routers/expenses.py (Anomaly Detection)
is_anomaly = False
past_expenses = db.query(Expense).filter(
    Expense.owner_id == user.id, 
    Expense.category == expense.category
).all()

# Requires at least 1 past expense to establish a baseline
if len(past_expenses) >= 1:
    avg_spend = sum(e.amount for e in past_expenses) / len(past_expenses)
    
    # Trigger if new expense is 3x the normal category spend and > ₹100
    if expense.amount > (avg_spend * 3.0) and expense.amount > 100: 
        is_anomaly = True
elif expense.amount > 5000: # Absolute high threshold fallback
    is_anomaly = True

new_expense = Expense(..., is_anomaly=is_anomaly)
```

### B. Machine Learning (Predictive Trend Forecasting)
To forecast next month's spending, the application uses a standard linear regression algorithm (Least Squares Method) computed over the user's monthly spending history.

```python
# Snapshot from app/routers/expenses.py (Linear Regression Forecast)

# 1. Aggregate spending by month
monthly_totals = defaultdict(float)
for e in past_year_expenses:
    month_key = f"{e.date.year}-{e.date.month:02d}"
    monthly_totals[month_key] += e.amount

# 2. Sort data chronologically
sorted_months = sorted(monthly_totals.keys())
y_values = [monthly_totals[m] for m in sorted_months]
x_values = list(range(1, len(y_values) + 1))

# 3. Apply Least Squares Formula: y = mx + b
n = len(x_values)
sum_x = sum(x_values)
sum_y = sum(y_values)
sum_xy = sum(x * y for x, y in zip(x_values, y_values))
sum_x_squared = sum(x ** 2 for x in x_values)

denominator = (n * sum_x_squared - sum_x ** 2)
if denominator != 0:
    m = (n * sum_xy - sum_x * sum_y) / denominator
    b = (sum_y - m * sum_x) / n
    next_x = n + 1
    predicted_next_month = (m * next_x) + b
```

### C. Pattern Recognition & Context Insights
The system looks at data grouped by timeframes to provide highly contextual advice.

```python
# Snapshot from app/routers/expenses.py (Pattern Analysis)

# Identify Weekly Frequency Surges
for desc, count in desc_counts_this_week.items():
    if count >= 3:
        smart_alerts.append(f"You ordered from or visited '{desc}' {count} times this week.")

# Identify Week-Over-Week Category Spikes
for cat, amount in cat_totals_this_week.items():
    last_week_amount = cat_totals_last_week.get(cat, 0)
    if last_week_amount > 0:
        increase_pct = ((amount - last_week_amount) / last_week_amount) * 100
        if increase_pct >= 40:
            smart_alerts.append(f"Your {cat} spending increased by {increase_pct:.0f}% compared to last week.")
```

### D. Generative AI Prompting for OCR
To convert an image into structured data without traditional hard-coded regex, a highly specific system prompt is sent to the Gemini 2.5 Flash model.

```python
# Snapshot from app/routers/expenses.py (Gemini AI Vision)
prompt = """
You are an expert financial receipt analyzer. 
Extract the following information from the image and return ONLY a valid JSON object.
Do not include markdown blocks or any other text.
Use this exact JSON schema:
{
    "amount": float,
    "category": string (Must be one of: Food & Dining, Transportation, Housing, Entertainment, Bills & Utilities, Shopping, Healthcare/Medicines, Other),
    "description": string (the merchant name or main item),
    "location": string (the city or physical address if visible, else empty string)
}
"""
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[prompt, receipt_image]
)
```

---

## 5. Summary
The Smart Expense Analyzer successfully demonstrates how AI and traditional software engineering can merge to create a proactive, intelligent tool. By moving away from static charts and implementing predictive AI and natural language features, the application solves real-world financial friction, ensuring users stay effortlessly on top of their budgets.

---

## 6. APIs Used

### **External APIs Integration**
- **Google Gemini API (`gemini-2.5-flash`)**: The core cognitive engine of the application. We securely send prompt schemas and image byte data to this API.
  - Used for **OCR Receipt Scanning** (Extracting data from images).
  - Used for **Voice-to-Text Parsing** (Converting natural language audio/text logs into structured JSON).
  - Used for the **AI Chatbot** (Answering financial queries based on user data).

### **Internal RESTful APIs (Developed via FastAPI)**

#### Authentication & User Management
- `POST /api/auth/signup` - Registers a new user and returns a JWT session cookie.
- `POST /api/auth/login` - Authenticates credentials and initiates a session.
- `POST /api/auth/logout` - Terminates the session and destroys the JWT cookie.
- `POST /api/auth/reset-password` - Updates the hashed password in the database.
- `POST /api/auth/set-budget` - Sets dynamic monthly budgets for the 8 spending categories.

#### Family Mode & Collaboration
- `POST /api/auth/family/create` - Generates a new family group and assigns the user as admin.
- `POST /api/auth/family/join` - Links the user to an existing family group via Family ID.
- `POST /api/auth/family/leave` - Unlinks the user from a family group.

#### Expense Management & AI Endpoints
- `GET /api/expenses/summary` - The heavy-lifting endpoint. Returns all expenses, computes the ML linear regression trendline, runs the anomaly detection loops, and returns context-aware pattern insights.
- `POST /api/expenses` - Logs a new expense manually or processes a natural language voice string. Updates user gamification streaks upon success.
- `PUT /api/expenses/{expense_id}` - Edits the details of an existing logged expense.
- `DELETE /api/expenses/{expense_id}` - Removes an expense from the database.
- `POST /api/expenses/upload-receipt` - Receives an image file, uploads it to the Gemini API, and returns the parsed JSON payload to the frontend.
- `POST /api/expenses/chat` - Feeds the user's spending data context and query to the Gemini API for conversational financial advice.
