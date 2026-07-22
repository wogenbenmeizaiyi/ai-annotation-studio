[CmdletBinding()]
param(
    [ValidateSet('web', 'api', 'full')]
    [string]$Profile = 'full',

    [ValidateSet('auto', 'external', 'local')]
    [string]$Infra = 'auto'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$WebApp = Join-Path $RepoRoot 'apps\web'
$AnnotationService = Join-Path $RepoRoot 'services\annotation'
$RecognitionService = Join-Path $RepoRoot 'services\recognition'
$LocalDirectory = Join-Path $RepoRoot '.local'
$EffectiveEnvironmentDirectory = Join-Path $LocalDirectory 'env'
$LogDirectory = Join-Path $LocalDirectory 'logs'
$InfraEnvironment = Join-Path $LocalDirectory 'infra.env'
$ProbeScript = Join-Path $PSScriptRoot 'probe_infrastructure.py'
$InfraScript = Join-Path $PSScriptRoot 'infra.ps1'
$AnnotationSourceEnvironment = Join-Path $AnnotationService '.env'
$RecognitionSourceEnvironment = Join-Path $RecognitionService '.env'
$ManagedProcesses = [Collections.Generic.List[object]]::new()

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$WorkingDirectory
    )

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

function Read-DotEnv {
    param([Parameter(Mandatory)][string]$Path)

    $values = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $values
    }

    foreach ($line in [IO.File]::ReadAllLines($Path)) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) {
            continue
        }
        if ($trimmed.StartsWith('export ')) {
            $trimmed = $trimmed.Substring(7).Trim()
        }
        $separator = $trimmed.IndexOf('=')
        if ($separator -le 0) {
            continue
        }
        $key = $trimmed.Substring(0, $separator).Trim()
        $value = $trimmed.Substring($separator + 1).Trim()
        if ($value.Length -ge 2) {
            $quotedWithSingle = $value.StartsWith("'") -and $value.EndsWith("'")
            $quotedWithDouble = $value.StartsWith('"') -and $value.EndsWith('"')
            if ($quotedWithSingle -or $quotedWithDouble) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }
        $values[$key] = $value
    }
    return $values
}

function Get-EnvironmentValue {
    param(
        [Parameter(Mandatory)][hashtable]$Values,
        [Parameter(Mandatory)][string]$Key,
        [string]$Default = ''
    )

    if ($Values.ContainsKey($Key) -and $Values[$Key]) {
        return [string]$Values[$Key]
    }
    return $Default
}

function Test-SameDatabase {
    param(
        [Parameter(Mandatory)][hashtable]$AnnotationValues,
        [Parameter(Mandatory)][hashtable]$RecognitionValues
    )

    $annotationTarget = '{0}:{1}/{2}' -f (
        Get-EnvironmentValue $AnnotationValues 'POSTGRES_HOST' 'localhost'
    ), (
        Get-EnvironmentValue $AnnotationValues 'POSTGRES_PORT' '5432'
    ), (
        Get-EnvironmentValue $AnnotationValues 'POSTGRES_DB' 'annotation_studio'
    )
    $recognitionTarget = '{0}:{1}/{2}' -f (
        Get-EnvironmentValue $RecognitionValues 'POSTGRES_HOST' 'localhost'
    ), (
        Get-EnvironmentValue $RecognitionValues 'POSTGRES_PORT' '5432'
    ), (
        Get-EnvironmentValue $RecognitionValues 'POSTGRES_DB' 'annotation_studio'
    )
    return $annotationTarget.Equals($recognitionTarget, [StringComparison]::OrdinalIgnoreCase)
}

function Write-EffectiveEnvironment {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination,
        [Parameter(Mandatory)][hashtable]$Overrides
    )

    $lines = [Collections.Generic.List[string]]::new()
    if (Test-Path -LiteralPath $Source) {
        foreach ($line in [IO.File]::ReadAllLines($Source)) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') {
                if ($Overrides.ContainsKey($Matches[1])) {
                    continue
                }
            }
            $lines.Add($line)
        }
    }
    foreach ($key in ($Overrides.Keys | Sort-Object)) {
        $lines.Add("$key=$($Overrides[$key])")
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    [IO.File]::WriteAllLines($Destination, $lines, [Text.UTF8Encoding]::new($false))
}

function Ensure-ApplicationDependencies {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw 'uv was not found. Install uv before starting the Python services.'
    }
    Write-Host 'Synchronizing annotation dependencies...' -ForegroundColor Cyan
    Invoke-CheckedCommand 'uv' @('sync', '--frozen') $AnnotationService
    Write-Host 'Synchronizing recognition dependencies...' -ForegroundColor Cyan
    Invoke-CheckedCommand 'uv' @('sync', '--frozen') $RecognitionService
}

