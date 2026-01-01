# V4 Training Strategy: Schema-in-Prompt Approach

## Overview

Based on the deep dive analysis, V4 will completely redesign our training approach to match proven SQLCoder methodology.

## Phase 1: New Training Data Generator

### Script: `generate_v4_training_data.py`

```python
"""
Generate V4 training data using schema-in-prompt format.
Each training example includes:
1. A natural language question
2. Relevant DDL (CREATE TABLE statements)
3. Expected SQL output with explanation
"""

TRAINING_CATEGORIES = {
    "ar_aging": {
        "tables": ["ARTH", "ARCM", "ARTL"],
        "questions": [
            "Calculate AR aging buckets (30/60/90) by customer",
            "Find unpaid invoices older than 60 days",
            "Sum outstanding balance by customer group",
        ]
    },
    "sl_costs": {
        "tables": ["SLHD", "SLIT", "APVM", "SLWI"],
        "questions": [
            "Get subcontractor costs with original and change orders",
            "Calculate retainage by SL",
            "Find SLs over budget",
        ]
    },
    # ... more categories
}
```

### Example Training Sample (V4 Format)

```json
{
  "instruction": "Generate a SQL query to answer the following question.\n\nQuestion: Calculate AR aging buckets (30/60/90 days) for unpaid invoices by customer\n\nDatabase Schema:\nCREATE TABLE ARTH (\n  ARCo tinyint NOT NULL,\n  Mth smalldatetime NOT NULL,\n  ARTrans int NOT NULL,\n  ARTransType char(1) NOT NULL,\n  CustGroup tinyint NOT NULL,\n  Customer int NOT NULL,\n  TransDate smalldatetime NULL,\n  PayFullDate smalldatetime NULL,\n  Amount decimal(12,2) NOT NULL,\n  -- AR Transaction Header\n  PRIMARY KEY (ARCo, Mth, ARTrans)\n);\n\nCREATE TABLE ARCM (\n  CustGroup tinyint NOT NULL,\n  Customer int NOT NULL,\n  Name varchar(60) NULL,\n  SortName varchar(20) NULL,\n  -- AR Customer Master\n  PRIMARY KEY (CustGroup, Customer)\n);",
  "input": "",
  "output": "To calculate AR aging buckets for unpaid invoices, we need to:\n1. Use ARTH for transaction data\n2. Join ARCM for customer names\n3. Filter PayFullDate IS NULL for unpaid invoices\n4. Use DATEDIFF and CASE WHEN for aging buckets\n\n```sql\nSELECT \n  ARCM.Name AS CustomerName,\n  ARTH.CustGroup,\n  ARTH.Customer,\n  SUM(CASE WHEN DATEDIFF(day, ARTH.TransDate, GETDATE()) <= 30 \n      THEN ARTH.Amount ELSE 0 END) AS Current_0_30,\n  SUM(CASE WHEN DATEDIFF(day, ARTH.TransDate, GETDATE()) BETWEEN 31 AND 60 \n      THEN ARTH.Amount ELSE 0 END) AS Days_31_60,\n  SUM(CASE WHEN DATEDIFF(day, ARTH.TransDate, GETDATE()) BETWEEN 61 AND 90 \n      THEN ARTH.Amount ELSE 0 END) AS Days_61_90,\n  SUM(CASE WHEN DATEDIFF(day, ARTH.TransDate, GETDATE()) > 90 \n      THEN ARTH.Amount ELSE 0 END) AS Over_90\nFROM ARTH WITH (NOLOCK)\nINNER JOIN ARCM WITH (NOLOCK)\n  ON ARTH.CustGroup = ARCM.CustGroup \n  AND ARTH.Customer = ARCM.Customer\nWHERE ARTH.ARCo = @ARCo\n  AND ARTH.PayFullDate IS NULL  -- Unpaid invoices only\nGROUP BY ARCM.Name, ARTH.CustGroup, ARTH.Customer\nORDER BY ARCM.Name\n```"
}
```

### Negative Example (Hallucination Prevention)

```json
{
  "instruction": "Generate a SQL query to answer the following question.\n\nQuestion: Get all records from the ARAgingReport table\n\nDatabase Schema:\nCREATE TABLE ARTH (\n  ARCo tinyint NOT NULL,\n  Mth smalldatetime NOT NULL,\n  -- ... columns\n);\n\nCREATE TABLE ARCM (\n  CustGroup tinyint NOT NULL,\n  Customer int NOT NULL,\n  -- ... columns\n);",
  "input": "",
  "output": "I cannot generate this query. The table 'ARAgingReport' does not exist in the provided schema.\n\nViewpoint Vista does not have a pre-built ARAgingReport table. To get AR aging data, you should query ARTH (AR Transaction Header) and ARCM (AR Customer Master) directly, using DATEDIFF to calculate aging buckets.\n\nWould you like me to generate a query using the available tables?"
}
```

