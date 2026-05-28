@echo off
echo ========================================
echo WATCHING BACKEND LOGS (Google OAuth)
echo ========================================
echo.
echo Press Ctrl+C to stop watching
echo.
docker compose logs -f backend
