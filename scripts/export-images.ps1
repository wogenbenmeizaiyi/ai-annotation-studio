[CmdletBinding()]
param(
    [ValidateSet('business', 'infrastructure', 'all')]
    [string]$ImageSet = 'business',

    [string]$Tag = 'offline',

    [ValidateSet('linux/amd64')]
    [string]$Platform = 'linux/amd64',

    [string]$OutputPath,

    [switch]$Build,

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ExportDirectory = Join-Path $RepoRoot '.local\exports'
$BusinessImages = @(
    "ai-studio-web:$Tag"
    "ai-studio-annotation:$Tag"
    "ai-studio-auth:$Tag"
    "ai-studio-recognition-api:$Tag"
    "ai-studio-recognition-worker-gpu:$Tag"
    "ai-studio-recognition-worker-multimodal:$Tag"
    "ai-studio-recognition-consumer:$Tag"
)
$InfrastructureImages = @(
    'postgres:alpine'
    'rabbitmq:management-alpine'
    'redis:alpine'
    'minio/minio:latest'
    'minio/mc:latest'
)

function Invoke-Docker {
    param([Parameter(Mandatory)][string[]]$Arguments)

    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker failed: $($Arguments -join ' ')"
    }
}

function Pull-DockerImage {
    param([Parameter(Mandatory)][string]$Image)

    for ($attempt = 1; $attempt -le 3; $attempt++) {
        Write-Host "Pulling base image $Image (attempt $attempt/3)..." -ForegroundColor Cyan
        & docker pull --platform $Platform $Image
        if ($LASTEXITCODE -eq 0) {
            return
        }
        if ($attempt -lt 3) {
            Start-Sleep -Seconds (3 * $attempt)
        }
    }
    throw "Failed to pull base image after 3 attempts: $Image"
}

function Build-BusinessImages {
    Write-Host "Building business images for $Platform..." -ForegroundColor Cyan

    foreach ($baseImage in @(
        'node:22-alpine'
        'nginx:alpine'
        'python:3.12-slim'
        'pytorch/pytorch:2.10.0-cuda13.0-cudnn9-runtime'
    )) {
        Pull-DockerImage $baseImage
    }

    Invoke-Docker @(
        'build', '--platform', $Platform,
        '--build-arg', 'VITE_APP_BASE_PATH=/',
        '-f', 'apps/web/deploy/Dockerfile',
        '-t', "ai-studio-web:$Tag",
        'apps/web'
    )
    Invoke-Docker @(
        'build', '--platform', $Platform,
        '-f', 'services/annotation/Dockerfile.deps',
        '-t', "ai-studio-annotation-deps:$Tag",
        'services/annotation'
    )
    Invoke-Docker @(
        'build', '--platform', $Platform,
        '--build-arg', "BASE_IMAGE=ai-studio-annotation-deps:$Tag",
        '-f', 'services/annotation/Dockerfile',
        '-t', "ai-studio-annotation:$Tag",
        'services/annotation'
    )
    Invoke-Docker @(
        'build', '--platform', $Platform,
        '-f', 'services/auth/Dockerfile.deps',
        '-t', "ai-studio-auth-deps:$Tag",
        'services/auth'
    )
    Invoke-Docker @(
        'build', '--platform', $Platform,
        '--build-arg', "BASE_IMAGE=ai-studio-auth-deps:$Tag",
        '-f', 'services/auth/Dockerfile',
        '-t', "ai-studio-auth:$Tag",
        'services/auth'
    )
    Invoke-Docker @(
        'build', '--platform', $Platform,
        '-f', 'services/recognition/Dockerfile.deps',
        '-t', "ai-studio-recognition-deps:$Tag",
        'services/recognition'
    )
    foreach ($target in @('api', 'consumer')) {
        Invoke-Docker @(
            'build', '--platform', $Platform,
            '--build-arg', "BASE_IMAGE=ai-studio-recognition-deps:$Tag",
            '-f', "services/recognition/Dockerfile.$target",
            '-t', "ai-studio-recognition-$target`:$Tag",
            'services/recognition'
        )
    }
    Invoke-Docker @(
        'build', '--platform', $Platform,
        '--build-arg', "BASE_IMAGE=ai-studio-recognition-deps:$Tag",
        '-f', 'services/recognition/Dockerfile.worker-gpu',
        '-t', "ai-studio-recognition-worker-gpu:$Tag",
        'services/recognition'
    )
    Invoke-Docker @(
        'build', '--platform', $Platform,
        '-f', 'services/recognition/Dockerfile.worker-multimodal',
        '-t', "ai-studio-recognition-worker-multimodal:$Tag",
        'services/recognition'
    )
}

