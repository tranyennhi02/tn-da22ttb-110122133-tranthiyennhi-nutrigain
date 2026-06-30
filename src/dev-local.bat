@echo off
REM ============================================================================
REM NutriGain - Local Development Mode
REM ============================================================================
REM Chế độ dev nhẹ: Docker chỉ chạy database, backend/frontend chạy local
REM ============================================================================

echo.
echo ========================================
echo NutriGain - Local Development Mode
echo ========================================
echo.

REM Kiểm tra Docker đang chạy
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo [1/3] Starting MySQL database container...
docker compose up -d db

echo.
echo [2/3] Waiting for database to be ready...
timeout /t 10 /nobreak >nul

echo.
echo [3/3] Database is ready!
echo.
echo ========================================
echo Next steps:
echo ========================================
echo.
echo 1. Start Backend (in new terminal):
echo    cd backend
echo    .venv\Scripts\activate
echo    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
echo.
echo 2. Start Frontend (in new terminal):
echo    cd frontend
echo    npm run dev
echo.
echo ========================================
echo Database Info:
echo ========================================
echo Host: localhost
echo Port: 3307
echo Database: food_recommender
echo User: nutrigain
echo Password: yennhi2602
echo ========================================
echo.

pause
