# VGPT2 v4 Training Guide

**Date:** 2025-01-15  
**Status:** 🔄 READY FOR TRAINING  
**Approach:** SQLCoder Methodology

---

## Executive Summary

V4 represents a **fundamental shift** from V3's trivia-based approach to **production-grade SQL generation**.

### Key Changes from V3

| Aspect | V3 (Old) | V4 (New) |
|--------|----------|----------|
| **Base Model** | Qwen2.5-7B-Instruct (general LLM) | SQLCoder-8B (SQL-specialized) |
| **Data Format** | Q&A trivia ("What columns in X?") | SQLCoder-style DDL-in-prompt |
| **Dataset Size** | 67,448 auto-generated | ~1,000 human-curated |
| **Quality** | Quantity over quality | Quality over quantity |
| **Task** | Information recall | SQL generation with schema context |

### Why SQLCoder?

1. **Outperforms GPT-4** on text-to-SQL benchmarks
2. **Same architecture** (LLaMA 3 8B) fits on A6000
3. **Trained on 20K human-curated examples** - matches our approach
4. **Schema-in-prompt** eliminates memorization issues

---

## Quick Start

### Prerequisites

```bash
# Verify CUDA is working
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0)}')"

# Verify LLaMA Factory
llamafactory-cli version
```

### Start V4 Training

```powershell
# Option 1: Direct command
llamafactory-cli train automation/configs/vgpt2_v4/stage1_sft.yaml

# Option 2: Use training script
.\training\01_start_sft_v4.ps1
```

### Monitor Training

```powershell
# Watch GPU usage
nvidia-smi -l 1

# Check training logs
Get-Content saves/vgpt2_v4/sft/trainer_log.jsonl -Tail 20 -Wait
```

---

## Training Configuration

### Stage 1: SFT (Supervised Fine-Tuning)

**Config:** `automation/configs/vgpt2_v4/stage1_sft.yaml`

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `model_name_or_path` | `defog/llama-3-sqlcoder-8b` | SQL-specialized base |
| `template` | `llama3` | SQLCoder uses LLaMA 3 template |
| `dataset` | `vgpt2_v4_sft_expanded` | SQLCoder-style DDL-in-prompt |
| `lora_rank` | 128 | Sufficient for ~1K examples |
| `per_device_train_batch_size` | 4 | Optimized for A6000 |
| `num_train_epochs` | 3.0 | Standard for curated data |
| `cutoff_len` | 4096 | SQLCoder context length |

**Expected Training Time:** 1-2 hours (3 epochs, ~1K examples)

### Stage 2: DPO (Optional)

**Config:** `automation/configs/vgpt2_v4/stage2_dpo.yaml`

Only run DPO if SFT shows issues with:
- Generating queries for non-existent tables
- Missing WITH (NOLOCK) hints
- Incorrect JOIN patterns

**Lesson from V3:** DPO v2 caused over-rejection. Use sparingly.

---

## Dataset Structure

### V4 Format (SQLCoder-style)

Each example includes:
1. **Question** - Natural language SQL request
2. **Database Schema** - CREATE TABLE DDL for relevant tables
3. **Output** - Explanation + SQL query + notes

```json
{
  "instruction": "Generate a SQL query...\n\nQuestion: List unpaid AP invoices\n\nDatabase Schema:\nCREATE TABLE APTH (...)\n\nProvide:\n1. A brief explanation\n2. The SQL query\n3. Any Vista-specific notes",
  "input": "",
  "output": "To find unpaid AP invoices:\n1. Query APTH...\n\n```sql\nSELECT ...\n```"
}
```

### Category Distribution (Current)

| Category | Count | Description |
|----------|-------|-------------|
| `ar_queries` | 217 | Accounts Receivable |
| `jc_queries` | 203 | Job Cost |
| `ap_queries` | 164 | Accounts Payable |
| `cross_module` | 129 | Multi-module queries |
| `negative` | 102 | Fake table rejection |
| `sl_queries` | 92 | Subcontracts |
| `gl_queries` | 3 | General Ledger |
| `pr_queries` | 2 | Payroll |

