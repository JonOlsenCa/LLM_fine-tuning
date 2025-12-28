# VGPT2 Fine-Tuning Setup Guide

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Python** | 3.11 | **3.12** |
| GPU VRAM | 24 GB | 48 GB (RTX A6000) |
| System RAM | 32 GB | 128 GB |
| CUDA | 12.1 | 12.4 |

> ⚠️ **CRITICAL: Do NOT use Python 3.13 or 3.14!**  
> Python 3.14 breaks the `dill` serialization library used by `datasets`.  
> Error: `TypeError: Pickler._batch_setitems() takes 2 positional arguments but 3 were given`

---

## Windows Setup (Step-by-Step)

### 1. Verify Python Version

```powershell
# List all installed Python versions
py -0p

# You should have Python 3.12 installed
# If not, download from: https://www.python.org/downloads/release/python-31210/
```

### 2. Create Virtual Environment with Python 3.12

```powershell
# Navigate to project
cd C:\Github\LLM_fine-tuning

# Create venv with SPECIFIC Python version (NOT default!)
py -3.12 -m venv venv

# Activate
.\venv\Scripts\Activate.ps1

# Verify
python --version  # Should show 3.12.x
```

### 3. Install PyTorch with CUDA

```powershell
# For CUDA 12.4 (RTX 30xx/40xx/A6000)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Verify CUDA
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')"
```

### 4. Install Dependencies (ORDER MATTERS!)

```powershell
# Step 1: Core dependencies FIRST (prevents broken installs)
pip install "numpy<2.0.0" cffi python-dateutil pandas

# Step 2: ML dependencies
pip install accelerate>=0.21.0 huggingface_hub>=0.25.0 packaging>=20.0 datasets

# Step 3: LLaMA-Factory
pip install -e "C:\Github\LLaMA-Factory[torch,metrics]"

# Step 4: bitsandbytes for Windows
pip install bitsandbytes
```

> ⚠️ **CRITICAL DEPENDENCY NOTES:**
> - `numpy` must be <2.0.0 - trl requires it, pip may install 2.4.0 which breaks things
> - `cffi` - required by soundfile, not always auto-installed
> - `python-dateutil` - required by pandas, sometimes missing

---

## Quick Verification

```powershell
# All should work without errors
python -c "import torch; print('PyTorch OK')"
python -c "import transformers; print('Transformers OK')"
python -c "import datasets; print('Datasets OK')"
python -c "from llamafactory.cli import main; print('LLaMA-Factory OK')"
```

---

## Training Configuration

Key settings for Windows in `automation/configs/vgpt2_lora_sft.yaml`:

```yaml
# MUST be 0 on Windows (CUDA multiprocessing bug)
dataloader_num_workers: 0

# Disable packing if training is slow (O(n²) attention on long sequences)
packing: false

# Save checkpoints frequently for crash recovery
save_steps: 200
save_total_limit: 5
```

---

## Start Training

```powershell
# Terminal 1: Resource monitor
python scripts/resource_monitor.py

# Terminal 2: Training
llamafactory-cli train automation/configs/vgpt2_lora_sft.yaml
```

---

## Checkpointing & Crash Recovery

### Checkpoint Settings (in `automation/configs/vgpt2_lora_sft.yaml`)

```yaml
# Checkpoints save every 200 steps (~12 minutes at 3.7s/it)
save_steps: 200
save_total_limit: 5  # Keep last 5 checkpoints to save disk space

# Checkpoints saved to:
output_dir: saves/vgpt2_v2_lora_sft
```

### Resume After Crash / Power Outage

1. **Find your last checkpoint:**
```powershell
dir saves\vgpt2_v2_lora_sft\checkpoint-*
```

2. **Edit config to resume:**
```yaml
# In automation/configs/vgpt2_lora_sft.yaml
resume_from_checkpoint: true
```

3. **Restart training:**
```powershell
llamafactory-cli train automation/configs/vgpt2_lora_sft.yaml
```

Training will automatically resume from the latest checkpoint.

### Expected Training Time

| Metric | Value |
|--------|-------|
| Total steps | 7,050 |
| Speed | ~3.7 s/it |
| Total time | **~7.3 hours** |
| Checkpoint interval | Every 200 steps (~12 min) |
| Max data loss on crash | ~12 minutes of training |

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| `Pickler._batch_setitems() takes 2 positional arguments` | Use Python 3.12, not 3.14 |
| `trl requires numpy<2.0.0` | Run `pip install "numpy<2.0.0"` |
| `No module named 'dateutil'` | Run `pip install python-dateutil` |
| `cffi>=1.0 not installed` | Run `pip install cffi` |
| `CUDA out of memory` | Reduce `per_device_train_batch_size` |
| Training stuck at 0% | Set `dataloader_num_workers: 0` |
| Very slow training (300+ s/it) | Disable `packing: false` |

---

## Hardware Used

- **GPU**: NVIDIA RTX A6000 (48GB VRAM)
- **CPU**: AMD Threadripper 7960X (48 cores)
- **RAM**: 128 GB DDR5
- **OS**: Windows 11

### Actual Training Performance (Dec 2024)

| Metric | Value |
|--------|-------|
| Training samples | 22,554 |
| Epochs | 5 |
| Total steps | 7,050 |
| Speed | 3.7 s/it |
| GPU utilization | 99% |
| VRAM usage | 39.6 / 48 GB (82.6%) |
| Temperature | 78°C |
| **Total training time** | **~7.3 hours** |

