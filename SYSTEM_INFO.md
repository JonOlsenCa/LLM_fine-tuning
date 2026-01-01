# System Configuration for LLM Fine-Tuning

This file documents the hardware and software configuration for training optimization.

## Hardware

### GPU
| Property | Value |
|----------|-------|
| Model | NVIDIA RTX A6000 |
| VRAM | 49,140 MiB (48 GB) |
| Driver | 573.73 |
| Compute Capability | 8.6 (Ampere) |
| Capabilities | BF16, TF32, FlashAttention-2 |

### CPU
| Property | Value |
|----------|-------|
| Model | AMD Ryzen Threadripper 7960X |
| Cores | 24 physical / 48 logical |
| Architecture | Zen 4 |

### Memory
| Property | Value |
|----------|-------|
| RAM | 130,570 MB (~128 GB) |

## Software

### Python Installations
| Version | Location | Notes |
|---------|----------|-------|
| 3.14.0 | C:\Python314 | System default, NO PyTorch CUDA support |
| 3.13.x | C:\Users\olsen\AppData\Local\Programs\Python\Python313 | |
| 3.12.10 | (via py launcher) | **RECOMMENDED** for PyTorch CUDA |

### CUDA/NVIDIA
| Property | Value |
|----------|-------|
| CUDA Toolkit | **NOT INSTALLED** (not needed - PyTorch bundles CUDA) |
| Driver CUDA Support | Up to CUDA 12.x |
| PyTorch Index | `cu124` (CUDA 12.4, verified working with Python 3.12) |

### PyTorch Compatibility Matrix
| Python | cu121 | cu124 | Notes |
|--------|-------|-------|-------|
| 3.12 | ✅ | ✅ | **Use this** |
| 3.13 | ❌ | ⚠️ | Limited |
| 3.14 | ❌ | ❌ | Not supported yet |

## Recommended Training Settings

With 48GB VRAM + 128GB RAM, aggressive settings are possible:

### For Qwen2.5-7B-Instruct (LoRA SFT)
```yaml
# Batch settings (48GB VRAM allows larger batches)
per_device_train_batch_size: 4      # Can go up to 8 with shorter sequences
gradient_accumulation_steps: 4      # Effective batch = 16
cutoff_len: 4096                    # Full context for schema-in-prompt

# Precision (A6000 supports BF16 natively)
bf16: true

# DataLoader (leverage 24 cores)
preprocessing_num_workers: 8
dataloader_num_workers: 4

# Flash Attention (A6000 supports it)
flash_attn: fa2
```

### Estimated Training Times (892 examples, 3 epochs)
| Batch Size | Est. Time |
|------------|-----------|
| 2 (current) | ~45 min  |
| 4           | ~25 min  |
| 8           | ~15 min  |

## Environment Setup Instructions

### Step 1: Close VS Code terminals (they lock the venv)

Close ALL terminals in VS Code, then in a NEW external PowerShell:

### Step 2: Remove corrupted venv
```powershell
# Kill any Python processes using the venv
Get-Process python | Where-Object {$_.Path -like "*LLM_fine-tuning*"} | Stop-Process -Force

# Remove the venv
Remove-Item -Recurse -Force C:\Github\LLM_fine-tuning\.venv
```

### Step 3: Create new venv with Python 3.12
```powershell
cd C:\Github\LLM_fine-tuning
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 4: Install PyTorch with CUDA 12.4
```powershell
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

### Step 5: Install LLaMA Factory
```powershell
pip install -e ".[dev]"
```

### Step 6: Verify
```powershell
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}')"
# Expected: CUDA: True, GPU: NVIDIA RTX A6000
```

---
*Generated: 2026-01-01*
*Last Updated: 2026-01-01*
