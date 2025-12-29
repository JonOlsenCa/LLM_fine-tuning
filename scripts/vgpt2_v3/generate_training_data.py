#!/usr/bin/env python3
"""
VGPT2 v3 Training Data Generator
=================================
Generates expanded training data for VGPT2 v3 fine-tuning.

This generator produces 100K+ training records from:
- Schema metadata (columns, tables, views)
- Stored procedure documentation
- View documentation
- Table documentation
- Function documentation
- Crystal Report SQL
- Relationship validation data
- Canonical rules and heuristics
- Expert SQL examples

Usage:
    python scripts/vgpt2_v3/generate_training_data.py --output data/vgpt2_v3_sft.json

    # Generate sample for testing
    python scripts/vgpt2_v3/generate_training_data.py --max-per-source 100 --output data/test_sample.json
"""

import json
import sys
import os
import logging
import random
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Iterator, Set
from enum import Enum
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCategory(Enum):
    """Categories for training data."""
    SCHEMA_QUERY = "schema_query"
    SQL_GENERATION = "sql_generation"
    SQL_VALIDATION = "sql_validation"
    BUSINESS_CONTEXT = "business_context"
    JOIN_PATTERN = "join_pattern"
    NEGATIVE_EXAMPLE = "negative_example"
    ERROR_CORRECTION = "error_correction"
    NAMING_CONVENTION = "naming_convention"


@dataclass
class TrainingRecord:
    """Single training record in Alpaca format."""
    instruction: str
    input: str = ""
    output: str = ""
    category: str = ""
    source: str = ""

    def to_alpaca(self) -> Dict:
        """Convert to Alpaca format."""
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output
        }


