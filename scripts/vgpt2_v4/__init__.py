# Copyright 2024-2025 Viewpoint, Inc.
# Licensed under the Apache License, Version 2.0.
#
# VGPT2 V4 Training Data Generation Package
#
# This package implements the "schema-in-prompt" training approach
# based on SQLCoder methodology for improved SQL generation.
#
# Key differences from V3:
# - Schema (DDL) included in every training prompt
# - Focus on SQL generation, not schema memorization
# - Quality over quantity (2,000 curated vs 67,000 auto-generated)
# - Proper negative examples for hallucination prevention

"""
VGPT2 V4 Training Data Generation Package

Modules:
    config: Configuration management and training categories
    ddl_extractor: Extract CREATE TABLE statements from metadata
    sql_generator: Generate SQL training examples
    negative_generator: Generate rejection/hallucination examples
    pipeline: Main orchestration pipeline
    evaluation: V4 evaluation framework
"""

__version__ = "4.0.0"
__author__ = "Viewpoint AI Team"

from .config import V4Config, TrainingCategory
from .ddl_extractor import DDLExtractor
from .sql_generator import SQLExampleGenerator
from .sql_generator_v2 import SQLExampleGeneratorV2
from .negative_generator import NegativeExampleGenerator
from .pipeline import V4Pipeline

__all__ = [
    "V4Config",
    "TrainingCategory",
    "DDLExtractor",
    "SQLExampleGenerator",
    "SQLExampleGeneratorV2",
    "NegativeExampleGenerator",
    "V4Pipeline",
]
