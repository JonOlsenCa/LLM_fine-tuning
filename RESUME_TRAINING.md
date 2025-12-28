# Resume VGPT2 Training

**Stopped at:** Step 1640/7050 (23%)  
**Last checkpoint:** `checkpoint-1600`  
**Date stopped:** 2025-12-28 ~2:40 PM  
**Remaining:** ~5,450 steps (~5.6 hours at 3.7s/it)

---

## To Resume Training

### 1. Activate environment
```powershell
cd C:\Github\LLM_fine-tuning
.\venv\Scripts\activate
```

### 2. Enable checkpoint resume (ALREADY DONE - just verify)
Edit `automation/configs/vgpt2_lora_sft.yaml` and uncomment:
```yaml
resume_from_checkpoint: true
```

### 3. Start training
```powershell
llamafactory-cli train automation/configs/vgpt2_lora_sft.yaml
```

Training will automatically resume from `checkpoint-1600`.

---

## Verify Checkpoint Exists
```powershell
dir saves\vgpt2_v2_lora_sft\checkpoint-*
```

You should see: `checkpoint-800`, `checkpoint-1000`, `checkpoint-1200`, `checkpoint-1400`, `checkpoint-1600`

---

## Expected Output on Resume
```
Resuming training from saves/vgpt2_v2_lora_sft/checkpoint-1600
```

Progress bar should start at ~23% (step 1600/7050).

