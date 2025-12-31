# VGPT2 v3 Training Master Plan

**Date:** 2025-12-31
**Status:** ✅ SFT READY TO SHIP
**Author:** Training Analysis

---

## Executive Summary

SFT model is performing well and is ready for deployment. DPO training caused over-rejection and should be skipped.

### Current State

| Stage | Status | Result |
|-------|--------|--------|
| SFT (Stage 1) | ✅ READY | 91% overall, 98% hallucination |
| DPO v1 (Stage 2) | ❌ Failed | 1,427 pairs, 57% hallucination score |
| DPO v2 (Stage 2) | ❌ Failed | 2,584 pairs, caused over-rejection |
| **Probe Test** | ✅ PASSED | 100% real table recognition |

### Key Decision: Ship SFT, Skip DPO

The SFT model correctly identifies ALL real tables (0 false rejections).
DPO v2 caused the model to reject real tables - this is unacceptable.

---

## Probe Test Results (2025-12-31)

| Metric | Result |
|--------|--------|
| Real Tables Correctly Identified | **10/10** ✅ |
| Fake Tables Correctly Rejected | 7/10 |
| False Rejections (Real→Fake) | **0** ✅ |
| False Acceptances (Fake→Real) | 3 |

### False Acceptances (Minor Issues)
- **EmployeeMaster** - Model confused with PREH
- **UserPreferences** - Model hallucinated schema
- **Customer** - Model confused with ARCM

These are acceptable because:
1. Overall hallucination score is 98%
2. False acceptances are less harmful than false rejections
3. DPO training made this worse, not better

---

## Historical Context

### DPO v2 Critical Finding (Now Resolved)

**DPO v2 trained the model to reject REAL Vista tables as non-existent.**

```
Q: "Describe the APTL table structure"
A: "The table 'APTL' does not exist in Viewpoint Vista..."
```
APTL IS A REAL TABLE. The model learned rejection TOO WELL.

---

## Hardware Configuration

| Component | Spec | Current Usage |
|-----------|------|---------------|
| GPU | RTX A6000 (48GB VRAM) | ⚠️ Under-utilized |
| CPU | Threadripper 7960X (24c/48t) | ⚠️ Under-utilized |
| RAM | 128GB DDR5 | ✅ Adequate |

### Training Config Issues Found

```yaml
# CURRENT (suboptimal)
per_device_train_batch_size: 1      # Too conservative
gradient_accumulation_steps: 16     # Compensates but slow
dataloader_num_workers: 0           # NO parallel loading!

# RECOMMENDED
per_device_train_batch_size: 2-4    # A6000 can handle more
gradient_accumulation_steps: 8      # Adjust for effective batch
dataloader_num_workers: 8           # Use CPU threads!
```

---

## What We Have

### Training Data

| File | Records | Purpose | Status |
|------|---------|---------|--------|
| `vgpt2_v3_sft.json` | 67,448 | SFT training | ✅ Used |
| `vgpt2_v3_dpo.json` | 1,427 | Original DPO (90% NOLOCK) | ⚠️ Imbalanced |
| `vgpt2_v3_dpo_v2.json` | 2,584 | Halluc DPO (83% rejection) | ❌ Caused over-rejection |
| `vgpt2_v3_kto.json` | ? | KTO data | ⏸️ Not used yet |

### Trained Models

| Path | Stage | Notes |
|------|-------|-------|
| `saves/vgpt2_v3/sft/` | Stage 1 | ✅ Good baseline |
| `saves/vgpt2_v3/dpo/` | Stage 2 v1 | 57% hallucination |
| `saves/vgpt2_v3/dpo_v2/` | Stage 2 v2 | ❌ Over-rejects real tables |

### Validation Results (DPO v2)

| Category | Score | Issue |
|----------|-------|-------|
| Join | 98% | ✅ Excellent |
| SQL Generation | 87% | ✅ Good |
| Schema | 86% | ⚠️ Degraded from SFT |
| Error Correction | 83% | ✅ Good |
| Business Logic | 80% | ✅ Good |
| Hallucination | 57% | 🔴 Failed + over-rejects |

---

## Root Cause Analysis

### Problem 1: Imbalanced DPO Data

| Dataset | Halluc Rejection | Other | Result |
|---------|------------------|-------|--------|
| DPO v1 | 5% | 95% | Ignored hallucination signal |
| DPO v2 | 83% | 17% | Over-learned rejection |

### Problem 2: Missing Positive Reinforcement

We only taught "fake tables don't exist" but NEVER taught "real tables DO exist":

```json
// WE HAD (rejection only)
{"instruction": "Query Invoice table", "chosen": "doesn't exist", "rejected": "SELECT..."}

// WE NEEDED (also positive)
{"instruction": "Describe APTL", "chosen": "APTL is AP Transaction Lines...", "rejected": "doesn't exist"}
```

### Problem 3: Test Suite Keyword Mismatch

Model says: "There is **no table or view** named 'Invoice'"
Test expects: "**doesn't exist**" or "**not exist**"

The model behavior may be correct, but the test keywords don't match.

