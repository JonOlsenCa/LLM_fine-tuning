# V4 Training Data Generation Pipeline
# Run this script from the project root directory
#
# Usage:
#   .\scripts\vgpt2_v4\run_v4_pipeline.ps1
#   .\scripts\vgpt2_v4\run_v4_pipeline.ps1 -VgptPath "D:\Github\VGPT2"

param(
    [string]$VgptPath = "C:\Github\VGPT2",
    [string]$OutputPath = "data\vgpt2_v4_sft.json",
    [switch]$Verbose,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "VGPT2 V4 Training Data Generation Pipeline" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Check Python environment
Write-Host "Checking Python environment..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "  Activating virtual environment..." -ForegroundColor Gray
    & .venv\Scripts\Activate.ps1
}

# Check VGPT2 path
if (-not (Test-Path $VgptPath)) {
    Write-Host "ERROR: VGPT2 path not found: $VgptPath" -ForegroundColor Red
    Write-Host "Please specify -VgptPath parameter or ensure VGPT2 repository is available" -ForegroundColor Red
    exit 1
}

$MetadataPath = Join-Path $VgptPath "Viewpoint_Database\_Metadata"
if (-not (Test-Path $MetadataPath)) {
    Write-Host "ERROR: Metadata directory not found: $MetadataPath" -ForegroundColor Red
    exit 1
}

Write-Host "  VGPT2 Path: $VgptPath" -ForegroundColor Green
Write-Host "  Output Path: $OutputPath" -ForegroundColor Green
Write-Host ""

# Build command
$PythonArgs = @(
    "scripts\vgpt2_v4\run_pipeline.py",
    "--vgpt2-path", $VgptPath,
    "--output", $OutputPath
)

if ($Verbose) {
    $PythonArgs += "--verbose"
}

if ($DryRun) {
    $PythonArgs += "--dry-run"
    Write-Host "DRY RUN MODE - No files will be saved" -ForegroundColor Yellow
    Write-Host ""
}

# Run pipeline
Write-Host "Running V4 pipeline..." -ForegroundColor Yellow
Write-Host ""

python $PythonArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host "SUCCESS! V4 training data generated." -ForegroundColor Green
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host ""
    
    if (-not $DryRun) {
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Review generated data: $OutputPath" -ForegroundColor White
        Write-Host "  2. Train SFT model:" -ForegroundColor White
        Write-Host "     llamafactory-cli train examples\train_lora\vgpt2_v4_sft.yaml" -ForegroundColor Gray
        Write-Host "  3. Evaluate the model:" -ForegroundColor White
        Write-Host "     python scripts\vgpt2_v4\evaluate.py --model saves\vgpt2_v4\sft" -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Red
    Write-Host "FAILED! Check error messages above." -ForegroundColor Red
    Write-Host "=" * 60 -ForegroundColor Red
    exit 1
}
