#!/usr/bin/env python3
"""
Training Data Validation Module

This module ensures that all declared data sources actually produce training records.
It provides pre-flight validation and prevents training on incomplete datasets.

SAFEGUARDS:
1. REQUIRED_SOURCES - Every source must have a generator that produces records
2. Pre-flight validation report - Shows exactly what was generated
3. Minimum record requirements - Each source must meet minimum thresholds
4. Abort on failure - Training will not proceed if validation fails

Author: VGPT2 Training Pipeline
Date: 2024-12-28
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class SourceRequirement:
    """Defines requirements for a data source."""
    source_name: str
    minimum_records: int
    source_path: str  # Relative to VGPT2 root
    description: str
    is_critical: bool = True  # If True, validation fails if 0 records


# ============================================================================
# REQUIRED DATA SOURCES - Every source here MUST produce records
# ============================================================================
REQUIRED_SOURCES: Dict[str, SourceRequirement] = {
    # TIER 1 - CRITICAL (Must have records)
    "Schema Metadata": SourceRequirement(
        source_name="Schema Metadata",
        minimum_records=1000,
        source_path="Viewpoint_Database/_Metadata/columns.json",
        description="Column definitions from columns.json",
        is_critical=True
    ),
    "SP Documentation": SourceRequirement(
        source_name="SP Documentation",
        minimum_records=500,
        source_path="Viewpoint_Database/Stored_Procedures/SP_Documentation",
        description="Stored procedure markdown documentation",
        is_critical=True
    ),
    "View Documentation": SourceRequirement(
        source_name="View Documentation",
        minimum_records=500,
        source_path="Viewpoint_Database/View/View_Documentation",
        description="View markdown documentation",
        is_critical=True
    ),
    "JOIN Patterns": SourceRequirement(
        source_name="JOIN Patterns",
        minimum_records=100,
        source_path="Viewpoint_Database/_Relationship_Validation/03_Join_Recipes",
        description="Validated JOIN recipes",
        is_critical=True
    ),
    "DDFI Forms": SourceRequirement(
        source_name="DDFI Forms",
        minimum_records=200,
        source_path="Viewpoint_Database/_Metadata/DDFI.json",
        description="Form field definitions with business context",
        is_critical=True
    ),
    
    # TIER 2 - CRITICAL NEW SOURCES (Previously missing)
    "Crystal Report SQL": SourceRequirement(
        source_name="Crystal Report SQL",
        minimum_records=500,
        source_path="Crystal_Reports_Documentation/_Extracted_SQL/Reformatted",
        description="Production Crystal Report SQL queries",
        is_critical=True
    ),
    "Canonical Rules": SourceRequirement(
        source_name="Canonical Rules",
        minimum_records=15,  # ~26 available from hardcoded rules
        source_path="_ai_orchestration/rules",
        description="SQL formatting rules (WITH NOLOCK, no aliases, etc.)",
        is_critical=True
    ),
    "Reference Documents": SourceRequirement(
        source_name="Reference Documents",
        minimum_records=10,  # ~16 available from 10 reference docs
        source_path="_ai_orchestration/reference",
        description="Viewpoint concepts (batches, groups, months, etc.)",
        is_critical=True
    ),
    "Heuristics": SourceRequirement(
        source_name="Heuristics",
        minimum_records=3,  # ~4 available from 6 heuristic docs
        source_path="_ai_orchestration/heuristics",
        description="SQL generation heuristics",
        is_critical=False  # Bonus content - can grow over time
    ),
    "Workflows": SourceRequirement(
        source_name="Workflows",
        minimum_records=3,  # ~4 available from workflow docs
        source_path="_ai_orchestration/workflows",
        description="SQL generation workflows",
        is_critical=False  # Bonus content - can grow over time
    ),

    # TIER 3 - Expert SQL and Synthetic (Should have records)
    "Experts V2": SourceRequirement(
        source_name="Experts V2",
        minimum_records=100,
        source_path="Experts_V2",
        description="Validated expert SQL queries",
        is_critical=True  # Now critical since we have 405 records
    ),
    "Naming Conventions": SourceRequirement(
        source_name="Naming Conventions",
        minimum_records=10,  # 26 hardcoded examples
        source_path="(hardcoded)",
        description="Viewpoint naming patterns",
        is_critical=True
    ),
    "Error Corrections": SourceRequirement(
        source_name="Error Corrections",
        minimum_records=5,  # 8 hardcoded examples
        source_path="(hardcoded)",
        description="Common SQL errors and fixes",
        is_critical=False  # Bonus - can add more later
    ),
    "Query Optimization": SourceRequirement(
        source_name="Query Optimization",
        minimum_records=3,  # 5 hardcoded examples
        source_path="(hardcoded)",
        description="SQL optimization patterns",
        is_critical=False  # Bonus - can add more later
    ),
}


@dataclass
class ValidationResult:
    """Result of validating a single source."""
    source_name: str
    record_count: int
    minimum_required: int
    is_critical: bool
    passed: bool
    message: str


@dataclass 
class ValidationReport:
    """Complete validation report."""
    results: List[ValidationResult]
    total_records: int
    passed: bool
    critical_failures: List[str]
    warnings: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "total_records": self.total_records,
            "passed": self.passed,
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "sources": [
                {
                    "source": r.source_name,
                    "count": r.record_count,
                    "minimum": r.minimum_required,
                    "passed": r.passed,
                    "message": r.message
                }
                for r in self.results
            ]
        }

    def print_report(self) -> str:
        """Generate human-readable validation report."""
        lines = []
        lines.append("=" * 70)
        lines.append("TRAINING DATA VALIDATION REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Summary
        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        lines.append(f"Total Records: {self.total_records:,}")
        lines.append(f"Sources Passed: {passed_count}/{total_count}")
        lines.append(f"Overall Status: {'✅ PASSED' if self.passed else '❌ FAILED'}")
        lines.append("")

        # Details by source
        lines.append("-" * 70)
        lines.append(f"{'Source':<30} {'Count':>10} {'Min':>10} {'Status':>15}")
        lines.append("-" * 70)

        for r in sorted(self.results, key=lambda x: (x.passed, -x.record_count)):
            status = "✅ PASS" if r.passed else ("❌ CRITICAL" if r.is_critical else "⚠️ WARNING")
            lines.append(f"{r.source_name:<30} {r.record_count:>10,} {r.minimum_required:>10,} {status:>15}")

        lines.append("-" * 70)

        # Critical failures
        if self.critical_failures:
            lines.append("")
            lines.append("❌ CRITICAL FAILURES (must fix before training):")
            for failure in self.critical_failures:
                lines.append(f"   • {failure}")

        # Warnings
        if self.warnings:
            lines.append("")
            lines.append("⚠️ WARNINGS (should fix):")
            for warning in self.warnings:
                lines.append(f"   • {warning}")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)


class TrainingDataValidator:
    """Validates training data against required sources."""

    def __init__(self, vgpt2_path: str):
        self.vgpt2_path = Path(vgpt2_path)

    def validate_sources_exist(self) -> List[str]:
        """Check that all required source paths exist."""
        missing = []
        for name, req in REQUIRED_SOURCES.items():
            if req.source_path == "(hardcoded)":
                continue
            path = self.vgpt2_path / req.source_path
            if not path.exists():
                missing.append(f"{name}: {req.source_path}")
        return missing

    def validate_records(self, records: List, source_counts: Dict[str, int]) -> ValidationReport:
        """
        Validate generated records against requirements.

        Args:
            records: List of TrainingRecord objects
            source_counts: Dict mapping source name to record count

        Returns:
            ValidationReport with pass/fail status
        """
        results = []
        critical_failures = []
        warnings = []

        for source_name, requirement in REQUIRED_SOURCES.items():
            count = source_counts.get(source_name, 0)
            passed = count >= requirement.minimum_records

            if passed:
                message = f"OK: {count} records (min: {requirement.minimum_records})"
            elif count == 0:
                message = f"ZERO RECORDS - generator not implemented or broken"
            else:
                message = f"Below minimum: {count} < {requirement.minimum_records}"

            result = ValidationResult(
                source_name=source_name,
                record_count=count,
                minimum_required=requirement.minimum_records,
                is_critical=requirement.is_critical,
                passed=passed,
                message=message
            )
            results.append(result)

            if not passed:
                if requirement.is_critical:
                    critical_failures.append(f"{source_name}: {message}")
                else:
                    warnings.append(f"{source_name}: {message}")

        # Check for sources in records that aren't in requirements
        known_sources = set(REQUIRED_SOURCES.keys())
        for source in source_counts.keys():
            if source not in known_sources:
                warnings.append(f"Unknown source '{source}' - add to REQUIRED_SOURCES")

        overall_passed = len(critical_failures) == 0

        return ValidationReport(
            results=results,
            total_records=len(records),
            passed=overall_passed,
            critical_failures=critical_failures,
            warnings=warnings
        )


def validate_before_training(records: List, source_counts: Dict[str, int],
                            vgpt2_path: str, abort_on_failure: bool = True) -> ValidationReport:
    """
    Main validation entry point. Call this before training.

    Args:
        records: Generated training records
        source_counts: Dict of source name -> record count
        vgpt2_path: Path to VGPT2 repository
        abort_on_failure: If True, raises exception on critical failures

    Returns:
        ValidationReport

    Raises:
        ValueError: If abort_on_failure=True and validation fails
    """
    validator = TrainingDataValidator(vgpt2_path)

    # First check source paths exist
    missing_paths = validator.validate_sources_exist()
    if missing_paths:
        logger.warning(f"Missing source paths: {missing_paths}")

    # Validate records
    report = validator.validate_records(records, source_counts)

    # Print report
    print(report.print_report())

    # Save report to file
    report_path = Path(vgpt2_path).parent / "LLM_fine-tuning" / "output" / "validation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)
    logger.info(f"Validation report saved to: {report_path}")

    # Abort if critical failures
    if abort_on_failure and not report.passed:
        raise ValueError(
            f"Training data validation FAILED with {len(report.critical_failures)} critical failures.\n"
            f"Fix these issues before training:\n" +
            "\n".join(f"  - {f}" for f in report.critical_failures)
        )

    return report


# ============================================================================
# GENERATOR REGISTRY - Maps source names to generator method names
# ============================================================================
GENERATOR_REGISTRY: Dict[str, str] = {
    "Schema Metadata": "generate_schema_queries",
    "SP Documentation": "generate_sp_examples",
    "View Documentation": "generate_view_examples",
    "JOIN Patterns": "generate_join_pattern_examples",
    "DDFI Forms": "generate_ddfi_examples",
    "Crystal Report SQL": "generate_crystal_report_examples",
    "Canonical Rules": "generate_canonical_rules_examples",
    "Reference Documents": "generate_reference_doc_examples",
    "Heuristics": "generate_heuristic_examples",
    "Workflows": "generate_workflow_examples",
    "Experts V2": "generate_experts_v2_examples",
    "Naming Conventions": "generate_naming_convention_examples",
    "Error Corrections": "generate_error_correction_examples",
    "Query Optimization": "generate_query_optimization_examples",
}


def verify_generators_exist(generator_instance) -> List[str]:
    """
    Verify that all required generators exist on the generator class.

    Returns:
        List of missing generator method names
    """
    missing = []
    for source_name, method_name in GENERATOR_REGISTRY.items():
        if not hasattr(generator_instance, method_name):
            missing.append(f"{source_name} -> {method_name}()")
    return missing

