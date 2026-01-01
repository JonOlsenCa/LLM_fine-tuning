# Deep Dive Analysis: Why Our Fine-Tuning Approach Isn't Working

## Executive Summary

**Our current approach is fundamentally flawed.** We're training the model the wrong way. Here's why:

| Aspect | SQLCoder (Works) | Our Approach (Doesn't Work) |
|--------|------------------|------------------------------|
| **Training Data Quality** | 20,000 **human-curated** questions | 67,448 **auto-generated** questions |
| **Training Data Format** | Question → SQL with schema context | "What columns in X?" → column list |
| **Prompt Structure** | Schema included in EVERY prompt | Schema trained as facts, not in prompts |
| **Training Goal** | Teach SQL generation patterns | Teach schema memorization |
| **Test Expectations** | Generate SQL from schema context | Generate SQL from memory |

## The Core Problem: We're Training Wrong

### What SQLCoder Does (The Right Way)

```
PROMPT FORMAT:
Generate a SQL query to answer: {user_question}

DDL statements:
CREATE TABLE ARTH (
  ARCo int,
  Mth datetime,
  CustGroup int,
  Customer int,
  PayFullDate datetime,
  ...
)

CREATE TABLE ARCM (
  CustGroup int,
  Customer int,
  Name varchar,
  ...
)

ANSWER:
```sql
SELECT ...
```

The model is trained to:
1. **Read the schema from the prompt** (not from memory)
2. **Generate appropriate SQL** based on the schema provided
3. **Reject requests for tables not in the provided schema**

### What We're Doing (The Wrong Way)

```json
{
  "instruction": "What columns are in the ARTH table?",
  "input": "",
  "output": "The ARTH table (Module: AR) contains: ARCo, Mth, CustGroup..."
}
```

We're training the model to:
1. **Memorize column lists** (not generate SQL)
2. **Recall from memory** (not read from context)
3. **Answer trivia questions** (not solve SQL problems)

## Why This Matters

### Test Question (complex_sql_001):
> "Write SQL to calculate AR aging buckets (30/60/90+ days) for unpaid invoices by customer"

### What We Expected the Model to Learn:
- ARTH and ARCM are the right tables
- PayFullDate IS NULL means unpaid
- Need DATEDIFF for aging
- Join on CustGroup/Customer

### What the Model Actually Learned:
- "ARTH contains: ARCo, Mth, CustGroup, Customer..." (memorized list)
- No understanding of *when* to use ARTH vs other tables
- No understanding of *how* these tables relate
- No training on *why* PayFullDate matters for unpaid invoices

### Result:
Model knows the columns exist but doesn't know how to combine them into meaningful queries.

## Evidence from Our Test Results

### SFT Model Score: 40.1%

| Question | Expected | Got | Analysis |
|----------|----------|-----|----------|
| AR Aging | ARTH + ARCM + PayFullDate IS NULL | ARTH only, no ARCM join, no PayFullDate | Model knows ARTH exists but not how to join or filter |
| JC Estimates | JCJP + JCCH + JCCP + JCCT | JCCD only | Model defaults to JCCD, doesn't know the estimate tables |
| AP Holds | APTD + APHD + APCO.RetHoldCode | APTD only, no APHD | Model doesn't know APHD is for hold details |
| Hallucination Test | Reject ARAgingReport | Tried to query it | Model didn't learn what DOESN'T exist |

### The Hallucination Problem (10% score)
Our training data is 100% positive examples. We never taught the model to say "this table doesn't exist." 

DPO was supposed to fix this, but:
- DPO training teaches preference between similar responses
- It doesn't add new knowledge
- The model still doesn't fundamentally understand the schema

## What SQLCoder Gets Right

1. **Schema-in-Context**: Every training example includes the relevant DDL
2. **Human Curation**: Questions reflect real user needs, not auto-generated trivia
3. **SQL Focus**: Training is on SQL generation, not schema Q&A
4. **Rejection Training**: Model learns to say "I cannot answer" when schema doesn't support the question

## The Fix: Complete Training Data Redesign

### Option 1: Schema-in-Prompt Approach (Recommended)

Transform our training data from:
```json
{
  "instruction": "What columns are in ARTH?",
  "output": "ARTH contains: ARCo, Mth..."
}
```

To:
```json
{
  "instruction": "Generate SQL for: Calculate AR aging buckets by customer\n\nDDL:\nCREATE TABLE ARTH (ARCo int, Mth datetime, CustGroup int, Customer int, PayFullDate datetime...)\nCREATE TABLE ARCM (CustGroup int, Customer int, Name varchar...)",
  "input": "",
  "output": "```sql\nSELECT ARCM.Name, ...\nFROM ARTH\nJOIN ARCM ON ARTH.CustGroup = ARCM.CustGroup AND ARTH.Customer = ARCM.Customer\nWHERE ARTH.PayFullDate IS NULL\n...\n```"
}
```

### Option 2: Use a Pre-trained SQL Model as Base

Instead of Qwen2.5-7B-Instruct, use:
- `defog/llama-3-sqlcoder-8b` - Already knows SQL patterns
- Then fine-tune on Vista-specific DDL and naming conventions

### Option 3: Hybrid RAG + Fine-Tuning

1. Keep a RAG system that provides schema context at runtime
2. Fine-tune only to teach Vista-specific conventions:
   - "WITH (NOLOCK)" pattern
   - "Co = @Co" filtering
   - Abbreviation mappings (ARTH = AR Transaction Header)

## Concrete Next Steps

### Phase 1: Training Data Regeneration
1. Create 1,000-2,000 **high-quality** SQL generation examples
2. Each example includes:
   - A realistic user question
   - Relevant DDL for 2-5 tables
   - A correct SQL query with explanation
3. Include 200+ negative examples (fake tables → rejection)

### Phase 2: Prompt Format Standardization
```
<|system|>
You are a SQL expert for Viewpoint Vista. Generate SQL based on the provided schema.
If a table doesn't exist in the schema, say so.
<|user|>
Question: {question}

Available Tables:
{ddl_statements}
<|assistant|>
```

### Phase 3: Evaluation Redesign
- Test with schema provided in prompt
- Measure SQL correctness, not schema recall
- Include hallucination tests with missing tables

## Why This Will Work

SQLCoder achieves **>80% accuracy** on complex SQL with only 20,000 training examples because:
1. Quality > Quantity
2. Task-specific training (SQL generation, not trivia)
3. Schema provided at inference time (no memory required)
4. Proper negative examples (rejection training)

Our 67,448 examples failed because they train the wrong skill (memorization vs. reasoning).

## Summary

| Problem | Cause | Solution |
|---------|-------|----------|
| Poor SQL generation | Training data is Q&A trivia, not SQL examples | Regenerate with SQL-focused examples |
| Missing joins (ARCM, APHD) | Model never saw these tables joined | Include multi-table join examples |
| Wrong tables (JCCD vs JCJP) | Training doesn't teach when to use which | Add business context to training |
| Hallucination (10%) | No negative examples | Add 200+ "doesn't exist" examples |
| DPO regression | DPO can't add knowledge, only refine | Fix SFT first, then consider DPO |

## Conclusion

**The technology is absolutely capable of this.** SQLCoder proves it.

**We are doing it the wrong way.** Our training data teaches schema memorization, not SQL generation.

**The fix is clear:** Regenerate training data with the SQLCoder format - schema-in-prompt, SQL-focused, human-quality questions, and proper negative examples.

---
*Analysis Date: 2025-06-26*
*Based on: SQLCoder methodology, our test results, training data review*
