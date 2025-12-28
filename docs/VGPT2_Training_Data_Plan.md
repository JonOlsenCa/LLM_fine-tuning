# VGPT2 Training Data Comprehensive Plan

**Version:** 2.1
**Date:** 2025-12-28
**Status:** ✅ COMPLETE - 23,742 records generated

---

## Executive Summary

The initial VGPT2 fine-tuning (v1) achieved basic Vista SQL awareness but failed on complex queries requiring:
- Proper use of reporting views (`brvJCCostRevenue`, `vrvJCCommittedCost`)
- WITH (NOLOCK) conventions
- Complex multi-table cost/revenue joins

**Root Cause:** Critical data sources were inventoried but never used for training data generation.

---

## 1. Data Source Inventory

### 1.1 VGPT2 Repository (`C:\Github\VGPT2`)

| Source | Files | Size | JSON | MD | SQL | Status |
|--------|-------|------|------|----|----|--------|
| **_Metadata** | 48 | 180MB | 17 | 5 | 0 | ✅ USED |
| **Stored_Procedures** | 28,334 | 162MB | 7,044 | 7,052 | 14,224 | ✅ USED |
| **View** | 10,285 | 20MB | 798 | 2,366 | 7,074 | ✅ USED |
| **_Relationship_Validation** | 861 | 1MB | 851 | 9 | 0 | ✅ USED |
| **Tables** | 3,552 | 10MB | 3 | 1,614 | 1,908 | ❌ NOT USED |
| **Crystal_Reports_SQL** | 2,454 | 3MB | 0 | 2 | 2,434 | ❌ NOT USED |
| **_ai_orchestration** | 54 | 1.3MB | 5 | 32 | 1 | ❌ NOT USED |
| **Experts/04_Experts** | 2,140 | 47MB | 120 | 824 | 472 | ⚠️ PARTIAL |
| **Experts_V2** | 1,170 | 24MB | 76 | 275 | 436 | ❌ NOT USED |
| **Functions** | 2,667 | 12MB | 3 | 1,067 | 1,587 | ❌ NOT USED |
| **Triggers** | 9,992 | 51MB | 2 | 2,503 | 7,479 | ❌ NOT USED |
| **Indexes** | 7,007 | 15MB | 2 | 3,462 | 3,531 | ❌ NOT USED |
| **_ERD** | 31 | 16MB | 5 | 14 | 1 | ❌ NOT USED |
| **SQL_Generator** | 99 | 21MB | 1 | 29 | 14 | ❌ NOT USED |

### 1.2 Vista Knowledge Base (`C:\Github\Vista_KB`)

| Source | Files | Size | Notes |
|--------|-------|------|-------|
| **web_content** | 6,268 | 2.4GB | Trimble help articles |
| **extracted_content** | 289 | 1.1MB | Processed articles |

### 1.3 Current Training Data Distribution (v2.1 - FINAL)

| Category | Count | % |
|----------|-------|---|
| Schema Metadata | 7,898 | 33% |
| SP Documentation | 7,040 | 30% |
| View Documentation | 2,350 | 10% |
| SQL Generation | 2,018 | 8% |
| DDFI Forms | 1,692 | 7% |
| Crystal Report SQL | 1,217 | 5% |
| JOIN Patterns | 1,033 | 4% |
| Experts V2 | 405 | 2% |
| Canonical Rules | 26 | <1% |
| Naming Conventions | 26 | <1% |
| Reference Documents | 16 | <1% |
| Error Corrections | 8 | <1% |
| Query Optimization | 5 | <1% |
| Heuristics | 4 | <1% |
| Workflows | 4 | <1% |
| **TOTAL** | **23,742** | 100% |

---

## 2. Critical Gaps Identified

### 2.1 Missing Data Sources

| Gap | Impact | Source Location | Est. Records |
|-----|--------|-----------------|--------------|
| **Crystal Report SQL** | Can't suggest `brvJCCostRevenue` | `Crystal_Reports_Documentation/_Extracted_SQL/` | 2,400+ |
| **Canonical SQL Rules** | Doesn't enforce WITH (NOLOCK) | `_ai_orchestration/rules/RULE_CanonicalSQL.md` | 50+ |
| **Reference Docs** | Missing batch processing, groups, etc. | `_ai_orchestration/reference/` | 200+ |
| **Heuristics** | No composite key discovery | `_ai_orchestration/heuristics/` | 100+ |
| **Workflows** | No SQL generation workflow | `_ai_orchestration/workflows/` | 50+ |
| **Experts_V2 SQL** | Validated expert queries | `Experts_V2/*/` | 500+ |
| **Table Documentation** | Missing table-level docs | `Viewpoint_Database/Tables/` | 1,600+ |
| **Function Documentation** | UDF reference missing | `Viewpoint_Database/Functions/` | 1,000+ |

