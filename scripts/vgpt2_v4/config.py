# Copyright 2024-2025 Viewpoint, Inc.
# Licensed under the Apache License, Version 2.0.

"""
V4 Configuration Module

Defines training categories, table priorities, and generation settings.
Uses YAML for external configuration with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml


class TrainingCategory(Enum):
    """Categories of training examples to generate."""
    AR_QUERIES = "ar_queries"           # Accounts Receivable
    AP_QUERIES = "ap_queries"           # Accounts Payable
    JC_QUERIES = "jc_queries"           # Job Cost
    SL_QUERIES = "sl_queries"           # Subcontracts
    PR_QUERIES = "pr_queries"           # Payroll
    GL_QUERIES = "gl_queries"           # General Ledger
    PM_QUERIES = "pm_queries"           # Project Management
    SM_QUERIES = "sm_queries"           # Service Management
    CROSS_MODULE = "cross_module"       # Multi-module joins
    NEGATIVE = "negative"               # Hallucination prevention
    EDGE_CASES = "edge_cases"           # Complex scenarios


@dataclass
class TableConfig:
    """Configuration for a single table."""
    name: str
    module: str
    description: str
    key_columns: List[str] = field(default_factory=list)
    common_joins: List[str] = field(default_factory=list)
    priority: int = 2  # 1=high, 2=medium, 3=low


@dataclass
class CategoryConfig:
    """Configuration for a training category."""
    name: str
    description: str
    primary_tables: List[str]
    target_count: int = 200
    include_negative: bool = True
    complexity_levels: List[str] = field(default_factory=lambda: ["basic", "intermediate", "advanced"])


@dataclass
class V4Config:
    """
    Main configuration for V4 training data generation.
    
    Can be loaded from YAML or constructed programmatically.
    """
    
    # Paths
    vgpt2_path: str = ""
    output_path: str = ""
    
    # Generation settings
    total_target_examples: int = 2500
    negative_example_ratio: float = 0.12  # 12% negative examples
    min_ddl_tables: int = 2
    max_ddl_tables: int = 6
    
    # Quality settings
    include_explanations: bool = True
    include_vista_patterns: bool = True  # WITH (NOLOCK), Co = @Co
    validate_sql_syntax: bool = True
    
    # Category configurations
    categories: Dict[str, CategoryConfig] = field(default_factory=dict)
    
    # Table configurations
    tables: Dict[str, TableConfig] = field(default_factory=dict)
    
    # Prompt templates
    system_prompt: str = ""
    user_prompt_template: str = ""
    
    @classmethod
    def load_from_yaml(cls, config_path: str) -> "V4Config":
        """Load configuration from YAML file."""
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        config = cls()
        
        # Load basic settings
        config.vgpt2_path = data.get("vgpt2_path", "")
        config.output_path = data.get("output_path", "")
        config.total_target_examples = data.get("total_target_examples", 2500)
        config.negative_example_ratio = data.get("negative_example_ratio", 0.12)
        config.min_ddl_tables = data.get("min_ddl_tables", 2)
        config.max_ddl_tables = data.get("max_ddl_tables", 6)
        config.include_explanations = data.get("include_explanations", True)
        config.include_vista_patterns = data.get("include_vista_patterns", True)
        config.validate_sql_syntax = data.get("validate_sql_syntax", True)
        
        # Load prompts
        prompts = data.get("prompts", {})
        config.system_prompt = prompts.get("system", DEFAULT_SYSTEM_PROMPT)
        config.user_prompt_template = prompts.get("user_template", DEFAULT_USER_PROMPT)
        
        # Load categories
        for cat_name, cat_data in data.get("categories", {}).items():
            config.categories[cat_name] = CategoryConfig(
                name=cat_name,
                description=cat_data.get("description", ""),
                primary_tables=cat_data.get("primary_tables", []),
                target_count=cat_data.get("target_count", 200),
                include_negative=cat_data.get("include_negative", True),
                complexity_levels=cat_data.get("complexity_levels", ["basic", "intermediate", "advanced"])
            )
        
        # Load tables
        for table_name, table_data in data.get("tables", {}).items():
            config.tables[table_name] = TableConfig(
                name=table_name,
                module=table_data.get("module", ""),
                description=table_data.get("description", ""),
                key_columns=table_data.get("key_columns", []),
                common_joins=table_data.get("common_joins", []),
                priority=table_data.get("priority", 2)
            )
        
        return config
    
    @classmethod
    def get_default(cls) -> "V4Config":
        """Get default configuration with standard Vista tables and categories."""
        config = cls()
        config.system_prompt = DEFAULT_SYSTEM_PROMPT
        config.user_prompt_template = DEFAULT_USER_PROMPT
        
        # Default categories
        config.categories = {
            TrainingCategory.AR_QUERIES.value: CategoryConfig(
                name="AR Queries",
                description="Accounts Receivable: Customers, invoices, payments, aging",
                primary_tables=["ARTH", "ARTL", "ARCM", "ARCO"],
                target_count=200
            ),
            TrainingCategory.AP_QUERIES.value: CategoryConfig(
                name="AP Queries",
                description="Accounts Payable: Vendors, invoices, holds, payments",
                primary_tables=["APTH", "APTL", "APTD", "APVM", "APCO", "APHD"],
                target_count=200
            ),
            TrainingCategory.JC_QUERIES.value: CategoryConfig(
                name="JC Queries",
                description="Job Cost: Jobs, phases, costs, estimates, projections",
                primary_tables=["JCJM", "JCJP", "JCCD", "JCCH", "JCCP", "JCCT", "JCCO"],
                target_count=300
            ),
            TrainingCategory.SL_QUERIES.value: CategoryConfig(
                name="SL Queries",
                description="Subcontracts: Subcontracts, items, billing, retainage",
                primary_tables=["SLHD", "SLIT", "SLWI", "SLCO"],
                target_count=200
            ),
            TrainingCategory.PR_QUERIES.value: CategoryConfig(
                name="PR Queries",
                description="Payroll: Employees, timecards, earnings, deductions",
                primary_tables=["PREH", "PRTH", "PRTD", "PRPC", "PRCO"],
                target_count=150
            ),
            TrainingCategory.GL_QUERIES.value: CategoryConfig(
                name="GL Queries",
                description="General Ledger: Accounts, transactions, balances",
                primary_tables=["GLDT", "GLJR", "GLAC", "GLCO"],
                target_count=150
            ),
            TrainingCategory.CROSS_MODULE.value: CategoryConfig(
                name="Cross-Module Joins",
                description="Queries spanning multiple Vista modules",
                primary_tables=["SLWI", "APTD", "JCCD", "ARTH"],
                target_count=300
            ),
            TrainingCategory.NEGATIVE.value: CategoryConfig(
                name="Negative Examples",
                description="Queries for non-existent tables - train rejection",
                primary_tables=[],
                target_count=300,
                include_negative=True
            ),
            TrainingCategory.EDGE_CASES.value: CategoryConfig(
                name="Edge Cases",
                description="Complex CTEs, aggregations, window functions",
                primary_tables=["JCCD", "APTH", "ARTH", "SLHD"],
                target_count=200
            ),
        }
        
        # Default table configurations (high priority tables)
        config.tables = DEFAULT_TABLE_CONFIGS
        
        return config
    
    def save_to_yaml(self, path: str) -> None:
        """Save configuration to YAML file."""
        data = {
            "vgpt2_path": self.vgpt2_path,
            "output_path": self.output_path,
            "total_target_examples": self.total_target_examples,
            "negative_example_ratio": self.negative_example_ratio,
            "min_ddl_tables": self.min_ddl_tables,
            "max_ddl_tables": self.max_ddl_tables,
            "include_explanations": self.include_explanations,
            "include_vista_patterns": self.include_vista_patterns,
            "validate_sql_syntax": self.validate_sql_syntax,
            "prompts": {
                "system": self.system_prompt,
                "user_template": self.user_prompt_template,
            },
            "categories": {},
            "tables": {},
        }
        
        for cat_name, cat_config in self.categories.items():
            data["categories"][cat_name] = {
                "description": cat_config.description,
                "primary_tables": cat_config.primary_tables,
                "target_count": cat_config.target_count,
                "include_negative": cat_config.include_negative,
                "complexity_levels": cat_config.complexity_levels,
            }
        
        for table_name, table_config in self.tables.items():
            data["tables"][table_name] = {
                "module": table_config.module,
                "description": table_config.description,
                "key_columns": table_config.key_columns,
                "common_joins": table_config.common_joins,
                "priority": table_config.priority,
            }
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


# =============================================================================
# DEFAULT PROMPTS
# =============================================================================

DEFAULT_SYSTEM_PROMPT = """You are a SQL expert for Viewpoint Vista, a construction ERP system.
Generate SQL queries based on the provided database schema.
Follow these rules:
1. Use WITH (NOLOCK) for all SELECT queries
2. Filter by company column (Co, APCo, ARCo, JCCo, etc.)
3. Use proper JOINs based on the schema relationships
4. If a table does not exist in the provided schema, say so clearly
5. Explain your query logic before providing the SQL"""

DEFAULT_USER_PROMPT = """Generate a SQL query to answer the following question.