function Ensure-WebDependencies {
    if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) {
        throw 'Corepack was not found. Install a supported Node.js version first.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $WebApp 'node_modules'))) {
        Write-Host 'Installing web dependencies...' -ForegroundColor Cyan
        Invoke-CheckedCommand 'corepack' @('pnpm', 'install', '--frozen-lockfile') $WebApp
    }
}

function Invoke-InfrastructureProbe {
    param(
        [Parameter(Mandatory)][string]$AnnotationEnvironment,
        [Parameter(Mandatory)][string]$RecognitionEnvironment
    )

    $recognitionPython = Join-Path $RecognitionService '.venv\Scripts\python.exe'
    $output = & $recognitionPython $ProbeScript `
        --annotation-env $AnnotationEnvironment `
        --recognition-env $RecognitionEnvironment
    $probeExitCode = $LASTEXITCODE
    try {
        $result = ($output -join [Environment]::NewLine) | ConvertFrom-Json
    }
    catch {
        Write-Host ($output -join [Environment]::NewLine) -ForegroundColor Red
        throw 'Infrastructure probe returned invalid output.'
    }

    foreach ($check in $result.checks) {
        if ($check.ok) {
            Write-Host "  [OK] $($check.name) -> $($check.target)" -ForegroundColor Green
        }
        else {
            Write-Host "  [FAIL] $($check.name) -> $($check.target): $($check.error)" -ForegroundColor Yellow
        }
    }
    return ($probeExitCode -eq 0 -and [bool]$result.ok)
}

function New-LocalEffectiveEnvironments {
    $localValues = Read-DotEnv $InfraEnvironment
    $annotationEffective = Join-Path $EffectiveEnvironmentDirectory 'annotation.env'
    $recognitionEffective = Join-Path $EffectiveEnvironmentDirectory 'recognition.env'

    $annotationOverrides = @{
        POSTGRES_HOST = '127.0.0.1'
        POSTGRES_PORT = Get-EnvironmentValue $localValues 'LOCAL_POSTGRES_PORT' '15432'
        POSTGRES_USER = Get-EnvironmentValue $localValues 'LOCAL_POSTGRES_USER'
        POSTGRES_PASSWORD = Get-EnvironmentValue $localValues 'LOCAL_POSTGRES_PASSWORD'
        POSTGRES_DB = 'annotation_studio_local'
        S3_ENDPOINT = "http://127.0.0.1:$(Get-EnvironmentValue $localValues 'LOCAL_MINIO_PORT' '19000')"
        S3_ACCESS_KEY = Get-EnvironmentValue $localValues 'LOCAL_MINIO_USER'
        S3_SECRET_KEY = Get-EnvironmentValue $localValues 'LOCAL_MINIO_PASSWORD'
        S3_REGION = 'us-east-1'
        S3_SIGNATURE_VERSION = 's3v4'
        S3_BUCKET_NAME = 'ai-cmm'
    }
    $recognitionOverrides = @{
        POSTGRES_HOST = '127.0.0.1'
        POSTGRES_PORT = Get-EnvironmentValue $localValues 'LOCAL_POSTGRES_PORT' '15432'
        POSTGRES_USER = Get-EnvironmentValue $localValues 'LOCAL_POSTGRES_USER'
        POSTGRES_PASSWORD = Get-EnvironmentValue $localValues 'LOCAL_POSTGRES_PASSWORD'
        POSTGRES_DB = 'recognition_service_local'
        RABBITMQ_HOST = '127.0.0.1'
        RABBITMQ_PORT = Get-EnvironmentValue $localValues 'LOCAL_RABBITMQ_PORT' '15673'
        RABBITMQ_USER = Get-EnvironmentValue $localValues 'LOCAL_RABBITMQ_USER'
        RABBITMQ_PASS = Get-EnvironmentValue $localValues 'LOCAL_RABBITMQ_PASSWORD'
        RABBITMQ_VHOST = '/'
        REDIS_HOST = '127.0.0.1'
        REDIS_PORT = Get-EnvironmentValue $localValues 'LOCAL_REDIS_PORT' '16379'
        REDIS_DB = '0'
        REDIS_PASSWORD = Get-EnvironmentValue $localValues 'LOCAL_REDIS_PASSWORD'
        S3_ENDPOINT = "http://127.0.0.1:$(Get-EnvironmentValue $localValues 'LOCAL_MINIO_PORT' '19000')"
        S3_ACCESS_KEY = Get-EnvironmentValue $localValues 'LOCAL_MINIO_USER'
        S3_SECRET_KEY = Get-EnvironmentValue $localValues 'LOCAL_MINIO_PASSWORD'
        S3_REGION = 'us-east-1'
        S3_SIGNATURE_VERSION = 's3v4'
    }
    Write-EffectiveEnvironment $AnnotationSourceEnvironment $annotationEffective $annotationOverrides
    Write-EffectiveEnvironment $RecognitionSourceEnvironment $recognitionEffective $recognitionOverrides
    return @($annotationEffective, $recognitionEffective)
}