**Total:** 912 examples (target: 3,000+)

### Expanding the Dataset

```bash
# Run expansion script
python scripts/expand_v4_training_data.py

# Preview changes
python scripts/expand_v4_training_data.py --preview
```

---

## Hardware Utilization

### A6000 (48GB VRAM) Optimization

```yaml
# Optimal settings for SQLCoder-8B with LoRA
per_device_train_batch_size: 4
gradient_accumulation_steps: 4
gradient_checkpointing: true
bf16: true
```

### Threadripper 7960X (24c/48t) Optimization

```yaml
preprocessing_num_workers: 16
# Note: dataloader_num_workers: 0 required on Windows
```

---

## Validation

### After Training

```powershell
# Run probe test
python scripts/probe_model.py --model saves/vgpt2_v4/sft

# Test SQL generation
llamafactory-cli chat \
  --model_name_or_path saves/vgpt2_v4/sft \
  --adapter_name_or_path saves/vgpt2_v4/sft \
  --template llama3
```

### Key Metrics

| Metric | Target | V3 SFT | V3 DPO |
|--------|--------|--------|--------|
| Real table recognition | 100% | 100% | 90% ❌ |
| Fake table rejection | 90%+ | 70% | 100% |
| SQL syntax validity | 95%+ | N/A | N/A |
| WITH (NOLOCK) usage | 100% | N/A | N/A |

---

## Troubleshooting

### "CUDA out of memory"

1. Reduce `per_device_train_batch_size` to 2
2. Enable `gradient_checkpointing: true`
3. Reduce `lora_rank` to 64

### "Model not found: defog/llama-3-sqlcoder-8b"

```bash
# Download model first
python -c "from transformers import AutoModelForCausalLM; AutoModelForCausalLM.from_pretrained('defog/llama-3-sqlcoder-8b')"
```

### "Training loss not decreasing"

1. Check learning rate (try 1e-4 instead of 2e-4)
2. Verify dataset format matches template
3. Check for data quality issues

---

## Files Reference

| File | Purpose |
|------|---------|
| `automation/configs/vgpt2_v4/stage1_sft.yaml` | SFT training config |
| `automation/configs/vgpt2_v4/stage2_dpo.yaml` | DPO training config |
| `data/vgpt2_v4_sft_expanded_clean.json` | Training dataset |
| `scripts/expand_v4_training_data.py` | Data expansion script |
| `training/01_start_sft_v4.ps1` | Training launcher |
| `saves/vgpt2_v4/sft/` | Output directory |

---

## Next Steps After Training

1. **Validate** with probe test (real/fake table recognition)
2. **Chat Test** with production-like queries
3. **Merge LoRA** for deployment (optional)
4. **DPO** only if hallucination issues persist
5. **Deploy** to production API

---

## Evidence Base

### SQLCoder Research

- Defog SQLCoder paper: https://defog.ai/blog/sqlcoder2-8b/
- SQLCoder-8B outperforms GPT-4 on Spider benchmark
- Trained on 20K human-curated SQL pairs
- Uses schema-in-prompt methodology

### V4 Strategy Documentation

- `docs/V4_TRAINING_STRATEGY.md` - Original strategy (June 2025)
- `docs/DEEP_DIVE_ANALYSIS.md` - V3 failure analysis
- `VGPT2_V3_DEEP_DIVE_REVIEW.md` - Comprehensive review

### Why V4 Will Succeed Where V3 Struggled

| V3 Problem | V4 Solution |
|------------|-------------|
| Wrong task (Q&A trivia) | Right task (SQL generation) |
| General LLM base | SQL-specialized base |
| Memorization required | Schema-in-prompt |
| 67K low-quality examples | 1K+ high-quality examples |
| DPO over-rejection | Skip DPO unless needed |
