$AppModule = "app.main:app"
$HostAddr = "0.0.0.0"
$Port = 8811

Write-Host "Starting FastAPI with uv..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow

& uv run uvicorn $AppModule --host $HostAddr --port $Port.ToString() --log-level debug --reload
