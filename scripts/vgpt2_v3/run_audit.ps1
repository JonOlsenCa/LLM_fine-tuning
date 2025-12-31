# Audit Training Data Coverage
# Usage: .\scripts\vgpt2_v3\run_audit.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Training Data Audit" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

.\venv\Scripts\activate.ps1
python scripts/vgpt2_v3/audit_training_data.py

Write-Host "`nAudit complete. Check output/training_audit.json for full details." -ForegroundColor Green