### 2.2 Missing Question Types

| Question Type | Example | Current Count |
|---------------|---------|---------------|
| Cost/Revenue Analysis | "Query for daily job profit" | 0 |
| Report View Selection | "Which vrv* view for AP aging?" | ~10 |
| Multi-table Aggregation | "Total committed cost by phase" | ~20 |
| WITH (NOLOCK) Usage | "Why use NOLOCK?" | ~5 |
| Base vs View Tables | "When to use bAPTH vs APTH?" | ~5 |
| Batch Processing | "How does AP batch posting work?" | 0 |
| Groups Concept | "What is VendorGroup?" | ~3 |

---

## 3. Proposed Data Generation Strategy

### 3.1 Tier 1: Critical (Must Have)

**Priority: IMMEDIATE**

#### 3.1.1 Crystal Report SQL Examples
- Source: `_Extracted_SQL/Raw/*.sql` and `_Extracted_SQL/Reformatted/*.sql`
- Generation: Parse SQL, extract table names, create Q&A pairs
- Example Q: "How do I get job cost and revenue by contract item?"
- Example A: "Use the brvJCCostRevenue view: `SELECT * FROM brvJCCostRevenue WITH (NOLOCK) WHERE JCCo = @JCCo`"
- Est. Records: 1,200 (one per unique report)

#### 3.1.2 Canonical Rules Training
- Source: `_ai_orchestration/rules/RULE_CanonicalSQL.md`
- Generation: Extract each rule as Q&A + wrong/right examples
- Example Q: "Should I use table aliases in Viewpoint queries?"
- Example A: "No. Viewpoint standards prohibit aliases. Use full table names..."
- Est. Records: 100+

#### 3.1.3 Reference Documents
- Source: `_ai_orchestration/reference/*.md`
- Key docs:
  - `ViewpointBatchProcessing.md` - Batch table patterns
  - `ViewpointCompanyColumns.md` - Company column joins
  - `ViewpointGroups.md` - VendorGroup, CustGroup, etc.
  - `ViewpointMonthHandling.md` - Mth column usage
  - `ViewpointKeyIDPatterns.md` - KeyID joins
- Est. Records: 200+

### 3.2 Tier 2: Important (Should Have)

**Priority: HIGH**

#### 3.2.1 Experts_V2 Validated SQL
- Source: `Experts_V2/04_approved/*.sql`
- These are production-validated queries
- Est. Records: 400+

#### 3.2.2 Heuristics Documentation
- Source: `_ai_orchestration/heuristics/*.md`
- Key docs:
  - `HE_CompositeKeyDiscovery.md` - Finding correct JOINs
  - `HE_CSVToSQL.md` - Query construction patterns
  - `HE_SQLObjectVerification.md` - Validating SQL objects
- Est. Records: 150+

#### 3.2.3 Workflow Documentation
- Source: `_ai_orchestration/workflows/*.md`
- Key docs:
  - `WF_SQLGeneration.md` - End-to-end SQL generation process
  - `WF_QuestionAnswering.md` - How to answer Vista questions
- Est. Records: 100+

### 3.3 Tier 3: Valuable (Nice to Have)

**Priority: MEDIUM**

#### 3.3.1 Function Documentation
- Source: `Viewpoint_Database/Functions/`
- 1,067 markdown files with UDF documentation
- Est. Records: 500+

#### 3.3.2 Table Documentation
- Source: `Viewpoint_Database/Tables/`
- 1,614 markdown files
- Est. Records: 800+

#### 3.3.3 Vista KB Articles
- Source: `Vista_KB/data/web_content/`
- Business workflow context
- Est. Records: 1,000+ (curated)

### 3.4 Tier 4: Excluded

**Do NOT include:**

| Source | Reason |
|--------|--------|
| `_archive/` folders | Outdated content |
| `Legacy_ERD_Diagrams/` | Superseded by `_ERD` |
| `Triggers/` | Too low-level, rarely queried |
| `Indexes/` | Internal optimization, not user-facing |
| Raw SP SQL files | Already covered by SP documentation |

---

## 4. Data Generation Implementation

### 4.1 New Generators Required

```python
# Add to generate_vgpt2_training_data.py

def generate_crystal_report_examples()    # NEW
def generate_canonical_rules_examples()   # NEW
def generate_reference_doc_examples()     # NEW
def generate_heuristic_examples()         # NEW
def generate_workflow_examples()          # NEW
def generate_experts_v2_examples()        # NEW
def generate_function_examples()          # NEW
def generate_table_doc_examples()         # NEW
```

