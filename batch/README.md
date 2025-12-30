# Batch Files for VGPT2 v3

Double-click any `.bat` file to run it. All files auto-activate the venv.

## Current Tasks (Run These Now)

| File | Purpose | Run? |
|------|---------|------|
| `01_validate_sft.bat` | Get SFT baseline scores | ✅ YES |
| `02_probe_sft.bat` | Test SFT real/fake table recognition | ✅ YES |
| `03_probe_dpo_v2.bat` | Confirm DPO v2 over-rejection bug | Optional |

## Utility

| File | Purpose |
|------|---------|
| `04_chat_sft.bat` | Interactive chat with SFT model |

## Output Files

After running, check `output/` folder:
- `validation_sft_baseline.json` - SFT validation scores
- `probe_sft.json` - SFT probe test results
- `probe_dpo_v2.json` - DPO v2 probe test results

## Notes

- Model loading takes 2-3 minutes (7B parameters)
- Each validation run takes ~10-15 minutes
- Probe tests take ~5-10 minutes
- Window stays open after completion (press any key to close)

