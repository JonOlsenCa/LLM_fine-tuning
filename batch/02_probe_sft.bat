@echo off
echo ========================================
echo VGPT2 v3 - Probe Test (SFT Model)
echo ========================================
echo This tests if the model correctly identifies
echo REAL tables (should say EXISTS) vs
echo FAKE tables (should say NOT EXISTS)
echo ========================================
echo.

cd /d C:\Github\LLM_fine-tuning
call venv\Scripts\activate.bat

echo Running probe test on SFT model...
echo Output will be saved to: output\probe_sft.json
echo.

python scripts/vgpt2_v3/probe_test.py --model saves/vgpt2_v3/sft --output output/probe_sft.json

echo.
echo ========================================
echo Probe test complete!
echo Results saved to: output\probe_sft.json
echo ========================================
pause

