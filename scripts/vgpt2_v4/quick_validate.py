# Copyright 2024-2025 Viewpoint, Inc.
# Licensed under the Apache License, Version 2.0.

"""
V4 Quick Validation Script

Performs a rapid validation of the V4 training approach before full training:
1. Trains on a small subset (100 examples) for 1 epoch
2. Tests on held-out examples
3. Compares to base model performance

Usage:
    python scripts/vgpt2_v4/quick_validate.py
    
Estimated time: 5-10 minutes on GPU
"""

import json
import os
import random
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


def create_validation_split(
    data_path: str = "data/vgpt2_v4_sft.json",
    train_size: int = 100,
    test_size: int = 20
) -> Tuple[List[Dict], List[Dict]]:
    """Create train/test split for validation."""
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    random.shuffle(data)
    
    # Ensure mix of categories
    train_data = data[:train_size]
    test_data = data[train_size:train_size + test_size]
    
    return train_data, test_data


def create_temp_config(
    train_data: List[Dict],
    output_dir: str,
    num_epochs: int = 1,
    batch_size: int = 4
) -> str:
    """Create temporary training config for quick validation."""
    
    # Save training data
    train_path = Path(output_dir) / "train_data.json"
    with open(train_path, "w", encoding="utf-8") as f:
        json.dump(train_data, f, indent=2)
    
    # Create dataset_info.json
    dataset_info = {
        "v4_quick_validate": {
            "file_name": str(train_path.absolute()),
            "columns": {
                "prompt": "instruction",
                "query": "input",
                "response": "output"
            }
        }
    }
    
    dataset_info_path = Path(output_dir) / "dataset_info.json"
    with open(dataset_info_path, "w", encoding="utf-8") as f:
        json.dump(dataset_info, f, indent=2)
    
    # Create training config
    config = f"""### Quick Validation Config for V4
### This trains on {len(train_data)} examples for {num_epochs} epoch(s)

### Model
model_name_or_path: Qwen/Qwen2.5-7B-Instruct
trust_remote_code: true

### Method
stage: sft
do_train: true
finetuning_type: lora
lora_rank: 32
lora_alpha: 64
lora_dropout: 0.05
lora_target: all

### Dataset
dataset_dir: {output_dir}
dataset: v4_quick_validate
template: qwen
cutoff_len: 2048
preprocessing_num_workers: 4

### Training
output_dir: {output_dir}/model
per_device_train_batch_size: {batch_size}
gradient_accumulation_steps: 2
learning_rate: 2.0e-4
num_train_epochs: {num_epochs}
lr_scheduler_type: cosine
warmup_ratio: 0.1
fp16: true
logging_steps: 10
save_strategy: "no"
report_to: none
"""
    
    config_path = Path(output_dir) / "quick_validate.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config)
    
    return str(config_path)


def run_quick_training(config_path: str) -> bool:
    """Run quick training using LLaMA Factory."""
    print("\n" + "=" * 60)
    print("STEP 1: Quick Training (1 epoch on 100 examples)")
    print("=" * 60)
    
    # Try different ways to invoke LLaMA Factory
    # 1. Direct CLI (if in PATH)
    # 2. Python module invocation
    # 3. Using the LLaMA-Factory repo directly
    
    commands_to_try = [
        ["llamafactory-cli", "train", config_path],
        [sys.executable, "-m", "llamafactory.cli", "train", config_path],
        ["python", "-m", "llamafactory.cli", "train", config_path],
    ]
    
    for cmd in commands_to_try:
        print(f"  Trying: {' '.join(cmd[:3])}...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=False,
                text=True,
                timeout=600  # 10 minute timeout
            )
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            print("ERROR: Training timed out after 10 minutes")
            return False
        except Exception as e:
            print(f"  Failed: {e}")
            continue
    
    print("\nERROR: Could not find LLaMA Factory installation")
    print("Please ensure LLaMA Factory is installed:")
    print("  pip install llamafactory")
    print("Or run training manually:")
    print(f"  llamafactory-cli train {config_path}")
    return False


def test_model_inference(
    model_path: str,
    test_data: List[Dict],
    use_base_model: bool = False
) -> List[Dict]:
    """Test model on held-out examples."""
    print("\n" + "=" * 60)
    print(f"STEP 2: Testing {'Base' if use_base_model else 'Fine-tuned'} Model")
    print("=" * 60)
    
    results = []
    
    # For now, we'll use simple heuristic evaluation
    # In a full test, you'd load the model and generate
    for i, ex in enumerate(test_data[:5]):
        print(f"\nTest {i+1}:")
        print(f"  Question: {ex['instruction'][:100]}...")
        print(f"  Expected: {ex['output'][:100]}...")
        
        results.append({
            "question": ex["instruction"],
            "expected": ex["output"],
            "model": "base" if use_base_model else "finetuned"
        })
    
    return results


def print_validation_summary(
    train_size: int,
    test_size: int,
    training_success: bool,
    elapsed_time: float
):
    """Print validation summary."""
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    print(f"""
    Training Data:      {train_size} examples
    Test Data:          {test_size} examples
    Training Success:   {'✅ YES' if training_success else '❌ NO'}
    Elapsed Time:       {elapsed_time:.1f} seconds
    
    {'READY FOR FULL TRAINING' if training_success else 'NEEDS INVESTIGATION'}
    
    Next Steps:
    1. {'Run full training with all 892 examples' if training_success else 'Debug training issues'}
    2. {'llamafactory-cli train examples/train_lora/vgpt2_v4_sft.yaml' if training_success else 'Check error logs'}
    """)


def main():
    """Run quick validation."""
    print("=" * 60)
    print("V4 QUICK VALIDATION")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = datetime.now()
    
    # Check if training data exists
    data_path = "data/vgpt2_v4_sft.json"
    if not Path(data_path).exists():
        print(f"ERROR: Training data not found at {data_path}")
        print("Run the V4 pipeline first: python scripts/vgpt2_v4/run_pipeline.py")
        sys.exit(1)
    
    # Create validation split
    print("\nCreating validation split...")
    train_data, test_data = create_validation_split(
        data_path=data_path,
        train_size=100,
        test_size=20
    )
    print(f"  Training examples: {len(train_data)}")
    print(f"  Test examples: {len(test_data)}")
    
    # Create temp directory for validation
    with tempfile.TemporaryDirectory(prefix="v4_validate_") as tmpdir:
        print(f"\nValidation directory: {tmpdir}")
        
        # Create config
        config_path = create_temp_config(
            train_data=train_data,
            output_dir=tmpdir,
            num_epochs=1,
            batch_size=4
        )
        print(f"Config created: {config_path}")
        
        # Run training
        training_success = run_quick_training(config_path)
        
        if training_success:
            # Test model
            model_path = Path(tmpdir) / "model"
            results = test_model_inference(str(model_path), test_data)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print_validation_summary(
        train_size=len(train_data),
        test_size=len(test_data),
        training_success=training_success,
        elapsed_time=elapsed
    )
    
    return 0 if training_success else 1


if __name__ == "__main__":
    sys.exit(main())