### 4.2 Question Type Templates

#### Crystal Reports
```
Q: "What view should I use for {report_purpose}?"
Q: "How do I query {business_metric} in Vista?"
Q: "Write a query similar to the {report_name} Crystal Report"
```

#### Canonical Rules
```
Q: "What is wrong with this query: {bad_sql}"
Q: "How should I {sql_operation} in Viewpoint?"
Q: "Why does my query return 'Invalid column name'?"
```

#### Reference Docs
```
Q: "How does {concept} work in Viewpoint?"
Q: "What is the purpose of {column/table}?"
Q: "How do I handle {pattern} in Vista SQL?"
```

### 4.3 Quality Controls

| Check | Implementation |
|-------|----------------|
| **SQL Syntax Validation** | SQLFluff lint on all generated SQL |
| **Column Name Verification** | Cross-check against `columns.json` |
| **Table Name Verification** | Cross-check against `_Viewpoint_ALL_Views_Tables_Complete.json` |
| **Duplicate Detection** | Hash-based dedup on Q+A pairs |
| **Length Validation** | Ensure answers aren't truncated |

---

## 5. Training Configuration Updates

### 5.1 System Prompt (Required)

```
You are VGPT, an expert SQL assistant for Viewpoint Vista construction ERP database.

Key conventions:
- Use views (APTH) not base tables (bAPTH) for SELECT queries
- Always add WITH (NOLOCK) after table names
- Filter by company columns (APCo, JCCo, PRCo, etc.)
- Use exact column name case (APCo not apco)
- Check for vrv*/brv* reporting views before writing custom SQL
- No table aliases - use full table names
- Viewpoint uses Latin1_General_BIN (case-sensitive)

Table naming:
- bXXXX = base table (for INSERT/UPDATE/DELETE)
- XXXX = view (for SELECT queries)
- vrv* = Viewpoint Report Views
- brv* = Batch Report Views

Always use WITH (NOLOCK) for read queries to prevent blocking.
```

### 5.2 Training Hyperparameters

| Parameter | Current | Proposed | Rationale |
|-----------|---------|----------|-----------|
| `num_train_epochs` | 3 | 5 | More epochs for larger dataset |
| `lora_rank` | 64 | 128 | Higher rank for more knowledge |
| `learning_rate` | 2e-4 | 1e-4 | Lower LR for stability |
| `cutoff_len` | 2048 | 4096 | Longer SQL queries |
| `max_samples` | 50000 | 100000 | Larger dataset |

---

## 6. Validation Plan

### 6.1 Test Questions (Must Pass)

| # | Question | Expected Behavior |
|---|----------|-------------------|
| 1 | "Write a query for daily job profit" | Uses `brvJCCostRevenue` or similar |
| 2 | "Difference between bAPTH and APTH" | Explains base table vs view |
| 3 | "Get unpaid AP invoices over $10K" | Uses APTH WITH (NOLOCK), APCo filter |
| 4 | "How to join APTH to vendors" | Uses VendorGroup+Vendor, not APCo |
| 5 | "What is VendorGroup?" | Explains shared master data concept |
| 6 | "Committed cost by phase" | Uses vrvJCCommittedCost or correct JCCD pattern |

### 6.2 Anti-Patterns (Must NOT Do)

| # | Anti-Pattern | Test Query |
|---|--------------|------------|
| 1 | Generic SQL | Should not return `SELECT * FROM invoices` |
| 2 | Wrong column names | Should not hallucinate `JCCD.Revenue` |
| 3 | Missing NOLOCK | All SELECT queries must have WITH (NOLOCK) |
| 4 | Table aliases | Should not use `FROM APTH a` |
| 5 | Case errors | Should not use `apco` or `APCO` |

---

## 7. Implementation Timeline

| Phase | Task | Est. Hours |
|-------|------|------------|
| 1 | Update `generate_vgpt2_training_data.py` | 4 |
| 2 | Generate new training data | 1 |
| 3 | Validate generated data | 2 |
| 4 | Run training (5 epochs) | 4 |
| 5 | Test with validation questions | 1 |
| 6 | Iterate if needed | 2-4 |
| **TOTAL** | | **14-16 hours** |

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| Training samples | 40,000+ |
| Test questions pass rate | 100% (6/6) |
| Anti-pattern violations | 0 |
| Eval loss | < 0.9 |
| Real-world query accuracy | > 80% |

---

