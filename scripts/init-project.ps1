#Requires -Version 5.1
<#
.SYNOPSIS
    Initializes ChainSentinel project scaffolds (frontend, backend, contracts, env).
.DESCRIPTION
    Run AFTER verify-environment.ps1 passes (or with known warnings).
    Does NOT start long-running services.
.PARAMETER SkipFrontend
    Skip Next.js create-next-app (if already initialized)
.PARAMETER SkipBackend
    Skip Python venv setup
.PARAMETER SkipContracts
    Skip Hardhat/Foundry init
.PARAMETER SkipDocker
    Skip docker compose up
.EXAMPLE
    .\scripts\init-project.ps1
    .\scripts\init-project.ps1 -SkipFrontend
#>
param(
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$SkipContracts,
    [switch]$SkipDocker,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

function Write-Step { param([string]$Msg) Write-Host "`n>> $Msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Msg) Write-Host "   OK: $Msg" -ForegroundColor Green }

Set-Location $Root

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ChainSentinel Project Initialization" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- Environment files ---
Write-Step "Copying environment templates..."
if (-not (Test-Path ".env") -or $Force) {
    Copy-Item ".env.example" ".env" -Force
    Write-Ok ".env created from .env.example"
}
if (Test-Path "backend\.env.example") {
    if (-not (Test-Path "backend\.env") -or $Force) {
        Copy-Item "backend\.env.example" "backend\.env" -Force
        Write-Ok "backend/.env created"
    }
}
if (Test-Path "frontend\.env.local.example") {
    if (-not (Test-Path "frontend\.env.local") -or $Force) {
        Copy-Item "frontend\.env.local.example" "frontend\.env.local" -Force
        Write-Ok "frontend/.env.local created"
    }
}

# --- Git ---
Write-Step "Initializing Git repository..."
if (-not (Test-Path ".git")) {
    git init
    git branch -M main
    Write-Ok "Git repository initialized (branch: main)"
} else {
    Write-Host "   Git already initialized" -ForegroundColor Yellow
}

# --- Frontend ---
if (-not $SkipFrontend) {
    Write-Step "Initializing Next.js 15 frontend..."
    $frontendMarker = Join-Path $Root "frontend\package.json"
    if ((Test-Path $frontendMarker) -and -not $Force) {
        Write-Host "   frontend/package.json exists — skipping (use -Force to re-init)" -ForegroundColor Yellow
    } else {
        Set-Location (Join-Path $Root "frontend")
        npx create-next-app@15 . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes
        npx shadcn@latest init --defaults --yes
        npm install ethers
        Set-Location $Root
        Write-Ok "Frontend initialized (Next.js 15 + ShadCN + ethers)"
    }
}

# --- Backend ---
if (-not $SkipBackend) {
    Write-Step "Initializing Python backend..."
    Set-Location (Join-Path $Root "backend")

    $pythonCmd = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $py312 = py -3.12 --version 2>&1
        if ($py312 -match "3.12") { $pythonCmd = "py -3.12" }
    }
    if (-not $pythonCmd) {
        $pythonCmd = "python"
        Write-Host "   WARN: Python 3.12 not found — using default python" -ForegroundColor Yellow
    }

    if (-not (Test-Path ".venv") -or $Force) {
        Invoke-Expression "$pythonCmd -m venv .venv"
        Write-Ok "Virtual environment created"
    }

    & ".\.venv\Scripts\Activate.ps1"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if (Test-Path "requirements-dev.txt") {
        pip install -r requirements-dev.txt
    }
    Set-Location $Root
    Write-Ok "Backend dependencies installed in .venv"
}

# --- Contracts ---
if (-not $SkipContracts) {
    Write-Step "Initializing smart contract toolchains..."
    Set-Location (Join-Path $Root "contracts")

    if (-not (Test-Path "package.json") -or $Force) {
        npm init -y
        npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
        npm install ethers
        npx hardhat init --yes 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "   Run manually: cd contracts && npx hardhat init" -ForegroundColor Yellow
        }
    }

    if (-not (Test-Path "foundry.toml") -or $Force) {
        if (Get-Command forge -ErrorAction SilentlyContinue) {
            forge init foundry --force --no-commit 2>$null
            Write-Ok "Foundry initialized in contracts/foundry/"
        } else {
            Write-Host "   WARN: forge not found — install Foundry first" -ForegroundColor Yellow
        }
    }

    Set-Location $Root
    Write-Ok "Contracts toolchain configured"
}

# --- Docker ---
if (-not $SkipDocker) {
    Write-Step "Starting Docker infrastructure..."
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
        Start-Sleep -Seconds 5
        docker compose -f docker/docker-compose.yml ps
        Write-Ok "Docker services started"
    } else {
        Write-Host "   WARN: Docker not installed — start manually after setup" -ForegroundColor Yellow
    }
}

# --- Ollama model ---
Write-Step "Checking Ollama Qwen 3 model..."
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    $models = ollama list 2>&1 | Out-String
    if ($models -notmatch "qwen3") {
        Write-Host "   Pulling qwen3:4b (recommended for 16 GB RAM)..." -ForegroundColor Yellow
        ollama pull qwen3:4b
    }
    Write-Ok "Ollama model ready"
} else {
    Write-Host "   WARN: Ollama not installed" -ForegroundColor Yellow
}

Set-Location $Root

Write-Host ""
Write-Host "Initialization complete." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. .\scripts\verify-environment.ps1" -ForegroundColor White
Write-Host "  2. Follow docs/12-30-day-roadmap.md — Day 1" -ForegroundColor White
Write-Host "  3. git add . && git commit -m 'chore: initialize ChainSentinel dev environment'" -ForegroundColor White
