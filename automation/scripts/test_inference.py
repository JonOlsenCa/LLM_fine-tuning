"""Test VGPT2 inference after training"""
import sys
sys.path.insert(0, "C:/Github/LLaMA-Factory/src")

from llamafactory.chat import ChatModel

args = {
    "model_name_or_path": "Qwen/Qwen2.5-1.5B-Instruct",
    "adapter_name_or_path": "C:/Github/LLaMA-Factory/saves/vgpt2_test",
    "template": "qwen",
    "finetuning_type": "lora"
}

print("Loading model...")
model = ChatModel(args)

test_prompts = [
    "Write a query to get all unpaid AP invoices over $10,000 for company 1",
    "What's the difference between bAPTH and APTH and when do I use each?",
]

for prompt in test_prompts:
    print(f"\n{'='*60}")
    print(f"PROMPT: {prompt}")
    print(f"{'='*60}")
    messages = [{"role": "user", "content": prompt}]
    response = model.chat(messages)
    print(f"RESPONSE:\n{response}")
    print()