## Appendix A: _ai_orchestration Contents (Critical Gap)

### Rules (MUST INCLUDE)
| File | Size | Purpose |
|------|------|---------|
| `RULE_CanonicalSQL.md` | 10.6KB | SQL formatting standards, WITH (NOLOCK), no aliases |
| `RULE_Safety.md` | 2.2KB | Safety guidelines for SQL generation |

### Reference Documents (MUST INCLUDE)
| File | Size | Purpose |
|------|------|---------|
| `ViewpointBatchProcessing.md` | 9.8KB | How batch tables work (AP, PR, etc.) |
| `ViewpointCompanyColumns.md` | 2.6KB | Company column patterns and joins |
| `ViewpointGroups.md` | 5.4KB | VendorGroup, CustGroup, etc. |
| `ViewpointKeyIDPatterns.md` | 5.1KB | KeyID-based joins |
| `ViewpointMonthHandling.md` | 3.0KB | Mth column usage patterns |
| `ViewpointSoftDeletes.md` | 4.3KB | Soft delete patterns |
| `ViewpointStatusCodes.md` | 5.4KB | Status code meanings |
| `ViewpointUDFields.md` | 4.1KB | User-defined field patterns |
| `ViewpointVASecurity.md` | 5.2KB | VA security integration |
| `ViewpointCustomImportArchitecture.md` | 4.1KB | Custom import patterns |

### Heuristics (SHOULD INCLUDE)
| File | Size | Purpose |
|------|------|---------|
| `HE_CompositeKeyDiscovery.md` | 4.9KB | Finding correct composite keys |
| `HE_CSVToSQL.md` | 21.4KB | Converting questions to SQL |
| `HE_DocumentationPlacement.md` | 4.5KB | Where to find docs |
| `HE_ResourceSelection.md` | 5.5KB | Which resource to use |
| `HE_SQLObjectVerification.md` | 5.4KB | Verifying SQL objects exist |

### Workflows (SHOULD INCLUDE)
| File | Size | Purpose |
|------|------|---------|
| `WF_SQLGeneration.md` | 22.8KB | Complete SQL generation process |
| `WF_QuestionAnswering.md` | 5.5KB | Q&A process |
| `WF_ExpertCreation.md` | 8.1KB | Expert SQL creation |
| `WF_CrystalReportSearch.md` | 6.8KB | Finding Crystal Report SQL |

### Capabilities (REFERENCE ONLY)
| File | Size | Purpose |
|------|------|---------|
| `CAP_AnswerQuestion.md` | 2.1KB | Question answering capability |
| `CAP_CreateExpert.md` | 2.6KB | Expert creation capability |
| `CAP_GenerateSQL.md` | 2.3KB | SQL generation capability |
| `CAP_ValidateSQL.md` | 2.7KB | SQL validation capability |

### GL Subledger Reconciliation (SPECIALIZED)
| File | Size | Purpose |
|------|------|---------|
| `ViewpointSubledgerGLMapping.md` | 10.7KB | GL to subledger mapping |
| `ViewpointSubledgerGLMapping_Supplement.md` | 12.8KB | Additional mappings |
| `EXPERT_ANALYSIS_SubledgerToGL.md` | 11.7KB | Analysis documentation |

---

## Appendix B: File Counts by Source

```
VGPT2 Repository Summary:
├── Viewpoint_Database/
│   ├── _Metadata/           48 files (180MB) - columns, DDFI, foreign keys
│   ├── Stored_Procedures/   28,334 files (162MB) - 7,044 SP docs
│   ├── View/                10,285 files (20MB) - 2,366 view docs
│   ├── Tables/              3,552 files (10MB) - table docs
│   ├── Functions/           2,667 files (12MB) - UDF docs
│   ├── Triggers/            9,992 files (51MB) - trigger docs
│   ├── Indexes/             7,007 files (15MB) - index docs
│   ├── _Relationship_Validation/  861 files (1MB) - JOIN recipes
│   └── _ERD/                31 files (16MB) - entity diagrams
├── Crystal_Reports_Documentation/
│   └── _Extracted_SQL/      2,454 files (3MB) - production SQL
├── _ai_orchestration/       54 files (1.3MB) - rules, heuristics
├── Experts/04_Experts/      2,140 files (47MB) - validated experts
└── Experts_V2/              1,170 files (24MB) - v2 experts

Vista_KB:
└── data/web_content/        6,268 files (2.4GB) - help articles
```

---

## Appendix C: Current vs Target Training Distribution