function Invoke-DatabaseMigration {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$ServiceDirectory,
        [Parameter(Mandatory)][string]$EnvironmentFile
    )

    $values = Read-DotEnv $EnvironmentFile
    $target = '{0}:{1}/{2}' -f (
        Get-EnvironmentValue $values 'POSTGRES_HOST' 'localhost'
    ), (
        Get-EnvironmentValue $values 'POSTGRES_PORT' '5432'
    ), (
        Get-EnvironmentValue $values 'POSTGRES_DB' 'annotation_studio'
    )
    Write-Host "Migrating $Name database: $target" -ForegroundColor Cyan

    $previousEnvironmentFile = $env:APP_ENV_FILE
    try {
        $env:APP_ENV_FILE = $EnvironmentFile
        Write-Host '  Current revision:'
        Invoke-CheckedCommand 'uv' @('run', 'alembic', 'current') $ServiceDirectory
        Write-Host '  Target revision:'
        Invoke-CheckedCommand 'uv' @('run', 'alembic', 'heads') $ServiceDirectory
        Invoke-CheckedCommand 'uv' @('run', 'alembic', 'upgrade', 'head') $ServiceDirectory
    }
    finally {
        if ($null -eq $previousEnvironmentFile) {
            Remove-Item Env:APP_ENV_FILE -ErrorAction SilentlyContinue
        }
        else {
            $env:APP_ENV_FILE = $previousEnvironmentFile
        }
    }
}

