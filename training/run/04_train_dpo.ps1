# ============================================================
# STEP 4: Start DPO Training (Stage 2)
# ============================================================
# Direct Preference Optimization on preference pairs
# Run AFTER SFT training completes
#
# Config: automation/configs/vgpt2_v3/stage2_dpo.yaml
# Input:  saves/vgpt2_v3/sft/ (from Stage 1)
# Output: saves/vgpt2_v3/dpo/
# ============================================================

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "STAGE 2: DIRECT PREFERENCE OPTIMIZATION (DPO)" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

Write-Host "`n[PRE-FLIGHT CHECK]" -ForegroundColor Yellow

# Check SFT output exists
Write-Host "  Checking SFT checkpoint..." -NoNewline
if (Test-Path "saves/vgpt2_v3/sft/adapter_model.safetensors") {
    Write-Host " OK" -ForegroundColor Green
} elseif (Test-Path "saves/vgpt2_v3/sft") {
    $checkpoints = Get-ChildItem -Path "saves/vgpt2_v3/sft" -Directory -Filter "checkpoint-*" | Sort-Object Name -Descending | Select-Object -First 1
    if ($checkpoints) {
        Write-Host " OK (using $($checkpoints.Name))" -ForegroundColor Green
    } else {
        Write-Host " WARNING - No final model, using latest checkpoint" -ForegroundColor Yellow
    }
} else {
    Write-Host " FAILED - Run Stage 1 (SFT) first!" -ForegroundColor Red
    exit 1
}

# Check DPO dataset
Write-Host "  Checking DPO dataset..." -NoNewline
if (Test-Path "data/vgpt2_v3_dpo.json") {
    $size = [math]::Round((Get-Item "data/vgpt2_v3_dpo.json").Length/1MB, 1)
    Write-Host " OK (${size} MB)" -ForegroundColor Green
} else {
    Write-Host " FAILED - DPO dataset not found!" -ForegroundColor Red
    Write-Host "  Generate with: python scripts/vgpt2_v3/generate_dpo_pairs.py" -ForegroundColor Yellow
    exit 1
}

# Check config
Write-Host "  Checking config..." -NoNewline
if (Test-Path "automation/configs/vgpt2_v3/stage2_dpo.yaml") {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED - Config not found!" -ForegroundColor Red
    exit 1
}

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "Starting DPO training in 5 seconds... (Ctrl+C to cancel)" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Cyan
Start-Sleep -Seconds 5

.\venv\Scripts\activate.ps1

$startTime = Get-Date
Write-Host "`nTraining started at: $startTime" -ForegroundColor Green

llamafactory-cli train automation/configs/vgpt2_v3/stage2_dpo.yaml

$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "DPO TRAINING COMPLETE" -ForegroundColor Green
Write-Host "Duration: $($duration.Hours)h $($duration.Minutes)m $($duration.Seconds)s"
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "`nNext: Run 05_train_kto.ps1 for KTO training (optional)"

