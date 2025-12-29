#!/usr/bin/env python3
"""
Comprehensive VGPT2 Model Test Suite
50+ questions covering: Schema Knowledge, SQL Generation, Edge Cases, Business Logic

Usage: python scripts/test_vgpt2_comprehensive.py
       OR: .\scripts\run_external.ps1 -Script "test_vgpt2_comprehensive.py"
"""

import torch
import json
import sys
from datetime import datetime
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Test Questions organized by category
TEST_QUESTIONS = {
    "schema_knowledge": [
        # Real Viewpoint tables/views
        "What columns are in dbo.bAPTH?",
        "What columns are in the APTH view?",
        "List the key columns in bAPVendor",
        "Describe the APTD table structure",
        "What is the primary key of bAPUI?",
        "What columns link bAPTD to bAPTH?",
        "What columns are in the Analytics.vDataSyncTracking table?",
        "Describe the key columns in Batch.Document",
        "What is the data type of DocumentId in Batch.Document?",
        "List all columns in APVM (vendor master)",
        "What columns are in bJCCM (Job Cost Contract Master)?",
        "What is the structure of the PRTH table?",
        "Describe the GLDT (GL Detail) table",
        "What columns are in bEMEM (Equipment Master)?",
        "What is the structure of ARCM (AR Customer Master)?",
    ],
    "sql_generation": [
        "Write SQL to get all unpaid invoices from bAPTH",
        "How do I join bAPTH and bAPVendor?",
        "Query to find duplicate invoice numbers in AP",
        "Get total invoice amount by vendor for 2024",
        "Find all invoices approved but not paid",
        "Write a query to get AP aging by vendor",
        "How do I query committed costs from vrvJCCommittedCost?",
        "Write SQL to find all active vendors in APVM",
        "Query to get job cost transactions for a specific job",
        "How do I join PRTH (PR Transaction Header) with employee data?",
        "Write SQL to get GL account balances by month",
        "Query to find all equipment with maintenance due",
        "How do I get AR customer outstanding balances?",
        "Write a query joining APTH with APTL (AP Transaction Lines)",
        "Query to find all vendors with no invoices in 90 days",
    ],
    "edge_cases_hallucination": [
        # These should trigger "does not exist" or similar responses
        "What is the Invoice table?",
        "How do I query the UserPreferences table?",
        "What columns are in the Payments table?",
        "Describe the CustomerOrders table",
        "What is the structure of the SalesData table?",
        "How do I join Invoice and Customer tables?",
        # Valid but might confuse: base vs view
        "What's the difference between bAPTH and APTH?",
        "When should I use bAPTH vs APTH?",
        "What's the difference between bAPTH and vrvAP_MVAllInvoices?",
    ],
    "naming_conventions": [
        "What naming convention do Viewpoint table prefixes follow?",
        "What does the 'b' prefix mean in Viewpoint tables?",
        "What is the vrv prefix used for?",
        "How are company columns named in Viewpoint?",
        "What is the correct way to reference tables in Viewpoint SQL?",
        "What's the difference between b-prefixed and non-prefixed tables?",
    ],
    "business_logic": [
        "How does the AP payment approval workflow work?",
        "What triggers a duplicate invoice warning?",
        "When is an invoice considered 'paid' in AP?",
        "How does batch processing work in Viewpoint AP?",
        "What tables are used for AP batch entry?",
        "How do VendorGroups work in Viewpoint?",
        "When should I use WITH (NOLOCK) in queries?",
        "How does company context work in Viewpoint queries?",
    ],
}

def load_model():
    """Load base model + LoRA adapter."""
    BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
    ADAPTER_PATH = "saves/vgpt2_v2_lora_sft"
    
    print(f"Loading base model: {BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True, local_files_only=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.bfloat16, device_map="auto",
        trust_remote_code=True, local_files_only=True
    )
    
    print(f"Loading LoRA adapter: {ADAPTER_PATH}")
    model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    model.eval()
    return model, tokenizer

def run_query(model, tokenizer, question: str) -> str:
    """Run a single query through the model."""
    messages = [{"role": "user", "content": question}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs, max_new_tokens=512, temperature=0.7, top_p=0.8,
            do_sample=True, pad_token_id=tokenizer.eos_token_id
        )
    return tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()

def main():
    print("=" * 70)
    print("  VGPT2 Comprehensive Test Suite")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    model, tokenizer = load_model()
    
    results = {"metadata": {"timestamp": datetime.now().isoformat(), "total_questions": 0}, "categories": {}}
    question_num = 0
    
    for category, questions in TEST_QUESTIONS.items():
        print(f"\n{'='*70}\n📁 Category: {category.upper()}\n{'='*70}")
        results["categories"][category] = []
        
        for q in questions:
            question_num += 1
            print(f"\n[{question_num}] 📝 {q}")
            print("-" * 60)
            response = run_query(model, tokenizer, q)
            print(f"🤖 {response[:500]}{'...' if len(response) > 500 else ''}")
            results["categories"][category].append({"question": q, "response": response})
    
    results["metadata"]["total_questions"] = question_num
    
    # Save results
    output_path = Path("output/vgpt2_test_results.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print(f"✅ Test complete! {question_num} questions processed.")
    print(f"📄 Results saved to: {output_path}")
    print("=" * 70)

if __name__ == "__main__":
    main()

