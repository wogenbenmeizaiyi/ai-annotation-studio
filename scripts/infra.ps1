[CmdletBinding()]
param(
    [ValidateSet('up', 'down', 'status', 'reset')]
    [string]$Action = 'status'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ComposeFile = Join-Path $RepoRoot 'infra\local\compose.yml'
$LocalDirectory = Join-Path $RepoRoot '.local'
$InfraEnvironment = Join-Path $LocalDirectory 'infra.env'

function New-RandomSecret {
    $bytes = [Security.Cryptography.RandomNumberGenerator]::GetBytes(24)
    return [Convert]::ToHexString($bytes).ToLowerInvariant()
}

function Ensure-InfraEnvironment {
    if (Test-Path -LiteralPath $InfraEnvironment) {
        return
    }

    New-Item -ItemType Directory -Path $LocalDirectory -Force | Out-Null
    $lines = @(
        'LOCAL_POSTGRES_USER=annotation_local'
        "LOCAL_POSTGRES_PASSWORD=$(New-RandomSecret)"
        'LOCAL_POSTGRES_PORT=15432'
        'LOCAL_RABBITMQ_USER=annotation_local'
        "LOCAL_RABBITMQ_PASSWORD=$(New-RandomSecret)"
        'LOCAL_RABBITMQ_PORT=15673'
        'LOCAL_RABBITMQ_MANAGEMENT_PORT=15674'
        "LOCAL_REDIS_PASSWORD=$(New-RandomSecret)"
        'LOCAL_REDIS_PORT=16379'
        'LOCAL_MINIO_USER=annotation_local'
        "LOCAL_MINIO_PASSWORD=$(New-RandomSecret)"
        'LOCAL_MINIO_PORT=19000'
        'LOCAL_MINIO_CONSOLE_PORT=19001'
    )
    [IO.File]::WriteAllLines(
        $InfraEnvironment,
        $lines,
        [Text.UTF8Encoding]::new($false)
    )
    Write-Host "Created local credentials: $InfraEnvironment" -ForegroundColor Green
}

function Assert-DockerReady {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker CLI was not found. Install and start Docker Desktop, or use -Infra external.'
    }
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Desktop is not running. Start it, or use -Infra external.'
    }
}

function Invoke-Compose {
    param([Parameter(Mandatory)][string[]]$Arguments)

    & docker compose --env-file $InfraEnvironment -f $ComposeFile @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed: $($Arguments -join ' ')"
    }
}

function Get-InfraEnvironmentValue {
    param([Parameter(Mandatory)][string]$Name)

    foreach ($line in [IO.File]::ReadAllLines($InfraEnvironment)) {
        if ($line -match "^$([Regex]::Escape($Name))=(.*)$") {
            return $Matches[1].Trim()
        }
    }
    throw "Missing $Name in $InfraEnvironment"
}

function Start-LocalInfrastructure {
    Ensure-InfraEnvironment
    Assert-DockerReady
    $databaseUser = Get-InfraEnvironmentValue 'LOCAL_POSTGRES_USER'
    Invoke-Compose @('up', '-d', '--wait', 'postgres', 'rabbitmq', 'redis', 'minio')
    foreach ($databaseName in @(
        'annotation_studio_local',
        'recognition_service_local',
        'auth_service_local'
    )) {
        $exists = & docker compose --env-file $InfraEnvironment -f $ComposeFile `
            exec -T postgres psql -U $databaseUser -d postgres -tAc `
            "SELECT 1 FROM pg_database WHERE datname='$databaseName'"
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to inspect local PostgreSQL database: $databaseName"
        }
        if (-not (($exists -join '').Trim())) {
            & docker compose --env-file $InfraEnvironment -f $ComposeFile `
                exec -T postgres createdb -U $databaseUser $databaseName
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to create local PostgreSQL database: $databaseName"
            }
        }
    }
    Invoke-Compose @('run', '--rm', 'minio-init')

    Write-Host 'Local infrastructure is ready:' -ForegroundColor Green
    Write-Host '  PostgreSQL: 127.0.0.1:15432'
    Write-Host '  RabbitMQ:   127.0.0.1:15673 (management: http://127.0.0.1:15674)'
    Write-Host '  Redis:      127.0.0.1:16379'
    Write-Host '  MinIO:      http://127.0.0.1:19000 (console: http://127.0.0.1:19001)'
}

switch ($Action) {
    'up' {
        Start-LocalInfrastructure
    }
    'down' {
        Ensure-InfraEnvironment
        Assert-DockerReady
        Invoke-Compose @('down', '--remove-orphans')
        Write-Host 'Local infrastructure stopped; named volumes were retained.' -ForegroundColor Green
    }
    'status' {
        if (-not (Test-Path -LiteralPath $InfraEnvironment)) {
            Write-Host 'Local infrastructure has not been initialized.' -ForegroundColor Yellow
            break
        }
        Assert-DockerReady
        Invoke-Compose @('ps')
    }
    'reset' {
        Ensure-InfraEnvironment
        Assert-DockerReady
        $confirmation = Read-Host 'Type RESET to delete all local infrastructure data'
        if ($confirmation -cne 'RESET') {
            Write-Host 'Reset cancelled.' -ForegroundColor Yellow
            break
        }
        Invoke-Compose @('down', '--volumes', '--remove-orphans')
        Start-LocalInfrastructure
        Write-Host 'Local infrastructure was recreated with empty data volumes.' -ForegroundColor Green
    }
}
