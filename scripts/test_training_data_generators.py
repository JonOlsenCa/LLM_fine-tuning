#!/usr/bin/env python3
"""
Unit Tests for Training Data Generators

These tests verify that each generator produces records from its source.
Run these BEFORE training to catch missing/broken generators early.

Usage:
    python test_training_data_generators.py
    
    # Or with pytest
    pytest test_training_data_generators.py -v

Author: VGPT2 Training Pipeline
Date: 2024-12-28
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from training_data_validation import (
    REQUIRED_SOURCES, 
    GENERATOR_REGISTRY,
    verify_generators_exist,
    TrainingDataValidator
)


class TestGeneratorRegistry(unittest.TestCase):
    """Test that all required sources have registered generators."""
    
    def test_all_sources_have_generators(self):
        """Every source in REQUIRED_SOURCES must have a generator in GENERATOR_REGISTRY."""
        missing = []
        for source_name in REQUIRED_SOURCES.keys():
            if source_name not in GENERATOR_REGISTRY:
                missing.append(source_name)
        
        self.assertEqual(
            missing, [],
            f"Sources without generators: {missing}"
        )
    
    def test_no_orphan_generators(self):
        """Every generator in GENERATOR_REGISTRY must have a source in REQUIRED_SOURCES."""
        orphans = []
        for source_name in GENERATOR_REGISTRY.keys():
            if source_name not in REQUIRED_SOURCES:
                orphans.append(source_name)
        
        self.assertEqual(
            orphans, [],
            f"Generators without sources: {orphans}"
        )


class TestSourcePaths(unittest.TestCase):
    """Test that source paths exist."""
    
    @classmethod
    def setUpClass(cls):
        cls.vgpt2_path = Path("C:/Github/VGPT2")
        if not cls.vgpt2_path.exists():
            raise unittest.SkipTest("VGPT2 path not found")
        cls.validator = TrainingDataValidator(str(cls.vgpt2_path))
    
    def test_all_source_paths_exist(self):
        """All non-hardcoded source paths must exist."""
        missing = self.validator.validate_sources_exist()
        self.assertEqual(
            missing, [],
            f"Missing source paths:\n" + "\n".join(f"  - {m}" for m in missing)
        )


class TestGeneratorMethods(unittest.TestCase):
    """Test that generator methods exist and are callable."""
    
    @classmethod
    def setUpClass(cls):
        cls.vgpt2_path = Path("C:/Github/VGPT2")
        if not cls.vgpt2_path.exists():
            raise unittest.SkipTest("VGPT2 path not found")
        
        # Import the generator class
        from generate_vgpt2_training_data import VGPT2DatasetGenerator
        cls.generator = VGPT2DatasetGenerator(str(cls.vgpt2_path))
    
    def test_all_generators_exist(self):
        """All registered generators must exist as methods."""
        missing = verify_generators_exist(self.generator)
        self.assertEqual(
            missing, [],
            f"Missing generator methods:\n" + "\n".join(f"  - {m}" for m in missing)
        )
    
    def test_generators_are_callable(self):
        """All generators must be callable."""
        for source_name, method_name in GENERATOR_REGISTRY.items():
            method = getattr(self.generator, method_name, None)
            self.assertTrue(
                callable(method),
                f"Generator {method_name} for '{source_name}' is not callable"
            )


class TestGeneratorOutput(unittest.TestCase):
    """Test that each generator produces records."""
    
    @classmethod
    def setUpClass(cls):
        cls.vgpt2_path = Path("C:/Github/VGPT2")
        if not cls.vgpt2_path.exists():
            raise unittest.SkipTest("VGPT2 path not found")
        
        from generate_vgpt2_training_data import VGPT2DatasetGenerator
        cls.generator = VGPT2DatasetGenerator(str(cls.vgpt2_path))
    
    def _test_generator_produces_records(self, source_name: str, method_name: str, min_records: int):
        """Helper to test a single generator."""
        method = getattr(self.generator, method_name, None)
        if method is None:
            self.fail(f"Generator method {method_name} not found")
        
        # Generate with small limit for speed
        records = method(max_records=100)
        
        self.assertIsInstance(records, list, f"{method_name} must return a list")
        self.assertGreater(
            len(records), 0,
            f"{method_name} produced 0 records - generator is broken or source is empty"
        )
    
    def test_schema_metadata_generator(self):
        """Schema Metadata generator produces records."""
        self._test_generator_produces_records(
            "Schema Metadata", "generate_schema_queries", 100
        )
    
    def test_sp_documentation_generator(self):
        """SP Documentation generator produces records."""
        self._test_generator_produces_records(
            "SP Documentation", "generate_sp_examples", 100
        )
    
    def test_view_documentation_generator(self):
        """View Documentation generator produces records."""
        self._test_generator_produces_records(
            "View Documentation", "generate_view_examples", 100
        )

    def test_join_patterns_generator(self):
        """JOIN Patterns generator produces records."""
        self._test_generator_produces_records(
            "JOIN Patterns", "generate_join_pattern_examples", 50
        )

    def test_ddfi_forms_generator(self):
        """DDFI Forms generator produces records."""
        self._test_generator_produces_records(
            "DDFI Forms", "generate_ddfi_examples", 100
        )

    def test_crystal_report_sql_generator(self):
        """Crystal Report SQL generator produces records."""
        self._test_generator_produces_records(
            "Crystal Report SQL", "generate_crystal_report_examples", 100
        )

    def test_canonical_rules_generator(self):
        """Canonical Rules generator produces records."""
        self._test_generator_produces_records(
            "Canonical Rules", "generate_canonical_rules_examples", 10
        )

    def test_reference_documents_generator(self):
        """Reference Documents generator produces records."""
        self._test_generator_produces_records(
            "Reference Documents", "generate_reference_doc_examples", 20
        )

    def test_heuristics_generator(self):
        """Heuristics generator produces records."""
        self._test_generator_produces_records(
            "Heuristics", "generate_heuristic_examples", 10
        )

    def test_workflows_generator(self):
        """Workflows generator produces records."""
        self._test_generator_produces_records(
            "Workflows", "generate_workflow_examples", 10
        )

    def test_experts_v2_generator(self):
        """Experts V2 generator produces records."""
        self._test_generator_produces_records(
            "Experts V2", "generate_experts_v2_examples", 50
        )

    def test_naming_conventions_generator(self):
        """Naming Conventions generator produces records."""
        self._test_generator_produces_records(
            "Naming Conventions", "generate_naming_convention_examples", 5
        )

    def test_error_corrections_generator(self):
        """Error Corrections generator produces records."""
        self._test_generator_produces_records(
            "Error Corrections", "generate_error_correction_examples", 5
        )

    def test_query_optimization_generator(self):
        """Query Optimization generator produces records."""
        self._test_generator_produces_records(
            "Query Optimization", "generate_query_optimization_examples", 5
        )


class TestFullGeneration(unittest.TestCase):
    """Test full generation and validation pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.vgpt2_path = Path("C:/Github/VGPT2")
        if not cls.vgpt2_path.exists():
            raise unittest.SkipTest("VGPT2 path not found")

    def test_full_validation_passes(self):
        """Full generation must pass validation."""
        from generate_vgpt2_training_data import VGPT2DatasetGenerator
        from training_data_validation import validate_before_training

        generator = VGPT2DatasetGenerator(str(self.vgpt2_path))

        # Generate all records
        records = generator.generate_all()

        # Get source counts
        source_counts = {}
        for record in records:
            source = record.source
            source_counts[source] = source_counts.get(source, 0) + 1

        # Validate (don't abort, just get report)
        report = validate_before_training(
            records, source_counts, str(self.vgpt2_path),
            abort_on_failure=False
        )

        # Check no critical failures
        self.assertEqual(
            report.critical_failures, [],
            f"Critical validation failures:\n" +
            "\n".join(f"  - {f}" for f in report.critical_failures)
        )


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)

