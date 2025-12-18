# LLaMA Factory - Single Training Job Script
# Usage: .\train_single.ps1 -ConfigPath "path/to/config.yaml"

param(
    [Parameter(Mandatory=$true)]
    [string]$ConfigPath,
    
    [Parameter(Mandatory=$false)]
    [string]$PythonEnv = ".\venv\Scripts\activate.ps1",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Get the project root directory (parent of automation folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item $ScriptDir).Parent.Parent.FullName

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LLaMA Factory Training Job" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Validate config file exists
if (-not (Test-Path $ConfigPath)) {
    Write-Host "ERROR: Config file not found: $ConfigPath" -ForegroundColor Red
    exit 1
}

Write-Host "Config File: $ConfigPath" -ForegroundColor Yellow
Write-Host "Project Root: $ProjectRoot" -ForegroundColor Yellow
Write-Host ""

# Change to project directory
Push-Location $ProjectRoot

try {
    # Activate virtual environment if it exists
    $VenvPath = Join-Path $ProjectRoot $PythonEnv
    if (Test-Path $VenvPath) {
        Write-Host "Activating virtual environment..." -ForegroundColor Green
        & $VenvPath
    }
    
    # Build the training command
    $TrainCmd = "python -m llamafactory.cli train `"$ConfigPath`""
    
    Write-Host "Command: $TrainCmd" -ForegroundColor Magenta
    Write-Host ""
    
    if ($DryRun) {
        Write-Host "[DRY RUN] Would execute the above command" -ForegroundColor Yellow
    } else {
        Write-Host "Starting training..." -ForegroundColor Green
        Write-Host "----------------------------------------" -ForegroundColor Gray
        
        $StartTime = Get-Date
        
        # Execute training
        Invoke-Expression $TrainCmd
        
        $EndTime = Get-Date
        $Duration = $EndTime - $StartTime
        
        Write-Host "----------------------------------------" -ForegroundColor Gray
        Write-Host "Training completed!" -ForegroundColor Green
        Write-Host "Duration: $($Duration.ToString('hh\:mm\:ss'))" -ForegroundColor Cyan
    }
} finally {
    Pop-Location
}

