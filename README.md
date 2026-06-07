# Trackr.ai - Smart Expense Analyzer

An AI-based smart expense analyzer that features OCR receipt scanning, Voice Inputs, and deep categorization built with Python (FastAPI) and Vanilla JS/CSS.

## Prerequisites
- Python 3.9+ 

## How to Run Locally

1. **Navigate to the core project directory:**
   ```bash
   git clone https://github.com/LAVANYA-GOSAIN/Smart_Expense_Analyzer.git
   cd Smart_Expense_Analyzer
   ```

2. **Activate the Virtual Environment:**
   ```bash
   source venv/bin/activate
   ```

3. **Run the FastAPI Server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   *(Note: The `--reload` flag ensures the server automatically updates if you edit any Python or HTML files!)*

4. **Open your Browser:**
   Go to **[http://127.0.0.1:8000](http://127.0.0.1:8000)** to see the Landing Page, or **[http://127.0.0.1:8000/signup](http://127.0.0.1:8000/signup)** to register an account and view the Dashboard!
