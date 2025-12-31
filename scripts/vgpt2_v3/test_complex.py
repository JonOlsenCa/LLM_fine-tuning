#!/usr/bin/env python3
"""Test SFT model against complex questions and compare to ground truth."""

import json
import argparse
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def load_model(model_path: str):
    """Load the SFT model with LoRA adapter."""
    base_model = "Qwen/Qwen2.5-7B-Instruct"
    print(f"Loading base model: {base_model}")

    tokenizer = AutoTokenizer.from_pretrained(base_model)

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype="auto",
        device_map="auto"
    )

    print(f"Loading LoRA adapter: {model_path}")
    model = PeftModel.from_pretrained(model, model_path)
    model.eval()

    return model, tokenizer

def generate_response(model, tokenizer, question: str, max_new_tokens: int = 512) -> str:
    """Generate a response for a question."""
    messages = [{"role": "user", "content": question}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs = tokenizer([text], return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.3,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )

    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    return response

def check_key_elements(response: str, key_elements: list) -> dict:
    """Check how many key elements are present in the response."""
    response_lower = response.lower()
    found = []
    missing = []
    
    for element in key_elements:
        if element.lower() in response_lower:
            found.append(element)
        else:
            missing.append(element)
    
    return {
        "found": found,
        "missing": missing,
        "score": len(found) / len(key_elements) if key_elements else 0
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="saves/vgpt2_v3/sft", help="Path to model")
    parser.add_argument("--questions", default="training/COMPLEX_TEST_QUESTIONS.json", help="Questions file")
    parser.add_argument("--output", default="output/complex_test_results.json", help="Output file")
    args = parser.parse_args()
    
    # Load questions
    with open(args.questions) as f:
        questions = json.load(f)
    
    print(f"Loaded {len(questions)} complex questions")
    
    # Load model
    model, tokenizer = load_model(args.model)
    
    # Test each question
    results = []
    for q in questions:
        print(f"\n{'='*60}")
        print(f"Testing: {q['id']}")
        print(f"Question: {q['question'][:80]}...")
        
        response = generate_response(model, tokenizer, q['question'])
        check = check_key_elements(response, q['key_elements'])
        
        result = {
            "id": q['id'],
            "category": q['category'],
            "question": q['question'],
            "ground_truth": q['ground_truth'],
            "model_response": response,
            "key_elements_found": check['found'],
            "key_elements_missing": check['missing'],
            "score": check['score']
        }
        results.append(result)
        
        print(f"Score: {check['score']:.0%} ({len(check['found'])}/{len(q['key_elements'])} key elements)")
        print(f"Found: {check['found']}")
        print(f"Missing: {check['missing']}")
        print(f"Response preview: {response[:200]}...")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    by_category = {}
    for r in results:
        cat = r['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(r['score'])
    
    for cat, scores in by_category.items():
        avg = sum(scores) / len(scores)
        print(f"{cat}: {avg:.0%} average ({len(scores)} questions)")
    
    overall = sum(r['score'] for r in results) / len(results)
    print(f"\nOVERALL: {overall:.0%}")
    
    # Save results
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump({"results": results, "summary": {"overall": overall, "by_category": {k: sum(v)/len(v) for k,v in by_category.items()}}}, f, indent=2)
    
    print(f"\nResults saved to {args.output}")

if __name__ == "__main__":
    main()

