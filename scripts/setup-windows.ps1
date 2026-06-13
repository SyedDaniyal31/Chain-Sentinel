#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Installs missing ChainSentinel development tools on Windows.
.DESCRIPTION
    Uses winget for package installs. Run AFTER reading docs/09-local-development-setup.md
.EXAMPLE
    # Run PowerShell as Administrator
    .\scripts\setup-windows.ps1
    .\scripts\setup-windows.ps1 -SkipDocker
#>
param(
    [switch]$SkipDocker,
    [switch]$SkipWsl,
    [switch]$SkipOllama,
    [switch]$SkipFoundry
)

$ErrorActionPreference = "Stop"

function Write-Step { param([string]$Msg) Write-Host "`n>> $Msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Msg) Write-Host "   OK: $Msg" -ForegroundColor Green }
function Write-Skip { param([string]$Msg) Write-Host "   SKIP: $Msg" -ForegroundColor Yellow }

function Test-Cmd {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-Winget {
    param([string]$Id, [string]$Label)
    if (Test-Cmd $Label.Split(" ")[0].ToLower()) {
        Write-Skip "$Label already installed"
        return
    }
    Write-Step "Installing $Label..."
    winget install --id $Id -e --accept-source-agreements --accept-package-agreements --disable-interactivity
    Write-Ok "$Label install command completed — verify in new terminal"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ChainSentinel Windows Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- Git ---
if (-not (Test-Cmd "git")) {
    Install-Winget -Id "Git.Git" -Label "Git"
} else { Write-Skip "Git already installed" }

# --- Node.js 22 LTS ---
$nodeVer = (node --version 2>$null)
if (-not $nodeVer -or $nodeVer -notmatch "v2[02]") {
    Write-Step "Installing Node.js 22 LTS (recommended for Next.js 15)..."
    winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements --disable-interactivity
    Write-Ok "Node.js LTS — restart terminal and verify: node --version"
} else {
    Write-Skip "Node.js already installed: $nodeVer"
}

# --- Python 3.12 (backend) ---
$py312 = (py -3.12 --version 2>$null)
if (-not $py312) {
    Install-Winget -Id "Python.Python.3.12" -Label "Python 3.12"
} else {
    Write-Skip "Python 3.12 already installed: $py312"
}

# --- Docker Desktop ---
if (-not $SkipDocker) {
    if (-not (Test-Cmd "docker")) {
        Install-Winget -Id "Docker.DockerDesktop" -Label "Docker Desktop"
        Write-Host "`n   IMPORTANT: Reboot after Docker Desktop install." -ForegroundColor Yellow
        Write-Host "   Then start Docker Desktop and run: docker run hello-world" -ForegroundColor Yellow
    } else {
        Write-Skip "Docker already installed"
    }
} else {
    Write-Skip "Docker install skipped (-SkipDocker)"
}

# --- WSL 2 ---
if (-not $SkipWsl) {
    $wslStatus = wsl --status 2>&1 | Out-String
    if ($wslStatus -match "not installed|requires") {
        Write-Step "Installing WSL 2 with Ubuntu 22.04..."
        wsl --install -d Ubuntu-22.04 --no-launch
        Write-Host "   IMPORTANT: Reboot required after WSL install." -ForegroundColor Yellow
    } else {
        Write-Skip "WSL already configured"
    }
} else {
    Write-Skip "WSL install skipped (-SkipWsl)"
}

# --- Ollama ---
if (-not $SkipOllama) {
    if (-not (Test-Cmd "ollama")) {
        Install-Winget -Id "Ollama.Ollama" -Label "Ollama"
        Write-Host "`n   After install, pull models:" -ForegroundColor Yellow
        Write-Host "     ollama pull qwen3:4b" -ForegroundColor White
        Write-Host "     ollama pull qwen3:8b   # optional" -ForegroundColor White
    } else {
        Write-Skip "Ollama already installed"
        if (-not (ollama list 2>$null | Select-String "qwen3")) {
            Write-Step "Pulling qwen3:4b model..."
            ollama pull qwen3:4b
        }
    }
} else {
    Write-Skip "Ollama install skipped (-SkipOllama)"
}

# --- Foundry ---
if (-not $SkipFoundry) {
    if (-not (Test-Cmd "forge")) {
        Write-Step "Installing Foundry via foundryup..."
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
        irm https://getfoundry.sh | iex
        foundryup
        Write-Ok "Foundry — restart terminal and verify: forge --version"
    } else {
        Write-Skip "Foundry already installed"
    }
} else {
    Write-Skip "Foundry install skipped (-SkipFoundry)"
}

# --- MetaMask note ---
Write-Host ""
Write-Host "Manual step: Install MetaMask browser extension" -ForegroundColor Magenta
Write-Host "  https://metamask.io/download/" -ForegroundColor White
Write-Host "  Use a dedicated dev wallet — never mainnet funds on local keys." -ForegroundColor Yellow

# --- Final verification ---
Write-Host ""
Write-Step "Running verification script..."
$verifyScript = Join-Path $PSScriptRoot "verify-environment.ps1"
if (Test-Path $verifyScript) {
    & $verifyScript
}

Write-Host ""
Write-Host "Setup complete. If Docker or WSL were installed, REBOOT before continuing." -ForegroundColor Cyan
