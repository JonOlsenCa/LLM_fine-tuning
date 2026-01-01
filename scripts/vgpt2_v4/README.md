# VGPT2 V4 Training Data Generation

## Overview

V4 is a complete redesign of the training data generation approach, based on the proven **SQLCoder methodology**. The key insight is that successful SQL fine-tuning requires **schema-in-prompt** training rather than schema memorization.

## Why V4?

### V3 Results (Failed Approach)
- **67,448 auto-generated examples** → 40% accuracy
- Training data: "What columns in ARTH?" → column list
- Model memorizes facts, doesn't learn SQL generation
- DPO made things worse (37.7% from 40.1%)
- Hallucination detection: only 10%

### V4 Approach (SQLCoder Methodology)
- **~2,500 curated examples** → target 70%+ accuracy
- Training data: Question + DDL → SQL with explanation
- Model learns to READ schema and GENERATE SQL
- Proper negative examples for hallucination prevention
- Schema provided at inference time (no memorization required)

## Architecture

```
scripts/vgpt2_v4/
├── __init__.py           # Package exports
├── config.py             # Configuration management
├── ddl_extractor.py      # Extract CREATE TABLE from metadata
├── sql_generator.py      # Generate SQL training examples
├── negative_generator.py # Hallucination prevention examples
├── pipeline.py           # Main orchestration
├── evaluation.py         # V4 evaluation framework
├── run_pipeline.py       # CLI entry point
└── README.md             # This file
```

## Quick Start

### 1. Generate Training Data

```bash
# From project root
python scripts/vgpt2_v4/run_pipeline.py --vgpt2-path C:/Github/VGPT2

# Or with custom output
python scripts/vgpt2_v4/run_pipeline.py \
    --vgpt2-path C:/Github/VGPT2 \
    --output data/vgpt2_v4_sft.json
```

### 2. Generate Default Config

```bash
python scripts/vgpt2_v4/run_pipeline.py --save-config config/v4_config.yaml
```

### 3. Run with Custom Config

```bash
python scripts/vgpt2_v4/run_pipeline.py --config config/v4_config.yaml
```

## Training Data Format

### V3 Format (Old - Don't Use)
```json
{
  "instruction": "What columns are in the ARTH table?",
  "input": "",
  "output": "The ARTH table contains: ARCo, Mth, ARTrans..."
}
```

### V4 Format (New - Schema-in-Prompt)
```json
{
  "instruction": "Generate a SQL query to answer the following question.\n\nQuestion: Calculate AR aging buckets by customer\n\nDatabase Schema:\nCREATE TABLE ARTH (\n  ARCo tinyint NOT NULL,\n  Mth datetime NOT NULL,\n  Customer int NOT NULL,\n  PayFullDate datetime NULL,\n  Amount decimal(12,2) NOT NULL\n);\n\nCREATE TABLE ARCM (\n  CustGroup tinyint NOT NULL,\n  Customer int NOT NULL,\n  Name varchar(60) NULL\n);",
  "input": "",
  "output": "To calculate AR aging buckets:\n1. Join ARTH to ARCM for customer names\n2. Filter PayFullDate IS NULL for unpaid\n3. Use DATEDIFF and CASE WHEN for buckets\n\n```sql\nSELECT \n  ARCM.Name,\n  SUM(CASE WHEN DATEDIFF(day, ARTH.TransDate, GETDATE()) <= 30 THEN Amount ELSE 0 END) AS Current\n  -- etc.\nFROM ARTH WITH (NOLOCK)\nINNER JOIN ARCM WITH (NOLOCK) ON ARTH.Customer = ARCM.Customer\nWHERE ARTH.PayFullDate IS NULL\nGROUP BY ARCM.Name\n```"
}
```

### Negative Example (Hallucination Prevention)
```json
{
  "instruction": "Generate a SQL query...\n\nQuestion: Get all records from the Customers table\n\nDatabase Schema:\nCREATE TABLE ARCM (...);\n...",
  "input": "",
  "output": "I cannot generate this query. The table 'Customers' does not exist in Viewpoint Vista.\n\nUse ARCM (AR Customer Master) for customer information.\n\n```sql\nSELECT * FROM ARCM WITH (NOLOCK) WHERE Co = @Co\n```"
}
```

## Configuration

The pipeline is configured via YAML:

```yaml
vgpt2_path: "C:/Github/VGPT2"
output_path: "data/vgpt2_v4_sft.json"

total_target_examples: 2500
negative_example_ratio: 0.12  # 12% rejection examples

include_explanations: true
include_vista_patterns: true  # WITH (NOLOCK), Co = @Co

categories:
  ar_queries:
    description: "Accounts Receivable queries"
    primary_tables: ["ARTH", "ARTL", "ARCM"]
    target_count: 200
  # ... more categories

tables:
  ARTH:
    module: "AR"
    description: "AR Transaction Header"
    key_columns: ["ARCo", "Mth", "ARTrans"]
    common_joins: ["ARTL", "ARCM"]
  # ... more tables
```

