# VGPT2 v3 Training Pipeline Orchestration
# ==========================================
# Complete training pipeline from data generation to validation
#
# Usage:
#   .\scripts\vgpt2_v3\run_pipeline.ps1                    # Full pipeline
#   .\scripts\vgpt2_v3\run_pipeline.ps1 -Stage data        # Data generation only
#   .\scripts\vgpt2_v3\run_pipeline.ps1 -Stage sft         # SFT training only
#   .\scripts\vgpt2_v3\run_pipeline.ps1 -Stage dpo         # DPO training only
#   .\scripts\vgpt2_v3\run_pipeline.ps1 -Stage validate    # Validation only
#   .\scripts\vgpt2_v3\run_pipeline.ps1 -Resume            # Resume from last checkpoint

param(
    [Parameter()]
    [ValidateSet("all", "data", "sft", "dpo", "kto", "validate")]
    [string]$Stage = "all",

    [Parameter()]
    [switch]$Resume,

    [Parameter()]
    [switch]$Quick,

    [Parameter()]
    [string]$VGPT2Path = "C:\Github\VGPT2"
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Step { param($msg) Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host $msg -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host $msg -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host $msg -ForegroundColor Red }

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

Write-Host @"

╔══════════════════════════════════════════════════════════════╗
║           VGPT2 v3 Training Pipeline                         ║
║           Production-Grade Viewpoint SQL Expert              ║
╚══════════════════════════════════════════════════════════════╝

Repository: $RepoRoot
VGPT2 Path: $VGPT2Path
Stage: $Stage
Resume: $Resume

"@ -ForegroundColor White

# Activate virtual environment
$VenvPath = Join-Path $RepoRoot "venv\Scripts\Activate.ps1"
if (Test-Path $VenvPath) {
    Write-Step "Activating virtual environment"
    . $VenvPath
    Write-Success "Virtual environment activated"
} else {
    Write-Warn "Virtual environment not found at $VenvPath"
}

# ============================================================================
# STAGE: Data Generation
# ============================================================================
function Invoke-DataGeneration {
    Write-Step "Stage: Data Generation"

    $DataDir = Join-Path $RepoRoot "data"
    if (-not (Test-Path $DataDir)) {
        New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    }

    # Generate SFT data
    Write-Host "Generating SFT training data..." -ForegroundColor Yellow
    $SftOutput = Join-Path $DataDir "vgpt2_v3_sft.json"
    python "$ScriptDir\generate_training_data.py" --vgpt2 $VGPT2Path --output $SftOutput
    if ($LASTEXITCODE -ne 0) { throw "SFT data generation failed" }
    Write-Success "Generated SFT data: $SftOutput"

    # Generate negative examples
    Write-Host "Generating negative examples..." -ForegroundColor Yellow
    $NegOutput = Join-Path $DataDir "vgpt2_v3_negatives.json"
    python "$ScriptDir\generate_negative_examples.py" --vgpt2 $VGPT2Path --output $NegOutput
    if ($LASTEXITCODE -ne 0) { throw "Negative example generation failed" }
    Write-Success "Generated negative examples: $NegOutput"

    # Generate KTO data
    Write-Host "Generating KTO binary feedback data..." -ForegroundColor Yellow
    $KtoOutput = Join-Path $DataDir "vgpt2_v3_kto.json"
    python "$ScriptDir\generate_kto_data.py" --vgpt2 $VGPT2Path --output $KtoOutput
    if ($LASTEXITCODE -ne 0) { throw "KTO data generation failed" }
    Write-Success "Generated KTO data: $KtoOutput"

    # Generate DPO pairs
    Write-Host "Generating DPO preference pairs..." -ForegroundColor Yellow
    $DpoOutput = Join-Path $DataDir "vgpt2_v3_dpo.json"
    python "$ScriptDir\generate_dpo_pairs.py" --vgpt2 $VGPT2Path --output $DpoOutput
    if ($LASTEXITCODE -ne 0) { throw "DPO pair generation failed" }
    Write-Success "Generated DPO pairs: $DpoOutput"

    # Merge SFT and negative examples
    Write-Host "Merging SFT data with negative examples..." -ForegroundColor Yellow
    $MergedOutput = Join-Path $DataDir "vgpt2_v3_sft_merged.json"
    python -c @"
import json
with open('$($SftOutput -replace '\\', '/')', 'r', encoding='utf-8') as f:
    sft = json.load(f)
with open('$($NegOutput -replace '\\', '/')', 'r', encoding='utf-8') as f:
    neg = json.load(f)
merged = sft + neg
with open('$($MergedOutput -replace '\\', '/')', 'w', encoding='utf-8') as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
print(f'Merged {len(sft)} SFT + {len(neg)} negative = {len(merged)} total')
"@
    Write-Success "Merged data saved: $MergedOutput"

    # Run data validation
    Write-Host "Validating generated data..." -ForegroundColor Yellow
    python "$ScriptDir\validate_data.py"
    if ($LASTEXITCODE -ne 0) { throw "Data validation failed" }

    Write-Success "Data generation complete!"
}

# ============================================================================
# STAGE: SFT Training
# ============================================================================
function Invoke-SFTTraining {
    Write-Step "Stage: SFT Training"

    $ConfigPath = Join-Path $RepoRoot "automation\configs\vgpt2_v3\stage1_sft.yaml"

    if ($Resume) {
        Write-Host "Resuming from checkpoint..." -ForegroundColor Yellow
        # Modify config to enable resume
        $Config = Get-Content $ConfigPath -Raw
        $Config = $Config -replace "resume_from_checkpoint: false", "resume_from_checkpoint: true"
        $Config | Set-Content $ConfigPath
    }

    Write-Host "Starting SFT training..." -ForegroundColor Yellow
    Write-Warn "This will take 8-12 hours. Monitor with: nvidia-smi -l 5"

    # Use external terminal to avoid VS Code Ctrl+C issues
    $ExternalScript = Join-Path $RepoRoot "scripts\run_external.ps1"
    if (Test-Path $ExternalScript) {
        & $ExternalScript -Command "llamafactory-cli train $ConfigPath"
    } else {
        llamafactory-cli train $ConfigPath
    }

    if ($LASTEXITCODE -ne 0) { throw "SFT training failed" }
    Write-Success "SFT training complete!"
}

# ============================================================================
# STAGE: DPO Training
# ============================================================================
function Invoke-DPOTraining {
    Write-Step "Stage: DPO Training"

    $ConfigPath = Join-Path $RepoRoot "automation\configs\vgpt2_v3\stage2_dpo.yaml"

    Write-Host "Starting DPO training..." -ForegroundColor Yellow
    Write-Warn "This will take 4-6 hours."

    $ExternalScript = Join-Path $RepoRoot "scripts\run_external.ps1"
    if (Test-Path $ExternalScript) {
        & $ExternalScript -Command "llamafactory-cli train $ConfigPath"
    } else {
        llamafactory-cli train $ConfigPath
    }

    if ($LASTEXITCODE -ne 0) { throw "DPO training failed" }
    Write-Success "DPO training complete!"
}

# ============================================================================
# STAGE: KTO Training
# ============================================================================
function Invoke-KTOTraining {
    Write-Step "Stage: KTO Training"

    $ConfigPath = Join-Path $RepoRoot "automation\configs\vgpt2_v3\stage3_kto.yaml"

    Write-Host "Starting KTO training..." -ForegroundColor Yellow
    Write-Warn "This will take 2-4 hours."

    $ExternalScript = Join-Path $RepoRoot "scripts\run_external.ps1"
    if (Test-Path $ExternalScript) {
        & $ExternalScript -Command "llamafactory-cli train $ConfigPath"
    } else {
        llamafactory-cli train $ConfigPath
    }

    if ($LASTEXITCODE -ne 0) { throw "KTO training failed" }
    Write-Success "KTO training complete!"
}

# ============================================================================
# STAGE: Validation
# ============================================================================
function Invoke-Validation {
    Write-Step "Stage: Validation"

    $ModelPath = Join-Path $RepoRoot "saves\vgpt2_v3\final"
    $OutputPath = Join-Path $RepoRoot "output\validation_report.json"

    # Check if model exists
    if (-not (Test-Path $ModelPath)) {
        Write-Warn "Final model not found at $ModelPath"
        # Try SFT model
        $ModelPath = Join-Path $RepoRoot "saves\vgpt2_v3\sft"
        if (-not (Test-Path $ModelPath)) {
            throw "No trained model found. Run training first."
        }
        Write-Warn "Using SFT model for validation: $ModelPath"
    }

    $ValidateArgs = @("$ScriptDir\run_validation.py", "--model", $ModelPath, "--output", $OutputPath)
    if ($Quick) {
        $ValidateArgs += "--quick"
    }

    Write-Host "Running validation suite..." -ForegroundColor Yellow
    python @ValidateArgs

    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Validation completed with warnings"
    } else {
        Write-Success "Validation passed!"
    }

    Write-Host "`nValidation report: $OutputPath" -ForegroundColor Cyan
}

# ============================================================================
# Main Pipeline Execution
# ============================================================================
try {
    $StartTime = Get-Date

    switch ($Stage) {
        "all" {
            Invoke-DataGeneration
            Invoke-SFTTraining
            Invoke-DPOTraining
            Invoke-KTOTraining
            Invoke-Validation
        }
        "data" { Invoke-DataGeneration }
        "sft" { Invoke-SFTTraining }
        "dpo" { Invoke-DPOTraining }
        "kto" { Invoke-KTOTraining }
        "validate" { Invoke-Validation }
    }

    $Duration = (Get-Date) - $StartTime
    Write-Host @"

╔══════════════════════════════════════════════════════════════╗
║                    Pipeline Complete!                         ║
╚══════════════════════════════════════════════════════════════╝

Duration: $($Duration.ToString("hh\:mm\:ss"))
Stage: $Stage

Next steps:
  1. Review validation report in output/validation_report.json
  2. Test interactively:
     llamafactory-cli chat --model_name_or_path Qwen/Qwen2.5-7B-Instruct \
       --adapter_name_or_path saves/vgpt2_v3/final --template qwen

"@ -ForegroundColor Green

} catch {
    Write-Err "Pipeline failed: $_"
    exit 1
}
