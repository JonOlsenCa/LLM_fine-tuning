# Fine-Tuning Strategy & Analysis

**Date:** December 27, 2025
**Context:** Local Windows Setup with NVIDIA GPU

## 1. Hardware & Environment Assessment
Your environment is successfully configured for local LLM fine-tuning, specifically tailored for **Windows** compatibility.

*   **GPU**: NVIDIA GPU confirmed (likely RTX 3090/4090 class given enterprise use).
*   **Software Stack**:
    *   **Python 3.12** (bypassing 3.14 incompatibilities).
    *   **CUDA 12.1** + **BitsAndBytes** (Windows wheels) enable **4-bit QLoRA**.
    *   **LLaMA-Factory**: Configured with `gradio` fixes for local web UI access.

**Capability**: You can efficiently fine-tune 7B, 8B (Llama-3, Mistral, Qwen), and potentially quantized 70B models locally.

---

## 2. High-Value Fine-Tuning Targets

Based on your repositories, three primary candidates exist:

| Repository | Application | Fine-Tuning Goal | Value Proposition |
| :--- | :--- | :--- | :--- |
| **VGPT2** | Expert Orchestrator | **Schema-Aware SQL Expert** | **Critical**: Solves hallucination in SQL generation by training on actual docs. |
| **AP_Wizard** | Enterprise Code | **C# / Azure Co-Pilot** | **High**: Enforces proprietary patterns (Supabase, Azure Functions) that generic models miss. |
| **BambooHR** | Candidate Screening | **Resume Analyst** | **Medium**: Privacy-focused local replacement for GPT-4o resume scoring. |

---

## 3. Deep Dive: VGPT2 SQL Expert Strategy

The most impactful immediate project is fixing the "Unvalidated Experts" in VGPT2 by fine-tuning a model on your **Viewpoint Documentation**.

### The Problem
Current experts likely rely on generic prompts, leading to:
*   **Hallucination**: Guessing column names or tables.
*   **Invalid Joins**: Missing intermediate tables (e.g., joining `Header` to `Detail` without the linker).
*   **Logic Gaps**: Ignoring business logic defined in docs (e.g., "Active records have `Status='A'`").

### The Solution: "Documentation-Driven" Fine-Tuning
We convert the `viewpoint_documentation` folder (SQL objects, schemas, markdown definitions) into an **Instruction Dataset** to train a model that *knows* the schema.

### Implementation Plan

#### Phase 1: Data Generation (Scripted)
Create a Python script to scrape the `viewpoint_documentation` folder and generate pairs of (Input Schema Context) -> (Output SQL).

**Example Training Record (Alpaca Format):**
```json
{
  "instruction": "Expert: Job Billing. Query: List all active contracts with over $50k billed.",
  "input": "Schema Context: Table [bJCMast] (Contract Master) has columns [JCCo], [Contract], [Status] ('A'=Active). Table [bJCBill] (Billing) has [BilledAmt]. Keys: bJCMast.JCCo = bJCBill.JCCo",
  "output": "SELECT m.Contract, m.ContractDesc, SUM(b.BilledAmt) FROM bJCMast m JOIN bJCBill b ON m.JCCo = b.JCCo AND m.Contract = b.Contract WHERE m.Status = 'A' GROUP BY m.Contract HAVING SUM(b.BilledAmt) > 50000;"
}
```

#### Phase 2: Training
*   **Base Model**: Llama-3-8B-Instruct (good balance of logic and SQL capability).
*   **Method**: QLoRA (4-bit) for efficiency.
*   **Dataset**: ~500-1000 generated examples from your docs.

#### Phase 3: Deployment as "Validator"
Instead of just generating code, this model acts as a **Quality Gate**:
1.  **Code Expert** (Legacy) generates a query.
2.  **Fine-Tuned Validator** receives the query + schema.
3.  **Validator** passes or rejects/corrects the query based on its training.

### Next Steps
1.  Add `C:\Github\VGPT2` to the active workspace to allow analysis of the `viewpoint_documentation` structure.
2.  Develop the `doc_to_dataset.py` script.
3.  Run a pilot training session using `LLaMA-Factory`.
