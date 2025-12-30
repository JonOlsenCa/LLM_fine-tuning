# VGPT2 v3 Training - Continuation Prompt

**Last Updated:** 2025-12-31
**Status:** SFT Complete, Evaluating Results

---

## 🎯 PASTE THIS TO CONTINUE

```
Continue VGPT2 v3 training. Current status:

1. SFT COMPLETE - 91% overall, 98% hallucination (see output/validation_sft_baseline.json)
2. DPO v2 FAILED - Caused over-rejection of real tables (see training/MASTER_PLAN.md)
3. NEXT STEP: Run probe test to confirm SFT doesn't reject real tables

Run batch\02_probe_sft.bat and share results. Then decide:
- If probe passes → SFT is ready, skip DPO
- If probe fails → Need targeted fixes

Key files:
- training/MASTER_PLAN.md - Full analysis
- training/GROUND_TRUTH_ANSWERS.md - Expected answers for all 47 tests
- batch/ folder - Double-click .bat files to run tests
```

---

## 📊 Current Results (SFT Baseline)

| Category | Score |
|----------|-------|
| Overall | 91% (45/47 passed) |
| Hallucination | 98% ✅ |
| JOIN | 98% ✅ |
| SQL Generation | 89% |
| Schema | 86% |
| Error Correction | 86% |
| Business Logic | 86% |

---

## 🔄 Decision Tree

```
                    Run Probe Test
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
    Real tables: EXISTS       Real tables: "NOT EXISTS"
    Fake tables: NOT EXISTS   (false rejections)
            │                         │
            ▼                         ▼
    ✅ SHIP SFT MODEL         Need targeted DPO v3
    (Skip DPO entirely)       (Small, balanced dataset)
```

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `saves/vgpt2_v3/sft/` | Trained SFT model (LoRA adapter) |
| `saves/vgpt2_v3/dpo_v2/` | Failed DPO model (DO NOT USE) |
| `output/validation_sft_baseline.json` | SFT test results |
| `training/MASTER_PLAN.md` | Full status and analysis |
| `training/GROUND_TRUTH_ANSWERS.md` | Expected answers |
| `batch/*.bat` | Runnable test scripts |

---

## 🚀 Batch Files to Run

| File | What it does |
|------|--------------|
| `batch\01_validate_sft.bat` | Full validation (47 tests) - DONE |
| `batch\02_probe_sft.bat` | Real vs fake table test - RUN THIS |
| `batch\03_probe_dpo_v2.bat` | Confirm DPO v2 bug (optional) |
| `batch\04_chat_sft.bat` | Interactive chat |

---

## ⚠️ What NOT to Do

1. **DO NOT run DPO v2 model** - It rejects real tables
2. **DO NOT create large DPO datasets** - Caused over-training
3. **DO NOT train hallucination further** - Already at 98%

---

## 📝 If Starting Fresh

1. Read `training/MASTER_PLAN.md` first
2. Check `output/validation_sft_baseline.json` for current scores
3. Run `batch\02_probe_sft.bat` to test real/fake table recognition
4. Share results before making any training decisions