| Category | Current | Target | Change |
|----------|---------|--------|--------|
| SP Documentation | 6,134 (32%) | 6,134 (15%) | - |
| Schema Queries | 3,649 (19%) | 4,000 (10%) | +351 |
| Crystal Report SQL | 0 (0%) | 2,400 (6%) | +2,400 |
| Canonical Rules | ~50 (0.3%) | 500 (1.2%) | +450 |
| Reference Docs | 0 (0%) | 400 (1%) | +400 |
| Expert SQL (V2) | 0 (0%) | 800 (2%) | +800 |
| JOIN Patterns | 799 (4%) | 1,500 (4%) | +701 |
| SQL Generation | 1,714 (9%) | 3,000 (7.5%) | +1,286 |
| View Purpose | 1,681 (9%) | 2,000 (5%) | +319 |
| DDFI Forms | 1,519 (8%) | 1,519 (4%) | - |
| Error Correction | ~50 (0.3%) | 500 (1.2%) | +450 |
| Query Optimization | 49 (0.3%) | 300 (0.7%) | +251 |
| Function Docs | 0 (0%) | 800 (2%) | +800 |
| Table Docs | 0 (0%) | 1,000 (2.5%) | +1,000 |
| Business Context | 3,487 (18%) | 5,000 (12.5%) | +1,513 |
| Heuristics/Workflows | 0 (0%) | 500 (1.2%) | +500 |
| Vista KB Articles | 0 (0%) | 2,000 (5%) | +2,000 |
| **TOTAL** | **19,132** | **~40,000** | **+20,868** |

---

## Appendix D: Detailed Metadata Files

### columns.json (29.96MB)
Contains all 167,000+ column definitions with:
- Table/View name
- Column name, data type, nullable
- Default values
- Column ordinal position

### DDFI.json (45.45MB)
Data Dictionary Form Items - business context for UI fields:
- Form name and tab
- Field labels and descriptions
- Validation rules
- Related tables/columns

### foreign_keys.json (0.65MB)
Foreign key relationships:
- Parent/child table pairs
- Key columns
- Relationship cardinality

### DDFH.json (9.12MB)
Data Dictionary Form Headers:
- Form names and titles
- Module associations
- Form descriptions

---

## Appendix E: Crystal Reports SQL Structure

Location: `Crystal_Reports_Documentation/_Extracted_SQL/`

```
_Extracted_SQL/
├── Raw/           # 1,219 .sql files - original extracted SQL
├── Reformatted/   # 1,219 .sql files - formatted for readability
├── Validated/     # 2 .md files - validation results
└── _scripts/      # 11 files - extraction/validation scripts
```

### Key Patterns in Crystal Report SQL
1. **Reporting Views:** Heavy use of `brvJC*`, `vrvJC*`, `brvAP*`, etc.
2. **UNION queries:** Many reports combine multiple sources
3. **Date filtering:** `WHERE Mth BETWEEN @StartMth AND @EndMth`
4. **Company filtering:** Always filter by company columns
5. **Aggregate queries:** SUM, AVG, COUNT with GROUP BY

---

## Appendix F: Implementation Checklist

### Phase 1: Generator Updates ✅ COMPLETE
- [x] Add `generate_crystal_report_examples()` function
- [x] Add `generate_canonical_rules_examples()` function
- [x] Add `generate_reference_doc_examples()` function
- [x] Add `generate_heuristic_examples()` function
- [x] Add `generate_workflow_examples()` function
- [x] Add `generate_experts_v2_examples()` function
- [x] Update `generate_all()` to call new generators
- [x] Add `training_data_validation.py` with pre-flight checks
- [x] Add source-to-generator mapping with enforcement

### Phase 2: Data Quality ✅ COMPLETE
- [x] Implement validation report with pass/fail status
- [x] Add minimum record thresholds per source
- [x] Add abort_on_failure option for CI/CD
- [ ] TODO: Implement SQL syntax validation with SQLFluff
- [ ] TODO: Add column name verification against `columns.json`

### Phase 3: Training (PENDING)
- [ ] Update system prompt in training config
- [ ] Adjust hyperparameters (epochs, rank, LR)
- [x] Generate new dataset: `output/vgpt2_training_data.json`
- [ ] Run training
- [ ] Evaluate on test questions

### Phase 4: Validation (PENDING)
- [ ] Test all 6 critical questions
- [ ] Verify no anti-patterns
- [ ] Deploy to production
- [ ] Monitor real-world accuracy

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-27 | Initial training data generation |
| 2.0 | 2025-12-28 | Identified gaps, comprehensive plan |
| 2.1 | 2025-12-28 | ✅ All 6 generators implemented, 23,742 records generated |

