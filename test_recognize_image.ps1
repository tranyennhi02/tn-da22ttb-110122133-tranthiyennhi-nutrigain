# Test script for POST /api/v1/ingredients/recognize-image
# Usage: .\test_recognize_image.ps1 -Token "your_jwt_token" -ImagePath "D:\path\to\image.jpg"

param(
    [string]$Token = "",
    [string]$ImagePath = "",
    [string]$BaseUrl = "http://localhost:8000"
)

if (-not $Token) {
    Write-Host "ERROR: Provide -Token parameter (JWT from localStorage.auth_token in browser)" -ForegroundColor Red
    exit 1
}

if (-not $ImagePath -or -not (Test-Path $ImagePath)) {
    # Use a default test image if none provided
    Write-Host "No image path provided or file not found. Creating a test image..." -ForegroundColor Yellow
    Add-Type -AssemblyName System.Drawing
    $bmp = New-Object System.Drawing.Bitmap(100, 100)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.Clear([System.Drawing.Color]::Orange)
    $g.Dispose()
    $ImagePath = "$env:TEMP\test_ingredient.jpg"
    $bmp.Save($ImagePath, [System.Drawing.Imaging.ImageFormat]::Jpeg)
    $bmp.Dispose()
    Write-Host "Created test image at: $ImagePath" -ForegroundColor Cyan
}

Write-Host "`n[TEST] POST $BaseUrl/api/v1/ingredients/recognize-image" -ForegroundColor Cyan
Write-Host "[TEST] Image: $ImagePath" -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ingredients/recognize-image" `
        -Method Post `
        -Headers @{ Authorization = "Bearer $Token" } `
        -Form @{ file = Get-Item $ImagePath }
    
    Write-Host "`n[RESPONSE] Status: 200 OK" -ForegroundColor Green
    Write-Host "[RESPONSE] success: $($response.success)" -ForegroundColor Green
    Write-Host "[RESPONSE] ingredients: $($response.ingredients -join ', ')" -ForegroundColor Green
    Write-Host "[RESPONSE] message: $($response.message)" -ForegroundColor Green
    Write-Host "[RESPONSE] confidence: $($response.confidence)" -ForegroundColor Green
    Write-Host "[RESPONSE] method: $($response.method)" -ForegroundColor Green
    
    $response | ConvertTo-Json -Depth 5
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "`n[ERROR] Status: $statusCode" -ForegroundColor Red
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    
    try {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $body = $reader.ReadToEnd()
        Write-Host "[ERROR BODY] $body" -ForegroundColor Yellow
    } catch {}
}
