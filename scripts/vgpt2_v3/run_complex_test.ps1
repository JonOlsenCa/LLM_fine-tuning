# Run Complex Test Suite for VGPT2 SFT Model
# Usage: .\scripts\vgpt2_v3\run_complex_test.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VGPT2 Complex Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\activate.ps1

# Run complex test
Write-Host "`nRunning complex test against SFT model..." -ForegroundColor Yellow
Write-Host "Model: saves/vgpt2_v3/sft" -ForegroundColor Gray
Write-Host "Questions: training/COMPLEX_TEST_QUESTIONS.json" -ForegroundColor Gray
Write-Host "Output: output/complex_test_results.json" -ForegroundColor Gray
Write-Host ""

python scripts/vgpt2_v3/test_complex.py `
    --model saves/vgpt2_v3/sft `
    --questions training/COMPLEX_TEST_QUESTIONS.json `
    --output output/complex_test_results.json

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Green
Write-Host "Results saved to: output/complex_test_results.json" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