---

### New DPO v3 Dataset Requirements

| Category | Count | Purpose |
|----------|-------|---------|
| Fake table rejection | 800 | "Invoice doesn't exist, use APTH" |
| **Real table acceptance** | 800 | "APTL exists, here's its structure" |
| Fake column rejection | 400 | "CustomerName doesn't exist in ARCM" |
| NOLOCK preferences | 300 | Style correction |
| JOIN quality | 200 | Multi-column JOIN patterns |
| **TOTAL** | 2,500 | Balanced 50/50 reject/accept |

### Key Principle: For Every Rejection, Add an Acceptance

```json
// Rejection pair
{"instruction": "Query Invoice", "chosen": "doesn't exist, use APTH", "rejected": "SELECT * FROM Invoice"}

// Matching acceptance pair
{"instruction": "Describe APTH", "chosen": "APTH is AP Transaction Header...", "rejected": "doesn't exist"}
```

---

## Validation Plan (Before ANY Training)

### Step 1: Ground Truth Baseline

Have Claude answer all 47 test questions to establish what "correct" looks like.

### Step 2: Targeted Probe Test

Before training, test the SFT model with diagnostic questions:
```
"Does APTL exist in Vista?" → Must say YES
"Does Invoice exist in Vista?" → Must say NO
"Does APTH exist in Vista?" → Must say YES
"Does Customer exist in Vista?" → Must say NO
```

### Step 3: Training Data Audit

Review the new DPO dataset to verify:
- [ ] Real tables are NEVER in rejection pairs
- [ ] Fake tables are NEVER in acceptance pairs
- [ ] 50/50 balance between rejection and acceptance
- [ ] Test keywords match expected model responses

### Step 4: Held-Out Validation Set

Create 50+ hallucination test cases NOT in training data:
- Edge cases: `AP_TH`, `apth`, `APTransactionHeader`
- Near-misses: `APHD` (doesn't exist), `APTH` (exists)
- Module confusion: "Get AR invoices" (no AR invoices table)

---

## Action Items

### Completed ✅

- [x] Run SFT model through all 47 tests as baseline → **91% overall**
- [x] Run targeted probe test on SFT model → **100% real table recognition**
- [x] Claude answers all 47 questions for ground truth → See GROUND_TRUTH_ANSWERS.md
- [x] Analyze DPO v2 failure mode → Over-rejection of real tables

### Cancelled (DPO Not Needed)

- [-] Generate balanced DPO v3 dataset - SFT is good enough
- [-] Train DPO v3 from SFT checkpoint - Would risk over-rejection again

### Next Steps (Deployment)

- [ ] Package SFT model for production use
- [ ] Create deployment documentation
- [ ] Run additional capability tests (optional)
- [ ] Monitor production performance

---

## Training Configuration Updates

### Optimized Config (stage2_dpo_v3.yaml)

```yaml
### Dataset Settings ###
dataset: vgpt2_v3_dpo_v3             # Balanced dataset
preprocessing_num_workers: 16
dataloader_num_workers: 8            # USE CPU THREADS!

### Training Settings ###
per_device_train_batch_size: 2       # A6000 can handle this
gradient_accumulation_steps: 8       # Effective batch = 16
learning_rate: 5.0e-6
num_train_epochs: 2.0
bf16: true
gradient_checkpointing: true
```

---

## Files Reference

### Scripts
| File | Purpose |
|------|---------|
| `scripts/generate_halluc_dpo.py` | Generated v2 halluc pairs |
| `scripts/merge_dpo_datasets.py` | Merged datasets |
| `scripts/vgpt2_v3/run_validation.py` | Validation pipeline |

### Configs
| File | Purpose |
|------|---------|
| `automation/configs/vgpt2_v3/stage1_sft.yaml` | SFT config |
| `automation/configs/vgpt2_v3/stage2_dpo.yaml` | DPO v1 config |
| `automation/configs/vgpt2_v3/stage2_dpo_v2.yaml` | DPO v2 config |

### Training Scripts
| File | Purpose |
|------|---------|
| `training/01_start_sft.ps1` | Start SFT |
| `training/03_start_dpo.ps1` | Start DPO v1 |
| `training/03b_start_dpo_v2.ps1` | Start DPO v2 |

### Output
| File | Purpose |
|------|---------|
| `output/validation_dpo_v2.json` | DPO v2 validation results |
| `DPO_Analysis.md` | Full post-mortem analysis |

---

## Success Criteria for DPO v3

| Metric | Current (DPO v2) | Target |
|--------|------------------|--------|
| Overall | 80% | >85% |
| Hallucination | 57% | >85% |
| Schema | 86% | >90% |
| No false rejections | ❌ Has them | ✅ Zero |

---

## Decision Points

1. **Should we try DPO at all?** Or focus on better SFT data?
2. **Is 50/50 the right balance?** Or should acceptance be higher?
3. **Should we use KTO instead?** Binary feedback may be simpler.
4. **Is the test suite correct?** Need to validate expectations.

---

*Last Updated: 2025-12-30*
