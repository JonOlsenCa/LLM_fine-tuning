# VGPT2 v3 Training Scripts

Run these scripts in order from this directory.

## Quick Start

```powershell
cd c:\Github\LLM_fine-tuning

# 1. Review what's running
.\training\run\00_review_resources.ps1

# 2. Kill resource hogs (Chrome, Teams, etc.)
.\training\run\01_stop_resource_hogs.ps1

# 3. Start monitor in SEPARATE terminal
.\training\run\02_start_monitor.ps1

# 4. Start SFT training (main terminal)
.\training\run\03_train_sft.ps1

# 5. After SFT completes, run DPO
.\training\run\04_train_dpo.ps1

# 6. Optional: KTO training
.\training\run\05_train_kto.ps1

# 7. View all checkpoints
.\training\run\06_view_checkpoints.ps1
```

## Scripts

| Script | Purpose |
|--------|---------|
| `00_review_resources.ps1` | Check GPU, RAM, CPU, disk space |
| `01_stop_resource_hogs.ps1` | Kill Chrome, Teams, Slack, etc. |
| `02_start_monitor.ps1` | Live monitor (run in separate terminal) |
| `03_train_sft.ps1` | Stage 1: Supervised Fine-Tuning |
| `04_train_dpo.ps1` | Stage 2: Direct Preference Optimization |
| `05_train_kto.ps1` | Stage 3: KTO (optional) |
| `06_view_checkpoints.ps1` | List all saved checkpoints |

## Checkpoint Locations

- **SFT**: `saves/vgpt2_v3/sft/`
- **DPO**: `saves/vgpt2_v3/dpo/`
- **KTO**: `saves/vgpt2_v3/kto/`

## Training Data

- **SFT**: `data/vgpt2_v3_sft_merged.json` (70,006 examples)
- **DPO**: `data/vgpt2_v3_dpo.json`
- **KTO**: `data/vgpt2_v3_kto.json`

## Configs

All configs in: `automation/configs/vgpt2_v3/`

## Resume Training

If training is interrupted, edit the config and set:
```yaml
resume_from_checkpoint: true
```

Then re-run the training script.

## Expected Timeline

| Stage | Duration | Checkpoints |
|-------|----------|-------------|
| SFT | 8-12 hours | ~52 |
| DPO | 2-4 hours | ~15 |
| KTO | 1-2 hours | ~10 |

