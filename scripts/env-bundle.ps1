[CmdletBinding()]
param(
    [string]$Output = ''
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Files = @(
    'services/auth/.env',
    'services/annotation/.env',
    'services/recognition/.env'
)

if (-not $Output) {
    $Output = Join-Path $RepoRoot '.local\env-bundle.b64'
}

$sb = [System.Text.StringBuilder]::new()
foreach ($Rel in $Files) {
    $Path = Join-Path $RepoRoot ($Rel -replace '/', [IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing file: $Rel"
    }
    [void]$sb.AppendLine("### FILE: $Rel")
    [void]$sb.Append((Get-Content -LiteralPath $Path -Raw))
    [void]$sb.AppendLine()
    [void]$sb.AppendLine()
}

$Text = $sb.ToString()
$Bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
$B64 = [Convert]::ToBase64String($Bytes)

$OutDir = Split-Path -Parent $Output
if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}
[IO.File]::WriteAllText($Output, $B64, [System.Text.Encoding]::ASCII)

Write-Host "Bundle written to: $Output"
Write-Host "GitLab variable name: ENV_BUNDLE_B64"
Write-Host "GitLab variable value ($($B64.Length) chars):"
Write-Host $B64
