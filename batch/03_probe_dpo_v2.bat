@echo off
echo ========================================
echo VGPT2 v3 - Probe Test (DPO v2 Model)
echo ========================================
echo This tests if DPO v2 has the over-rejection bug
echo (incorrectly saying real tables don't exist)
echo ========================================
echo.

cd /d C:\Github\LLM_fine-tuning
call venv\Scripts\activate.bat

echo Running probe test on DPO v2 model...
echo Output will be saved to: output\probe_dpo_v2.json
echo.

python scripts/vgpt2_v3/probe_test.py --model saves/vgpt2_v3/dpo_v2 --output output/probe_dpo_v2.json

echo.
echo ========================================
echo Probe test complete!
echo Results saved to: output\probe_dpo_v2.json
echo ========================================
pause

