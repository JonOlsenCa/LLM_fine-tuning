@echo off
echo ========================================
echo VGPT2 v3 - Validate SFT Model (Baseline)
echo ========================================
echo.

cd /d C:\Github\LLM_fine-tuning
call venv\Scripts\activate.bat

echo Running validation on SFT model...
echo Output will be saved to: output\validation_sft_baseline.json
echo.

python scripts/vgpt2_v3/run_validation.py --model saves/vgpt2_v3/sft --output output/validation_sft_baseline.json --quick

echo.
echo ========================================
echo Validation complete!
echo Results saved to: output\validation_sft_baseline.json
echo ========================================
pause

