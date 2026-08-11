# ===========================================
# AI Image Recognition Server & Worker Starter
# ===========================================
# 服务配置
$UvicornApp = "api_server:app"
$UvicornPort = "7987"
$CeleryApp = "worker_server"
$ConsumerApp = "result_consumer"
$QueueName = "tasks.image.disease_detection"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$PWD\api\src;$PWD\worker\src;$PWD\consumer\src;$PWD\core\src;$PWD\engine\src"

Write-Host "[*] 正在启动服务 (后台模式)..." -ForegroundColor Cyan

# 检查虚拟环境
if (-not (Test-Path ".venv\Scripts\uvicorn.exe")) {
    Write-Host "[!] 错误: 未检测到虚拟环境 (.venv)。" -ForegroundColor Red
    Write-Host "[*] 请先在项目根目录运行: uv sync" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

# 清理日志
$LogDir = "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
Remove-Item "$LogDir\api.log" -ErrorAction SilentlyContinue
Remove-Item "$LogDir\worker.log" -ErrorAction SilentlyContinue
Remove-Item "$LogDir\consumer.log" -ErrorAction SilentlyContinue

# 1. Start FastAPI
Write-Host "[1/3] 启动 FastAPI: http://localhost:$UvicornPort" -ForegroundColor Green
$ApiJob = Start-Job {
    $Root = if ($using:PSScriptRoot) { $using:PSScriptRoot } else { (Get-Location).Path }
    & "$Root\.venv\Scripts\uvicorn.exe" $using:UvicornApp --host 0.0.0.0 --port $using:UvicornPort --log-level info *> "$using:LogDir\api.log"
}
Start-Sleep -Seconds 3

# 获取 uvicorn 进程用于显示和停止
$ApiProc = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Select-Object -First 1

# 2. Start Celery Worker
Write-Host "[2/3] 启动 Celery Worker" -ForegroundColor Green
$WorkerProc = Start-Process -FilePath ".venv\Scripts\celery.exe" `
    -ArgumentList "-A $CeleryApp worker --loglevel=info -Q $QueueName --logfile=$LogDir\worker.log --pool=solo" `
    -WindowStyle Hidden -PassThru

# 3. Start Consumer
Write-Host "[3/3] 启动 Consumer" -ForegroundColor Green
$ConsumerProc = Start-Process -FilePath ".venv\Scripts\python.exe" `
    -ArgumentList "-m $ConsumerApp" `
    -RedirectStandardOutput "$LogDir\consumer.log" `
    -WindowStyle Hidden -PassThru

# Status
Write-Host ""
Write-Host "[*] 服务已在后台启动!" -ForegroundColor Green
if ($ApiProc) {
    Write-Host "    FastAPI PID: $($ApiProc.Id) -> http://localhost:$UvicornPort/docs"
} else {
    Write-Host "    FastAPI: 运行中"
}
Write-Host "    Worker PID:  $($WorkerProc.Id) -> 运行中"
Write-Host "    Consumer PID: $($ConsumerProc.Id) -> 运行中"
Write-Host "[*] 日志: $LogDir\api.log, $LogDir\worker.log, $LogDir\consumer.log"
Write-Host ""
Write-Host "按 [回车键] 停止所有服务..." -ForegroundColor Yellow
Read-Host

# Stop Services
Write-Host "[*] 正在停止服务..." -ForegroundColor DarkGray
if ($ApiJob) {
    Stop-Job $ApiJob -ErrorAction SilentlyContinue
    Remove-Job $ApiJob -ErrorAction SilentlyContinue
}
# 兜底：强制结束残留的 uvicorn 进程
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Stop-Process -Id $WorkerProc.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $ConsumerProc.Id -Force -ErrorAction SilentlyContinue
Write-Host "[*] 所有服务已停止。" -ForegroundColor Green
