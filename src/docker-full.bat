@echo off
REM ============================================================================
REM NutriGain - Full Docker Mode
REM ============================================================================
REM Chạy tất cả services trong Docker (database + backend + frontend)
REM ============================================================================

echo.
echo ========================================
echo NutriGain - Full Docker Mode
echo ========================================
echo.

REM Kiểm tra Docker đang chạy
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo Starting all services (database + backend + frontend)...
echo This may take a few minutes on first run...
echo.

docker compose up --build

echo.
echo Services stopped.
echo.

pause
