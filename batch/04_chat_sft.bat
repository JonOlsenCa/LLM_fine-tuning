@echo off
echo ========================================
echo VGPT2 v3 - Interactive Chat (SFT Model)
echo ========================================
echo Type questions and press Enter.
echo Type 'exit' to quit.
echo ========================================
echo.

cd /d C:\Github\LLM_fine-tuning
call venv\Scripts\activate.bat

python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

print('Loading model (this takes 2-3 minutes)...')
tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen2.5-7B-Instruct')
model = AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-7B-Instruct', torch_dtype=torch.bfloat16, device_map='auto')
model = PeftModel.from_pretrained(model, 'saves/vgpt2_v3/sft')
print('Model loaded!\n')

while True:
    try:
        q = input('You: ')
        if q.lower() in ['exit', 'quit', 'q']:
            break
        messages = [{'role': 'user', 'content': q}]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer([text], return_tensors='pt').to(model.device)
        outputs = model.generate(**inputs, max_new_tokens=512, temperature=0.3, do_sample=True)
        response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        print(f'\nVGPT2: {response}\n')
    except KeyboardInterrupt:
        break
print('Goodbye!')
"

pause

