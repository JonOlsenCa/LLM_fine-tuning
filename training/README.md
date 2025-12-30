# VGPT2 v3 Training Directory

**Status:** 🔴 PAUSED - See [MASTER_PLAN.md](MASTER_PLAN.md) for details

---

## 🚀 Quick Start: Run Batch Files

When the AI assistant needs you to run something, it will create a `.bat` file in the `batch/` folder.

```
C:\Github\LLM_fine-tuning\batch\
```

**Just double-click the .bat file to run it.** No terminal commands needed.

### Current Tasks - Run These Now:
1. `batch\01_validate_sft.bat` - Get SFT baseline scores
2. `batch\02_probe_sft.bat` - Test real/fake table recognition

---

## ⚠️ IMPORTANT: Read Before Training

Before starting any new training, read:
1. **[MASTER_PLAN.md](MASTER_PLAN.md)** - Full status, analysis, and action plan
2. **[../DPO_Analysis.md](../DPO_Analysis.md)** - DPO failure post-mortem

### Current Issues
- DPO v2 caused model to reject REAL Vista tables
- Test suite keywords don't match model responses
- Hardware under-utilized (dataloader_num_workers: 0)

---

## Training History

| Date | Stage | Result | Notes |
|------|-------|--------|-------|
| 2025-12-28 | SFT | ✅ Success | 67K examples, 15.9 hrs |
| 2025-12-29 | DPO v1 | ❌ Failed | 57% hallucination, imbalanced data |
| 2025-12-30 | DPO v2 | ❌ Failed | Over-rejection of real tables |

---

## Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `01_start_sft.ps1` | Start Stage 1 SFT | ✅ Working |
| `02_resume_sft.ps1` | Resume SFT | ✅ Working |
| `03_start_dpo.ps1` | Start DPO v1 | ⚠️ Imbalanced data |
| `03b_start_dpo_v2.ps1` | Start DPO v2 | ❌ Caused over-rejection |
| `04_start_kto.ps1` | Start KTO | ⏸️ Not tested |
| `05_validate.ps1` | Run validation | ✅ Working |
| `monitor_gpu.ps1` | GPU monitoring | ✅ Working |
| `monitor_checkpoints.ps1` | Checkpoint monitoring | ✅ Working |

---

## Model Checkpoints

```
saves/vgpt2_v3/
├── sft/          # ✅ Stage 1 - Good baseline
├── dpo/          # ⚠️ Stage 2 v1 - 57% hallucination
└── dpo_v2/       # ❌ Stage 2 v2 - Over-rejects real tables
```

---

## Quick Commands

```powershell
# Activate environment
cd C:\Github\LLM_fine-tuning
.\venv\Scripts\Activate.ps1

# Run validation on a model
python scripts/vgpt2_v3/run_validation.py --model saves/vgpt2_v3/sft --quick

# Monitor GPU
.\training\monitor_gpu.ps1

# Start SFT (if needed)
.\training\01_start_sft.ps1
```

---

## Next Steps

See [MASTER_PLAN.md](MASTER_PLAN.md) for:
1. Validation plan before any more training
2. Balanced DPO v3 dataset requirements
3. Hardware optimization settings
4. Success criteria

---

## Related Files

| Location | Purpose |
|----------|---------|
| `automation/configs/vgpt2_v3/` | Training YAML configs |
| `data/vgpt2_v3_*.json` | Training datasets |
| `scripts/vgpt2_v3/` | Data generation & validation |
| `output/validation_*.json` | Test results |

---

*Last Updated: 2025-12-30*

