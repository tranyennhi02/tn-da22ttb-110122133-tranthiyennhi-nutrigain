$root = "D:\DOANTOTNGHIEP\NutriGain"

Write-Host "Starting NutriGain local development..."

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$root\backend'; `$env:PYTHONPATH='$root;$root\backend'; ..\.venv-1\Scripts\activate; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --log-level debug"
)

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$root\frontend'; `$env:VITE_API_TARGET='http://127.0.0.1:8000'; `$env:VITE_API_BASE_URL='http://127.0.0.1:8000'; npm run dev"
)

Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Frontend: http://localhost:5173"