Question: {question}

Database Schema:
{ddl_statements}

Provide:
1. A brief explanation of the approach
2. The SQL query
3. Any important notes about Vista-specific conventions used"""


# =============================================================================
# DEFAULT TABLE CONFIGURATIONS
# =============================================================================

DEFAULT_TABLE_CONFIGS = {
    # AR Tables
    "ARTH": TableConfig(
        name="ARTH",
        module="AR",
        description="AR Transaction Header - Invoice and payment headers",
        key_columns=["ARCo", "Mth", "ARTrans"],
        common_joins=["ARTL", "ARCM"],
        priority=1
    ),
    "ARTL": TableConfig(
        name="ARTL",
        module="AR",
        description="AR Transaction Line - Invoice line details",
        key_columns=["ARCo", "Mth", "ARTrans", "ARLine"],
        common_joins=["ARTH"],
        priority=1
    ),
    "ARCM": TableConfig(
        name="ARCM",
        module="AR",
        description="AR Customer Master - Customer information",
        key_columns=["CustGroup", "Customer"],
        common_joins=["ARTH"],
        priority=1
    ),
    
    # AP Tables
    "APTH": TableConfig(
        name="APTH",
        module="AP",
        description="AP Transaction Header - Vendor invoice headers",
        key_columns=["APCo", "Mth", "APTrans"],
        common_joins=["APTL", "APTD", "APVM"],
        priority=1
    ),
    "APTL": TableConfig(
        name="APTL",
        module="AP",
        description="AP Transaction Line - Invoice line details",
        key_columns=["APCo", "Mth", "APTrans", "APLine"],
        common_joins=["APTH", "APTD"],
        priority=1
    ),
    "APTD": TableConfig(
        name="APTD",
        module="AP",
        description="AP Transaction Detail - Payment details and retainage",
        key_columns=["APCo", "Mth", "APTrans", "APLine", "APSeq"],
        common_joins=["APTL", "APTH"],
        priority=1
    ),
    "APVM": TableConfig(
        name="APVM",
        module="AP",
        description="AP Vendor Master - Vendor information",
        key_columns=["VendorGroup", "Vendor"],
        common_joins=["APTH", "SLHD"],
        priority=1
    ),
    "APHD": TableConfig(
        name="APHD",
        module="AP",
        description="AP Hold Detail - Invoice hold information",
        key_columns=["APCo", "Mth", "APTrans", "APLine", "HoldCode"],
        common_joins=["APTD", "APCO"],
        priority=2
    ),
    "APCO": TableConfig(
        name="APCO",
        module="AP",
        description="AP Company Settings - Company-level AP configuration",
        key_columns=["APCo"],
        common_joins=["APTH", "APHD"],
        priority=2
    ),
    
    # JC Tables
    "JCJM": TableConfig(
        name="JCJM",
        module="JC",
        description="JC Job Master - Job/project header information",
        key_columns=["JCCo", "Job"],
        common_joins=["JCJP", "JCCD", "JCCM"],
        priority=1
    ),
    "JCJP": TableConfig(
        name="JCJP",
        module="JC",
        description="JC Job Phase - Job phase definitions for billing",
        key_columns=["JCCo", "Job", "PhaseGroup", "Phase"],
        common_joins=["JCCP", "JCJM"],
        priority=1
    ),
    "JCCD": TableConfig(
        name="JCCD",
        module="JC",
        description="JC Cost Detail - Actual job costs posted",
        key_columns=["JCCo", "Mth", "CostTrans"],
        common_joins=["JCJM", "JCCP"],
        priority=1
    ),
    "JCCH": TableConfig(
        name="JCCH",
        module="JC",
        description="JC Cost Header - Cost code header with unit flags",
        key_columns=["JCCo", "Job", "PhaseGroup", "Phase", "CostType"],
        common_joins=["JCCP", "JCCT"],
        priority=1
    ),
    "JCCP": TableConfig(
        name="JCCP",
        module="JC",
        description="JC Cost Phase - Cost tracking by phase with estimates",
        key_columns=["JCCo", "Job", "PhaseGroup", "Phase", "CostType"],
        common_joins=["JCCH", "JCJP", "JCCT"],
        priority=1
    ),
    "JCCT": TableConfig(
        name="JCCT",
        module="JC",
        description="JC Cost Type - Cost type definitions",
        key_columns=["PhaseGroup", "CostType"],
        common_joins=["JCCP", "JCCH"],
        priority=2
    ),
    
    # SL Tables
    "SLHD": TableConfig(
        name="SLHD",
        module="SL",
        description="SL Header - Subcontract header information",
        key_columns=["SLCo", "SL"],
        common_joins=["SLIT", "SLWI", "APVM"],
        priority=1
    ),
    "SLIT": TableConfig(
        name="SLIT",
        module="SL",
        description="SL Item - Subcontract line items with costs",
        key_columns=["SLCo", "SL", "SLItem"],
        common_joins=["SLHD", "SLWI"],
        priority=1
    ),
    "SLWI": TableConfig(
        name="SLWI",
        module="SL",
        description="SL Work Item - Billing worksheets with retainage",
        key_columns=["SLCo", "SL", "SLItem", "WIType", "WINum"],
        common_joins=["SLIT", "APTD"],
        priority=1
    ),
    
    # PR Tables
    "PREH": TableConfig(
        name="PREH",
        module="PR",
        description="PR Employee Header - Employee master data",
        key_columns=["PRCo", "Employee"],
        common_joins=["PRTH", "PRPC"],
        priority=1
    ),
    "PRTH": TableConfig(
        name="PRTH",
        module="PR",
        description="PR Timecard Header - Timecard headers",
        key_columns=["PRCo", "PRGroup", "PREndDate", "Employee", "PaySeq"],
        common_joins=["PREH", "PRTD"],
        priority=1
    ),
    
    # GL Tables
    "GLDT": TableConfig(
        name="GLDT",
        module="GL",
        description="GL Detail - General ledger transaction details",
        key_columns=["GLCo", "Mth", "GLTrans"],
        common_joins=["GLAC", "GLJR"],
        priority=1
    ),
    "GLAC": TableConfig(
        name="GLAC",
        module="GL",
        description="GL Account - Chart of accounts",
        key_columns=["GLCo", "GLAcct"],
        common_joins=["GLDT"],
        priority=2
    ),
    
    # HQ Tables
    "HQCO": TableConfig(
        name="HQCO",
        module="HQ",
        description="HQ Company - Company master information",
        key_columns=["HQCo"],
        common_joins=["JCCO", "APCO", "ARCO"],
        priority=2
    ),
}
