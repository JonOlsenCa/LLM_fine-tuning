# LLaMA Factory - Hyperparameter Sweep Script
# Generates configs and runs all combinations
# Usage: .\parameter_sweep.ps1 -Model "llama3-8b" -Dataset "alpaca_en_demo"

param(
    [Parameter(Mandatory=$true)]
    [string]$Model,
    
    [Parameter(Mandatory=$true)]
    [string]$Dataset,
    
    [Parameter(Mandatory=$false)]
    [string]$LearningRates = "1e-4,5e-5,1e-5",
    
    [Parameter(Mandatory=$false)]
    [string]$LoraRanks = "8,16",
    
    [Parameter(Mandatory=$false)]
    [string]$BatchSizes = "1,2",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputBase = "saves/sweep",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$Parallel,
    
    [Parameter(Mandatory=$false)]
    [int]$MaxJobs = 1
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item $ScriptDir).Parent.Parent.FullName
$AutomationDir = (Get-Item $ScriptDir).Parent.FullName

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LLaMA Factory Parameter Sweep" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Model: $Model" -ForegroundColor Yellow
Write-Host "Dataset: $Dataset" -ForegroundColor Yellow
Write-Host "Learning Rates: $LearningRates" -ForegroundColor Yellow
Write-Host "LoRA Ranks: $LoraRanks" -ForegroundColor Yellow
Write-Host "Batch Sizes: $BatchSizes" -ForegroundColor Yellow
Write-Host ""

# Generate timestamp for this sweep
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$SweepDir = Join-Path $AutomationDir "configs/sweep_$Timestamp"

# Create sweep directory
New-Item -ItemType Directory -Path $SweepDir -Force | Out-Null

Push-Location $ProjectRoot

try {
    # Activate venv
    $VenvPath = Join-Path $ProjectRoot "venv\Scripts\activate.ps1"
    if (Test-Path $VenvPath) {
        & $VenvPath
    }
    
    # Generate configs using Python
    Write-Host "Generating sweep configurations..." -ForegroundColor Green
    
    $PythonCode = @"
import sys
sys.path.insert(0, '$($AutomationDir -replace '\\', '/')')
from config_generator_extras import ParameterSweep

sweep = ParameterSweep(
    base_model='$Model',
    dataset='$Dataset',
    output_base='$($OutputBase -replace '\\', '/')',
)

learning_rates = [float(x) for x in '$LearningRates'.split(',')]
lora_ranks = [int(x) for x in '$LoraRanks'.split(',')]
batch_sizes = [int(x) for x in '$BatchSizes'.split(',')]

for name, config in sweep.generate_sweep(
    learning_rates=learning_rates,
    lora_ranks=lora_ranks,
    batch_sizes=batch_sizes,
):
    path = config.save('$($SweepDir -replace '\\', '/')/' + name + '.yaml')
    print(f'Generated: {path}')
"@
    
    python -c $PythonCode
    
    Write-Host ""
    Write-Host "Configs saved to: $SweepDir" -ForegroundColor Green
    Write-Host ""
    
    # Run batch training
    $BatchScript = Join-Path $ScriptDir "train_batch.ps1"
    $BatchArgs = @{
        ConfigDir = $SweepDir
        DryRun = $DryRun
    }
    
    if ($Parallel) {
        $BatchArgs.Parallel = $true
        $BatchArgs.MaxJobs = $MaxJobs
    }
    
    & $BatchScript @BatchArgs
    
} finally {
    Pop-Location
}

