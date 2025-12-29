#!/usr/bin/env python3
"""
VGPT2 v3 Data Quality Validation Script
========================================
Validates all generated datasets before training.

Checks:
1. File existence and JSON validity
2. Record counts and structure
3. Field completeness
4. Deduplication stats
5. Format-specific validation (KTO labels, DPO pairs, etc.)

Usage:
    python scripts/vgpt2_v3/validate_data.py
    python scripts/vgpt2_v3/validate_data.py --fix  # Auto-fix issues where possible
"""

import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataValidator:
    """Validates VGPT2 training datasets."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.issues = []
        self.warnings = []
        self.stats = {}

    def validate_all(self) -> Tuple[bool, Dict]:
        """
        Validate all datasets.

        Returns:
            (all_valid, stats_dict)
        """
        logger.info("=" * 60)
        logger.info("VGPT2 v3 Data Quality Validation")
        logger.info("=" * 60)

        # Define expected datasets
        datasets = {
            "vgpt2_v3_sft.json": self._validate_sft,
            "vgpt2_v3_negatives.json": self._validate_sft,
            "vgpt2_v3_sft_merged.json": self._validate_sft,
            "vgpt2_v3_dpo.json": self._validate_dpo,
            "vgpt2_v3_kto.json": self._validate_kto,
        }

        all_valid = True

        for filename, validator in datasets.items():
            filepath = self.data_dir / filename
            logger.info(f"\n--- Validating {filename} ---")

            if not filepath.exists():
                self.issues.append(f"Missing file: {filename}")
                logger.error(f"  FILE NOT FOUND: {filepath}")
                all_valid = False
                continue

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                valid, stats = validator(data, filename)
                self.stats[filename] = stats

                if not valid:
                    all_valid = False

            except json.JSONDecodeError as e:
                self.issues.append(f"Invalid JSON in {filename}: {e}")
                logger.error(f"  INVALID JSON: {e}")
                all_valid = False
            except Exception as e:
                self.issues.append(f"Error reading {filename}: {e}")
                logger.error(f"  ERROR: {e}")
                all_valid = False

        # Print summary
        self._print_summary(all_valid)

        return all_valid, self.stats

    def _validate_sft(self, data: List[Dict], filename: str) -> Tuple[bool, Dict]:
        """Validate SFT dataset format."""
        valid = True
        stats = {
            "total_records": len(data),
            "unique_instructions": 0,
            "avg_output_length": 0,
            "empty_outputs": 0,
            "duplicates": 0,
        }

        if not data:
            self.issues.append(f"{filename}: Empty dataset")
            logger.error("  EMPTY DATASET")
            return False, stats

        # Required fields
        required = ["instruction", "output"]
        missing_fields = []

        # Check first record structure
        first = data[0]
        for field in required:
            if field not in first:
                missing_fields.append(field)

        if missing_fields:
            self.issues.append(f"{filename}: Missing required fields: {missing_fields}")
            logger.error(f"  Missing fields: {missing_fields}")
            valid = False

        # Check all records
        seen_instructions = set()
        output_lengths = []
        empty_outputs = 0

        for i, record in enumerate(data):
            # Check for empty instruction
            if not record.get("instruction", "").strip():
                self.warnings.append(f"{filename}[{i}]: Empty instruction")

            # Check for empty output
            output = record.get("output", "")
            if not output.strip():
                empty_outputs += 1
            else:
                output_lengths.append(len(output))

            # Track duplicates
            instr = record.get("instruction", "").lower().strip()
            if instr in seen_instructions:
                stats["duplicates"] += 1
            else:
                seen_instructions.add(instr)

        stats["unique_instructions"] = len(seen_instructions)
        stats["empty_outputs"] = empty_outputs
        stats["avg_output_length"] = sum(output_lengths) / len(output_lengths) if output_lengths else 0

        # Log stats
        logger.info(f"  Total records: {stats['total_records']}")
        logger.info(f"  Unique instructions: {stats['unique_instructions']}")
        logger.info(f"  Duplicates: {stats['duplicates']}")
        logger.info(f"  Avg output length: {stats['avg_output_length']:.0f} chars")

        if empty_outputs > 0:
            self.warnings.append(f"{filename}: {empty_outputs} records with empty outputs")
            logger.warning(f"  Empty outputs: {empty_outputs}")

        return valid, stats

    def _validate_dpo(self, data: List[Dict], filename: str) -> Tuple[bool, Dict]:
        """Validate DPO dataset format."""
        valid = True
        stats = {
            "total_pairs": len(data),
            "unique_instructions": 0,
            "avg_chosen_length": 0,
            "avg_rejected_length": 0,
        }

        if not data:
            self.issues.append(f"{filename}: Empty dataset")
            logger.error("  EMPTY DATASET")
            return False, stats

        # Required fields for DPO
        required = ["instruction", "chosen", "rejected"]
        first = data[0]
        missing_fields = [f for f in required if f not in first]

        if missing_fields:
            self.issues.append(f"{filename}: Missing required DPO fields: {missing_fields}")
            logger.error(f"  Missing DPO fields: {missing_fields}")
            valid = False
            return valid, stats

        # Validate records
        seen_instructions = set()
        chosen_lengths = []
        rejected_lengths = []

        for i, record in enumerate(data):
            instr = record.get("instruction", "").lower().strip()
            seen_instructions.add(instr)

            chosen = record.get("chosen", "")
            rejected = record.get("rejected", "")

            if chosen:
                chosen_lengths.append(len(chosen))
            if rejected:
                rejected_lengths.append(len(rejected))

            # Check that chosen != rejected
            if chosen == rejected:
                self.warnings.append(f"{filename}[{i}]: chosen equals rejected")

        stats["unique_instructions"] = len(seen_instructions)
        stats["avg_chosen_length"] = sum(chosen_lengths) / len(chosen_lengths) if chosen_lengths else 0
        stats["avg_rejected_length"] = sum(rejected_lengths) / len(rejected_lengths) if rejected_lengths else 0

        logger.info(f"  Total pairs: {stats['total_pairs']}")
        logger.info(f"  Unique instructions: {stats['unique_instructions']}")
        logger.info(f"  Avg chosen length: {stats['avg_chosen_length']:.0f} chars")
        logger.info(f"  Avg rejected length: {stats['avg_rejected_length']:.0f} chars")

        return valid, stats

    def _validate_kto(self, data: List[Dict], filename: str) -> Tuple[bool, Dict]:
        """Validate KTO dataset format."""
        valid = True
        stats = {
            "total_examples": len(data),
            "positive_count": 0,
            "negative_count": 0,
            "label_format_correct": True,
        }

        if not data:
            self.issues.append(f"{filename}: Empty dataset")
            logger.error("  EMPTY DATASET")
            return False, stats

        # Required fields for KTO
        required = ["instruction", "output", "label"]
        first = data[0]
        missing_fields = [f for f in required if f not in first]

        if missing_fields:
            self.issues.append(f"{filename}: Missing required KTO fields: {missing_fields}")
            logger.error(f"  Missing KTO fields: {missing_fields}")
            valid = False
            return valid, stats

        # Validate records
        positive = 0
        negative = 0
        label_issues = 0

        for i, record in enumerate(data):
            label = record.get("label")

            # Check label format (should be string "true" or "false")
            if label == "true":
                positive += 1
            elif label == "false":
                negative += 1
            elif label is True:
                # Boolean instead of string - ISSUE
                label_issues += 1
                positive += 1
            elif label is False:
                label_issues += 1
                negative += 1
            else:
                self.warnings.append(f"{filename}[{i}]: Invalid label value: {label}")

        stats["positive_count"] = positive
        stats["negative_count"] = negative

        if label_issues > 0:
            self.issues.append(f"{filename}: {label_issues} records have boolean labels (should be string)")
            logger.error(f"  LABEL FORMAT ERROR: {label_issues} records use boolean instead of string")
            stats["label_format_correct"] = False
            valid = False

        logger.info(f"  Total examples: {stats['total_examples']}")
        logger.info(f"  Positive (thumbs_up): {stats['positive_count']}")
        logger.info(f"  Negative (thumbs_down): {stats['negative_count']}")
        logger.info(f"  Label format: {'OK' if stats['label_format_correct'] else 'ERROR'}")

        # Check balance
        if positive > 0 and negative > 0:
            ratio = positive / negative
            if ratio > 3 or ratio < 0.33:
                self.warnings.append(f"{filename}: Imbalanced labels (ratio {ratio:.2f})")
                logger.warning(f"  Imbalanced: {ratio:.2f} positive/negative ratio")

        return valid, stats

    def _print_summary(self, all_valid: bool):
        """Print validation summary."""
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 60)

        if all_valid and not self.issues:
            logger.info("STATUS: ALL DATASETS VALID")
        else:
            logger.error(f"STATUS: VALIDATION FAILED ({len(self.issues)} issues)")

        if self.issues:
            logger.error("\nISSUES (must fix):")
            for issue in self.issues:
                logger.error(f"  - {issue}")

        if self.warnings:
            logger.warning(f"\nWARNINGS ({len(self.warnings)}):")
            for warn in self.warnings[:10]:  # Limit to first 10
                logger.warning(f"  - {warn}")
            if len(self.warnings) > 10:
                logger.warning(f"  ... and {len(self.warnings) - 10} more")

        # Print dataset stats table
        logger.info("\nDATASET STATISTICS:")
        logger.info("-" * 50)
        for filename, stats in self.stats.items():
            count = stats.get("total_records") or stats.get("total_pairs") or stats.get("total_examples", 0)
            logger.info(f"  {filename}: {count} records")

    def fix_kto_labels(self) -> int:
        """Fix KTO labels from boolean to string."""
        kto_path = self.data_dir / "vgpt2_v3_kto.json"
        if not kto_path.exists():
            return 0

        with open(kto_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        fixed = 0
        for record in data:
            if record.get("label") is True:
                record["label"] = "true"
                fixed += 1
            elif record.get("label") is False:
                record["label"] = "false"
                fixed += 1

        if fixed > 0:
            with open(kto_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Fixed {fixed} KTO labels (boolean -> string)")

        return fixed


def main():
    parser = argparse.ArgumentParser(description="Validate VGPT2 training data")
    parser.add_argument('--data-dir', type=str, default='data',
                        help='Data directory path')
    parser.add_argument('--fix', action='store_true',
                        help='Auto-fix issues where possible')

    args = parser.parse_args()

    validator = DataValidator(args.data_dir)

    if args.fix:
        logger.info("Running with --fix flag: will attempt to fix issues")
        fixed = validator.fix_kto_labels()
        if fixed > 0:
            logger.info(f"Fixed {fixed} issues")

    valid, stats = validator.validate_all()

    if not valid:
        logger.error("\nPlease fix the issues above before training.")
        exit(1)
    else:
        logger.info("\nAll datasets are valid and ready for training!")
        exit(0)


if __name__ == "__main__":
    main()
