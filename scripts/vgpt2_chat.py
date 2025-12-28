"""VGPT2 Interactive Chat with System Prompt"""
import sys
import os

# Add LLaMA-Factory to path
sys.path.insert(0, "C:/Github/LLaMA-Factory/src")

from llamafactory.chat import ChatModel

SYSTEM_PROMPT = """You are VGPT, an expert SQL assistant for Viewpoint Vista construction ERP database.

Key conventions:
- Use views (APTH) not base tables (bAPTH) for SELECT queries
- Always add WITH (NOLOCK) after table names: SELECT * FROM APTH WITH (NOLOCK)
- Filter by company columns (APCo, JCCo, PRCo, etc.)
- Use exact column name case (APCo not apco)
- Check for vrv* reporting views before writing custom SQL

Table naming:
- bXXXX = base table (for INSERT/UPDATE/DELETE)
- XXXX = view (for SELECT queries)
- Examples: bAPTH/APTH, bJCCD/JCCD, bPRTH/PRTH

Common modules:
- AP = Accounts Payable (APTH, APTD, APVM)
- AR = Accounts Receivable (ARTH, ARTD)
- JC = Job Cost (JCCD, JCJM, JCCP)
- PR = Payroll (PRTH, PRPC, PRRH)
- GL = General Ledger (GLDT, GLAC)
- PO = Purchase Orders (POHD, POIT)
- EM = Equipment Management (EMEM, EMBF)

Always use WITH (NOLOCK) for read queries to prevent blocking."""

MODEL_PATH = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_PATH = "C:/Github/LLaMA-Factory/saves/vgpt2_full"

def main():
    print("Loading VGPT2 model...")
    model = ChatModel({
        "model_name_or_path": MODEL_PATH,
        "adapter_name_or_path": ADAPTER_PATH,
        "template": "qwen",
        "finetuning_type": "lora"
    })
    print("Model loaded!\n")
    print("="*60)
    print("VGPT2 - Viewpoint Vista SQL Assistant")
    print("Type 'quit' or 'exit' to end")
    print("="*60)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            print("Generating response...")
            messages = [{"role": "user", "content": user_input}]
            response = model.chat(messages, system=SYSTEM_PROMPT)

            # Extract response text
            if isinstance(response, list) and len(response) > 0:
                response_text = response[0].response_text
            elif hasattr(response, 'response_text'):
                response_text = response.response_text
            else:
                response_text = str(response)

            print(f"\nVGPT2:\n{response_text}")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            import traceback
            print(f"Error: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    main()

