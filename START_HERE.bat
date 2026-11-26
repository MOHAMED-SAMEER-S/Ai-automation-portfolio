@echo off
cd /d "%~dp0"
echo === AI Automation Portfolio ===
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv || (echo Python not found. Install Python 3.11+ and tick "Add to PATH". & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
echo Installing packages (first time takes a minute)...
pip install -q -r requirements.txt || (echo Install failed. & pause & exit /b 1)
if not exist .env copy .env.example .env >nul
echo Running tests...
python -m pytest -q
echo Starting dashboard - your browser will open.
streamlit run dashboard.py
pause