function Start-ManagedProcess {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [hashtable]$Environment = @{}
    )

    New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    $stdout = Join-Path $LogDirectory "$Name.out.log"
    $stderr = Join-Path $LogDirectory "$Name.err.log"
    $previousValues = @{}
    $process = $null
    try {
        foreach ($key in $Environment.Keys) {
            $previousValues[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
            [Environment]::SetEnvironmentVariable($key, [string]$Environment[$key], 'Process')
        }
        $process = Start-Process `
            -FilePath $FilePath `
            -ArgumentList $Arguments `
            -WorkingDirectory $WorkingDirectory `
            -RedirectStandardOutput $stdout `
            -RedirectStandardError $stderr `
            -WindowStyle Hidden `
            -PassThru
    }
    finally {
        foreach ($key in $Environment.Keys) {
            [Environment]::SetEnvironmentVariable($key, $previousValues[$key], 'Process')
        }
    }
    if ($null -eq $process) {
        throw "Failed to start $Name."
    }
    $ManagedProcesses.Add([pscustomobject]@{ Name = $Name; Process = $process })
    Write-Host "Started $Name (PID $($process.Id)); logs: $stdout" -ForegroundColor Green
}

function Stop-ManagedProcess {
    param([Parameter(Mandatory)]$Entry)

    if ($Entry.Process.HasExited) {
        return
    }
    Write-Host "Stopping $($Entry.Name) (PID $($Entry.Process.Id))..." -ForegroundColor Yellow
    & taskkill.exe /PID $Entry.Process.Id /T /F *> $null
}

if ($Profile -in @('api', 'full')) {
    Ensure-ApplicationDependencies

    $annotationEnvironment = $AnnotationSourceEnvironment
    $recognitionEnvironment = $RecognitionSourceEnvironment
    $useLocalInfrastructure = $Infra -eq 'local'

    if ($Infra -in @('auto', 'external')) {
        $externalFilesExist = (Test-Path -LiteralPath $AnnotationSourceEnvironment) -and (
            Test-Path -LiteralPath $RecognitionSourceEnvironment
        )
        if (-not $externalFilesExist) {
            if ($Infra -eq 'external') {
                throw 'Both services require a .env file when -Infra external is selected.'
            }
            Write-Host 'External .env files are incomplete; selecting local infrastructure.' -ForegroundColor Yellow
            $useLocalInfrastructure = $true
        }
        else {
            $annotationValues = Read-DotEnv $AnnotationSourceEnvironment
            $recognitionValues = Read-DotEnv $RecognitionSourceEnvironment
            if (Test-SameDatabase $annotationValues $recognitionValues) {
                if ($Infra -eq 'external') {
                    throw 'The two services point to the same PostgreSQL database. Configure separate databases.'
                }
                Write-Host 'External services share one database; selecting isolated local infrastructure.' -ForegroundColor Yellow
                $useLocalInfrastructure = $true
            }
            else {
                Write-Host 'Checking configured external infrastructure...' -ForegroundColor Cyan
                $externalReady = Invoke-InfrastructureProbe `
                    $AnnotationSourceEnvironment `
                    $RecognitionSourceEnvironment
                if (-not $externalReady) {
                    if ($Infra -eq 'external') {
                        throw 'One or more external infrastructure checks failed.'
                    }
                    Write-Host 'External checks failed; selecting local infrastructure.' -ForegroundColor Yellow
                    $useLocalInfrastructure = $true
                }
            }
        }
    }

    if ($useLocalInfrastructure) {
        & $InfraScript -Action up
        if ($LASTEXITCODE -ne 0) {
            throw 'Local infrastructure failed to start.'
        }
        $effectiveEnvironments = New-LocalEffectiveEnvironments
        $annotationEnvironment = $effectiveEnvironments[0]
        $recognitionEnvironment = $effectiveEnvironments[1]
        Write-Host 'Verifying local infrastructure...' -ForegroundColor Cyan
        if (-not (Invoke-InfrastructureProbe $annotationEnvironment $recognitionEnvironment)) {
            throw 'Local infrastructure started but failed protocol checks.'
        }
    }
    else {
        Write-Host 'Using configured external infrastructure.' -ForegroundColor Green
    }

    Invoke-DatabaseMigration 'annotation' $AnnotationService $annotationEnvironment
    Invoke-DatabaseMigration 'recognition' $RecognitionService $recognitionEnvironment
}

if ($Profile -in @('web', 'full')) {
    Ensure-WebDependencies
}

try {
    if ($Profile -in @('api', 'full')) {
        $recognitionPythonPath = @(
            (Join-Path $RecognitionService 'api\src')
            (Join-Path $RecognitionService 'worker\src')
            (Join-Path $RecognitionService 'consumer\src')
            (Join-Path $RecognitionService 'core\src')
            (Join-Path $RecognitionService 'engine\src')
        ) -join ';'
        $annotationPython = Join-Path $AnnotationService '.venv\Scripts\python.exe'
        Start-ManagedProcess 'annotation-api' $annotationPython @('run.py') $AnnotationService (@{
            APP_ENV_FILE = $annotationEnvironment
            PYTHONUTF8 = '1'
            PYTHONIOENCODING = 'utf-8'
        })

        $recognitionEnvironmentVariables = @{
            APP_ENV_FILE = $recognitionEnvironment
            PYTHONPATH = $recognitionPythonPath
            PYTHONUTF8 = '1'
            PYTHONIOENCODING = 'utf-8'
        }
        $recognitionUvicorn = Join-Path $RecognitionService '.venv\Scripts\uvicorn.exe'
        Start-ManagedProcess 'recognition-api' $recognitionUvicorn @(
            'api_server:app', '--host', '0.0.0.0', '--port', '7987', '--reload'
        ) $RecognitionService $recognitionEnvironmentVariables

        if ($Profile -eq 'full') {
            $recognitionCelery = Join-Path $RecognitionService '.venv\Scripts\celery.exe'
            Start-ManagedProcess 'recognition-worker' $recognitionCelery @(
                '-A', 'worker_server.celery_app', 'worker', '--loglevel=info', '--pool=solo',
                '-Q', 'tasks.image.disease_detection', '--concurrency=1'
            ) $RecognitionService $recognitionEnvironmentVariables
            $recognitionPython = Join-Path $RecognitionService '.venv\Scripts\python.exe'
            Start-ManagedProcess 'recognition-consumer' $recognitionPython @(
                '-m', 'result_consumer'
            ) $RecognitionService $recognitionEnvironmentVariables
        }
    }

    if ($Profile -in @('web', 'full')) {
        Start-ManagedProcess 'web' $env:ComSpec @(
            '/d', '/s', '/c', 'corepack pnpm dev'
        ) $WebApp
    }

    Write-Host ''
    Write-Host 'Native development processes are running. Press Ctrl+C to stop them.' -ForegroundColor Cyan
    if ($Profile -in @('web', 'full')) {
        Write-Host '  Web:         http://127.0.0.1:5173'
    }
    if ($Profile -in @('api', 'full')) {
        Write-Host '  Annotation:  http://127.0.0.1:8811/docs'
        Write-Host '  Recognition: http://127.0.0.1:7987/docs'
    }

    while ($true) {
        Start-Sleep -Seconds 1
        $exited = $ManagedProcesses | Where-Object { $_.Process.HasExited }
        if ($exited) {
            $names = ($exited | ForEach-Object { $_.Name }) -join ', '
            throw "One or more development processes exited: $names. Check $LogDirectory."
        }
    }
}
finally {
    for ($index = $ManagedProcesses.Count - 1; $index -ge 0; $index--) {
        Stop-ManagedProcess $ManagedProcesses[$index]
    }
    Write-Host 'Native development processes stopped. Infrastructure containers were retained.' -ForegroundColor Green
}
