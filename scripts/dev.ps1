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
$AuthService = Join-Path $RepoRoot 'services\auth'
$LocalDirectory = Join-Path $RepoRoot '.local'
$EffectiveEnvironmentDirectory = Join-Path $LocalDirectory 'env'
$LogDirectory = Join-Path $LocalDirectory 'logs'
$InfraEnvironment = Join-Path $LocalDirectory 'infra.env'
$ProbeScript = Join-Path $PSScriptRoot 'probe_infrastructure.py'
$InfraScript = Join-Path $PSScriptRoot 'infra.ps1'
$AnnotationSourceEnvironment = Join-Path $AnnotationService '.env'
$RecognitionSourceEnvironment = Join-Path $RecognitionService '.env'
$AuthSourceEnvironment = Join-Path $AuthService '.env'
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

function Resolve-EnvironmentFilePath {
    param(
        [Parameter(Mandatory)][string]$Value,
        [Parameter(Mandatory)][string]$BaseDirectory
    )

    if ([IO.Path]::IsPathRooted($Value)) {
        return [IO.Path]::GetFullPath($Value)
    }
    return [IO.Path]::GetFullPath((Join-Path $BaseDirectory $Value))
}

function Ensure-ApplicationDependencies {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw 'uv was not found. Install uv before starting the Python services.'
    }
    Write-Host 'Synchronizing annotation dependencies...' -ForegroundColor Cyan
    Invoke-CheckedCommand 'uv' @('sync', '--frozen') $AnnotationService
    Write-Host 'Synchronizing recognition dependencies...' -ForegroundColor Cyan
    Invoke-CheckedCommand 'uv' @('sync', '--frozen') $RecognitionService
    Write-Host 'Synchronizing auth dependencies...' -ForegroundColor Cyan
    Invoke-CheckedCommand 'uv' @('sync', '--frozen') $AuthService
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
        [Parameter(Mandatory)][string]$RecognitionEnvironment,
        [Parameter(Mandatory)][string]$AuthEnvironment
    )

    $recognitionPython = Join-Path $RecognitionService '.venv\Scripts\python.exe'
    $output = & $recognitionPython $ProbeScript `
        --annotation-env $AnnotationEnvironment `
        --recognition-env $RecognitionEnvironment `
        --auth-env $AuthEnvironment
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
    $authEffective = Join-Path $EffectiveEnvironmentDirectory 'auth.env'
    $authKeyDirectory = Join-Path $LocalDirectory 'auth'
    $authPrivateKey = Join-Path $authKeyDirectory 'private.pem'
    $authPublicKey = Join-Path $authKeyDirectory 'public.pem'

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
        AUTH_PUBLIC_KEY_PATH = $authPublicKey
        AUTH_REDIS_HOST = '127.0.0.1'
        AUTH_REDIS_PORT = Get-EnvironmentValue $localValues 'LOCAL_REDIS_PORT' '16379'
        AUTH_REDIS_PASSWORD = Get-EnvironmentValue $localValues 'LOCAL_REDIS_PASSWORD'
        AUTH_REDIS_DB = '3'
        AUTH_ALLOWED_ORIGINS = 'http://127.0.0.1:5173,http://localhost:5173'
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
        AUTH_PUBLIC_KEY_PATH = $authPublicKey
        AUTH_REDIS_DB = '3'
        PLATFORM_ALLOWED_ORIGINS = 'http://127.0.0.1:5173,http://localhost:5173'
    }
    $authOverrides = @{
        POSTGRES_HOST = '127.0.0.1'
        POSTGRES_PORT = Get-EnvironmentValue $localValues 'LOCAL_POSTGRES_PORT' '15432'
        POSTGRES_USER = Get-EnvironmentValue $localValues 'LOCAL_POSTGRES_USER'
        POSTGRES_PASSWORD = Get-EnvironmentValue $localValues 'LOCAL_POSTGRES_PASSWORD'
        POSTGRES_DB = 'auth_service_local'
        REDIS_HOST = '127.0.0.1'
        REDIS_PORT = Get-EnvironmentValue $localValues 'LOCAL_REDIS_PORT' '16379'
        REDIS_PASSWORD = Get-EnvironmentValue $localValues 'LOCAL_REDIS_PASSWORD'
        REDIS_DB = '3'
        AUTH_PRIVATE_KEY_PATH = $authPrivateKey
        AUTH_PUBLIC_KEY_PATH = $authPublicKey
        AUTH_COOKIE_SECURE = 'false'
        AUTH_ALLOWED_ORIGINS = 'http://127.0.0.1:5173,http://localhost:5173'
    }
    Write-EffectiveEnvironment $AnnotationSourceEnvironment $annotationEffective $annotationOverrides
    Write-EffectiveEnvironment $RecognitionSourceEnvironment $recognitionEffective $recognitionOverrides
    Write-EffectiveEnvironment $AuthSourceEnvironment $authEffective $authOverrides
    return @($annotationEffective, $recognitionEffective, $authEffective)
}

function New-ExternalEffectiveEnvironments {
    $authValues = Read-DotEnv $AuthSourceEnvironment
    $annotationEffective = Join-Path $EffectiveEnvironmentDirectory 'external-annotation.env'
    $recognitionEffective = Join-Path $EffectiveEnvironmentDirectory 'external-recognition.env'
    $authEffective = Join-Path $EffectiveEnvironmentDirectory 'external-auth.env'

    $authPrivateKey = Resolve-EnvironmentFilePath (
        Get-EnvironmentValue $authValues 'AUTH_PRIVATE_KEY_PATH' '.local/keys/auth-private.pem'
    ) $AuthService
    $authPublicKey = Resolve-EnvironmentFilePath (
        Get-EnvironmentValue $authValues 'AUTH_PUBLIC_KEY_PATH' '.local/keys/auth-public.pem'
    ) $AuthService
    $authIssuer = Get-EnvironmentValue $authValues 'AUTH_ISSUER' 'ai-annotation-studio-auth'
    $authAudience = Get-EnvironmentValue $authValues 'AUTH_AUDIENCE' 'ai-annotation-studio'
    $authAllowedOrigins = Get-EnvironmentValue $authValues 'AUTH_ALLOWED_ORIGINS' (
        'http://localhost:5173,http://127.0.0.1:5173'
    )
    $authRedisHost = Get-EnvironmentValue $authValues 'REDIS_HOST' 'localhost'
    $authRedisPort = Get-EnvironmentValue $authValues 'REDIS_PORT' '6379'
    $authRedisPassword = Get-EnvironmentValue $authValues 'REDIS_PASSWORD'
    $authRedisDatabase = Get-EnvironmentValue $authValues 'REDIS_DB' '3'
    if ($authRedisPassword) {
        $encodedRedisPassword = [Uri]::EscapeDataString($authRedisPassword)
        $authRedisUrl = "redis://:${encodedRedisPassword}@${authRedisHost}:${authRedisPort}/${authRedisDatabase}"
    }
    else {
        $authRedisUrl = "redis://${authRedisHost}:${authRedisPort}/${authRedisDatabase}"
    }

    $annotationOverrides = @{
        AUTH_PUBLIC_KEY_PATH = $authPublicKey
        AUTH_ISSUER = $authIssuer
        AUTH_AUDIENCE = $authAudience
        AUTH_REDIS_HOST = $authRedisHost
        AUTH_REDIS_PORT = $authRedisPort
        AUTH_REDIS_PASSWORD = $authRedisPassword
        AUTH_REDIS_DB = $authRedisDatabase
        AUTH_ALLOWED_ORIGINS = $authAllowedOrigins
    }
    $recognitionOverrides = @{
        AUTH_PUBLIC_KEY_PATH = $authPublicKey
        AUTH_ISSUER = $authIssuer
        AUTH_AUDIENCE = $authAudience
        AUTH_REDIS_URL = $authRedisUrl
        AUTH_REDIS_DB = $authRedisDatabase
        PLATFORM_ALLOWED_ORIGINS = $authAllowedOrigins
    }
    $authOverrides = @{
        AUTH_PRIVATE_KEY_PATH = $authPrivateKey
        AUTH_PUBLIC_KEY_PATH = $authPublicKey
    }

    Write-EffectiveEnvironment `
        $AnnotationSourceEnvironment $annotationEffective $annotationOverrides
    Write-EffectiveEnvironment `
        $RecognitionSourceEnvironment $recognitionEffective $recognitionOverrides
    Write-EffectiveEnvironment $AuthSourceEnvironment $authEffective $authOverrides
    return @($annotationEffective, $recognitionEffective, $authEffective)
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

function Assert-TcpPortAvailable {
    param(
        [Parameter(Mandatory)][int]$Port,
        [Parameter(Mandatory)][string]$ServiceName
    )

    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Start()
    }
    catch {
        throw "$ServiceName cannot start because port $Port is already in use. Stop the existing development process and try again."
    }
    finally {
        $listener.Stop()
    }
}

if ($Profile -in @('api', 'full')) {
    Assert-TcpPortAvailable 8787 'Auth API'
    Assert-TcpPortAvailable 8811 'Annotation API'
    Assert-TcpPortAvailable 7987 'Recognition API'
}
if ($Profile -in @('web', 'full')) {
    Assert-TcpPortAvailable 5173 'Web application'
}

if ($Profile -in @('api', 'full')) {
    Ensure-ApplicationDependencies

    $annotationEnvironment = $AnnotationSourceEnvironment
    $recognitionEnvironment = $RecognitionSourceEnvironment
    $authEnvironment = $AuthSourceEnvironment
    $useLocalInfrastructure = $Infra -eq 'local'

    if ($Infra -in @('auto', 'external')) {
        $externalFilesExist = (Test-Path -LiteralPath $AnnotationSourceEnvironment) -and (
            Test-Path -LiteralPath $RecognitionSourceEnvironment
        ) -and (Test-Path -LiteralPath $AuthSourceEnvironment)
        if (-not $externalFilesExist) {
            if ($Infra -eq 'external') {
                throw 'All three services require a .env file when -Infra external is selected.'
            }
            Write-Host 'External .env files are incomplete; selecting local infrastructure.' -ForegroundColor Yellow
            $useLocalInfrastructure = $true
        }
        else {
            $annotationValues = Read-DotEnv $AnnotationSourceEnvironment
            $recognitionValues = Read-DotEnv $RecognitionSourceEnvironment
            $authValues = Read-DotEnv $AuthSourceEnvironment
            if (Test-SameDatabase $annotationValues $recognitionValues) {
                if ($Infra -eq 'external') {
                    throw 'The two services point to the same PostgreSQL database. Configure separate databases.'
                }
                Write-Host 'External services share one database; selecting isolated local infrastructure.' -ForegroundColor Yellow
                $useLocalInfrastructure = $true
            }
            elseif ((Test-SameDatabase $annotationValues $authValues) -or (
                Test-SameDatabase $recognitionValues $authValues
            )) {
                if ($Infra -eq 'external') {
                    throw 'Annotation, recognition, and auth must use three separate PostgreSQL databases.'
                }
                Write-Host 'External services share one database; selecting isolated local infrastructure.' -ForegroundColor Yellow
                $useLocalInfrastructure = $true
            }
            else {
                Write-Host 'Checking configured external infrastructure...' -ForegroundColor Cyan
                $externalReady = Invoke-InfrastructureProbe `
                    $AnnotationSourceEnvironment `
                    $RecognitionSourceEnvironment `
                    $AuthSourceEnvironment
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
        $authEnvironment = $effectiveEnvironments[2]
        Write-Host 'Verifying local infrastructure...' -ForegroundColor Cyan
        if (-not (Invoke-InfrastructureProbe $annotationEnvironment $recognitionEnvironment $authEnvironment)) {
            throw 'Local infrastructure started but failed protocol checks.'
        }
    }
    else {
        $effectiveEnvironments = New-ExternalEffectiveEnvironments
        $annotationEnvironment = $effectiveEnvironments[0]
        $recognitionEnvironment = $effectiveEnvironments[1]
        $authEnvironment = $effectiveEnvironments[2]
        Write-Host 'Using configured external infrastructure.' -ForegroundColor Green
    }

    Invoke-DatabaseMigration 'annotation' $AnnotationService $annotationEnvironment
    Invoke-DatabaseMigration 'recognition' $RecognitionService $recognitionEnvironment
    Invoke-DatabaseMigration 'auth' $AuthService $authEnvironment
    $previousAuthEnvironmentFile = $env:APP_ENV_FILE
    try {
        $env:APP_ENV_FILE = $authEnvironment
        Invoke-CheckedCommand 'uv' @('run', 'python', '-m', 'scripts.ensure_keys') $AuthService
    }
    finally {
        if ($null -eq $previousAuthEnvironmentFile) {
            Remove-Item Env:APP_ENV_FILE -ErrorAction SilentlyContinue
        }
        else {
            $env:APP_ENV_FILE = $previousAuthEnvironmentFile
        }
    }
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
        $authPython = Join-Path $AuthService '.venv\Scripts\python.exe'
        Start-ManagedProcess 'auth-api' $authPython @('run.py') $AuthService (@{
            APP_ENV_FILE = $authEnvironment
            PYTHONUTF8 = '1'
            PYTHONIOENCODING = 'utf-8'
        })
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
        Write-Host '  Auth:        http://127.0.0.1:8787/docs'
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
