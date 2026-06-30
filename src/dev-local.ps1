# ============================================================================
# NutriGain - Local Development Mode (PowerShell)
# ============================================================================
# Chế độ dev nhẹ: Docker chỉ chạy database, backend/frontend chạy local
# ============================================================================

Write-Host ""
Write-Host "========================================"
Write-Host "NutriGain - Local Development Mode"
Write-Host "========================================"
Write-Host ""

# Kiểm tra Docker đang chạy
try {
    docker info | Out-Null
} catch {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[1/3] Starting MySQL database container..." -ForegroundColor Cyan
docker compose up -d db

Write-Host ""
Write-Host "[2/3] Waiting for database to be ready..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "[3/3] Database is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "========================================"
Write-Host "Next steps:"
Write-Host "========================================"
Write-Host ""
Write-Host "1. Start Backend (in new terminal):" -ForegroundColor Yellow
Write-Host "   cd backend"
Write-Host "   .venv\Scripts\activate"
Write-Host "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Write-Host ""
Write-Host "2. Start Frontend (in new terminal):" -ForegroundColor Yellow
Write-Host "   cd frontend"
Write-Host "   npm run dev"
Write-Host ""
Write-Host "========================================"
Write-Host "Database Info:"
Write-Host "========================================"
Write-Host "Host: localhost"
Write-Host "Port: 3307"
Write-Host "Database: food_recommender"
Write-Host "User: nutrigain"
Write-Host "Password: yennhi2602"
Write-Host "========================================"
Write-Host ""

Read-Host "Press Enter to exit"
