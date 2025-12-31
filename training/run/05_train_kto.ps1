# ============================================================
# STEP 5: Start KTO Training (Stage 3 - Optional)
# ============================================================
# Kahneman-Tversky Optimization using thumbs up/down signals
# Run AFTER DPO training completes
#
# Config: automation/configs/vgpt2_v3/stage3_kto.yaml
# Input:  saves/vgpt2_v3/dpo/ (from Stage 2)
# Output: saves/vgpt2_v3/kto/
# ============================================================

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "STAGE 3: KAHNEMAN-TVERSKY OPTIMIZATION (KTO)" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

Write-Host "`n[PRE-FLIGHT CHECK]" -ForegroundColor Yellow

# Check DPO output exists
Write-Host "  Checking DPO checkpoint..." -NoNewline
if (Test-Path "saves/vgpt2_v3/dpo") {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED - Run Stage 2 (DPO) first!" -ForegroundColor Red
    exit 1
}

# Check KTO dataset
Write-Host "  Checking KTO dataset..." -NoNewline
if (Test-Path "data/vgpt2_v3_kto.json") {
    $size = [math]::Round((Get-Item "data/vgpt2_v3_kto.json").Length/1MB, 1)
    Write-Host " OK (${size} MB)" -ForegroundColor Green
} else {
    Write-Host " FAILED - KTO dataset not found!" -ForegroundColor Red
    Write-Host "  Generate with: python scripts/vgpt2_v3/generate_kto_data.py" -ForegroundColor Yellow
    exit 1
}

# Check config
Write-Host "  Checking config..." -NoNewline
if (Test-Path "automation/configs/vgpt2_v3/stage3_kto.yaml") {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED - Config not found!" -ForegroundColor Red
    exit 1
}

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "Starting KTO training in 5 seconds... (Ctrl+C to cancel)" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Cyan
Start-Sleep -Seconds 5

.\venv\Scripts\activate.ps1

$startTime = Get-Date
Write-Host "`nTraining started at: $startTime" -ForegroundColor Green

llamafactory-cli train automation/configs/vgpt2_v3/stage3_kto.yaml

$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "KTO TRAINING COMPLETE" -ForegroundColor Green
Write-Host "Duration: $($duration.Hours)h $($duration.Minutes)m $($duration.Seconds)s"
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "`nAll training stages complete!"
Write-Host "Run 06_view_checkpoints.ps1 to see all saved checkpoints"

