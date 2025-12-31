# Generate Comprehensive Training Data and Test Suite
# Generates:
# - 1,500+ targeted training examples
# - 500+ test questions with ground truth

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Comprehensive Training Data Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

.\venv\Scripts\activate.ps1

Write-Host "`nGenerating comprehensive training data..." -ForegroundColor Yellow
python scripts/vgpt2_v3/generate_comprehensive_training.py

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Generation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nOutputs:" -ForegroundColor Yellow
Write-Host "  Training: data/vgpt2_v3_advanced.json" -ForegroundColor Gray
Write-Host "  Test Suite: training/COMPREHENSIVE_TEST_SUITE.json" -ForegroundColor Gray

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Review the generated data" -ForegroundColor Gray
Write-Host "2. Merge training data with existing dataset" -ForegroundColor Gray
Write-Host "3. Re-train the model" -ForegroundColor Gray
Write-Host "4. Run test suite to validate" -ForegroundColor Gray

