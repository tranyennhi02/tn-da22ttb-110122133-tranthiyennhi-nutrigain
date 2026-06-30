# ============================================================================
# NutriGain Backend - Local Development (PowerShell)
# ============================================================================
# Chạy backend local với database trong Docker
# Đảm bảo đã chạy: docker compose up -d db
# ============================================================================

Write-Host ""
Write-Host "========================================"
Write-Host "NutriGain Backend - Local Development"
Write-Host "========================================"
Write-Host ""

# Kiểm tra virtual environment
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "[ERROR] Virtual environment not found at .venv" -ForegroundColor Red
    Write-Host "Please create it first:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv"
    Write-Host "  .venv\Scripts\Activate.ps1"
    Write-Host "  pip install -r requirements.txt"
    Read-Host "Press Enter to exit"
    exit 1
}

# Activate virtual environment
Write-Host "[1/3] Activating virtual environment..." -ForegroundColor Cyan
& .venv\Scripts\Activate.ps1

# Load .env.local if exists
if (Test-Path ".env.local") {
    Write-Host "[2/3] Using .env.local configuration..." -ForegroundColor Cyan
    $env:ENV_FILE = ".env.local"
} else {
    Write-Host "[2/3] Using .env configuration..." -ForegroundColor Cyan
    $env:ENV_FILE = ".env"
}

Write-Host "[3/3] Starting backend server..." -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================"
Write-Host "Backend will start at:"
Write-Host "http://localhost:8000" -ForegroundColor Green
Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""

# Start uvicorn with reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
