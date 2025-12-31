# ============================================================
# STEP 3: Start SFT Training (Stage 1)
# ============================================================
# Supervised Fine-Tuning on 70,006 examples
# Expected time: 8-12 hours on RTX A6000
#
# Config: automation/configs/vgpt2_v3/stage1_sft.yaml
# Output: saves/vgpt2_v3/sft/
# ============================================================

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "STAGE 1: SUPERVISED FINE-TUNING (SFT)" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

Write-Host "`n[TRAINING CONFIGURATION]" -ForegroundColor Yellow
Write-Host "  Model:        Qwen/Qwen2.5-7B-Instruct"
Write-Host "  Dataset:      vgpt2_v3_sft_merged (70,006 examples)"
Write-Host "  LoRA Rank:    256"
Write-Host "  Context:      8192 tokens"
Write-Host "  Epochs:       3"
Write-Host "  Batch Size:   2 (effective: 16 with grad accum)"
Write-Host "  Checkpoints:  Every 250 steps (~52 total)"
Write-Host "  Output:       saves/vgpt2_v3/sft/"

Write-Host "`n[PRE-FLIGHT CHECK]" -ForegroundColor Yellow

# Check GPU
Write-Host "  Checking GPU..." -NoNewline
$gpu = nvidia-smi --query-gpu=name,memory.free --format=csv,noheader 2>$null
if ($gpu) {
    Write-Host " OK ($gpu)" -ForegroundColor Green
} else {
    Write-Host " FAILED - No GPU detected!" -ForegroundColor Red
    exit 1
}

# Check dataset
Write-Host "  Checking dataset..." -NoNewline
if (Test-Path "data/vgpt2_v3_sft_merged.json") {
    $size = [math]::Round((Get-Item "data/vgpt2_v3_sft_merged.json").Length/1MB, 1)
    Write-Host " OK (${size} MB)" -ForegroundColor Green
} else {
    Write-Host " FAILED - Dataset not found!" -ForegroundColor Red
    exit 1
}

# Check config
Write-Host "  Checking config..." -NoNewline
if (Test-Path "automation/configs/vgpt2_v3/stage1_sft.yaml") {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED - Config not found!" -ForegroundColor Red
    exit 1
}

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "Starting training in 5 seconds... (Ctrl+C to cancel)" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Activate venv and start training
.\venv\Scripts\activate.ps1

$startTime = Get-Date
Write-Host "`nTraining started at: $startTime" -ForegroundColor Green
Write-Host "Monitor progress in a separate terminal with: .\training\run\02_start_monitor.ps1`n"

llamafactory-cli train automation/configs/vgpt2_v3/stage1_sft.yaml

$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "TRAINING COMPLETE" -ForegroundColor Green
Write-Host "Started:  $startTime"
Write-Host "Ended:    $endTime"
Write-Host "Duration: $($duration.Hours)h $($duration.Minutes)m $($duration.Seconds)s"
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "`nNext: Run 04_train_dpo.ps1 for preference training"

