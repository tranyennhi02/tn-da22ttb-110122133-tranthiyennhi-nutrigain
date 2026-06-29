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
echo [1/4] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Set cache paths (inside src/ structure as required by school)
echo [2/4] Configuring cache paths...
set HF_HOME=%CD%\..\.cache\huggingface
set TORCH_HOME=%CD%\..\.cache\torch
set TRANSFORMERS_CACHE=%CD%\..\.cache\huggingface\transformers

REM Create cache directories if they don't exist
if not exist "%HF_HOME%" mkdir "%HF_HOME%"
if not exist "%TORCH_HOME%" mkdir "%TORCH_HOME%"

REM Load .env.local if exists
if exist ".env.local" (
    echo [3/4] Using .env.local configuration...
    set ENV_FILE=.env.local
) else (
    echo [3/4] Using .env configuration...
    set ENV_FILE=.env
)

echo [4/4] Starting backend server...
echo.
echo ========================================
echo Backend will start at:
echo http://localhost:8000
echo API docs: http://localhost:8000/docs
echo Cache location: src\.cache\
echo ========================================
echo.
echo IMPORTANT: Server runs WITHOUT --reload for CLIP stability
echo To restart after code changes, press Ctrl+C and run again
echo.

REM Start uvicorn WITHOUT reload for CLIP/PyTorch stability
REM The --reload flag causes DLL loading issues with PyTorch on Windows
uvicorn app.main:app --host 0.0.0.0 --port 8000
