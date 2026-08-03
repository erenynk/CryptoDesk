Write-Host "CryptoDesk build baslatiliyor..." -ForegroundColor Cyan

if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force
}

if (Test-Path "dist") {
    Remove-Item "dist" -Recurse -Force
}

if (Test-Path "CryptoDesk.spec") {
    Remove-Item "CryptoDesk.spec" -Force
}

pyinstaller `
    --noconfirm `
    --windowed `
    --name CryptoDesk `
    app.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Build tamamlandi." -ForegroundColor Green
    Write-Host "EXE konumu: dist\CryptoDesk\CryptoDesk.exe" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Build basarisiz oldu." -ForegroundColor Red
}