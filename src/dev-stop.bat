@echo off
REM ============================================================================
REM NutriGain - Stop Development Database
REM ============================================================================

echo.
echo ========================================
echo Stopping NutriGain Database
echo ========================================
echo.

docker compose stop db

echo.
echo Database stopped successfully!
echo To start again: docker compose up -d db
echo.

pause
