# VGPT2 v3 Training Pipeline - Deep Dive Critical Review

**Date:** 2025-12-29  
**Status:** Pre-Training Review (Updated after fixes)

---

## Executive Summary

After your initial fixes (KTO format, merged SFT, fail-fast validation), several issues were resolved. However, a deeper analysis reveals **new critical issues** that could significantly impact training effectiveness.

### Issues Fixed ✅
- KTO label format (now string "true"/"false")
- Negatives merged into SFT (60,007 records)
- Validation fail-fast check added

### New Issues Found ⚠️
See detailed sections below.

---

## 1. CRITICAL: Severe NOLOCK Training Imbalance

### The Problem
**Only 1.5% of your SFT data teaches WITH (NOLOCK)** - your most important SQL pattern.

| Metric | Count | Percentage |
|--------|-------|------------|
| Total SFT records | 59,021 | 100% |
| Records with `WITH (NOLOCK)` | 882 | **1.5%** |
| Records with any SQL | 3,360 | 5.7% |

### Why This Matters
- NOLOCK is required in **every** Viewpoint SELECT query
- With only 1.5% of training teaching this, the model won't consistently apply it
- Your validation tests expect NOLOCK in all SQL responses - high failure rate likely

### Root Cause
Looking at `generate_training_data.py`, most generators produce **schema descriptions** (what columns exist, what tables do) rather than **SQL examples**. The SQL generation examples are:
- Hardcoded rules (~20 examples)
- Crystal Report SQL (variable)
- Expert SQL files (limited)

### Fix Required
Add a dedicated SQL pattern generator that creates 5,000-10,000 examples explicitly showing:
```sql
SELECT ... FROM TableName WITH (NOLOCK) WHERE ...
```

---

## 2. CRITICAL: SFT Data is Heavily Schema-Biased

### The Problem
Your SFT data is **85%+ schema descriptions** and **<6% SQL generation**.

| Content Type | Estimated % | Training Focus |
|--------------|-------------|----------------|
| Schema descriptions ("What columns in X?") | ~55% | Knowledge |
| Business context ("What does X do?") | ~30% | Knowledge |
| SQL generation examples | ~6% | **Critical skill** |
| Error correction | ~2% | Important skill |
| JOIN patterns | ~3% | Important skill |
| Negative examples | ~4% | Anti-hallucination |

### Why This Matters
The model will be very good at **describing** schemas but poor at **generating correct SQL**.

### Fix Required
Increase SQL generation examples from ~3,500 to **15,000-20,000** (25-30% of dataset).

---

## 3. HIGH: Output Length Distribution Skewed Short

### The Problem
| Length Bucket | Count | Percentage |
|---------------|-------|------------|
| < 50 chars | 8,623 | **14.6%** |
| 50-200 chars | 24,633 | 41.7% |
| 200-500 chars | 12,118 | 20.5% |
| 500-1000 chars | 7,868 | 13.3% |
| > 1000 chars | 2,806 | 4.8% |

**14.6% of outputs are less than 50 characters** - these are likely too short to be useful.

### Sample Short Outputs (< 50 chars)
These are probably things like:
- "The APTH table is in the AP module."
- "APCo" (just the column name)
- "Yes" / "No" responses

### Fix Required
1. Filter or regenerate outputs < 50 chars
2. Ensure all schema queries include column lists, not just confirmations
3. Add context and explanation to short outputs

---

## 4. HIGH: DPO Preference Signal May Be Too Obvious

### Analysis
| Metric | Chosen | Rejected |
|--------|--------|----------|
| Contains NOLOCK | 1,421 (99.6%) | 349 (24.5%) |
| Average length | Longer | Shorter |

### The Problem
The chosen/rejected pairs have a **very obvious distinguishing feature** (NOLOCK present/absent). The model might learn to just "add NOLOCK" rather than deeply understanding SQL correctness.

### Why This Matters
- DPO works best when the difference is subtle
- If the signal is too obvious, the model doesn't learn nuanced preferences
- May not generalize to other correctness issues (JOINs, company filters, etc.)

### Fix Required
Create more DPO pairs where the difference is:
- Complete vs incomplete JOINs (both have NOLOCK)
- Correct vs incorrect company filtering (both have NOLOCK)
- Proper vs improper column case (both have NOLOCK)
- Real vs hallucinated tables (both have NOLOCK)

---

## 5. MEDIUM: KTO Label Imbalance

### Current Distribution
| Label | Count | Percentage |
|-------|-------|------------|
| true (good) | 934 | 46.3% |
| false (bad) | 1,084 | 53.7% |

### The Issue
This is actually **reasonably balanced** (0.86 ratio), but KTO typically works better with more "true" examples to learn from. A 60/40 or 70/30 split favoring "true" is often recommended.

### Fix (Optional)
Consider generating more "true" examples to shift balance to 60/40.

---

## 6. MEDIUM: Validation Test Suite Coverage Gaps

### Analysis of `run_validation.py`

The test suite has good categories but **limited depth**:

| Category | Claimed Count | Actual Implemented |
|----------|---------------|-------------------|
| Schema tests | "100 questions" | **12 implemented** |
| SQL generation | "150 questions" | **12 implemented** |
| Hallucination | "100 questions" | **10 implemented** |
| JOIN tests | "50 questions" | **5 implemented** |
| Error correction | "50 questions" | **5 implemented** |
| Business logic | "50 questions" | **5 implemented** |
| **TOTAL** | **500 claimed** | **49 actual** |

### The Problem
The test suite claims 500 questions but only has ~49 implemented. The `get_full_suite()` method just returns what's defined in the static methods.

### Fix Required
Either:
1. Implement the missing 450+ test cases
2. Or update documentation to reflect actual count (~50 tests)
3. Consider loading tests from a JSON file for easier expansion

---

## 7. MEDIUM: No Data Shuffling

### The Problem
Looking at the generators, data is generated in sequential order by source:
1. Schema columns (all together)
2. SP documentation (all together)
3. View documentation (all together)
4. etc.

If LLaMA-Factory doesn't shuffle internally, the model will see all similar examples together, leading to:
- Poor generalization
- Catastrophic forgetting of early topics

### Fix Required
Add shuffling before saving:
```python
import random
random.shuffle(all_records)
```

---

## 8. MEDIUM: Missing `input` Field Utilization

### The Problem
Most SFT records have empty `input` fields:
```json
{
  "instruction": "What columns are in APTH?",
  "input": "",  // EMPTY
  "output": "The APTH table contains..."
}
```

### Why This Matters
The `input` field could carry additional context like:
- The user's current SQL attempt (for error correction)
- Schema context for the question
- Company/filter context

### Current Usage
Only error correction examples use `input` (for the wrong SQL to fix).

### Fix (Optional Enhancement)
Consider populating `input` with context for SQL generation questions.

---

## 9. LOW: Hardcoded Generation Limits

### The Problem
Several generators have hardcoded limits or implicit caps:
```python
def generate_extended_schema_examples(self, max_records: Optional[int] = None):
    # Only generates ~4 examples per table
    # With ~1000 tables = ~4000 records max
```

### Impact
Even without `max_records`, generators produce limited output due to internal logic.

### Fix Required
Review each generator's internal limits and expand pattern coverage.

---

## 10. LOW: Negatives Missing Category Metadata

### The Problem
Merged SFT shows:
- Records with refusal language: 1,473
- Records with "negative" category: **0**

The negative examples don't include category metadata, making it impossible to:
- Track their impact during training
- Filter them for analysis
- Ensure proper distribution

### Fix (Optional)
Add category field to negative examples:
```python
{
  "instruction": "...",
  "output": "...",
  "category": "negative_example"  # Add this
}
```

---

## Priority Action Matrix

| Issue | Severity | Effort | Impact | Recommendation |
|-------|----------|--------|--------|----------------|
| 1. NOLOCK training imbalance | CRITICAL | Medium | Very High | **Fix before training** |
| 2. Schema-biased data | CRITICAL | High | Very High | **Fix before training** |
| 3. Short outputs | HIGH | Medium | High | Fix before training |
| 4. DPO too obvious | HIGH | Medium | High | Fix before training |
| 5. KTO imbalance | MEDIUM | Low | Medium | Optional |
| 6. Validation gaps | MEDIUM | High | Medium | Fix after first training |
| 7. No shuffling | MEDIUM | Low | Medium | **Quick fix** |
| 8. Empty input fields | MEDIUM | Medium | Low | Optional |
| 9. Hardcoded limits | LOW | Medium | Low | Future improvement |
| 10. Missing category | LOW | Low | Low | Optional |

---

## Recommended Pre-Training Fixes

### Must Do (Before Training)
1. **Add SQL pattern generator** - Create 10K+ examples with proper NOLOCK usage
2. **Shuffle data** - Add `random.shuffle()` before saving
3. **Filter short outputs** - Remove or regenerate outputs < 50 chars

### Should Do (Before Training)
4. **Diversify DPO pairs** - Add pairs where NOLOCK isn't the only difference
5. **Expand SQL generation** - Increase from 6% to 25% of dataset

### Can Wait (After First Training)
6. Expand validation test suite
7. Add category metadata to negatives
8. Populate input fields with context

---

## Quick Wins (< 30 minutes each)

### 1. Add Shuffling
```python
# In generate_training_data.py, before saving:
import random
random.shuffle(all_records)
```

### 2. Filter Short Outputs
```python
# Filter records with output < 50 chars
filtered = [r for r in records if len(r.get('output', '')) >= 50]
```

### 3. Check NOLOCK Coverage
```python
# Add to validation
nolock_count = sum(1 for r in records if 'WITH (NOLOCK)' in r.get('output', ''))
if nolock_count < len(records) * 0.10:  # Less than 10%
    logger.warning(f"Low NOLOCK coverage: {nolock_count}/{len(records)}")
```

---

## Conclusion

Your pipeline is **structurally sound** but has **content distribution issues** that will likely cause:
1. Inconsistent NOLOCK usage in generated SQL
2. Good schema knowledge but poor SQL generation
3. Validation test failures on SQL correctness

**Recommendation:** Spend 2-4 hours fixing issues 1-5 before starting training. The time investment will significantly improve model quality and reduce iteration cycles.