class VGPT2V3DataGenerator:
    """
    Expanded data generator for VGPT2 v3.

    Targets 100K+ records with comprehensive coverage.
    """

    def __init__(self, vgpt2_path: str, vista_kb_path: Optional[str] = None):
        self.vgpt2 = Path(vgpt2_path)
        self.vista_kb = Path(vista_kb_path) if vista_kb_path else None

        # Key directories
        self.metadata_dir = self.vgpt2 / "Viewpoint_Database" / "_Metadata"
        self.sp_docs_dir = self.vgpt2 / "Viewpoint_Database" / "Stored_Procedures" / "SP_Documentation"
        self.view_docs_dir = self.vgpt2 / "Viewpoint_Database" / "View" / "View_Documentation"
        self.table_docs_dir = self.vgpt2 / "Viewpoint_Database" / "Tables"
        self.function_docs_dir = self.vgpt2 / "Viewpoint_Database" / "Functions"
        self.relationship_dir = self.vgpt2 / "Viewpoint_Database" / "_Relationship_Validation"
        self.ai_orchestration_dir = self.vgpt2 / "_ai_orchestration"
        self.crystal_dir = self.vgpt2 / "Crystal_Reports_Documentation" / "_Extracted_SQL"
        self.experts_dir = self.vgpt2 / "Experts_V2"

        # Caches
        self._columns_cache = None
        self._ddfi_cache = None
        self._tables_list_cache = None

        # Statistics
        self.stats = {}

        logger.info(f"Initialized VGPT2V3DataGenerator with path: {vgpt2_path}")

    # =========================================================================
    # DATA LOADING
    # =========================================================================

    def load_columns(self) -> List[Dict]:
        """Load columns.json."""
        if self._columns_cache is None:
            columns_file = self.metadata_dir / "columns.json"
            if columns_file.exists():
                with open(columns_file, 'r', encoding='utf-8') as f:
                    self._columns_cache = json.load(f)
                logger.info(f"Loaded {len(self._columns_cache)} column definitions")
            else:
                self._columns_cache = []
        return self._columns_cache

    def load_ddfi(self) -> List[Dict]:
        """Load DDFI.json (form field definitions)."""
        if self._ddfi_cache is None:
            ddfi_file = self.metadata_dir / "DDFI.json"
            if ddfi_file.exists():
                with open(ddfi_file, 'r', encoding='utf-8') as f:
                    self._ddfi_cache = json.load(f)
                logger.info(f"Loaded {len(self._ddfi_cache)} DDFI field definitions")
            else:
                self._ddfi_cache = []
        return self._ddfi_cache

    def load_tables_list(self) -> List[Dict]:
        """Load complete tables/views list."""
        if self._tables_list_cache is None:
            tables_file = self.metadata_dir / "_Viewpoint_ALL_Views_Tables_Complete.json"
            if tables_file.exists():
                with open(tables_file, 'r', encoding='utf-8') as f:
                    self._tables_list_cache = json.load(f)
            else:
                self._tables_list_cache = []
        return self._tables_list_cache

    # =========================================================================
    # GENERATION METHODS
    # =========================================================================

    def generate_all(self, max_per_source: Optional[int] = None) -> List[TrainingRecord]:
        """Generate all training records."""
        all_records = []

        generators = [
            ("Schema Columns (Extended)", self.generate_extended_schema_examples),
            ("SP Documentation", self.generate_sp_examples),
            ("View Documentation", self.generate_view_examples),
            ("Table Documentation", self.generate_table_doc_examples),
            ("Function Documentation", self.generate_function_examples),
            ("DDFI Forms (Extended)", self.generate_extended_ddfi_examples),
            ("JOIN Patterns", self.generate_join_examples),
            ("Crystal Report SQL", self.generate_crystal_examples),
            ("Canonical Rules", self.generate_canonical_rules),
            ("Reference Documents", self.generate_reference_docs),
            ("Heuristics", self.generate_heuristic_examples),
            ("Workflows", self.generate_workflow_examples),
            ("Experts V2", self.generate_experts_v2_examples),
            ("Naming Conventions", self.generate_naming_conventions),
            ("Error Corrections", self.generate_error_corrections),
            ("Query Optimization", self.generate_optimization_examples),
            ("SQL Generation", self.generate_sql_generation_examples),
            ("Module Overview", self.generate_module_overview_examples),
            # New generators added for v3.1
            ("Trigger Documentation", self.generate_trigger_examples),
            ("Index Metadata", self.generate_index_examples),
            ("Constraint Metadata", self.generate_constraint_examples),
            ("SQL Patterns", self.generate_more_sql_examples),
            ("Column Usage", self.generate_column_usage_examples),
            # New generators for v3.3 - Address NOLOCK, SQL coverage, short outputs
            ("NOLOCK Best Practices", self.generate_nolock_examples),
            ("SQL Generation Expanded", self.generate_expanded_sql_examples),
            ("Extended Schema Explanations", self.generate_extended_schema_explanations),
            # Additional generators to significantly boost NOLOCK and SQL coverage
            ("Table Query Examples", self.generate_table_query_examples),
            ("NOLOCK Fix Examples", self.generate_nolock_fix_examples),
        ]

        for name, generator in generators:
            logger.info(f"Generating {name}...")
            try:
                records = list(generator(max_per_source))
                all_records.extend(records)
                self.stats[name] = len(records)
                logger.info(f"  -> {len(records)} records")
            except Exception as e:
                logger.error(f"Error generating {name}: {e}")
                self.stats[name] = 0

        logger.info(f"\nTotal records generated: {len(all_records)}")
        return all_records

    def generate_extended_schema_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate comprehensive schema examples."""
        columns = self.load_columns()
        count = 0

        # Group by table
        tables = {}
        for col in columns:
            if not isinstance(col, dict):
                continue
            obj_name = col.get('ObjectName', 'unknown')
            if obj_name not in tables:
                tables[obj_name] = {
                    'columns': [],
                    'module': col.get('Module', 'Unknown'),
                    'schema': col.get('SchemaName', 'dbo'),
                    'type': col.get('ObjectType', 'Table')
                }
            tables[obj_name]['columns'].append(col)

        for table_name, info in tables.items():
            if max_records and count >= max_records:
                break

            cols = info['columns']
            module = info['module']
            obj_type = info['type'].lower()

            # Type 1: List all columns
            col_names = [c.get('ColumnName', '') for c in cols[:20]]
            col_list = ", ".join(col_names)
            if len(cols) > 20:
                col_list += f"... ({len(cols)} total)"

            yield TrainingRecord(
                instruction=f"What columns are in the {table_name} {obj_type}?",
                output=f"The {table_name} {obj_type} (Module: {module}) contains: {col_list}",
                category=DataCategory.SCHEMA_QUERY.value,
                source="columns.json"
            )
            count += 1

            # Type 2: Describe specific columns with types
            if len(cols) >= 3 and count < (max_records or float('inf')):
                detail_cols = cols[:5]
                details = []
                for c in detail_cols:
                    nullable = "nullable" if c.get('IsNullable') == 'True' else "not null"
                    details.append(f"- {c.get('ColumnName')} ({c.get('DataType')}, {nullable})")

                yield TrainingRecord(
                    instruction=f"Describe the key columns in {table_name}",
                    output=f"Key columns in {table_name}:\n" + "\n".join(details),
                    category=DataCategory.SCHEMA_QUERY.value,
                    source="columns.json"
                )
                count += 1

            # Type 3: Data type questions
            for col in cols[:2]:
                if max_records and count >= max_records:
                    break
                yield TrainingRecord(
                    instruction=f"What is the data type of {col.get('ColumnName')} in {table_name}?",
                    output=f"The {col.get('ColumnName')} column in {table_name} has data type {col.get('DataType')}.",
                    category=DataCategory.SCHEMA_QUERY.value,
                    source="columns.json"
                )
                count += 1

            # Type 4: Primary key questions
            pk_cols = [c for c in cols if c.get('IsPrimaryKey') == 'True']
            if pk_cols and count < (max_records or float('inf')):
                pk_names = ", ".join(c.get('ColumnName', '') for c in pk_cols)
                yield TrainingRecord(
                    instruction=f"What is the primary key of {table_name}?",
                    output=f"The primary key of {table_name} is: {pk_names}",
                    category=DataCategory.SCHEMA_QUERY.value,
                    source="columns.json"
                )
                count += 1

    def generate_sp_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate stored procedure examples."""
        if not self.sp_docs_dir.exists():
            return

        count = 0
        for md_file in self.sp_docs_dir.glob("*.md"):
            if max_records and count >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                sp_name = md_file.stem

                # Extract overview
                overview = self._extract_section(content, "## Overview", "##")
                if overview and len(overview) > 50:
                    yield TrainingRecord(
                        instruction=f"What does the stored procedure {sp_name} do?",
                        output=overview.strip()[:2000],
                        category=DataCategory.BUSINESS_CONTEXT.value,
                        source="SP_Documentation"
                    )
                    count += 1

                # Extract parameters
                params = self._extract_section(content, "## Parameters", "##")
                if params and count < (max_records or float('inf')):
                    yield TrainingRecord(
                        instruction=f"What parameters does {sp_name} accept?",
                        output=params.strip()[:2000],
                        category=DataCategory.BUSINESS_CONTEXT.value,
                        source="SP_Documentation"
                    )
                    count += 1

            except Exception as e:
                logger.warning(f"Error processing SP {md_file}: {e}")

    def generate_view_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate view documentation examples."""
        if not self.view_docs_dir.exists():
            return

        count = 0
        for md_file in self.view_docs_dir.glob("*.md"):
            if max_records and count >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                view_name = md_file.stem

                # Overview
                overview = self._extract_section(content, "## Overview", "##")
                if overview:
                    yield TrainingRecord(
                        instruction=f"What is the purpose of the {view_name} view?",
                        output=overview.strip()[:2000],
                        category=DataCategory.BUSINESS_CONTEXT.value,
                        source="View_Documentation"
                    )
                    count += 1

                # Tables used
                tables_section = self._extract_section(content, "## Tables Used", "##")
                if tables_section and count < (max_records or float('inf')):
                    yield TrainingRecord(
                        instruction=f"What tables does the {view_name} view use?",
                        output=tables_section.strip()[:1500],
                        category=DataCategory.SCHEMA_QUERY.value,
                        source="View_Documentation"
                    )
                    count += 1

            except Exception as e:
                logger.warning(f"Error processing view {md_file}: {e}")

    def generate_table_doc_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate table documentation examples."""
        if not self.table_docs_dir.exists():
            return

        count = 0
        for md_file in self.table_docs_dir.rglob("*.md"):
            if max_records and count >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                table_name = md_file.stem

                # Skip if too short
                if len(content) < 100:
                    continue

                yield TrainingRecord(
                    instruction=f"Describe the {table_name} table in Viewpoint Vista",
                    output=content[:3000],
                    category=DataCategory.BUSINESS_CONTEXT.value,
                    source="Table_Documentation"
                )
                count += 1

            except Exception as e:
                logger.warning(f"Error processing table {md_file}: {e}")

    def generate_function_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate function documentation examples."""
        func_docs = self.function_docs_dir / "Function_Documentation" if self.function_docs_dir.exists() else None
        if not func_docs or not func_docs.exists():
            return

        count = 0
        for md_file in func_docs.glob("*.md"):
            if max_records and count >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                func_name = md_file.stem

                if len(content) < 100:
                    continue

                yield TrainingRecord(
                    instruction=f"What does the {func_name} function do in Viewpoint?",
                    output=content[:2000],
                    category=DataCategory.BUSINESS_CONTEXT.value,
                    source="Function_Documentation"
                )
                count += 1

            except Exception as e:
                logger.warning(f"Error processing function {md_file}: {e}")

    def generate_extended_ddfi_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate extended DDFI form field examples."""
        ddfi = self.load_ddfi()
        count = 0

        # Group by form
        forms = {}
        for field in ddfi:
            form = field.get('Form', 'unknown')
            if form not in forms:
                forms[form] = []
            forms[form].append(field)

        for form_name, fields in forms.items():
            if max_records and count >= max_records:
                break

            # Filter to fields with descriptions
            useful_fields = [f for f in fields if f.get('Description') and f.get('Description') != 'NULL']
            if not useful_fields:
                continue

            # Form overview
            field_names = [f.get('Description', '')[:50] for f in useful_fields[:15]]
            yield TrainingRecord(
                instruction=f"What fields are available on the {form_name} form in Viewpoint?",
                output=f"The {form_name} form includes: {', '.join(field_names)}",
                category=DataCategory.BUSINESS_CONTEXT.value,
                source="DDFI.json"
            )
            count += 1

            # Individual field details
            for field in useful_fields[:3]:
                if max_records and count >= max_records:
                    break

                desc = field.get('Description', '')
                col = field.get('ColumnName', '')
                tab = field.get('Tab', '')

                if desc and col:
                    yield TrainingRecord(
                        instruction=f"What is the {desc} field on the {form_name} form?",
                        output=f"The '{desc}' field on {form_name} (Tab: {tab}) maps to column {col} in the database.",
                        category=DataCategory.BUSINESS_CONTEXT.value,
                        source="DDFI.json"
                    )
                    count += 1

    def generate_join_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate JOIN pattern examples."""
        join_recipes_dir = self.relationship_dir / "03_Join_Recipes"
        if not join_recipes_dir.exists():
            return

        count = 0
        for json_file in join_recipes_dir.glob("*.json"):
            if max_records and count >= max_records:
                break

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    recipe = json.load(f)

                view_name = recipe.get('view', json_file.stem)
                hops = recipe.get('hops', [])

                for hop in hops:
                    if max_records and count >= max_records:
                        break

                    from_table = hop.get('from', '').replace('dbo.', '')
                    to_table = hop.get('to', '').replace('dbo.', '')
                    join_type = hop.get('join_type', 'INNER')
                    left_cols = hop.get('left_on', [])
                    right_cols = hop.get('right_on', [])

                    # Skip CTEs
                    if 'cte_' in from_table.lower() or 'cte_' in to_table.lower():
                        continue

                    if not left_cols or not right_cols:
                        continue

                    # Build JOIN condition
                    conditions = []
                    for l, r in zip(left_cols, right_cols):
                        conditions.append(f"{from_table}.{l} = {to_table}.{r}")

                    sql = f"FROM {from_table} WITH (NOLOCK)\n{join_type} JOIN {to_table} WITH (NOLOCK)\n  ON " + "\n  AND ".join(conditions)

                    yield TrainingRecord(
                        instruction=f"How do I join {from_table} with {to_table} in Viewpoint Vista?",
                        output=f"To join {from_table} with {to_table}:\n\n```sql\n{sql}\n```\n\nThis pattern is used in the {view_name} view.",
                        category=DataCategory.JOIN_PATTERN.value,
                        source="03_Join_Recipes"
                    )
                    count += 1

            except Exception as e:
                logger.warning(f"Error processing join recipe {json_file}: {e}")

    def generate_crystal_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate Crystal Report SQL examples."""
        reformatted_dir = self.crystal_dir / "Reformatted"
        if not reformatted_dir.exists():
            return

        count = 0
        for sql_file in reformatted_dir.glob("*.sql"):
            if max_records and count >= max_records:
                break

            try:
                content = sql_file.read_text(encoding='utf-8')
                report_name = sql_file.stem

                if len(content.strip()) < 50:
                    continue

                # Truncate very long SQL
                sql_content = content.strip()[:4000]

                yield TrainingRecord(
                    instruction=f"Show me the SQL used in the {report_name} Crystal Report",
                    output=f"The {report_name} Crystal Report uses:\n\n```sql\n{sql_content}\n```",
                    category=DataCategory.SQL_GENERATION.value,
                    source="Crystal_Reports_SQL"
                )
                count += 1

            except Exception as e:
                logger.warning(f"Error processing Crystal Report {sql_file}: {e}")

    def generate_canonical_rules(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate canonical SQL rules examples."""
        # Hardcoded comprehensive rules
        rules = [
            {
                "q": "What is the correct way to reference tables in Viewpoint Vista SQL?",
                "a": """In Viewpoint Vista:
- Use view names (APTH) not base tables (bAPTH) for SELECT queries
- Don't use schema prefix (dbo.) for views - they default to dbo
- Always use WITH (NOLOCK) after view names: FROM APTH WITH (NOLOCK)
- Use exact column case from the database (APCo, not apco)
- Viewpoint uses Latin1_General_BIN collation (case-sensitive)"""
            },
            {
                "q": "What naming convention do Viewpoint table prefixes follow?",
                "a": """Viewpoint table/view prefixes indicate the module:
- AP = Accounts Payable
- AR = Accounts Receivable
- GL = General Ledger
- JC = Job Cost
- PR = Payroll
- PM = Project Management
- EM = Equipment Management
- IN = Inventory
- SM = Service Management
- HR = Human Resources
- HQ = Headquarters (company-wide settings)
- MS = Material Sales
- PO = Purchase Orders
- SL = Subcontracts"""
            },
            {
                "q": "What's the difference between b-prefixed and non-prefixed tables?",
                "a": """In Viewpoint Vista:
- b-prefixed tables (bAPTH) are base/physical tables used for data modification
- Non-prefixed names (APTH) are views built on base tables
- Always use views for SELECT queries (better performance, security)
- Use base tables only when inserting/updating data
- Views enforce Viewpoint's Data Type Security and Row-Level Security"""
            },
            {
                "q": "How should I handle company context in Viewpoint queries?",
                "a": """Most Viewpoint tables use company columns:
- APCo = AP Company
- JCCo = Job Cost Company
- PRCo = Payroll Company
- GLCo = GL Company
- HQCo = Headquarters Company

Always filter by company in WHERE clause or JOIN conditions to ensure data isolation between companies."""
            },
            {
                "q": "Why must I use WITH (NOLOCK) in Viewpoint queries?",
                "a": """WITH (NOLOCK) is required for SELECT queries because:
- Prevents blocking production transactions
- Viewpoint's batch processing uses exclusive locks
- Reports should never block data entry
- Only omit NOLOCK when you specifically need transactional consistency

Example:
SELECT * FROM APTH WITH (NOLOCK) WHERE APCo = 1"""
            },
            {
                "q": "Should I use table aliases in Viewpoint SQL?",
                "a": """No. Viewpoint standards prohibit table aliases because:
- Full table names are easier to validate
- Case sensitivity issues are more visible
- Queries are self-documenting

Wrong: SELECT a.* FROM APTH a WHERE a.APCo = 1
Right: SELECT APTH.* FROM APTH WITH (NOLOCK) WHERE APTH.APCo = 1"""
            },
            {
                "q": "How are dates stored in Viewpoint Vista?",
                "a": """Viewpoint date handling:
- Month (Mth) columns store first day of month as datetime
- For example, January 2024 is stored as '2024-01-01 00:00:00'
- Date columns use datetime type
- For month comparisons: WHERE Mth = '2024-01-01'
- For date ranges: WHERE Date >= @StartDate AND Date < @EndDate"""
            },
            {
                "q": "What are vrv* and brv* views in Viewpoint?",
                "a": """Viewpoint reporting views:
- vrv* = Viewpoint Report Views (optimized for reporting)
- brv* = Base Report Views

These are pre-built views designed for Crystal Reports. Always check if a vrv* view exists before writing custom SQL - they're optimized and validated.

Examples:
- brvJCCostRevenue - Job Cost and Revenue
- vrvAPAgingDetail - AP Aging Detail
- vrvARAgingSummary - AR Aging Summary"""
            },
        ]

        count = 0
        for rule in rules:
            if max_records and count >= max_records:
                break
            yield TrainingRecord(
                instruction=rule["q"],
                output=rule["a"],
                category=DataCategory.NAMING_CONVENTION.value,
                source="Canonical_Rules"
            )
            count += 1

    def generate_reference_docs(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate reference document examples."""
        ref_dir = self.ai_orchestration_dir / "reference"
        if not ref_dir.exists():
            return

        count = 0
        for md_file in ref_dir.glob("*.md"):
            if max_records and count >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                doc_name = md_file.stem.replace('Viewpoint', '').replace('_', ' ').strip()

                if len(content) < 200:
                    continue

                yield TrainingRecord(
                    instruction=f"How does {doc_name} work in Viewpoint Vista?",
                    output=content[:3000],
                    category=DataCategory.BUSINESS_CONTEXT.value,
                    source="Reference_Documents"
                )
                count += 1

            except Exception as e:
                logger.warning(f"Error processing reference doc {md_file}: {e}")

    def generate_heuristic_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate heuristic examples."""
        heuristics_dir = self.ai_orchestration_dir / "heuristics"
        if not heuristics_dir.exists():
            return

        count = 0
        for md_file in heuristics_dir.glob("*.md"):
            if max_records and count >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                name = md_file.stem.replace('HE_', '').replace('_', ' ')

                yield TrainingRecord(
                    instruction=f"What is the heuristic for {name} in Viewpoint?",
                    output=content[:2500],
                    category=DataCategory.BUSINESS_CONTEXT.value,
                    source="Heuristics"
                )
                count += 1

            except Exception as e:
                logger.warning(f"Error processing heuristic {md_file}: {e}")

    def generate_workflow_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate workflow examples."""
        workflows_dir = self.ai_orchestration_dir / "workflows"
        if not workflows_dir.exists():
            return

        count = 0
        for md_file in workflows_dir.glob("*.md"):
            if max_records and count >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                name = md_file.stem.replace('WF_', '').replace('_', ' ')

                yield TrainingRecord(
                    instruction=f"What is the workflow for {name}?",
                    output=content[:2500],
                    category=DataCategory.BUSINESS_CONTEXT.value,
                    source="Workflows"
                )
                count += 1

            except Exception as e:
                logger.warning(f"Error processing workflow {md_file}: {e}")

    def generate_experts_v2_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate Expert V2 SQL examples."""
        if not self.experts_dir.exists():
            return

        count = 0
        for sql_file in self.experts_dir.rglob("*.sql"):
            if max_records and count >= max_records:
                break

            if sql_file.name.startswith("00_validate"):
                continue

            try:
                content = sql_file.read_text(encoding='utf-8')

                if len(content.strip()) < 50:
                    continue

                # Get purpose from comments or filename
                purpose = sql_file.stem.replace("_", " ")
                lines = content.split('\n')
                for line in lines[:10]:
                    if 'Purpose:' in line:
                        purpose = line.split('Purpose:')[1].strip()
                        break

                yield TrainingRecord(
                    instruction=f"Write a SQL query to: {purpose}",
                    input="Viewpoint Vista database",
                    output=content.strip()[:4000],
                    category=DataCategory.SQL_GENERATION.value,
                    source="Experts_V2"
                )
                count += 1

            except Exception as e:
                logger.warning(f"Error processing expert SQL {sql_file}: {e}")

    def generate_naming_conventions(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate naming convention examples."""
        conventions = [
            {
                "q": "What columns are commonly used for JOINs in Viewpoint?",
                "a": """Common JOIN columns in Viewpoint:
- Company columns (APCo, JCCo, PRCo, GLCo)
- Key sequences (KeyID, Seq, Line)
- Reference numbers (Invoice, PO, Job, Contract)
- Month columns (Mth - stored as datetime)
- VendorGroup + Vendor for vendor JOINs
- CustGroup + Customer for customer JOINs

Always check foreign_keys.json or relationship cards for validated JOIN patterns."""
            },
            {
                "q": "How do Groups work in Viewpoint master tables?",
                "a": """Master tables like APVM (vendors), ARCM (customers) use Groups instead of companies:
- Multiple companies can share the same VendorGroup or CustGroup
- Join through the transaction table or look up the Group from HQCO
- APVM uses VendorGroup + Vendor as its key
- ARCM uses CustGroup + Customer as its key

Wrong: SELECT * FROM APVM WHERE APCo = 1
Right: SELECT APVM.* FROM APTH WITH (NOLOCK) INNER JOIN APVM WITH (NOLOCK) ON APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor WHERE APTH.APCo = 1"""
            },
            {
                "q": "What status codes are used in Viewpoint AP?",
                "a": """AP transaction status codes in APTH:
- 0 = Open (unpaid)
- 1 = Fully Paid
- 2 = Cleared
- 3 = Voided

To find unpaid invoices:
SELECT * FROM APTH WITH (NOLOCK) WHERE APCo = @APCo AND Status = 0"""
            },
        ]

        count = 0
        for conv in conventions:
            if max_records and count >= max_records:
                break
            yield TrainingRecord(
                instruction=conv["q"],
                output=conv["a"],
                category=DataCategory.NAMING_CONVENTION.value,
                source="Naming_Conventions"
            )
            count += 1

    def generate_error_corrections(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate error correction examples."""
        corrections = [
            {
                "wrong": "SELECT * FROM dbo.APTH",
                "right": "SELECT * FROM APTH WITH (NOLOCK)",
                "explanation": "Don't use 'dbo.' prefix. Add WITH (NOLOCK) for read queries."
            },
            {
                "wrong": "SELECT * FROM bAPTH WHERE APCo = 1",
                "right": "SELECT * FROM APTH WITH (NOLOCK) WHERE APCo = 1",
                "explanation": "Use views (APTH) not base tables (bAPTH) for SELECT queries."
            },
            {
                "wrong": "SELECT apco, vendor FROM APTH",
                "right": "SELECT APCo, Vendor FROM APTH WITH (NOLOCK)",
                "explanation": "Use exact column case. Viewpoint is case-sensitive."
            },
            {
                "wrong": "WHERE Mth = '2024-01'",
                "right": "WHERE Mth = '2024-01-01'",
                "explanation": "Month columns store first day of month. Use '2024-01-01' format."
            },
            {
                "wrong": "FROM APTH a JOIN APTL b ON a.APTrans = b.APTrans",
                "right": "FROM APTH WITH (NOLOCK) JOIN APTL WITH (NOLOCK) ON APTH.APCo = APTL.APCo AND APTH.Mth = APTL.Mth AND APTH.APTrans = APTL.APTrans",
                "explanation": "No aliases. Include company + month in JOIN. Add WITH (NOLOCK)."
            },
            {
                "wrong": "SELECT Job FROM JCCD WHERE Job LIKE '%100%'",
                "right": "SELECT Job FROM JCCD WITH (NOLOCK) WHERE JCCo = @JCCo AND Job LIKE '%100%'",
                "explanation": "Always filter by company column for data isolation."
            },
        ]

        count = 0
        for ec in corrections:
            if max_records and count >= max_records:
                break
            yield TrainingRecord(
                instruction="Fix this Viewpoint Vista SQL query:",
                input=ec["wrong"],
                output=f"Corrected SQL:\n```sql\n{ec['right']}\n```\n\nExplanation: {ec['explanation']}",
                category=DataCategory.ERROR_CORRECTION.value,
                source="Error_Corrections"
            )
            count += 1

    def generate_optimization_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate query optimization examples."""
        optimizations = [
            {
                "scenario": "Query selects all columns unnecessarily",
                "before": "SELECT * FROM APTH WITH (NOLOCK) WHERE APCo = 1",
                "after": "SELECT APCo, Mth, APTrans, Vendor, InvNum, GrossAmt\nFROM APTH WITH (NOLOCK)\nWHERE APCo = 1",
                "tip": "Only select needed columns to reduce I/O."
            },
            {
                "scenario": "Check for reporting views before custom JOINs",
                "before": "SELECT h.*, d.*\nFROM APTH h JOIN APTL d ON h.APCo = d.APCo...",
                "after": "SELECT * FROM vrvAPTransactionDetail WITH (NOLOCK) WHERE APCo = @APCo",
                "tip": "Use vrv*/brv* reporting views when available - they're pre-optimized."
            },
            {
                "scenario": "Date function prevents index usage",
                "before": "WHERE YEAR(ActDate) = 2024",
                "after": "WHERE ActDate >= '2024-01-01' AND ActDate < '2025-01-01'",
                "tip": "Avoid functions on columns in WHERE - use range comparisons."
            },
        ]

        count = 0
        for opt in optimizations:
            if max_records and count >= max_records:
                break
            yield TrainingRecord(
                instruction=f"Optimize this Viewpoint SQL query. Scenario: {opt['scenario']}",
                input=opt["before"],
                output=f"Optimized SQL:\n```sql\n{opt['after']}\n```\n\nTip: {opt['tip']}",
                category=DataCategory.SQL_VALIDATION.value,
                source="Query_Optimization"
            )
            count += 1

    def generate_sql_generation_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate SQL from natural language examples."""
        examples = [
            {
                "q": "Get all unpaid AP invoices for company 1",
                "sql": """SELECT APCo, Mth, APTrans, Vendor, InvNum, InvDate, GrossAmt
FROM APTH WITH (NOLOCK)
WHERE APCo = 1
  AND Status = 0
ORDER BY InvDate DESC"""
            },
            {
                "q": "Find all jobs for company 5 that are active",
                "sql": """SELECT JCCo, Job, Description, Contract, JobStatus
FROM JCJM WITH (NOLOCK)
WHERE JCCo = 5
  AND JobStatus = 1
ORDER BY Job"""
            },
            {
                "q": "Get vendor information for vendor 12345",
                "sql": """SELECT VendorGroup, Vendor, Name, Address, City, State, Zip, Phone
FROM APVM WITH (NOLOCK)
WHERE Vendor = 12345"""
            },
            {
                "q": "List all GL accounts for company 1",
                "sql": """SELECT GLCo, GLAcct, Description, AcctType, Active
FROM GLAC WITH (NOLOCK)
WHERE GLCo = 1
ORDER BY GLAcct"""
            },
            {
                "q": "Find AP invoices over $10,000 from last month",
                "sql": """SELECT APCo, Vendor, InvNum, InvDate, GrossAmt
FROM APTH WITH (NOLOCK)
WHERE APCo = @APCo
  AND Mth = @LastMonth
  AND GrossAmt > 10000
ORDER BY GrossAmt DESC"""
            },
        ]

        count = 0
        for ex in examples:
            if max_records and count >= max_records:
                break
            yield TrainingRecord(
                instruction=f"Write a SQL query to: {ex['q']}",
                output=f"```sql\n{ex['sql']}\n```",
                category=DataCategory.SQL_GENERATION.value,
                source="SQL_Generation"
            )
            count += 1

    def generate_module_overview_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate module overview examples."""
        modules = [
            {
                "module": "AP (Accounts Payable)",
                "tables": "APTH (Transaction Header), APTL (Transaction Lines), APVM (Vendor Master), APTB (Batch Header)",
                "description": "Manages vendor invoices, payments, and 1099 reporting."
            },
            {
                "module": "AR (Accounts Receivable)",
                "tables": "ARTH (Transaction Header), ARTL (Transaction Lines), ARCM (Customer Master)",
                "description": "Manages customer invoices, receipts, and aging."
            },
            {
                "module": "JC (Job Cost)",
                "tables": "JCJM (Job Master), JCCD (Cost Detail), JCCH (Cost History), JCCI (Contract Items)",
                "description": "Tracks project costs, budgets, revenue recognition."
            },
            {
                "module": "GL (General Ledger)",
                "tables": "GLDT (Detail Transactions), GLAC (Chart of Accounts), GLCO (Company Setup)",
                "description": "Core financial accounting and reporting."
            },
            {
                "module": "PR (Payroll)",
                "tables": "PRTH (Timecard Header), PRTD (Timecard Detail), PREH (Employee Header)",
                "description": "Manages employee time, pay, deductions, and taxes."
            },
        ]

        count = 0
        for mod in modules:
            if max_records and count >= max_records:
                break
            yield TrainingRecord(
                instruction=f"What is the {mod['module']} module in Viewpoint Vista?",
                output=f"The {mod['module']} module {mod['description']}\n\nKey tables:\n{mod['tables']}",
                category=DataCategory.BUSINESS_CONTEXT.value,
                source="Module_Overview"
            )
            count += 1

    def generate_trigger_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate training examples from trigger documentation (2500+ files)."""
        trigger_dir = self.vgpt2 / "Viewpoint_Database" / "Triggers" / "Trigger_Documentation"
        if not trigger_dir.exists():
            return

        count = 0
        for md_file in trigger_dir.glob("*.md"):
            if max_records and count >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                trigger_name = md_file.stem

                # Extract key sections
                purpose = self._extract_section(content, "**Purpose:**", "**Business Context:**")
                business = self._extract_section(content, "**Business Context:**", "**Key Logic:**")
                key_logic = self._extract_section(content, "**Key Logic:**", "**Effects:**")
                effects = self._extract_section(content, "**Effects:**", "**Modification History:**")

                # Extract metadata
                module = self._extract_section(content, "**Module:**", "**Parent Table:**")
                parent_table = self._extract_section(content, "**Parent Table:**", "**Event:**")
                event = self._extract_section(content, "**Event:**", "**Type:**")

                if purpose:
                    # Question about trigger purpose
                    yield TrainingRecord(
                        instruction=f"What does the {trigger_name} trigger do in Viewpoint Vista?",
                        output=f"The {trigger_name} trigger is in the {module or 'Viewpoint'} module on table {parent_table or 'unknown'}.\n\n**Purpose:** {purpose}\n\n**When it fires:** {event or 'On data modification'}",
                        category=DataCategory.BUSINESS_CONTEXT.value,
                        source="Trigger_Documentation"
                    )
                    count += 1

                if key_logic and count < (max_records or float('inf')):
                    # Question about trigger logic
                    yield TrainingRecord(
                        instruction=f"Explain the logic of the {trigger_name} trigger",
                        output=f"**Key Logic:**\n{key_logic}\n\n**Effects:**\n{effects or 'Validates data and may roll back on error.'}",
                        category=DataCategory.BUSINESS_CONTEXT.value,
                        source="Trigger_Documentation"
                    )
                    count += 1

                if parent_table and count < (max_records or float('inf')):
                    # Question about what triggers exist on a table
                    yield TrainingRecord(
                        instruction=f"What triggers exist on the {parent_table} table?",
                        output=f"The {trigger_name} trigger fires on {event or 'data modification'} events on {parent_table}.\n\n{purpose or ''}",
                        category=DataCategory.SCHEMA_QUERY.value,
                        source="Trigger_Documentation"
                    )
                    count += 1

            except Exception as e:
                logger.debug(f"Error processing trigger {md_file}: {e}")
                continue

    def generate_index_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate training examples about database indexes."""
        index_file = self.vgpt2 / "Viewpoint_Database" / "Indexes" / "_data" / "indexes.json"
        if not index_file.exists():
            # Try alternative location
            index_file = self.metadata_dir / "indexes.json"
        if not index_file.exists():
            return

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                indexes = json.load(f)
        except Exception:
            return

        count = 0
        for idx in indexes:
            if max_records and count >= max_records:
                break

            table_name = idx.get('TableName', '')
            index_name = idx.get('IndexName', '')
            columns = idx.get('Columns', idx.get('IndexColumns', ''))
            is_unique = idx.get('IsUnique', False)
            is_pk = idx.get('IsPrimaryKey', False)

            if table_name and index_name:
                idx_type = "primary key" if is_pk else ("unique index" if is_unique else "index")
                yield TrainingRecord(
                    instruction=f"What indexes exist on the {table_name} table?",
                    output=f"The {table_name} table has the {index_name} {idx_type} on columns: {columns}",
                    category=DataCategory.SCHEMA_QUERY.value,
                    source="Index_Metadata"
                )
                count += 1

    def generate_constraint_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate training examples about database constraints."""
        constraint_dir = self.vgpt2 / "Viewpoint_Database" / "Constraints" / "_data"
        if not constraint_dir.exists():
            return

        count = 0
        for json_file in constraint_dir.glob("*.json"):
            if max_records and count >= max_records:
                break

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    constraints = json.load(f)

                if isinstance(constraints, list):
                    for c in constraints:
                        if max_records and count >= max_records:
                            break

                        table = c.get('TableName', '')
                        name = c.get('ConstraintName', '')
                        ctype = c.get('ConstraintType', '')
                        definition = c.get('Definition', c.get('CheckClause', ''))

                        if table and name:
                            yield TrainingRecord(
                                instruction=f"What constraints exist on {table}?",
                                output=f"The {table} table has a {ctype} constraint named {name}.\n\nDefinition: {definition}",
                                category=DataCategory.SCHEMA_QUERY.value,
                                source="Constraint_Metadata"
                            )
                            count += 1
            except Exception:
                continue

    def generate_more_sql_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate additional SQL generation examples for common patterns."""
        patterns = [
            # AP Module patterns
            {"q": "Get all invoices paid to vendor 5000 in 2024", "sql": "SELECT APCo, Mth, APTrans, Vendor, InvNum, InvDate, GrossAmt, PaidDate, PaidMth\nFROM APTH WITH (NOLOCK)\nWHERE APCo = @APCo\n  AND Vendor = 5000\n  AND PaidMth >= '2024-01-01'\n  AND PaidMth < '2025-01-01'\nORDER BY PaidDate"},
            {"q": "Find AP invoices with retainage", "sql": "SELECT APCo, Vendor, InvNum, GrossAmt, Retainage\nFROM APTH WITH (NOLOCK)\nWHERE APCo = @APCo\n  AND Retainage > 0\nORDER BY Retainage DESC"},
            {"q": "List all AP batches pending approval", "sql": "SELECT APCo, Mth, BatchId, BatchSeq, Status, Source\nFROM APTB WITH (NOLOCK)\nWHERE APCo = @APCo\n  AND Status = 0\nORDER BY Mth, BatchId"},
            {"q": "Get vendor 1099 information", "sql": "SELECT VendorGroup, Vendor, Name, TaxId, Vendor1099\nFROM APVM WITH (NOLOCK)\nWHERE VendorGroup = @VendorGroup\n  AND Vendor1099 = 'Y'"},
            # JC Module patterns
            {"q": "Get all costs for job 12345", "sql": "SELECT JCCo, Job, Phase, CostType, ActualCost, ActualUnits\nFROM JCCD WITH (NOLOCK)\nWHERE JCCo = @JCCo\n  AND Job = '12345'\nORDER BY Phase, CostType"},
            {"q": "Find jobs over budget", "sql": "SELECT JCJM.JCCo, JCJM.Job, JCJM.Description,\n  SUM(JCCD.EstCost) AS Budget,\n  SUM(JCCD.ActualCost) AS Actual\nFROM JCJM WITH (NOLOCK)\nINNER JOIN JCCD WITH (NOLOCK)\n  ON JCJM.JCCo = JCCD.JCCo AND JCJM.Job = JCCD.Job\nWHERE JCJM.JCCo = @JCCo\nGROUP BY JCJM.JCCo, JCJM.Job, JCJM.Description\nHAVING SUM(JCCD.ActualCost) > SUM(JCCD.EstCost)"},
            {"q": "Get job revenue by month", "sql": "SELECT JCCo, Job, Mth, SUM(ActualRevenue) AS Revenue\nFROM JCCD WITH (NOLOCK)\nWHERE JCCo = @JCCo\n  AND Job = @Job\nGROUP BY JCCo, Job, Mth\nORDER BY Mth"},
            {"q": "Find all change orders for a contract", "sql": "SELECT JCCo, Contract, Item, Description, OrigContractAmt, ContractAmt\nFROM JCCI WITH (NOLOCK)\nWHERE JCCo = @JCCo\n  AND Contract = @Contract\n  AND Item > 0\nORDER BY Item"},
            # PR Module patterns
            {"q": "Get employee hours this pay period", "sql": "SELECT PRCo, Employee, PayPeriod, SUM(Hours) AS TotalHours\nFROM PRTD WITH (NOLOCK)\nWHERE PRCo = @PRCo\n  AND PayPeriod = @PayPeriod\nGROUP BY PRCo, Employee, PayPeriod"},
            {"q": "Find employees with overtime", "sql": "SELECT PRCo, Employee, PayPeriod, EarnType, Hours\nFROM PRTD WITH (NOLOCK)\nWHERE PRCo = @PRCo\n  AND EarnType IN ('OT', 'DT')\n  AND Hours > 0\nORDER BY Employee"},
            {"q": "Get all active employees", "sql": "SELECT PRCo, Employee, FirstName, LastName, HireDate, Dept, Craft\nFROM PREH WITH (NOLOCK)\nWHERE PRCo = @PRCo\n  AND ActiveYN = 'Y'\nORDER BY LastName, FirstName"},
            # GL Module patterns
            {"q": "Get GL transactions for an account", "sql": "SELECT GLCo, Mth, GLAcct, Jrnl, Amount, Description\nFROM GLDT WITH (NOLOCK)\nWHERE GLCo = @GLCo\n  AND GLAcct = @GLAcct\nORDER BY Mth, Jrnl"},
            {"q": "Calculate account balance by month", "sql": "SELECT GLCo, Mth, GLAcct, SUM(Amount) AS Balance\nFROM GLDT WITH (NOLOCK)\nWHERE GLCo = @GLCo\n  AND GLAcct = @GLAcct\nGROUP BY GLCo, Mth, GLAcct\nORDER BY Mth"},
            {"q": "Find all expense accounts", "sql": "SELECT GLCo, GLAcct, Description, AcctType\nFROM GLAC WITH (NOLOCK)\nWHERE GLCo = @GLCo\n  AND AcctType = 'E'\n  AND Active = 'Y'\nORDER BY GLAcct"},
            # AR Module patterns
            {"q": "Get customer aging", "sql": "SELECT ARCo, CustGroup, Customer, InvNum, InvDate, Amount,\n  DATEDIFF(day, InvDate, GETDATE()) AS DaysOld\nFROM ARTH WITH (NOLOCK)\nWHERE ARCo = @ARCo\n  AND Status = 0\nORDER BY DaysOld DESC"},
            {"q": "Find all open AR invoices", "sql": "SELECT ARCo, CustGroup, Customer, InvNum, InvDate, Amount, Balance\nFROM ARTH WITH (NOLOCK)\nWHERE ARCo = @ARCo\n  AND Balance > 0\nORDER BY InvDate"},
            # EM Module patterns
            {"q": "Get equipment costs", "sql": "SELECT EMCo, Equipment, CostCode, ActualCost, ActualHours\nFROM EMCD WITH (NOLOCK)\nWHERE EMCo = @EMCo\n  AND Equipment = @Equipment\nORDER BY CostCode"},
            {"q": "Find all active equipment", "sql": "SELECT EMCo, Equipment, Description, Category, Status\nFROM EMEM WITH (NOLOCK)\nWHERE EMCo = @EMCo\n  AND Status = 'A'\nORDER BY Equipment"},
            # PO Module patterns
            {"q": "Get all open purchase orders", "sql": "SELECT POCo, PO, Vendor, Description, TotalAmt, Status\nFROM POHD WITH (NOLOCK)\nWHERE POCo = @POCo\n  AND Status = 0\nORDER BY PO"},
            {"q": "Find PO line items for a PO", "sql": "SELECT POCo, PO, POItem, Description, UM, UnitPrice, RecvdAmt\nFROM POIT WITH (NOLOCK)\nWHERE POCo = @POCo\n  AND PO = @PO\nORDER BY POItem"},
            # Complex JOINs
            {"q": "Get AP invoice with vendor and GL info", "sql": "SELECT APTH.APCo, APTH.Vendor, APVM.Name AS VendorName,\n  APTH.InvNum, APTH.GrossAmt, APTL.GLCo, APTL.GLAcct\nFROM APTH WITH (NOLOCK)\nINNER JOIN APVM WITH (NOLOCK)\n  ON APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor\nINNER JOIN APTL WITH (NOLOCK)\n  ON APTH.APCo = APTL.APCo AND APTH.Mth = APTL.Mth AND APTH.APTrans = APTL.APTrans\nWHERE APTH.APCo = @APCo"},
            {"q": "Get job costs with cost type descriptions", "sql": "SELECT JCCD.JCCo, JCCD.Job, JCCD.Phase, JCCD.CostType,\n  JCCT.Description AS CostTypeDesc, JCCD.ActualCost\nFROM JCCD WITH (NOLOCK)\nINNER JOIN JCCT WITH (NOLOCK)\n  ON JCCD.PhaseGroup = JCCT.PhaseGroup AND JCCD.CostType = JCCT.CostType\nWHERE JCCD.JCCo = @JCCo AND JCCD.Job = @Job"},
        ]

        count = 0
        for p in patterns:
            if max_records and count >= max_records:
                break
            yield TrainingRecord(
                instruction=f"Write SQL to: {p['q']}",
                output=f"```sql\n{p['sql']}\n```\n\nNote: Always use WITH (NOLOCK) for SELECT queries and filter by company column.",
                category=DataCategory.SQL_GENERATION.value,
                source="SQL_Patterns"
            )
            count += 1

    def generate_column_usage_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate examples about how specific columns are used."""
        columns = self.load_columns()
        count = 0

        # Group by table
        tables = {}
        for col in columns:
            if not isinstance(col, dict):
                continue
            obj_name = col.get('ObjectName', '')
            if obj_name and obj_name not in tables:
                tables[obj_name] = []
            if obj_name:
                tables[obj_name].append(col)

        # Generate multiple questions per table
        for table_name, cols in tables.items():
            if max_records and count >= max_records:
                break

            # Get primary key columns (usually first few)
            pk_cols = [c for c in cols if 'key' in c.get('ColumnName', '').lower() or c.get('ColumnPosition', '1') == '1']

            # Get descriptive columns
            desc_cols = [c for c in cols if 'desc' in c.get('ColumnName', '').lower() or 'name' in c.get('ColumnName', '').lower()]

            # Get amount/money columns
            amt_cols = [c for c in cols if c.get('DataType', '') in ('money', 'decimal', 'numeric') and ('amt' in c.get('ColumnName', '').lower() or 'amount' in c.get('ColumnName', '').lower() or 'cost' in c.get('ColumnName', '').lower())]

            if pk_cols:
                yield TrainingRecord(
                    instruction=f"What are the key columns in {table_name}?",
                    output=f"The key columns in {table_name} are: {', '.join([c.get('ColumnName', '') for c in pk_cols[:5]])}",
                    category=DataCategory.SCHEMA_QUERY.value,
                    source="Column_Usage"
                )
                count += 1

            if desc_cols and count < (max_records or float('inf')):
                yield TrainingRecord(
                    instruction=f"What columns contain descriptions in {table_name}?",
                    output=f"Description columns in {table_name}: {', '.join([c.get('ColumnName', '') for c in desc_cols[:5]])}",
                    category=DataCategory.SCHEMA_QUERY.value,
                    source="Column_Usage"
                )
                count += 1

            if amt_cols and count < (max_records or float('inf')):
                yield TrainingRecord(
                    instruction=f"What amount/money columns are in {table_name}?",
                    output=f"Amount columns in {table_name}: {', '.join([c.get('ColumnName', '') + ' (' + c.get('DataType', '') + ')' for c in amt_cols[:5]])}",
                    category=DataCategory.SCHEMA_QUERY.value,
                    source="Column_Usage"
                )
                count += 1

    def generate_nolock_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate extensive NOLOCK usage examples to increase coverage from 1.5% to 10%+."""
        # NOLOCK is critical - we need many examples showing it in different contexts
        tables = self.load_tables_list()
        columns = self.load_columns()

        # Group columns by table
        table_cols = {}
        for col in columns:
            if isinstance(col, dict):
                tbl = col.get('ObjectName', '')
                if tbl and tbl not in table_cols:
                    table_cols[tbl] = []
                if tbl:
                    table_cols[tbl].append(col.get('ColumnName', ''))

        count = 0

        # Get list of core tables for SQL examples
        core_tables = [
            ('APTH', 'APCo', 'AP invoices'),
            ('APTL', 'APCo', 'AP invoice lines'),
            ('APVM', 'VendorGroup', 'vendors'),
            ('ARTH', 'ARCo', 'AR invoices'),
            ('ARTL', 'ARCo', 'AR invoice lines'),
            ('ARCM', 'CustGroup', 'customers'),
            ('JCJM', 'JCCo', 'jobs'),
            ('JCCD', 'JCCo', 'job costs'),
            ('JCCH', 'JCCo', 'job cost history'),
            ('PREH', 'PRCo', 'employees'),
            ('PRTH', 'PRCo', 'timecards'),
            ('PRTD', 'PRCo', 'timecard details'),
            ('GLDT', 'GLCo', 'GL transactions'),
            ('GLAC', 'GLCo', 'GL accounts'),
            ('EMEM', 'EMCo', 'equipment'),
            ('EMCD', 'EMCo', 'equipment costs'),
            ('POHD', 'POCo', 'purchase orders'),
            ('POIT', 'POCo', 'PO items'),
            ('INMM', 'INCo', 'inventory materials'),
            ('INMT', 'INCo', 'inventory transactions'),
            ('SMWH', 'SMCo', 'work orders'),
            ('HQCO', 'HQCo', 'company setup'),
        ]

        # Pattern 1: Basic NOLOCK explanation (many variations)
        nolock_explanations = [
            {
                "q": "Why do I need WITH (NOLOCK) in Viewpoint queries?",
                "a": """WITH (NOLOCK) is REQUIRED for all SELECT queries in Viewpoint Vista because:

1. **Prevents blocking**: Production transactions (AP batches, payroll, etc.) use exclusive locks. Without NOLOCK, your report query could block critical business operations.

2. **Performance**: NOLOCK allows read operations without waiting for write locks to release.

3. **Standard practice**: All Viewpoint Crystal Reports use NOLOCK. Custom queries should too.

Example:
```sql
SELECT APCo, Vendor, InvNum, GrossAmt
FROM APTH WITH (NOLOCK)
WHERE APCo = 1 AND Status = 0
```

Only omit NOLOCK when you specifically need transactional consistency (very rare)."""
            },
            {
                "q": "Show me how to use NOLOCK correctly",
                "a": """Here's the correct NOLOCK syntax for Viewpoint:

**Single table:**
```sql
SELECT APCo, Vendor, InvNum, GrossAmt
FROM APTH WITH (NOLOCK)
WHERE APCo = 1
```

**Multiple tables with JOIN:**
```sql
SELECT APTH.APCo, APTH.Vendor, APVM.Name
FROM APTH WITH (NOLOCK)
INNER JOIN APVM WITH (NOLOCK)
  ON APTH.VendorGroup = APVM.VendorGroup
  AND APTH.Vendor = APVM.Vendor
WHERE APTH.APCo = 1
```

Key rules:
- Place WITH (NOLOCK) immediately after each table name
- Apply to ALL tables in the query
- Never use table aliases (a, b, etc.)"""
            },
            {
                "q": "What happens if I forget NOLOCK?",
                "a": """If you omit WITH (NOLOCK) in a Viewpoint query:

1. **Query may hang**: If AP/AR batch posting is in progress, your query waits for the lock to release - potentially minutes or hours.

2. **Blocking cascade**: Your query takes a shared lock, which can then block batch processes waiting for exclusive locks.

3. **Timeout errors**: Long-running reports may timeout while waiting for locks.

**Wrong (no NOLOCK):**
```sql
SELECT * FROM APTH WHERE APCo = 1  -- Can block!
```

**Correct (with NOLOCK):**
```sql
SELECT * FROM APTH WITH (NOLOCK) WHERE APCo = 1
```

Always use NOLOCK for reporting and ad-hoc queries."""
            },
            {
                "q": "Is NOLOCK the same as READ UNCOMMITTED?",
                "a": """Yes, WITH (NOLOCK) is equivalent to setting isolation level READ UNCOMMITTED for that table.

**Table hint (preferred in Viewpoint):**
```sql
SELECT * FROM APTH WITH (NOLOCK) WHERE APCo = 1
```

**Session-level equivalent:**
```sql
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
SELECT * FROM APTH WHERE APCo = 1
-- Affects all queries until changed
```

Viewpoint convention is to use the table hint WITH (NOLOCK) because:
- It's explicit per table
- Doesn't affect other queries in the session
- Matches Crystal Reports standard"""
            },
        ]

        for ex in nolock_explanations:
            if max_records and count >= max_records:
                break
            yield TrainingRecord(
                instruction=ex["q"],
                output=ex["a"],
                category=DataCategory.SQL_VALIDATION.value,
                source="NOLOCK_Best_Practices"
            )
            count += 1

        # Pattern 2: Generate SQL with NOLOCK for each core table
        for table, co_col, desc in core_tables:
            if max_records and count >= max_records:
                break

            # Get some columns for this table
            cols = table_cols.get(table, [])[:6]
            col_list = ", ".join(cols) if cols else "*"

            yield TrainingRecord(
                instruction=f"Write SQL to query all {desc} from {table}",
                output=f"""```sql
SELECT {col_list}
FROM {table} WITH (NOLOCK)
WHERE {co_col} = @{co_col}
ORDER BY {cols[0] if cols else co_col}
```

Note: WITH (NOLOCK) prevents blocking production transactions. Always include company filter ({co_col}).""",
                category=DataCategory.SQL_GENERATION.value,
                source="NOLOCK_Best_Practices"
            )
            count += 1

            # Also generate a "fix this query" example
            if count < (max_records or float('inf')):
                yield TrainingRecord(
                    instruction=f"Fix this query: SELECT * FROM {table}",
                    output=f"""The query is missing WITH (NOLOCK) and a company filter.

**Corrected:**
```sql
SELECT {col_list}
FROM {table} WITH (NOLOCK)
WHERE {co_col} = @{co_col}
```

Issues fixed:
1. Added WITH (NOLOCK) to prevent blocking
2. Added company filter ({co_col}) for data isolation
3. Specified columns instead of SELECT *""",
                    category=DataCategory.ERROR_CORRECTION.value,
                    source="NOLOCK_Best_Practices"
                )
                count += 1

        # Pattern 3: JOIN examples with NOLOCK on both tables
        join_pairs = [
            ('APTH', 'APTL', 'APCo', 'Mth', 'APTrans', 'invoice header and lines'),
            ('APTH', 'APVM', 'VendorGroup', 'Vendor', None, 'invoices and vendor names'),
            ('JCJM', 'JCCD', 'JCCo', 'Job', None, 'jobs and cost details'),
            ('JCJM', 'JCCH', 'JCCo', 'Job', None, 'jobs and cost history'),
            ('PREH', 'PRTH', 'PRCo', 'Employee', None, 'employees and timecards'),
            ('ARTH', 'ARTL', 'ARCo', 'Mth', 'ARTrans', 'AR transactions'),
            ('ARTH', 'ARCM', 'CustGroup', 'Customer', None, 'AR transactions and customers'),
            ('POHD', 'POIT', 'POCo', 'PO', None, 'PO headers and items'),
            ('GLDT', 'GLAC', 'GLCo', 'GLAcct', None, 'GL transactions and accounts'),
        ]

        for t1, t2, key1, key2, key3, desc in join_pairs:
            if max_records and count >= max_records:
                break

            join_cond = f"{t1}.{key1} = {t2}.{key1} AND {t1}.{key2} = {t2}.{key2}"
            if key3:
                join_cond += f" AND {t1}.{key3} = {t2}.{key3}"

            yield TrainingRecord(
                instruction=f"Write SQL to join {desc}",
                output=f"""```sql
SELECT {t1}.*, {t2}.*
FROM {t1} WITH (NOLOCK)
INNER JOIN {t2} WITH (NOLOCK)
  ON {join_cond}
WHERE {t1}.{key1} = @{key1}
```

Key points:
- WITH (NOLOCK) is required on BOTH tables
- Always include the company column ({key1}) in the JOIN condition
- No table aliases - use full table names""",
                category=DataCategory.JOIN_PATTERN.value,
                source="NOLOCK_Best_Practices"
            )
            count += 1

        # Pattern 4: Common mistakes to fix (NOLOCK related)
        mistakes = [
            {
                "wrong": "SELECT a.* FROM APTH a WHERE a.APCo = 1",
                "right": "SELECT APTH.* FROM APTH WITH (NOLOCK) WHERE APTH.APCo = 1",
                "issues": "Missing NOLOCK, using table alias 'a'"
            },
            {
                "wrong": "SELECT * FROM JCJM j JOIN JCCD c ON j.Job = c.Job",
                "right": "SELECT JCJM.*, JCCD.* FROM JCJM WITH (NOLOCK) INNER JOIN JCCD WITH (NOLOCK) ON JCJM.JCCo = JCCD.JCCo AND JCJM.Job = JCCD.Job",
                "issues": "Missing NOLOCK on both tables, incomplete JOIN (missing JCCo), using aliases"
            },
            {
                "wrong": "FROM dbo.APTH WHERE APCo = 1",
                "right": "FROM APTH WITH (NOLOCK) WHERE APCo = 1",
                "issues": "Don't use 'dbo.' prefix, add WITH (NOLOCK)"
            },
            {
                "wrong": "SELECT * FROM PREH, PRTH WHERE PREH.Employee = PRTH.Employee",
                "right": "SELECT PREH.*, PRTH.* FROM PREH WITH (NOLOCK) INNER JOIN PRTH WITH (NOLOCK) ON PREH.PRCo = PRTH.PRCo AND PREH.Employee = PRTH.Employee WHERE PREH.PRCo = @PRCo",
                "issues": "Missing NOLOCK, implicit JOIN syntax, missing company in JOIN condition"
            },
        ]

        for m in mistakes:
            if max_records and count >= max_records:
                break
            yield TrainingRecord(
                instruction=f"Fix this Viewpoint SQL: {m['wrong']}",
                output=f"""**Corrected SQL:**
```sql
{m['right']}
```

**Issues fixed:** {m['issues']}

Remember: Always use WITH (NOLOCK) on every table in SELECT queries.""",
                category=DataCategory.ERROR_CORRECTION.value,
                source="NOLOCK_Best_Practices"
            )
            count += 1

    def generate_expanded_sql_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate many more SQL generation examples to increase SQL content from 4% to 15%+."""
        count = 0

        # Comprehensive SQL patterns organized by module and complexity
        sql_examples = [
            # ===== AP Module - Basic Queries =====
            {"q": "Get all AP invoices for company 1", "sql": "SELECT APCo, Mth, APTrans, Vendor, InvNum, InvDate, GrossAmt, Status\nFROM APTH WITH (NOLOCK)\nWHERE APCo = 1\nORDER BY InvDate DESC"},
            {"q": "Find unpaid AP invoices", "sql": "SELECT APCo, Vendor, InvNum, InvDate, GrossAmt, DueDate\nFROM APTH WITH (NOLOCK)\nWHERE APCo = @APCo AND Status = 0\nORDER BY DueDate"},
            {"q": "Get AP invoices for a specific vendor", "sql": "SELECT APCo, Mth, APTrans, InvNum, InvDate, GrossAmt, Status\nFROM APTH WITH (NOLOCK)\nWHERE APCo = @APCo AND Vendor = @Vendor\nORDER BY InvDate DESC"},
            {"q": "Find AP invoices over $50,000", "sql": "SELECT APCo, Vendor, InvNum, InvDate, GrossAmt\nFROM APTH WITH (NOLOCK)\nWHERE APCo = @APCo AND GrossAmt > 50000\nORDER BY GrossAmt DESC"},
            {"q": "Get AP invoices by month", "sql": "SELECT APCo, Mth, COUNT(*) AS InvoiceCount, SUM(GrossAmt) AS TotalAmount\nFROM APTH WITH (NOLOCK)\nWHERE APCo = @APCo\nGROUP BY APCo, Mth\nORDER BY Mth"},
            {"q": "Find AP invoices due this week", "sql": "SELECT APCo, Vendor, InvNum, GrossAmt, DueDate\nFROM APTH WITH (NOLOCK)\nWHERE APCo = @APCo \n  AND Status = 0\n  AND DueDate BETWEEN GETDATE() AND DATEADD(day, 7, GETDATE())\nORDER BY DueDate"},
            {"q": "Get AP invoice line details", "sql": "SELECT APTL.APCo, APTL.Mth, APTL.APTrans, APTL.APLine,\n  APTL.GLCo, APTL.GLAcct, APTL.Amount, APTL.Description\nFROM APTL WITH (NOLOCK)\nWHERE APTL.APCo = @APCo AND APTL.Mth = @Mth AND APTL.APTrans = @APTrans\nORDER BY APTL.APLine"},
            {"q": "Sum AP by vendor", "sql": "SELECT APCo, Vendor, COUNT(*) AS InvoiceCount,\n  SUM(GrossAmt) AS TotalGross, SUM(Retainage) AS TotalRetainage\nFROM APTH WITH (NOLOCK)\nWHERE APCo = @APCo\nGROUP BY APCo, Vendor\nORDER BY TotalGross DESC"},

            # ===== AP Module - Advanced =====
            {"q": "Get AP with vendor names", "sql": "SELECT APTH.APCo, APTH.Vendor, APVM.Name AS VendorName,\n  APTH.InvNum, APTH.InvDate, APTH.GrossAmt, APTH.Status\nFROM APTH WITH (NOLOCK)\nINNER JOIN APVM WITH (NOLOCK)\n  ON APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor\nWHERE APTH.APCo = @APCo\nORDER BY APTH.InvDate DESC"},
            {"q": "AP aging report query", "sql": "SELECT APTH.APCo, APTH.Vendor, APVM.Name,\n  APTH.InvNum, APTH.InvDate, APTH.GrossAmt,\n  DATEDIFF(day, APTH.DueDate, GETDATE()) AS DaysOverdue\nFROM APTH WITH (NOLOCK)\nINNER JOIN APVM WITH (NOLOCK)\n  ON APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor\nWHERE APTH.APCo = @APCo AND APTH.Status = 0\nORDER BY DaysOverdue DESC"},
            {"q": "AP invoice with GL distribution", "sql": "SELECT APTH.APCo, APTH.Vendor, APTH.InvNum, APTH.GrossAmt,\n  APTL.GLCo, APTL.GLAcct, APTL.Amount, GLAC.Description AS AcctDesc\nFROM APTH WITH (NOLOCK)\nINNER JOIN APTL WITH (NOLOCK)\n  ON APTH.APCo = APTL.APCo AND APTH.Mth = APTL.Mth AND APTH.APTrans = APTL.APTrans\nINNER JOIN GLAC WITH (NOLOCK)\n  ON APTL.GLCo = GLAC.GLCo AND APTL.GLAcct = GLAC.GLAcct\nWHERE APTH.APCo = @APCo"},

            # ===== JC Module - Basic =====
            {"q": "Get all jobs for a company", "sql": "SELECT JCCo, Job, Description, Contract, JobStatus, StartDate\nFROM JCJM WITH (NOLOCK)\nWHERE JCCo = @JCCo\nORDER BY Job"},
            {"q": "Find active jobs", "sql": "SELECT JCCo, Job, Description, Contract, StartDate\nFROM JCJM WITH (NOLOCK)\nWHERE JCCo = @JCCo AND JobStatus = 1\nORDER BY StartDate DESC"},
            {"q": "Get job cost details", "sql": "SELECT JCCo, Job, Phase, CostType, ActualCost, ActualUnits, EstCost, EstUnits\nFROM JCCD WITH (NOLOCK)\nWHERE JCCo = @JCCo AND Job = @Job\nORDER BY Phase, CostType"},
            {"q": "Sum job costs by phase", "sql": "SELECT JCCo, Job, Phase,\n  SUM(EstCost) AS BudgetCost, SUM(ActualCost) AS ActualCost,\n  SUM(ActualCost) - SUM(EstCost) AS Variance\nFROM JCCD WITH (NOLOCK)\nWHERE JCCo = @JCCo AND Job = @Job\nGROUP BY JCCo, Job, Phase\nORDER BY Phase"},
            {"q": "Get job revenue", "sql": "SELECT JCCo, Job, Phase, Mth, ActualRevenue, BilledAmt\nFROM JCCD WITH (NOLOCK)\nWHERE JCCo = @JCCo AND Job = @Job AND ActualRevenue <> 0\nORDER BY Mth, Phase"},
            {"q": "Find jobs over budget", "sql": "SELECT JCCo, Job, Description,\n  SUM(EstCost) AS Budget, SUM(ActualCost) AS Actual,\n  SUM(ActualCost) - SUM(EstCost) AS OverBudget\nFROM JCJM WITH (NOLOCK)\nINNER JOIN JCCD WITH (NOLOCK) ON JCJM.JCCo = JCCD.JCCo AND JCJM.Job = JCCD.Job\nWHERE JCJM.JCCo = @JCCo\nGROUP BY JCJM.JCCo, JCJM.Job, JCJM.Description\nHAVING SUM(ActualCost) > SUM(EstCost)"},

            # ===== JC Module - Advanced =====
            {"q": "Job profitability report", "sql": "SELECT JCJM.JCCo, JCJM.Job, JCJM.Description,\n  SUM(JCCD.ActualCost) AS TotalCost,\n  SUM(JCCD.ActualRevenue) AS TotalRevenue,\n  SUM(JCCD.ActualRevenue) - SUM(JCCD.ActualCost) AS Profit,\n  CASE WHEN SUM(JCCD.ActualRevenue) > 0 \n    THEN (SUM(JCCD.ActualRevenue) - SUM(JCCD.ActualCost)) / SUM(JCCD.ActualRevenue) * 100\n    ELSE 0 END AS ProfitMargin\nFROM JCJM WITH (NOLOCK)\nINNER JOIN JCCD WITH (NOLOCK) ON JCJM.JCCo = JCCD.JCCo AND JCJM.Job = JCCD.Job\nWHERE JCJM.JCCo = @JCCo\nGROUP BY JCJM.JCCo, JCJM.Job, JCJM.Description"},
            {"q": "Job cost by cost type", "sql": "SELECT JCCD.JCCo, JCCD.Job, JCCD.CostType, JCCT.Description,\n  SUM(JCCD.EstCost) AS Budget, SUM(JCCD.ActualCost) AS Actual\nFROM JCCD WITH (NOLOCK)\nINNER JOIN JCCT WITH (NOLOCK)\n  ON JCCD.PhaseGroup = JCCT.PhaseGroup AND JCCD.CostType = JCCT.CostType\nWHERE JCCD.JCCo = @JCCo AND JCCD.Job = @Job\nGROUP BY JCCD.JCCo, JCCD.Job, JCCD.CostType, JCCT.Description\nORDER BY JCCD.CostType"},

            # ===== PR Module =====
            {"q": "Get all employees", "sql": "SELECT PRCo, Employee, FirstName, LastName, HireDate, Dept, Craft, ActiveYN\nFROM PREH WITH (NOLOCK)\nWHERE PRCo = @PRCo\nORDER BY LastName, FirstName"},
            {"q": "Find active employees", "sql": "SELECT PRCo, Employee, FirstName, LastName, HireDate, Dept\nFROM PREH WITH (NOLOCK)\nWHERE PRCo = @PRCo AND ActiveYN = 'Y'\nORDER BY LastName, FirstName"},
            {"q": "Get employee hours by pay period", "sql": "SELECT PRCo, Employee, PayPeriod, SUM(Hours) AS TotalHours\nFROM PRTD WITH (NOLOCK)\nWHERE PRCo = @PRCo AND PayPeriod = @PayPeriod\nGROUP BY PRCo, Employee, PayPeriod\nORDER BY Employee"},
            {"q": "Find overtime hours", "sql": "SELECT PREH.PRCo, PREH.Employee, PREH.LastName, PREH.FirstName,\n  PRTD.PayPeriod, SUM(PRTD.Hours) AS OTHours\nFROM PRTD WITH (NOLOCK)\nINNER JOIN PREH WITH (NOLOCK)\n  ON PRTD.PRCo = PREH.PRCo AND PRTD.Employee = PREH.Employee\nWHERE PRTD.PRCo = @PRCo AND PRTD.EarnType IN ('OT', 'DT')\nGROUP BY PREH.PRCo, PREH.Employee, PREH.LastName, PREH.FirstName, PRTD.PayPeriod"},
            {"q": "Employee timecard details", "sql": "SELECT PRTH.PRCo, PRTH.Employee, PRTH.PayPeriod, PRTH.Type,\n  PRTD.PostSeq, PRTD.EarnType, PRTD.Hours, PRTD.Amt\nFROM PRTH WITH (NOLOCK)\nINNER JOIN PRTD WITH (NOLOCK)\n  ON PRTH.PRCo = PRTD.PRCo AND PRTH.Employee = PRTD.Employee\n  AND PRTH.PayPeriod = PRTD.PayPeriod AND PRTH.Type = PRTD.Type\nWHERE PRTH.PRCo = @PRCo AND PRTH.Employee = @Employee"},

            # ===== GL Module =====
            {"q": "Get GL transactions", "sql": "SELECT GLCo, Mth, GLAcct, Jrnl, GLRef, Amount, Description\nFROM GLDT WITH (NOLOCK)\nWHERE GLCo = @GLCo AND Mth = @Mth\nORDER BY GLAcct, Jrnl"},
            {"q": "Account balance by month", "sql": "SELECT GLCo, GLAcct, Mth, SUM(Amount) AS Balance\nFROM GLDT WITH (NOLOCK)\nWHERE GLCo = @GLCo AND GLAcct = @GLAcct\nGROUP BY GLCo, GLAcct, Mth\nORDER BY Mth"},
            {"q": "Trial balance query", "sql": "SELECT GLAC.GLCo, GLAC.GLAcct, GLAC.Description, GLAC.AcctType,\n  ISNULL(SUM(GLDT.Amount), 0) AS Balance\nFROM GLAC WITH (NOLOCK)\nLEFT JOIN GLDT WITH (NOLOCK)\n  ON GLAC.GLCo = GLDT.GLCo AND GLAC.GLAcct = GLDT.GLAcct\n  AND GLDT.Mth <= @AsOfMonth\nWHERE GLAC.GLCo = @GLCo AND GLAC.Active = 'Y'\nGROUP BY GLAC.GLCo, GLAC.GLAcct, GLAC.Description, GLAC.AcctType\nORDER BY GLAC.GLAcct"},
            {"q": "Find GL accounts by type", "sql": "SELECT GLCo, GLAcct, Description, AcctType, Active\nFROM GLAC WITH (NOLOCK)\nWHERE GLCo = @GLCo AND AcctType = @AcctType\nORDER BY GLAcct"},

            # ===== AR Module =====
            {"q": "Get AR invoices", "sql": "SELECT ARCo, CustGroup, Customer, Invoice, InvDate, Amount, Balance\nFROM ARTH WITH (NOLOCK)\nWHERE ARCo = @ARCo\nORDER BY InvDate DESC"},
            {"q": "Find open AR invoices", "sql": "SELECT ARCo, Customer, Invoice, InvDate, Amount, Balance,\n  DATEDIFF(day, InvDate, GETDATE()) AS Age\nFROM ARTH WITH (NOLOCK)\nWHERE ARCo = @ARCo AND Balance > 0\nORDER BY Age DESC"},
            {"q": "AR with customer names", "sql": "SELECT ARTH.ARCo, ARTH.Customer, ARCM.Name AS CustomerName,\n  ARTH.Invoice, ARTH.InvDate, ARTH.Amount, ARTH.Balance\nFROM ARTH WITH (NOLOCK)\nINNER JOIN ARCM WITH (NOLOCK)\n  ON ARTH.CustGroup = ARCM.CustGroup AND ARTH.Customer = ARCM.Customer\nWHERE ARTH.ARCo = @ARCo\nORDER BY ARTH.InvDate DESC"},
            {"q": "Customer aging summary", "sql": "SELECT ARCM.CustGroup, ARCM.Customer, ARCM.Name,\n  SUM(CASE WHEN DATEDIFF(day, ARTH.InvDate, GETDATE()) <= 30 THEN ARTH.Balance ELSE 0 END) AS Current30,\n  SUM(CASE WHEN DATEDIFF(day, ARTH.InvDate, GETDATE()) BETWEEN 31 AND 60 THEN ARTH.Balance ELSE 0 END) AS Days31_60,\n  SUM(CASE WHEN DATEDIFF(day, ARTH.InvDate, GETDATE()) > 60 THEN ARTH.Balance ELSE 0 END) AS Over60\nFROM ARTH WITH (NOLOCK)\nINNER JOIN ARCM WITH (NOLOCK)\n  ON ARTH.CustGroup = ARCM.CustGroup AND ARTH.Customer = ARCM.Customer\nWHERE ARTH.ARCo = @ARCo AND ARTH.Balance > 0\nGROUP BY ARCM.CustGroup, ARCM.Customer, ARCM.Name"},

            # ===== EM Module =====
            {"q": "Get all equipment", "sql": "SELECT EMCo, Equipment, Description, Category, Type, Status\nFROM EMEM WITH (NOLOCK)\nWHERE EMCo = @EMCo\nORDER BY Equipment"},
            {"q": "Find active equipment", "sql": "SELECT EMCo, Equipment, Description, Category, HourMeter, Odometer\nFROM EMEM WITH (NOLOCK)\nWHERE EMCo = @EMCo AND Status = 'A'\nORDER BY Category, Equipment"},
            {"q": "Equipment cost summary", "sql": "SELECT EMEM.EMCo, EMEM.Equipment, EMEM.Description,\n  SUM(EMCD.ActualCost) AS TotalCost, SUM(EMCD.ActualHours) AS TotalHours\nFROM EMEM WITH (NOLOCK)\nINNER JOIN EMCD WITH (NOLOCK)\n  ON EMEM.EMCo = EMCD.EMCo AND EMEM.Equipment = EMCD.Equipment\nWHERE EMEM.EMCo = @EMCo\nGROUP BY EMEM.EMCo, EMEM.Equipment, EMEM.Description"},

            # ===== PO Module =====
            {"q": "Get open purchase orders", "sql": "SELECT POCo, PO, Vendor, Description, TotalAmt, Status\nFROM POHD WITH (NOLOCK)\nWHERE POCo = @POCo AND Status = 0\nORDER BY PO"},
            {"q": "PO with line items", "sql": "SELECT POHD.POCo, POHD.PO, POHD.Vendor, POHD.Description,\n  POIT.POItem, POIT.Description AS ItemDesc, POIT.UM, POIT.UnitPrice, POIT.CurCost\nFROM POHD WITH (NOLOCK)\nINNER JOIN POIT WITH (NOLOCK)\n  ON POHD.POCo = POIT.POCo AND POHD.PO = POIT.PO\nWHERE POHD.POCo = @POCo AND POHD.PO = @PO\nORDER BY POIT.POItem"},
            {"q": "PO commitments by job", "sql": "SELECT POIT.POCo, POIT.PO, POIT.Job, POIT.Phase,\n  SUM(POIT.CurCost) AS Committed, SUM(POIT.RecvdCost) AS Received\nFROM POIT WITH (NOLOCK)\nWHERE POIT.POCo = @POCo AND POIT.Job IS NOT NULL\nGROUP BY POIT.POCo, POIT.PO, POIT.Job, POIT.Phase"},

            # ===== Cross-Module =====
            {"q": "Get company list", "sql": "SELECT HQCo, Name, Address, City, State, Zip\nFROM HQCO WITH (NOLOCK)\nORDER BY HQCo"},
            {"q": "Find all 1099 vendors", "sql": "SELECT VendorGroup, Vendor, Name, TaxId, Address, City, State, Zip\nFROM APVM WITH (NOLOCK)\nWHERE VendorGroup = @VendorGroup AND Vendor1099 = 'Y'\nORDER BY Name"},
        ]

        for ex in sql_examples:
            if max_records and count >= max_records:
                break
            yield TrainingRecord(
                instruction=f"Write SQL to: {ex['q']}",
                output=f"```sql\n{ex['sql']}\n```\n\nNote: WITH (NOLOCK) prevents blocking production transactions. Always filter by company column.",
                category=DataCategory.SQL_GENERATION.value,
                source="SQL_Generation_Expanded"
            )
            count += 1

    def generate_extended_schema_explanations(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate longer, more detailed schema explanations to reduce short outputs."""
        columns = self.load_columns()
        count = 0

        # Group by table
        tables = {}
        for col in columns:
            if not isinstance(col, dict):
                continue
            obj_name = col.get('ObjectName', '')
            if obj_name and obj_name not in tables:
                tables[obj_name] = {
                    'columns': [],
                    'module': col.get('Module', 'Unknown'),
                    'type': col.get('ObjectType', 'Table')
                }
            if obj_name:
                tables[obj_name]['columns'].append(col)

        # Generate detailed explanations for major tables
        major_tables_info = {
            'APTH': 'Accounts Payable Transaction Header. Core table for tracking vendor invoices, payments, and 1099 reporting.',
            'APTL': 'Accounts Payable Transaction Lines. Contains GL distributions and cost allocations for AP invoices.',
            'APVM': 'Accounts Payable Vendor Master. Central repository for all vendor information shared across companies via VendorGroup.',
            'ARTH': 'Accounts Receivable Transaction Header. Tracks customer invoices, payments, and collections.',
            'ARCM': 'Accounts Receivable Customer Master. Customer information shared via CustGroup across companies.',
            'JCJM': 'Job Cost Job Master. The central job/project table containing all job-level information.',
            'JCCD': 'Job Cost Cost Detail. Detailed cost and revenue transactions at the phase/cost type level.',
            'JCCH': 'Job Cost Cost History. Historical cost data typically summarized by month.',
            'PREH': 'Payroll Employee Header. Master employee information including demographics, rates, and deductions.',
            'PRTH': 'Payroll Timecard Header. Timecard header records for payroll processing.',
            'PRTD': 'Payroll Timecard Detail. Individual earnings, hours, and amounts by earn type.',
            'GLDT': 'General Ledger Detail Transactions. All financial transactions posting to the GL.',
            'GLAC': 'General Ledger Account Chart. Chart of accounts with account types and hierarchies.',
            'EMEM': 'Equipment Management Equipment Master. Central equipment/asset repository.',
            'POHD': 'Purchase Order Header. PO header information including vendor, terms, and status.',
            'POIT': 'Purchase Order Items. Line items on purchase orders with cost and receipt tracking.',
        }

        for table_name, info in tables.items():
            if max_records and count >= max_records:
                break

            if table_name not in major_tables_info:
                continue

            cols = info['columns']
            module = info['module']
            desc = major_tables_info.get(table_name, '')

            # Get key columns
            pk_cols = [c for c in cols if c.get('IsPrimaryKey') == 'True']
            fk_cols = [c for c in cols if c.get('IsForeignKey') == 'True']

            # Build detailed column list
            col_details = []
            for c in cols[:15]:
                cname = c.get('ColumnName', '')
                dtype = c.get('DataType', '')
                nullable = 'nullable' if c.get('IsNullable') == 'True' else 'required'
                col_details.append(f"  - {cname} ({dtype}, {nullable})")

            pk_list = ', '.join([c.get('ColumnName', '') for c in pk_cols]) if pk_cols else 'Not defined'

            output = f"""{table_name} is in the {module} module.

**Purpose:** {desc}

**Primary Key:** {pk_list}

**Key Columns:**
{chr(10).join(col_details)}
{f'... and {len(cols) - 15} more columns' if len(cols) > 15 else ''}

**Usage Example:**
```sql
SELECT {', '.join([c.get('ColumnName', '') for c in cols[:5]])}
FROM {table_name} WITH (NOLOCK)
WHERE {pk_cols[0].get('ColumnName', 'ID') if pk_cols else 'ID'} = @Value
```

Always use WITH (NOLOCK) for SELECT queries to prevent blocking."""

            yield TrainingRecord(
                instruction=f"Tell me about the {table_name} table in Viewpoint Vista",
                output=output,
                category=DataCategory.SCHEMA_QUERY.value,
                source="Extended_Schema"
            )
            count += 1

            # Also generate a "what columns" question with more detail
            if count < (max_records or float('inf')):
                col_list_detailed = []
                for c in cols[:20]:
                    cname = c.get('ColumnName', '')
                    dtype = c.get('DataType', '')
                    col_list_detailed.append(f"{cname} ({dtype})")

                yield TrainingRecord(
                    instruction=f"What columns does {table_name} have?",
                    output=f"""The {table_name} table ({module} module) contains {len(cols)} columns.

**Primary columns:** {', '.join(col_list_detailed[:10])}

**Additional columns:** {', '.join(col_list_detailed[10:20]) if len(col_list_detailed) > 10 else 'See above'}

**Primary Key:** {pk_list}

To query this table:
```sql
SELECT * FROM {table_name} WITH (NOLOCK) WHERE {pk_cols[0].get('ColumnName', 'ID') if pk_cols else 'ID'} = @Value
```""",
                    category=DataCategory.SCHEMA_QUERY.value,
                    source="Extended_Schema"
                )
                count += 1

    def generate_table_query_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate SQL query examples for every table to massively boost NOLOCK and SQL coverage."""
        columns = self.load_columns()
        count = 0

        # Group columns by table
        tables = {}
        for col in columns:
            if not isinstance(col, dict):
                continue
            obj_name = col.get('ObjectName', '')
            if obj_name and obj_name not in tables:
                tables[obj_name] = {
                    'columns': [],
                    'module': col.get('Module', 'Unknown'),
                    'type': col.get('ObjectType', 'Table')
                }
            if obj_name:
                tables[obj_name]['columns'].append(col)

        # Standard company column mapping
        company_cols = {
            'AP': 'APCo', 'AR': 'ARCo', 'JC': 'JCCo', 'PR': 'PRCo',
            'GL': 'GLCo', 'EM': 'EMCo', 'PO': 'POCo', 'IN': 'INCo',
            'SM': 'SMCo', 'HQ': 'HQCo', 'HR': 'HRCo', 'SL': 'SLCo',
            'MS': 'MSCo', 'PM': 'PMCo', 'VA': 'VACo', 'DM': 'DMCo'
        }

        # Question templates for variety
        question_templates = [
            "How do I query {table}?",
            "Write SQL to select from {table}",
            "Query {table} for company 1",
            "Get all records from {table}",
            "Show me how to read {table}",
            "SELECT from {table}",
        ]

        for table_name, info in tables.items():
            if max_records and count >= max_records:
                break

            cols = info['columns']
            module = info['module']

            # Skip views with complex names (like vrv*, brv*)
            if table_name.startswith(('vrv', 'brv', 'sys', 'fn_')):
                continue

            # Get first 6 columns
            col_names = [c.get('ColumnName', '') for c in cols[:6] if c.get('ColumnName')]
            if not col_names:
                continue

            col_list = ', '.join(col_names)

            # Determine company column
            prefix = table_name[:2] if len(table_name) >= 2 else ''
            co_col = company_cols.get(prefix, 'Company')

            # Check if company column exists in this table
            table_col_names = [c.get('ColumnName', '') for c in cols]
            if co_col not in table_col_names:
                # Try to find a *Co column
                co_cols_in_table = [c for c in table_col_names if c.endswith('Co')]
                co_col = co_cols_in_table[0] if co_cols_in_table else None

            # Rotate through question templates
            template_idx = count % len(question_templates)
            question = question_templates[template_idx].format(table=table_name)

            if co_col:
                sql = f"""SELECT {col_list}
FROM {table_name} WITH (NOLOCK)
WHERE {co_col} = @{co_col}
ORDER BY {col_names[0]}"""

                output = f"""```sql
{sql}
```

This query selects key columns from {table_name} ({module} module).

Important:
- WITH (NOLOCK) prevents blocking production transactions
- Always filter by company column ({co_col})
- Use exact column case (Viewpoint is case-sensitive)"""
            else:
                sql = f"""SELECT {col_list}
FROM {table_name} WITH (NOLOCK)
ORDER BY {col_names[0]}"""

                output = f"""```sql
{sql}
```

This query selects key columns from {table_name} ({module} module).

Important:
- WITH (NOLOCK) prevents blocking production transactions
- Use exact column case (Viewpoint is case-sensitive)"""

            yield TrainingRecord(
                instruction=question,
                output=output,
                category=DataCategory.SQL_GENERATION.value,
                source="Table_Query_Examples"
            )
            count += 1

            # Generate a second variation if we have room
            if max_records and count >= max_records:
                break

            # Add a "how to filter" example
            if len(cols) >= 3 and co_col:
                filter_col = cols[2].get('ColumnName', '') if cols[2].get('ColumnName') != co_col else cols[1].get('ColumnName', '')
                if filter_col:
                    yield TrainingRecord(
                        instruction=f"Filter {table_name} by {filter_col}",
                        output=f"""```sql
SELECT {col_list}
FROM {table_name} WITH (NOLOCK)
WHERE {co_col} = @{co_col}
  AND {filter_col} = @{filter_col}
ORDER BY {col_names[0]}
```

Always include:
- WITH (NOLOCK) to prevent blocking
- Company filter ({co_col}) for data isolation
- Specific columns instead of SELECT *""",
                        category=DataCategory.SQL_GENERATION.value,
                        source="Table_Query_Examples"
                    )
                    count += 1

    def generate_nolock_fix_examples(self, max_records: Optional[int] = None) -> Iterator[TrainingRecord]:
        """Generate many examples of fixing queries by adding NOLOCK."""
        columns = self.load_columns()
        count = 0

        # Group columns by table
        tables = {}
        for col in columns:
            if not isinstance(col, dict):
                continue
            obj_name = col.get('ObjectName', '')
            if obj_name and obj_name not in tables:
                tables[obj_name] = []
            if obj_name:
                tables[obj_name].append(col.get('ColumnName', ''))

        # Standard company column mapping
        company_cols = {
            'AP': 'APCo', 'AR': 'ARCo', 'JC': 'JCCo', 'PR': 'PRCo',
            'GL': 'GLCo', 'EM': 'EMCo', 'PO': 'POCo', 'IN': 'INCo',
            'SM': 'SMCo', 'HQ': 'HQCo', 'HR': 'HRCo', 'SL': 'SLCo',
        }

        # Error patterns to fix
        error_patterns = [
            # Missing NOLOCK
            {
                "wrong": "SELECT * FROM {table}",
                "issues": ["Missing WITH (NOLOCK)", "Missing company filter", "Using SELECT *"]
            },
            # Using alias
            {
                "wrong": "SELECT t.* FROM {table} t WHERE t.{co} = 1",
                "issues": ["Missing WITH (NOLOCK)", "Using table alias 't'"]
            },
            # Using dbo prefix
            {
                "wrong": "SELECT * FROM dbo.{table} WHERE {co} = 1",
                "issues": ["Missing WITH (NOLOCK)", "Using 'dbo.' prefix", "Using SELECT *"]
            },
            # Wrong case
            {
                "wrong": "SELECT {col_lower} FROM {table} WHERE {co_lower} = 1",
                "issues": ["Missing WITH (NOLOCK)", "Wrong column case ({col_lower} should be {col})"]
            },
        ]

        for table_name, col_names in tables.items():
            if max_records and count >= max_records:
                break

            # Skip system tables
            if table_name.startswith(('sys', 'fn_', 'vrv', 'brv')):
                continue

            if not col_names or len(col_names) < 3:
                continue

            # Get first few columns
            cols = col_names[:5]
            col_list = ', '.join(cols)

            # Determine company column
            prefix = table_name[:2] if len(table_name) >= 2 else ''
            co_col = company_cols.get(prefix, None)
            if not co_col or co_col not in col_names:
                co_cols_in_table = [c for c in col_names if c.endswith('Co')]
                co_col = co_cols_in_table[0] if co_cols_in_table else None

            if not co_col:
                continue

            # Generate one fix example per table
            pattern = error_patterns[count % len(error_patterns)]
            wrong_query = pattern["wrong"].format(
                table=table_name,
                co=co_col,
                col_lower=cols[0].lower() if cols else 'id',
                co_lower=co_col.lower()
            )
            issues = [i.format(col_lower=cols[0].lower() if cols else 'id', col=cols[0] if cols else 'ID') for i in pattern["issues"]]

            correct_query = f"""SELECT {col_list}
FROM {table_name} WITH (NOLOCK)
WHERE {co_col} = @{co_col}"""

            yield TrainingRecord(
                instruction=f"Fix this query: {wrong_query}",
                output=f"""**Issues found:**
{chr(10).join(['- ' + i for i in issues])}

**Corrected SQL:**
```sql
{correct_query}
```

**Best practices:**
- Always use WITH (NOLOCK) for SELECT queries
- Always filter by company column ({co_col})
- Use full table names, not aliases
- Match exact column case
- Specify columns instead of SELECT *""",
                category=DataCategory.ERROR_CORRECTION.value,
                source="NOLOCK_Fix_Examples"
            )
            count += 1

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _extract_section(self, content: str, start_marker: str, end_marker: str) -> Optional[str]:
        """Extract section from markdown."""
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return None

        start_idx += len(start_marker)
        end_idx = content.find(end_marker, start_idx)

        if end_idx == -1:
            return content[start_idx:].strip()

        return content[start_idx:end_idx].strip()

    def save_dataset(self, records: List[TrainingRecord], output_path: str, deduplicate: bool = True):
        """Save dataset to JSON file with optional deduplication."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to Alpaca format
        data = [r.to_alpaca() for r in records]

        # Deduplicate by instruction text
        if deduplicate:
            seen = set()
            unique_data = []
            for item in data:
                key = item['instruction'].lower().strip()
                if key not in seen:
                    seen.add(key)
                    unique_data.append(item)
            removed = len(data) - len(unique_data)
            if removed > 0:
                logger.info(f"Removed {removed} duplicate records")
            data = unique_data

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(data)} records to {output_file}")

    def print_stats(self):
        """Print generation statistics."""
        print("\n" + "=" * 60)
        print("VGPT2 v3 Data Generation Statistics")
        print("=" * 60)

        total = 0
        for source, count in sorted(self.stats.items(), key=lambda x: -x[1]):
            print(f"  {source}: {count:,}")
            total += count

        print("-" * 60)
        print(f"  TOTAL: {total:,}")
        print("=" * 60)


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="VGPT2 v3 Training Data Generator"
    )
    parser.add_argument('--vgpt2', type=str, default='C:/Github/VGPT2',
                        help='Path to VGPT2 repository')
    parser.add_argument('--output', type=str, default='data/vgpt2_v3_sft.json',
                        help='Output file path')
    parser.add_argument('--max-per-source', type=int, default=None,
                        help='Maximum records per source (for testing)')

    args = parser.parse_args()

    generator = VGPT2V3DataGenerator(args.vgpt2)

    records = generator.generate_all(max_per_source=args.max_per_source)
    generator.save_dataset(records, args.output)
    generator.print_stats()

    print(f"\nGenerated {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
