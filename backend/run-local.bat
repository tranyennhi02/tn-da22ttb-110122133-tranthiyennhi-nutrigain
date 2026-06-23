@echo off
REM ============================================================================
REM NutriGain Backend - Local Development
REM ============================================================================
REM Chạy backend local với database trong Docker
REM Đảm bảo đã chạy: docker compose up -d db
REM ============================================================================

echo.
echo ========================================
echo NutriGain Backend - Local Development
echo ========================================
echo.

REM Kiểm tra virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at .venv
    echo Please create it first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/3] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Load .env.local if exists
if exist ".env.local" (
    echo [2/3] Using .env.local configuration...
    set ENV_FILE=.env.local
) else (
    echo [2/3] Using .env configuration...
    set ENV_FILE=.env
)

echo [3/3] Starting backend server...
echo.
echo ========================================
echo Backend will start at:
echo http://localhost:8000
echo API docs: http://localhost:8000/docs
echo ========================================
echo.

REM Start uvicorn with reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