## Modules

### DDLExtractor
Extracts CREATE TABLE statements from VGPT2 metadata:
```python
from vgpt2_v4 import DDLExtractor

extractor = DDLExtractor("C:/Github/VGPT2")
extractor.load_all()

# Get DDL for specific tables
ddl = extractor.get_ddl(["ARTH", "ARCM"])
print(ddl)
```

### SQLExampleGenerator
Generates SQL training examples:
```python
from vgpt2_v4 import V4Config, SQLExampleGenerator

config = V4Config.get_default()
generator = SQLExampleGenerator(config, extractor)
examples = generator.generate_all()
```

### NegativeExampleGenerator
Generates hallucination prevention examples:
```python
from vgpt2_v4 import NegativeExampleGenerator

neg_gen = NegativeExampleGenerator(config, extractor)
negative_examples = neg_gen.generate_all()
```

### V4Pipeline
Complete orchestration:
```python
from vgpt2_v4 import V4Pipeline

pipeline = V4Pipeline(vgpt2_path="C:/Github/VGPT2")
examples = pipeline.run()
print(f"Generated {len(examples)} examples")
```

## Training Category Distribution

| Category | Target Count | Description |
|----------|-------------|-------------|
| AR Queries | 200 | Customers, invoices, aging, payments |
| AP Queries | 200 | Vendors, invoices, holds, retainage |
| JC Queries | 300 | Jobs, phases, costs, estimates |
| SL Queries | 200 | Subcontracts, billing, retainage |
| PR Queries | 150 | Employees, timecards, earnings |
| GL Queries | 150 | Accounts, transactions, balances |
| Cross-Module | 300 | Multi-module join scenarios |
| Negative | 300 | Hallucination prevention |
| Edge Cases | 200 | CTEs, window functions, complex |

**Total: ~2,000 examples**

## Evaluation

V4 includes a new evaluation framework that tests with schema-in-prompt:

```python
from vgpt2_v4.evaluation import V4Evaluator

evaluator = V4Evaluator(ddl_extractor, model_fn)
evaluator.load_questions("training/v4_eval_questions.json")
summary = evaluator.evaluate_all(model_name="V4 SFT")
evaluator.print_summary(summary)
```

## Success Metrics

| Metric | V3 (Current) | V4 (Target) |
|--------|--------------|-------------|
| Overall Score | 40% | >70% |
| Complex SQL | 39% | >65% |
| Business Logic | 42% | >70% |
| Cross-Module | 58% | >80% |
| Hallucination Detection | 10% | >90% |

## Why This Will Work

1. **SQLCoder proved it**: 20K examples → beats GPT-4 on SQL
2. **Quality over quantity**: Curated > auto-generated
3. **Schema-in-prompt**: Read context, don't memorize
4. **Proper negatives**: Learn to reject invalid tables
5. **Task-aligned**: Train SQL generation, not trivia

## Next Steps After Generation

1. **Generate V4 training data**:
   ```bash
   python scripts/vgpt2_v4/run_pipeline.py
   ```

2. **Train SFT model**:
   ```bash
   llamafactory-cli train examples/train_lora/vgpt2_v4_sft.yaml
   ```

3. **Evaluate**:
   ```bash
   python scripts/vgpt2_v4/evaluate.py --model saves/vgpt2_v4/sft
   ```

4. **Compare with V3**:
   ```bash
   python scripts/vgpt2_v3/compare_models.py --v3 saves/vgpt2_v3/sft --v4 saves/vgpt2_v4/sft
   ```

## Troubleshooting

### "VGPT2 path does not exist"
Set the environment variable or pass the path:
```bash
export VGPT2_PATH=C:/Github/VGPT2
python scripts/vgpt2_v4/run_pipeline.py
```

### "columns.json not found"
Make sure your VGPT2 repository has the `Viewpoint_Database/_Metadata/` directory with metadata files.

### Low example count
Check that the DDL extractor loaded tables correctly:
```python
extractor = DDLExtractor("C:/Github/VGPT2")
extractor.load_all()
print(f"Loaded {len(extractor.get_all_table_names())} tables")
```

## References

- [SQLCoder Methodology](https://github.com/defog-ai/sqlcoder)
- [Deep Dive Analysis](../../docs/DEEP_DIVE_ANALYSIS.md)
- [V4 Training Strategy](../../docs/V4_TRAINING_STRATEGY.md)
