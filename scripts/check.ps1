[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$WebApp = Join-Path $RepoRoot 'apps\web'
$AnnotationService = Join-Path $RepoRoot 'services\annotation'
$RecognitionService = Join-Path $RepoRoot 'services\recognition'
$AuthService = Join-Path $RepoRoot 'services\auth'
$ComposeFile = Join-Path $RepoRoot 'infra\local\compose.yml'

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$WorkingDirectory
    )

    Write-Host "> $FilePath $($Arguments -join ' ')" -ForegroundColor DarkGray
    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$FilePath failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) {
    throw 'Corepack was not found.'
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv was not found.'
}

Write-Host 'Checking web application...' -ForegroundColor Cyan
Invoke-CheckedCommand 'corepack' @('pnpm', 'install', '--frozen-lockfile') $WebApp
Invoke-CheckedCommand 'corepack' @('pnpm', 'type-check') $WebApp

Write-Host 'Checking annotation service...' -ForegroundColor Cyan
Invoke-CheckedCommand 'uv' @('sync', '--frozen') $AnnotationService
Invoke-CheckedCommand 'uv' @('run', 'python', '-m', 'compileall', '-q', 'app') $AnnotationService
Invoke-CheckedCommand 'uv' @('run', 'alembic', 'heads') $AnnotationService

Write-Host 'Checking recognition service...' -ForegroundColor Cyan
Invoke-CheckedCommand 'uv' @('sync', '--frozen') $RecognitionService
Invoke-CheckedCommand 'uv' @('run', 'ruff', 'check', '.') $RecognitionService
Invoke-CheckedCommand 'uv' @(
    'run', 'python', '-m', 'compileall', '-q', 'api', 'worker', 'consumer', 'core', 'engine', 'scripts'
) $RecognitionService
Invoke-CheckedCommand 'uv' @('run', 'alembic', 'heads') $RecognitionService

Push-Location $RecognitionService
try {
    & uv run pytest
    if ($LASTEXITCODE -eq 5) {
        Write-Host 'No pytest test cases were collected; continuing.' -ForegroundColor Yellow
    }
    elseif ($LASTEXITCODE -ne 0) {
        throw "pytest failed with exit code $LASTEXITCODE"
    }
}

finally {
    Pop-Location
}

Write-Host 'Checking auth service...' -ForegroundColor Cyan
Invoke-CheckedCommand 'uv' @('sync', '--frozen') $AuthService
Invoke-CheckedCommand 'uv' @('run', 'ruff', 'check', '.') $AuthService
Invoke-CheckedCommand 'uv' @('run', 'python', '-m', 'compileall', '-q', 'app', 'scripts') $AuthService
Invoke-CheckedCommand 'uv' @('run', 'alembic', 'heads') $AuthService
Invoke-CheckedCommand 'uv' @('run', 'pytest') $AuthService

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host 'Validating local infrastructure Compose file...' -ForegroundColor Cyan
    $env:LOCAL_POSTGRES_USER = 'check'
    $env:LOCAL_POSTGRES_PASSWORD = 'check-password'
    $env:LOCAL_RABBITMQ_USER = 'check'
    $env:LOCAL_RABBITMQ_PASSWORD = 'check-password'
    $env:LOCAL_REDIS_PASSWORD = 'check-password'
    $env:LOCAL_MINIO_USER = 'check'
    $env:LOCAL_MINIO_PASSWORD = 'check-password'
    Invoke-CheckedCommand 'docker' @('compose', '-f', $ComposeFile, 'config', '--quiet') $RepoRoot
}
else {
    Write-Host 'Docker CLI not found; skipped Compose validation.' -ForegroundColor Yellow
}

if (Test-Path -LiteralPath (Join-Path $RepoRoot '.git')) {
    Write-Host 'Checking tracked files for local secrets and runtime data...' -ForegroundColor Cyan
    $tracked = & git -C $RepoRoot ls-files
    if ($LASTEXITCODE -ne 0) {
        throw 'git ls-files failed.'
    }
    $suspicious = $tracked | Where-Object {
        ($_ -match '(^|/)\.local/') -or
        ($_ -match '(^|/)logs?/' ) -or
        (($_ -match '(^|/)\.env($|\.)') -and ($_ -notmatch '\.env\.example$'))
    }
    if ($suspicious) {
        throw "Sensitive or runtime files are tracked:`n$($suspicious -join "`n")"
    }
}

Write-Host 'All configured checks passed.' -ForegroundColor Green
