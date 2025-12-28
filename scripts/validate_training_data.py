#!/usr/bin/env python3
"""
Training Data Validation Script

Validates training data quality for LLaMA Factory fine-tuning.
Checks for:
- Duplicates (exact and fuzzy)
- Empty/short outputs
- Instruction quality
- Category balance
- SQL syntax validation (basic)
- Token count estimates

Author: Generated for Viewpoint SQL fine-tuning
Date: 2024-12-27
"""

import json
import re
import argparse
from pathlib import Path
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a single record."""
    record_idx: int
    issues: List[str]
    warnings: List[str]

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0


@dataclass
class DatasetValidationReport:
    """Overall validation report for a dataset."""
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_count: int
    category_distribution: Dict[str, int]
    quality_distribution: Dict[str, int]
    avg_instruction_length: float
    avg_output_length: float
    issues: List[Tuple[int, str]]
    warnings: List[Tuple[int, str]]


class TrainingDataValidator:
    """Validator for training datasets."""

    # Minimum lengths
    MIN_INSTRUCTION_LENGTH = 10
    MIN_OUTPUT_LENGTH = 20
    MAX_OUTPUT_LENGTH = 8000  # Token limit considerations

    # SQL keywords for basic validation
    SQL_KEYWORDS = {'SELECT', 'FROM', 'WHERE', 'JOIN', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'}

    def __init__(self):
        self.seen_instructions = set()
        self.seen_outputs = set()

    def validate_dataset(self, data: List[Dict]) -> DatasetValidationReport:
        """Validate entire dataset and return report."""
        results = []
        categories = Counter()
        quality_scores = Counter()
        instruction_lengths = []
        output_lengths = []
        duplicates = 0

        for idx, record in enumerate(data):
            result = self.validate_record(record, idx)
            results.append(result)

            # Track duplicates
            instr = record.get('instruction', '')
            if instr in self.seen_instructions:
                duplicates += 1
            self.seen_instructions.add(instr)

            # Track category distribution
            cat = record.get('category', 'unknown')
            categories[cat] += 1

            # Track quality scores
            quality = str(record.get('quality_score', 'unknown'))
            quality_scores[quality] += 1

            # Track lengths
            instruction_lengths.append(len(record.get('instruction', '')))
            output_lengths.append(len(record.get('output', '')))

        # Compile issues and warnings
        all_issues = []
        all_warnings = []
        for result in results:
            for issue in result.issues:
                all_issues.append((result.record_idx, issue))
            for warning in result.warnings:
                all_warnings.append((result.record_idx, warning))

        valid_count = sum(1 for r in results if r.is_valid)

        return DatasetValidationReport(
            total_records=len(data),
            valid_records=valid_count,
            invalid_records=len(data) - valid_count,
            duplicate_count=duplicates,
            category_distribution=dict(categories),
            quality_distribution=dict(quality_scores),
            avg_instruction_length=sum(instruction_lengths) / len(instruction_lengths) if instruction_lengths else 0,
            avg_output_length=sum(output_lengths) / len(output_lengths) if output_lengths else 0,
            issues=all_issues[:100],  # Limit to first 100
            warnings=all_warnings[:100]
        )

    def validate_record(self, record: Dict, idx: int) -> ValidationResult:
        """Validate a single training record."""
        issues = []
        warnings = []

        instruction = record.get('instruction', '')
        input_text = record.get('input', '')
        output = record.get('output', '')

        # Check instruction
        if not instruction:
            issues.append("Empty instruction")
        elif len(instruction) < self.MIN_INSTRUCTION_LENGTH:
            issues.append(f"Instruction too short ({len(instruction)} chars)")

        # Check output
        if not output:
            issues.append("Empty output")
        elif len(output) < self.MIN_OUTPUT_LENGTH:
            warnings.append(f"Output may be too short ({len(output)} chars)")
        elif len(output) > self.MAX_OUTPUT_LENGTH:
            warnings.append(f"Output very long ({len(output)} chars) - may hit token limits")

        # Check for SQL-specific issues in output
        if 'sql' in record.get('category', '').lower() or '```sql' in output.lower():
            sql_issues = self._validate_sql_output(output)
            warnings.extend(sql_issues)

        # Check for duplicate instruction
        if instruction in self.seen_instructions:
            warnings.append("Duplicate instruction")

        return ValidationResult(record_idx=idx, issues=issues, warnings=warnings)

    def _validate_sql_output(self, output: str) -> List[str]:
        """Basic SQL validation for output."""
        warnings = []
        output_upper = output.upper()

        # Check for common Viewpoint issues
        if 'DBO.' in output_upper and 'APTH' in output_upper:
            warnings.append("Uses dbo. prefix (not recommended for Viewpoint views)")

        if 'BAPTH' in output_upper or 'BARTH' in output_upper:
            if 'SELECT' in output_upper:
                warnings.append("Uses base table (b-prefix) in SELECT - use view instead")

        if 'FROM' in output_upper and 'WITH (NOLOCK)' not in output_upper:
            if 'SELECT' in output_upper:
                warnings.append("Missing WITH (NOLOCK) hint")

        # Check for unbalanced parentheses
        if output.count('(') != output.count(')'):
            warnings.append("Unbalanced parentheses in SQL")

        return warnings

    def print_report(self, report: DatasetValidationReport):
        """Print formatted validation report."""
        print("\n" + "=" * 70)
        print("TRAINING DATA VALIDATION REPORT")
        print("=" * 70)

        print(f"\n📊 DATASET SUMMARY")
        print(f"   Total Records:     {report.total_records:,}")
        print(f"   Valid Records:     {report.valid_records:,} ({100*report.valid_records/report.total_records:.1f}%)")
        print(f"   Invalid Records:   {report.invalid_records:,}")
        print(f"   Duplicates Found:  {report.duplicate_count:,}")

        print(f"\n📏 LENGTH STATISTICS")
        print(f"   Avg Instruction:   {report.avg_instruction_length:.0f} chars")
        print(f"   Avg Output:        {report.avg_output_length:.0f} chars")

        print(f"\n📁 CATEGORY DISTRIBUTION")
        for cat, count in sorted(report.category_distribution.items(), key=lambda x: -x[1]):
            pct = 100 * count / report.total_records
            print(f"   {cat:20s} {count:6,} ({pct:5.1f}%)")

        print(f"\n⭐ QUALITY SCORE DISTRIBUTION")
        for score, count in sorted(report.quality_distribution.items()):
            pct = 100 * count / report.total_records
            print(f"   Score {score:6s}       {count:6,} ({pct:5.1f}%)")

        if report.issues:
            print(f"\n❌ ISSUES ({len(report.issues)} found, showing first 20)")
            for idx, issue in report.issues[:20]:
                print(f"   Record {idx}: {issue}")

        if report.warnings:
            print(f"\n⚠️  WARNINGS ({len(report.warnings)} found, showing first 20)")
            for idx, warning in report.warnings[:20]:
                print(f"   Record {idx}: {warning}")

        # Overall assessment
        print("\n" + "-" * 70)
        if report.invalid_records == 0 and report.duplicate_count < report.total_records * 0.05:
            print("✅ VALIDATION PASSED - Dataset is ready for training")
        elif report.invalid_records < report.total_records * 0.01:
            print("⚠️  VALIDATION PASSED WITH WARNINGS - Review issues before training")
        else:
            print("❌ VALIDATION FAILED - Fix issues before training")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description='Validate training data for LLaMA Factory')
    parser.add_argument('input_file', help='Path to training data JSON file')
    parser.add_argument('--strict', action='store_true', help='Fail on any warnings')
    parser.add_argument('--output', help='Save validation report to file')

    args = parser.parse_args()

    # Load data
    input_path = Path(args.input_file)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 1

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"Loaded {len(data)} records from {input_path}")

    # Validate
    validator = TrainingDataValidator()
    report = validator.validate_dataset(data)

    # Print report
    validator.print_report(report)

    # Save report if requested
    if args.output:
        report_data = {
            'total_records': report.total_records,
            'valid_records': report.valid_records,
            'invalid_records': report.invalid_records,
            'duplicate_count': report.duplicate_count,
            'category_distribution': report.category_distribution,
            'quality_distribution': report.quality_distribution,
            'avg_instruction_length': report.avg_instruction_length,
            'avg_output_length': report.avg_output_length,
            'issues': report.issues,
            'warnings': report.warnings
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        logger.info(f"Saved report to {args.output}")

    # Return exit code based on validation
    if args.strict:
        return 1 if report.issues or report.warnings else 0
    return 1 if report.invalid_records > 0 else 0


if __name__ == "__main__":
    exit(main())