function Test-ImageExists {
    param([Parameter(Mandatory)][string]$Image)

    & docker image inspect $Image *> $null
    return $LASTEXITCODE -eq 0
}

function Compress-TarArchive {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination
    )

    $sourceStream = [IO.File]::OpenRead($Source)
    $destinationStream = [IO.File]::Create($Destination)
    $gzipStream = [IO.Compression.GZipStream]::new(
        $destinationStream,
        [IO.Compression.CompressionLevel]::Fastest
    )
    try {
        $buffer = [byte[]]::new(4MB)
        while (($read = $sourceStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
            $gzipStream.Write($buffer, 0, $read)
        }
    }
    finally {
        $gzipStream.Dispose()
        $destinationStream.Dispose()
        $sourceStream.Dispose()
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker was not found. Start Docker Desktop and try again.'
}

Push-Location $RepoRoot
try {
    $dockerPlatform = (& docker info --format '{{.OSType}}/{{.Architecture}}' 2>$null).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker is not available. Start Docker Desktop and use Linux containers.'
    }
    if (-not $dockerPlatform.StartsWith('linux/')) {
        throw "Docker is using $dockerPlatform. Switch Docker Desktop to Linux containers."
    }

    if ($Build -and $ImageSet -in @('business', 'all')) {
        Build-BusinessImages
    }

    $images = switch ($ImageSet) {
        'business' { $BusinessImages }
        'infrastructure' { $InfrastructureImages }
        'all' { $BusinessImages + $InfrastructureImages }
    }
    $missingImages = @($images | Where-Object { -not (Test-ImageExists $_) })
    if ($missingImages.Count -gt 0) {
        Write-Host 'Missing images:' -ForegroundColor Red
        $missingImages | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        if ($ImageSet -in @('business', 'all') -and -not $Build) {
            Write-Host 'Run again with -Build to build business images first.' `
                -ForegroundColor Yellow
        }
        throw 'The requested image set is incomplete.'
    }

    if (-not $OutputPath) {
        $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $OutputPath = Join-Path $ExportDirectory (
            "ai-annotation-studio-$ImageSet-$Tag-$timestamp.tar.gz"
        )
    }
    elseif (-not [IO.Path]::IsPathRooted($OutputPath)) {
        $OutputPath = Join-Path $RepoRoot $OutputPath
    }
    $OutputPath = [IO.Path]::GetFullPath($OutputPath)
    if (-not $OutputPath.EndsWith('.tar.gz', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'OutputPath must end with .tar.gz.'
    }

    $outputDirectory = Split-Path -Parent $OutputPath
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
    $checksumPath = "$OutputPath.sha256"
    if ((Test-Path -LiteralPath $OutputPath) -or (Test-Path -LiteralPath $checksumPath)) {
        if (-not $Force) {
            throw "Output already exists: $OutputPath. Use -Force to overwrite it."
        }
        Remove-Item -LiteralPath $OutputPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $checksumPath -Force -ErrorAction SilentlyContinue
    }

    $temporaryTar = Join-Path $outputDirectory (
        ".$([IO.Path]::GetFileNameWithoutExtension($OutputPath)).$PID.tar"
    )
    try {
        Write-Host 'Exporting images:' -ForegroundColor Cyan
        $images | ForEach-Object { Write-Host "  $_" }
        Invoke-Docker (@('save', '--output', $temporaryTar) + $images)
        Write-Host "Compressing to $OutputPath..." -ForegroundColor Cyan
        Compress-TarArchive $temporaryTar $OutputPath
    }
    finally {
        if (Test-Path -LiteralPath $temporaryTar) {
            Remove-Item -LiteralPath $temporaryTar -Force
        }
    }

    $hash = (Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $checksumLine = "$hash  $([IO.Path]::GetFileName($OutputPath))"
    [IO.File]::WriteAllText(
        $checksumPath,
        "$checksumLine$([Environment]::NewLine)",
        [Text.UTF8Encoding]::new($false)
    )

    $size = [math]::Round((Get-Item -LiteralPath $OutputPath).Length / 1GB, 2)
    Write-Host ''
    Write-Host "Archive:  $OutputPath" -ForegroundColor Green
    Write-Host "Checksum: $checksumPath" -ForegroundColor Green
    Write-Host "Size:     $size GiB"
}
finally {
    Pop-Location
}