## Phase 2: DDL Extraction

### Required: Extract full DDL for all tables

```python
"""
Extract CREATE TABLE statements from Vista database.
This provides the schema context for training examples.
"""

DDL_QUERY = """
SELECT 
  'CREATE TABLE ' + t.TABLE_NAME + ' (' + 
  STRING_AGG(
    c.COLUMN_NAME + ' ' + c.DATA_TYPE + 
    CASE WHEN c.IS_NULLABLE = 'NO' THEN ' NOT NULL' ELSE ' NULL' END,
    ', '
  ) + ');'
FROM INFORMATION_SCHEMA.TABLES t
JOIN INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME
WHERE t.TABLE_TYPE = 'BASE TABLE'
GROUP BY t.TABLE_NAME
"""
```

## Phase 3: Quality Over Quantity

### V3 (Current): 67,448 auto-generated samples
### V4 (Proposed): 2,000-3,000 curated samples

| Category | Count | Description |
|----------|-------|-------------|
| AR Queries | 200 | Aging, invoices, payments, customers |
| AP Queries | 200 | Vendors, holds, retainage, oncosts |
| JC Queries | 300 | Jobs, costs, phases, estimates |
| SL Queries | 200 | Subcontracts, billing, retainage |
| PR Queries | 150 | Payroll, timecards, deductions |
| GL Queries | 150 | Ledger, accounts, balances |
| Cross-Module | 300 | Multi-module joins |
| Negative Examples | 300 | Fake tables → rejection |
| Edge Cases | 200 | Complex joins, CTEs, aggregations |

## Phase 4: Evaluation Redesign

### New Test Format

```json
{
  "id": "test_001",
  "question": "Calculate AR aging buckets by customer",
  "schema_context": "CREATE TABLE ARTH...\nCREATE TABLE ARCM...",
  "expected_output": "SQL query with proper joins and filters",
  "evaluation_criteria": {
    "tables_used": ["ARTH", "ARCM"],
    "joins_correct": ["ARTH.CustGroup = ARCM.CustGroup"],
    "filters_present": ["PayFullDate IS NULL"],
    "aggregations": ["GROUP BY customer"],
    "vista_patterns": ["WITH (NOLOCK)", "Co = @Co"]
  }
}
```

## Timeline

### Week 1: Data Generation
- [ ] Extract DDL for all Vista tables
- [ ] Write V4 training data generator
- [ ] Create 500 seed examples manually

### Week 2: Training Data Completion
- [ ] Generate 2,000+ total examples
- [ ] Add 300 negative examples
- [ ] Review and validate quality

### Week 3: Training
- [ ] SFT with new V4 dataset
- [ ] Evaluate on complex questions
- [ ] Compare with V3 results

### Week 4: Refinement
- [ ] Analyze failures
- [ ] Add targeted examples for weak areas
- [ ] Consider DPO if SFT succeeds (>70% target)

## Success Criteria

| Metric | V3 (Current) | V4 (Target) |
|--------|--------------|-------------|
| Overall Score | 40% | >70% |
| Complex SQL | 39% | >65% |
| Business Logic | 42% | >70% |
| Cross-Module | 58% | >80% |
| Hallucination Detection | 10% | >90% |

## Key Insights from SQLCoder

1. **20,000 examples** was enough for state-of-the-art SQL generation
2. **Human curation** > auto-generation
3. **Schema in prompt** = model reads context, doesn't memorize
4. **Consistent format** = model learns the pattern

## Appendix: Table Coverage Priority

### High Priority (Most Common Queries)
- ARTH, ARTL, ARCM - AR
- APTH, APTL, APTD, APVM - AP
- JCCD, JCCP, JCJP, JCJM - JC
- SLHD, SLIT, SLWI - SL
- PRTH, PRPC, PREH - PR
- GLDT, GLJR - GL

### Medium Priority (Joins and References)
- APCO, ARCO, JCCO - Company settings
- HQCO - HQ Company
- HQLC - Locations

### Low Priority (Less Frequent)
- Audit tables
- Lookup tables
- System tables

---
*Created: 2025-06-26*
*Status: Ready for Implementation*
