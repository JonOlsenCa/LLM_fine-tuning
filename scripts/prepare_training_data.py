#!/usr/bin/env python3
"""
Training Data Preparation Script

Cleans, deduplicates, and splits training data for LLaMA Factory.
- Removes short/empty outputs
- Deduplicates by instruction
- Creates train/eval split
- Balances categories (optional upsampling)
- Adds system prompts

Author: Generated for Viewpoint SQL fine-tuning
Date: 2024-12-27
"""

import json
import random
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# VGPT System prompt
SYSTEM_PROMPT = """You are VGPT, an expert SQL assistant for Viewpoint Vista construction ERP database.

Key conventions:
- Use views (APTH) not base tables (bAPTH) for SELECT queries
- Always add WITH (NOLOCK) after table names
- Filter by company columns (APCo, JCCo, PRCo, etc.)
- Use exact column name case (APCo not apco)
- Check for vrv* reporting views before writing custom SQL"""


def load_data(input_path: str) -> List[Dict]:
    """Load training data from JSON file."""
    with open(input_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def clean_data(data: List[Dict], min_output_len: int = 20) -> Tuple[List[Dict], Dict]:
    """Clean training data by removing low-quality records."""
    stats = {
        'original': len(data),
        'short_output': 0,
        'empty_instruction': 0,
        'duplicates': 0
    }
    
    seen_instructions = set()
    cleaned = []
    
    for record in data:
        instruction = record.get('instruction', '').strip()
        output = record.get('output', '').strip()
        
        # Skip empty instructions
        if not instruction or len(instruction) < 10:
            stats['empty_instruction'] += 1
            continue
        
        # Skip short outputs
        if not output or len(output) < min_output_len:
            stats['short_output'] += 1
            continue
        
        # Skip duplicates
        if instruction in seen_instructions:
            stats['duplicates'] += 1
            continue
        
        seen_instructions.add(instruction)
        cleaned.append(record)
    
    stats['cleaned'] = len(cleaned)
    return cleaned, stats


def add_system_prompt(data: List[Dict], system_prompt: str = SYSTEM_PROMPT) -> List[Dict]:
    """Add system prompt to each record for ShareGPT format."""
    result = []
    for record in data:
        # Convert to ShareGPT conversation format
        result.append({
            "conversations": [
                {"from": "system", "value": system_prompt},
                {"from": "human", "value": record.get('instruction', '') + 
                    ("\n\n" + record.get('input', '') if record.get('input') else "")},
                {"from": "gpt", "value": record.get('output', '')}
            ]
        })
    return result


def split_data(data: List[Dict], eval_ratio: float = 0.1, seed: int = 42) -> Tuple[List[Dict], List[Dict]]:
    """Split data into train and eval sets."""
    random.seed(seed)
    data_copy = data.copy()
    random.shuffle(data_copy)
    
    split_idx = int(len(data_copy) * (1 - eval_ratio))
    return data_copy[:split_idx], data_copy[split_idx:]


def balance_categories(data: List[Dict], min_samples: int = 100) -> List[Dict]:
    """Upsample underrepresented categories."""
    by_category = defaultdict(list)
    
    for record in data:
        cat = record.get('category', 'unknown')
        by_category[cat].append(record)
    
    # Find max category size (capped)
    max_size = min(max(len(v) for v in by_category.values()), 5000)
    
    balanced = []
    for cat, records in by_category.items():
        if len(records) < min_samples:
            # Upsample small categories
            multiplier = min_samples // len(records) + 1
            upsampled = records * multiplier
            balanced.extend(upsampled[:min_samples])
            logger.info(f"  Upsampled {cat}: {len(records)} -> {min_samples}")
        else:
            balanced.extend(records)
    
    return balanced


def save_data(data: List[Dict], output_path: str):
    """Save data to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(data)} records to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Prepare training data for LLaMA Factory')
    parser.add_argument('input_file', help='Input JSON file (full format with metadata)')
    parser.add_argument('--output-dir', default='data', help='Output directory')
    parser.add_argument('--eval-ratio', type=float, default=0.1, help='Eval set ratio')
    parser.add_argument('--min-output-len', type=int, default=20, help='Min output length')
    parser.add_argument('--balance', action='store_true', help='Balance categories')
    parser.add_argument('--format', choices=['alpaca', 'sharegpt'], default='sharegpt')
    
    args = parser.parse_args()
    
    # Load data
    logger.info(f"Loading data from {args.input_file}")
    data = load_data(args.input_file)
    
    # Clean data
    logger.info("Cleaning data...")
    cleaned, stats = clean_data(data, args.min_output_len)
    logger.info(f"  Original: {stats['original']}")
    logger.info(f"  Removed short outputs: {stats['short_output']}")
    logger.info(f"  Removed duplicates: {stats['duplicates']}")
    logger.info(f"  Cleaned: {stats['cleaned']}")
    
    # Balance categories if requested
    if args.balance:
        logger.info("Balancing categories...")
        cleaned = balance_categories(cleaned)
    
    # Split into train/eval
    logger.info(f"Splitting data (eval ratio: {args.eval_ratio})...")
    train_data, eval_data = split_data(cleaned, args.eval_ratio)
    logger.info(f"  Train: {len(train_data)}, Eval: {len(eval_data)}")
    
    # Convert format
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    if args.format == 'sharegpt':
        logger.info("Converting to ShareGPT format with system prompt...")
        train_data = add_system_prompt(train_data)
        eval_data = add_system_prompt(eval_data)
        train_file = output_dir / "vgpt2_train_sharegpt.json"
        eval_file = output_dir / "vgpt2_eval_sharegpt.json"
    else:
        train_file = output_dir / "vgpt2_train.json"
        eval_file = output_dir / "vgpt2_eval.json"
        # Convert to alpaca format (remove metadata)
        train_data = [{"instruction": r.get("instruction",""), "input": r.get("input",""), 
                       "output": r.get("output","")} for r in train_data]
        eval_data = [{"instruction": r.get("instruction",""), "input": r.get("input",""), 
                      "output": r.get("output","")} for r in eval_data]
    
    # Save
    save_data(train_data, str(train_file))
    save_data(eval_data, str(eval_file))
    
    print(f"\n✅ Data preparation complete!")
    print(f"   Train: {train_file} ({len(train_data)} records)")
    print(f"   Eval:  {eval_file} ({len(eval_data)} records)")


if __name__ == "__main__":
    main()

