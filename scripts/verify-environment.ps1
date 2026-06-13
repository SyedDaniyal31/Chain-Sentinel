#Requires -Version 5.1
<#
.SYNOPSIS
    Verifies ChainSentinel development environment prerequisites.
.DESCRIPTION
    Checks OS, hardware, and all required tools. Never assumes installation.
.EXAMPLE
    .\scripts\verify-environment.ps1
    .\scripts\verify-environment.ps1 -Detailed
#>
param(
    [switch]$Detailed
)

$ErrorActionPreference = "SilentlyContinue"
$script:Results = @()
$script:Pass = 0
$script:Fail = 0
$script:Warn = 0

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Add-Result {
    param(
        [string]$Category,
        [string]$Tool,
        [string]$Status,
        [string]$Version = "",
        [string]$Notes = ""
    )
    $script:Results += [PSCustomObject]@{
        Category = $Category
        Tool     = $Tool
        Status   = $Status
        Version  = $Version
        Notes    = $Notes
    }
    switch ($Status) {
        "PASS" { $script:Pass++ }
        "FAIL" { $script:Fail++ }
        "WARN" { $script:Warn++ }
    }
}

function Get-VersionOutput {
    param([string]$Command)
    try {
        $output = Invoke-Expression $Command 2>&1 | Out-String
        return ($output.Trim() -split "`n")[0]
    } catch {
        return "not found"
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ChainSentinel Environment Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- System ---
Write-Host "[System]" -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$ram = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$gpu = (Get-CimInstance Win32_VideoController | Select-Object -First 1).Name

Add-Result -Category "System" -Tool "OS" -Status "PASS" -Version "$($os.Caption) $($os.Version)" -Notes "Build $($os.BuildNumber)"
Add-Result -Category "System" -Tool "CPU" -Status "PASS" -Version $cpu.Name -Notes "$($cpu.NumberOfCores)C/$($cpu.NumberOfLogicalProcessors)T"
Add-Result -Category "System" -Tool "RAM" -Status $(if ($ram -ge 16) { "PASS" } elseif ($ram -ge 8) { "WARN" } else { "FAIL" }) -Version "${ram} GB" -Notes $(if ($ram -lt 16) { "16 GB recommended for Ollama" } else { "Adequate" })
Add-Result -Category "System" -Tool "GPU" -Status "PASS" -Version $gpu -Notes $(if ($gpu -match "Intel|AMD Radeon Graphics") { "Integrated GPU - use qwen3:4b for Ollama" } else { "Discrete GPU - larger models possible" })

# --- Core tools ---
Write-Host "[Core Tools]" -ForegroundColor Yellow

$tools = @(
    @{ Name = "git";     Cmd = "git --version";     Critical = $true },
    @{ Name = "node";    Cmd = "node --version";    Critical = $true },
    @{ Name = "npm";     Cmd = "npm --version";     Critical = $true },
    @{ Name = "python";  Cmd = "python --version";  Critical = $true },
    @{ Name = "py";      Cmd = "py --version";      Critical = $true },
    @{ Name = "pip";     Cmd = "pip --version";     Critical = $true },
    @{ Name = "docker";  Cmd = "docker --version";  Critical = $true },
    @{ Name = "compose"; Cmd = "docker compose version"; Critical = $true; Alt = "docker-compose" },
    @{ Name = "psql";    Cmd = "psql --version";    Critical = $false; Note = "Optional - use Adminer or Docker exec" },
    @{ Name = "ollama";  Cmd = "ollama --version";  Critical = $true },
    @{ Name = "forge";   Cmd = "forge --version";   Critical = $true },
    @{ Name = "cast";    Cmd = "cast --version";    Critical = $false },
    @{ Name = "anvil";   Cmd = "anvil --version";   Critical = $false },
    @{ Name = "rustc";   Cmd = "rustc --version";   Critical = $false; Note = "Required to build Foundry from source" },
    @{ Name = "winget";  Cmd = "winget --version";  Critical = $false; Note = "Used by setup-windows.ps1" },
    @{ Name = "wsl";     Cmd = "wsl --version";     Critical = $false; Note = "Recommended for Docker + Foundry" }
)

foreach ($t in $tools) {
    $ver = Get-VersionOutput $t.Cmd
    if ($ver -eq "not found" -or $ver -match "not recognized|cannot find") {
        $status = if ($t.Critical) { "FAIL" } else { "WARN" }
        Add-Result -Category "Tools" -Tool $t.Name -Status $status -Notes $(if ($t.Note) { $t.Note } else { "Run setup-windows.ps1" })
    } else {
        Add-Result -Category "Tools" -Tool $t.Name -Status "PASS" -Version $ver
    }
}

# --- Python 3.12 check ---
Write-Host "[Python Versions]" -ForegroundColor Yellow
$py312 = Get-VersionOutput "py -3.12 --version"
if ($py312 -match "3.12") {
    Add-Result -Category "Python" -Tool "Python 3.12" -Status "PASS" -Version $py312 -Notes "Recommended for backend"
} else {
    Add-Result -Category "Python" -Tool "Python 3.12" -Status "WARN" -Notes "Install via: winget install Python.Python.3.12"
}

$pyVer = Get-VersionOutput "python --version"
if ($pyVer -match "3.14") {
    Add-Result -Category "Python" -Tool "Default Python" -Status "WARN" -Version $pyVer -Notes "3.14 is bleeding-edge - use 3.12 venv for backend"
}

# --- Node version check ---
Write-Host "[Compatibility]" -ForegroundColor Yellow
$nodeVer = Get-VersionOutput "node --version"
if ($nodeVer -match "v(1[89]|2[0-9]|3[0-9])") {
    Add-Result -Category "Compat" -Tool "Node.js for Next.js 15" -Status "PASS" -Version $nodeVer -Notes "Requires >= 18.18.0"
} elseif ($nodeVer -match "v\d") {
    Add-Result -Category "Compat" -Tool "Node.js for Next.js 15" -Status "FAIL" -Version $nodeVer -Notes "Upgrade to Node 20 or 22 LTS"
}

# --- Ollama models ---
Write-Host "[Ollama Models]" -ForegroundColor Yellow
if (Test-CommandExists "ollama") {
    $models = ollama list 2>&1 | Out-String
    if ($models -match "qwen3") {
        Add-Result -Category "AI" -Tool "Qwen 3 model" -Status "PASS" -Notes "Found in ollama list"
    } else {
        Add-Result -Category "AI" -Tool "Qwen 3 model" -Status "WARN" -Notes "Run: ollama pull qwen3:4b"
    }
}

# --- Docker running ---
Write-Host "[Docker Status]" -ForegroundColor Yellow
if (Test-CommandExists "docker") {
    $dockerInfo = docker info 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        Add-Result -Category "Docker" -Tool "Docker daemon" -Status "PASS" -Notes "Running"
    } else {
        Add-Result -Category "Docker" -Tool "Docker daemon" -Status "FAIL" -Notes "Start Docker Desktop"
    }
}

# --- Project structure ---
Write-Host "[Project Structure]" -ForegroundColor Yellow
$requiredDirs = @("frontend", "backend", "contracts", "docker", "docs", "scripts", "database", ".github")
$root = Split-Path $PSScriptRoot -Parent
foreach ($dir in $requiredDirs) {
    $path = Join-Path $root $dir
    if (Test-Path $path) {
        Add-Result -Category "Project" -Tool "dir/$dir" -Status "PASS"
    } else {
        Add-Result -Category "Project" -Tool "dir/$dir" -Status "FAIL" -Notes "Missing directory"
    }
}

# --- Ollama recommendation ---
Write-Host ""
Write-Host "[Ollama Model Recommendation]" -ForegroundColor Magenta
if ($ram -le 16) {
    Write-Host "  Primary:  qwen3:4b  (fits 16 GB RAM + Docker + IDE)" -ForegroundColor Green
    Write-Host "  Optional: qwen3:8b  (close other apps first)" -ForegroundColor Yellow
    Write-Host "  Avoid:    qwen3:14b+ (insufficient RAM)" -ForegroundColor Red
}

# --- Output table ---
Write-Host ""
Write-Host "Results:" -ForegroundColor Cyan
$script:Results | Format-Table -AutoSize Category, Tool, Status, Version, Notes

Write-Host "Summary: PASS=$script:Pass  WARN=$script:Warn  FAIL=$script:Fail" -ForegroundColor $(if ($script:Fail -eq 0) { "Green" } else { "Red" })

if ($script:Fail -gt 0) {
    Write-Host ""
    Write-Host "Action required: Run as Administrator:" -ForegroundColor Yellow
    Write-Host "  .\scripts\setup-windows.ps1" -ForegroundColor White
    exit 1
} elseif ($script:Warn -gt 0) {
    Write-Host ""
    Write-Host "Warnings present - review notes above. Development may proceed with limitations." -ForegroundColor Yellow
    exit 0
} else {
    Write-Host ""
    Write-Host "Environment ready for ChainSentinel development." -ForegroundColor Green
    exit 0
}
