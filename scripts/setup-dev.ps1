<#
.SYNOPSIS
  One-click dev setup for WebGuard (Windows).

.DESCRIPTION
  Checks prerequisites, creates the backend virtualenv, installs backend + frontend
  dependencies and creates the .env files from their examples. Safe to re-run: it never
  overwrites an existing .env or recreates an existing virtualenv.

.PARAMETER CheckOnly
  Only verify prerequisites; change nothing.

.PARAMETER Docker
  Skip the local toolchain and start the hot-reload Docker stack instead
  (docker/docker-compose.dev.yml).

.EXAMPLE
  .\scripts\setup-dev.ps1
  .\scripts\setup-dev.ps1 -CheckOnly
  .\scripts\setup-dev.ps1 -Docker
#>
[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$Docker
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [ok]   $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [warn] $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }

# Run a native command and stop the script if it exits non-zero (PowerShell's
# $ErrorActionPreference does not do that for external programs).
function Invoke-Checked {
    param([string]$What, [scriptblock]$Command)
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$What failed (exit code $LASTEXITCODE)" }
}

function Get-VersionOf($exe, $versionArgs) {
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { return $null }
    $out = & $exe @versionArgs 2>&1 | Out-String
    if ($out -match '(\d+)\.(\d+)(?:\.(\d+))?') { return [version]"$($Matches[1]).$($Matches[2])" }
    return $null
}

# ---------------------------------------------------------------- prerequisites
Write-Step "Checking prerequisites"
$failed = $false

$py = $null
foreach ($candidate in @('python', 'py')) {
    $v = Get-VersionOf $candidate @('--version')
    if ($v -and $v -ge [version]'3.12') { $py = $candidate; Write-Ok "Python $v ($candidate)"; break }
}
if (-not $py -and -not $Docker) { Write-Fail "Python 3.12+ not found (https://www.python.org/downloads/)"; $failed = $true }

$node = Get-VersionOf 'node' @('--version')
if ($node -and $node -ge [version]'18.0') { Write-Ok "Node.js $node" }
elseif (-not $Docker) { Write-Fail "Node.js 18+ not found (https://nodejs.org/)"; $failed = $true }

if (Get-VersionOf 'git' @('--version')) { Write-Ok "Git" } else { Write-Warn "Git not found (only needed to contribute)" }

$dockerOk = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    # `docker info` writes to stderr when the daemon is down; with
    # $ErrorActionPreference = 'Stop' that would abort the script, so relax it just here.
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    docker info 2>$null | Out-Null
    $dockerExit = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($dockerExit -eq 0) { $dockerOk = $true; Write-Ok "Docker (daemon running)" }
    else { Write-Warn "Docker installed but the daemon is not running - start Docker Desktop" }
} else { Write-Warn "Docker not found (optional for local dev, required for -Docker)" }
if ($Docker -and -not $dockerOk) { Write-Fail "-Docker needs a running Docker daemon"; $failed = $true }

if ($failed) { throw "Prerequisites missing - fix the items marked FAIL and re-run." }
if ($CheckOnly) { Write-Host "`nAll prerequisites OK." -ForegroundColor Green; return }

# ---------------------------------------------------------------- docker mode
if ($Docker) {
    Write-Step "Starting hot-reload Docker stack"
    Push-Location (Join-Path $Root 'docker')
    try { Invoke-Checked "docker compose up" { docker compose -f docker-compose.dev.yml up -d --build } }
    finally { Pop-Location }
    Write-Host "`nFrontend: http://localhost:5173   API docs: http://localhost:8000/docs" -ForegroundColor Green
    Write-Host "Stop with: docker compose -f docker/docker-compose.dev.yml down"
    return
}

# ---------------------------------------------------------------- env files
Write-Step "Creating .env files (existing ones are kept)"
foreach ($dir in @('backend', 'frontend')) {
    $example = Join-Path $Root "$dir\.env.example"
    $target  = Join-Path $Root "$dir\.env"
    if (-not (Test-Path $example)) { continue }
    if (Test-Path $target) { Write-Ok "$dir\.env already exists - left untouched" }
    else { Copy-Item $example $target; Write-Ok "created $dir\.env" }
}

# ---------------------------------------------------------------- backend
Write-Step "Backend: virtualenv + dependencies"
$backend = Join-Path $Root 'backend'
$venv    = Join-Path $backend '.venv'
if (-not (Test-Path $venv)) {
    Invoke-Checked "venv creation" { & $py -m venv $venv }
    Write-Ok "created backend\.venv"
} else { Write-Ok "backend\.venv already exists" }
$venvPy = Join-Path $venv 'Scripts\python.exe'
Push-Location $backend
try {
    Invoke-Checked "pip upgrade"    { & $venvPy -m pip install --quiet --upgrade pip }
    Invoke-Checked "backend install" { & $venvPy -m pip install --quiet -e ".[dev]" }
} finally { Pop-Location }
Write-Ok "backend dependencies installed"

# ---------------------------------------------------------------- frontend
Write-Step "Frontend: npm ci"
Push-Location (Join-Path $Root 'frontend')
try { Invoke-Checked "npm ci" { npm ci --no-audit --no-fund } } finally { Pop-Location }
Write-Ok "frontend dependencies installed"

# ---------------------------------------------------------------- done
Write-Host "`nSetup complete." -ForegroundColor Green
Write-Host @"

Run the app (two terminals):
  Backend : cd backend; .\.venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --reload
  Frontend: cd frontend; npm run dev

Then open http://localhost:5173  (API docs: http://localhost:8000/docs)
Run the checks CI runs:  cd backend; ruff check app tests; pytest   |   cd frontend; npm run lint; npm test
"@
