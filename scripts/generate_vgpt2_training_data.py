#!/usr/bin/env python3
"""
VGPT2 Training Dataset Generator

Generates training data for fine-tuning from the VGPT2 repository.

DATA SOURCE PRIORITY (based on breadth and quality):

TIER 1 - HIGHEST QUALITY (Production-validated, complete):
  1. Schema Metadata (_Metadata/columns.json, indexes.json)
  2. Stored Procedure Documentation (7,041 SP docs with business context)
  3. View Documentation (2,351 view docs)
  4. Relationship Validation (validated JOIN recipes)

TIER 2 - BUSINESS CONTEXT (Wide coverage, not table-specific):
  5. DDFI Field Definitions (form field descriptions, validation rules)
  6. DDFH Form Definitions (form-to-view mappings)
  7. Trimble Help Articles (Vista_KB - business workflow context)
  8. Support Articles (Azure AI Search index - KB articles)

TIER 3 - SPECIALIZED (Narrow but deep):
  9. Expert SQL (validated SQL queries - small but high quality)
  10. Crystal Report SQL (production report queries)
  11. Reference Documents (_ai_orchestration/reference/)

EXCLUDED (older versions or superseded):
  - Functions/Function_Documentation (older format)
  - Legacy_ERD_Diagrams (superseded by _ERD)
  - _archive folders

Author: Generated for Viewpoint SQL fine-tuning
Date: 2024-12-27
"""

import json
import csv
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Iterator
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatasetCategory(Enum):
    """Categories for training data - each will generate different types of examples."""
    SCHEMA_QUERY = "schema_query"           # "What columns are in APTH?" → answer
    SQL_GENERATION = "sql_generation"        # Natural language → SQL
    SQL_VALIDATION = "sql_validation"        # SQL → corrected SQL / validation
    BUSINESS_CONTEXT = "business_context"    # "How does AP posting work?" → explanation
    JOIN_PATTERN = "join_pattern"            # Table A + Table B → correct JOIN
    RULE_ENFORCEMENT = "rule_enforcement"    # Wrong SQL → correct SQL + explanation


@dataclass
class TrainingRecord:
    """Single training record in Alpaca format."""
    instruction: str
    input: str = ""
    output: str = ""
    category: str = ""
    source: str = ""
    quality_score: float = 1.0  # 0-1, higher is better
    
    def to_alpaca(self) -> Dict:
        """Convert to Alpaca format for LLaMA Factory."""
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output
        }


@dataclass
class DataSourceInventory:
    """Inventory of all data sources with statistics."""
    source_name: str
    path: str
    file_count: int = 0
    total_size_mb: float = 0.0
    estimated_records: int = 0
    quality_tier: int = 1  # 1=highest, 3=lowest
    notes: str = ""


class VGPT2DatasetGenerator:
    """
    Main generator class for VGPT2 training data.
    
    Usage:
        generator = VGPT2DatasetGenerator(
            vgpt2_path="C:/Github/VGPT2",
            vista_kb_path="C:/Github/Vista_KB"  # Optional
        )
        
        # Step 1: Inventory all sources
        inventory = generator.inventory_sources()
        
        # Step 2: Generate training data
        records = generator.generate_all()
        
        # Step 3: Save dataset
        generator.save_dataset(records, "output/vgpt2_training.json")
    """
    
    def __init__(self, vgpt2_path: str, vista_kb_path: Optional[str] = None):
        self.vgpt2 = Path(vgpt2_path)
        self.vista_kb = Path(vista_kb_path) if vista_kb_path else None
        
        # Validate paths exist
        if not self.vgpt2.exists():
            raise ValueError(f"VGPT2 path does not exist: {vgpt2_path}")
        
        # Key subdirectories
        self.metadata_dir = self.vgpt2 / "Viewpoint_Database" / "_Metadata"
        self.sp_docs_dir = self.vgpt2 / "Viewpoint_Database" / "Stored_Procedures" / "SP_Documentation"
        self.view_docs_dir = self.vgpt2 / "Viewpoint_Database" / "View" / "View_Documentation"
        self.relationship_dir = self.vgpt2 / "Viewpoint_Database" / "_Relationship_Validation"
        self.ai_orchestration_dir = self.vgpt2 / "_ai_orchestration"
        self.experts_dir = self.vgpt2 / "Experts_V2"
        
        # Loaded data caches
        self._columns_cache = None
        self._ddfi_cache = None
        self._ddfh_cache = None
        
        logger.info(f"Initialized VGPT2DatasetGenerator with path: {vgpt2_path}")
    
    def inventory_sources(self) -> List[DataSourceInventory]:
        """Inventory all available data sources with statistics."""
        inventory = []
        
        # TIER 1 Sources
        inventory.extend(self._inventory_tier1_schema())
        inventory.extend(self._inventory_tier1_sp_docs())
        inventory.extend(self._inventory_tier1_view_docs())
        inventory.extend(self._inventory_tier1_relationships())
        
        # TIER 2 Sources
        inventory.extend(self._inventory_tier2_ddfi())
        inventory.extend(self._inventory_tier2_ddfh())
        inventory.extend(self._inventory_tier2_help_articles())
        
        # TIER 3 Sources
        inventory.extend(self._inventory_tier3_experts())
        inventory.extend(self._inventory_tier3_reference())
        
        return inventory

    # =========================================================================
    # TIER 1 INVENTORY METHODS
    # =========================================================================

    def _inventory_tier1_schema(self) -> List[DataSourceInventory]:
        """Inventory schema metadata files."""
        results = []

        # columns.json - primary schema source
        columns_file = self.metadata_dir / "columns.json"
        if columns_file.exists():
            size_mb = columns_file.stat().st_size / (1024 * 1024)
            # Estimate: ~30MB file with ~50K column definitions
            results.append(DataSourceInventory(
                source_name="Schema Columns",
                path=str(columns_file),
                file_count=1,
                total_size_mb=round(size_mb, 2),
                estimated_records=50000,  # Approximate column count
                quality_tier=1,
                notes="Primary schema source - all table/view columns with types"
            ))

        # indexes.json
        indexes_file = self.metadata_dir / "indexes.json"
        if indexes_file.exists():
            size_mb = indexes_file.stat().st_size / (1024 * 1024)
            results.append(DataSourceInventory(
                source_name="Schema Indexes",
                path=str(indexes_file),
                file_count=1,
                total_size_mb=round(size_mb, 2),
                estimated_records=5000,
                quality_tier=1,
                notes="Index definitions - useful for query optimization context"
            ))

        # foreign_keys.json
        fk_file = self.metadata_dir / "foreign_keys.json"
        if fk_file.exists():
            size_mb = fk_file.stat().st_size / (1024 * 1024)
            results.append(DataSourceInventory(
                source_name="Foreign Keys",
                path=str(fk_file),
                file_count=1,
                total_size_mb=round(size_mb, 2),
                estimated_records=2000,
                quality_tier=1,
                notes="FK relationships - critical for JOIN validation"
            ))

        return results

    def _inventory_tier1_sp_docs(self) -> List[DataSourceInventory]:
        """Inventory stored procedure documentation."""
        if not self.sp_docs_dir.exists():
            return []

        md_files = list(self.sp_docs_dir.glob("*.md"))
        total_size = sum(f.stat().st_size for f in md_files) / (1024 * 1024)

        return [DataSourceInventory(
            source_name="Stored Procedure Documentation",
            path=str(self.sp_docs_dir),
            file_count=len(md_files),
            total_size_mb=round(total_size, 2),
            estimated_records=len(md_files),  # 1 record per SP
            quality_tier=1,
            notes="AI-generated SP docs with business context, parameters, SQL"
        )]

    def _inventory_tier1_view_docs(self) -> List[DataSourceInventory]:
        """Inventory view documentation."""
        if not self.view_docs_dir.exists():
            return []

        md_files = list(self.view_docs_dir.glob("*.md"))
        total_size = sum(f.stat().st_size for f in md_files) / (1024 * 1024)

        return [DataSourceInventory(
            source_name="View Documentation",
            path=str(self.view_docs_dir),
            file_count=len(md_files),
            total_size_mb=round(total_size, 2),
            estimated_records=len(md_files),
            quality_tier=1,
            notes="View definitions with SQL, tables used, complexity analysis"
        )]

    def _inventory_tier1_relationships(self) -> List[DataSourceInventory]:
        """Inventory relationship validation data."""
        if not self.relationship_dir.exists():
            return []

        results = []

        # Join Recipes (most valuable for training)
        join_recipes_dir = self.relationship_dir / "03_Join_Recipes"
        if join_recipes_dir.exists():
            json_files = list(join_recipes_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in json_files) / (1024 * 1024)
            results.append(DataSourceInventory(
                source_name="Join Recipes",
                path=str(join_recipes_dir),
                file_count=len(json_files),
                total_size_mb=round(total_size, 2),
                estimated_records=len(json_files) * 5,  # ~5 JOINs per recipe
                quality_tier=1,
                notes="Production-validated JOIN patterns from views"
            ))

        # Object Cards (table/view metadata)
        object_cards_dir = self.relationship_dir / "01_Object_Cards"
        if object_cards_dir.exists():
            json_files = list(object_cards_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in json_files) / (1024 * 1024)
            results.append(DataSourceInventory(
                source_name="Object Cards",
                path=str(object_cards_dir),
                file_count=len(json_files),
                total_size_mb=round(total_size, 2),
                estimated_records=len(json_files),
                quality_tier=1,
                notes="Table/view metadata with column info"
            ))

        # Relationship Cards
        rel_cards_dir = self.relationship_dir / "02_Relationship_Cards"
        if rel_cards_dir.exists():
            json_files = list(rel_cards_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in json_files) / (1024 * 1024)
            results.append(DataSourceInventory(
                source_name="Relationship Cards",
                path=str(rel_cards_dir),
                file_count=len(json_files),
                total_size_mb=round(total_size, 2),
                estimated_records=len(json_files) * 3,
                quality_tier=1,
                notes="Table relationship definitions"
            ))

        return results

    # =========================================================================
    # TIER 2 INVENTORY METHODS
    # =========================================================================

    def _inventory_tier2_ddfi(self) -> List[DataSourceInventory]:
        """Inventory DDFI field definitions."""
        ddfi_file = self.metadata_dir / "DDFI.json"
        if not ddfi_file.exists():
            return []

        size_mb = ddfi_file.stat().st_size / (1024 * 1024)
        return [DataSourceInventory(
            source_name="DDFI Field Definitions",
            path=str(ddfi_file),
            file_count=1,
            total_size_mb=round(size_mb, 2),
            estimated_records=50000,  # ~50K field definitions
            quality_tier=2,
            notes="Form field descriptions, validation rules, status text - business context"
        )]

    def _inventory_tier2_ddfh(self) -> List[DataSourceInventory]:
        """Inventory DDFH form definitions."""
        ddfh_file = self.metadata_dir / "DDFH.json"
        if not ddfh_file.exists():
            return []

        size_mb = ddfh_file.stat().st_size / (1024 * 1024)
        return [DataSourceInventory(
            source_name="DDFH Form Definitions",
            path=str(ddfh_file),
            file_count=1,
            total_size_mb=round(size_mb, 2),
            estimated_records=2000,  # ~2K forms
            quality_tier=2,
            notes="Form-to-view mappings, form titles, module assignments"
        )]

    def _inventory_tier2_help_articles(self) -> List[DataSourceInventory]:
        """Inventory Trimble help articles from Vista_KB."""
        if not self.vista_kb:
            return []

        results = []

        # Web content (HTML articles)
        web_content = self.vista_kb / "data" / "web_content"
        if web_content.exists():
            html_files = list(web_content.rglob("*.html"))
            total_size = sum(f.stat().st_size for f in html_files) / (1024 * 1024)
            results.append(DataSourceInventory(
                source_name="Trimble Help Articles (HTML)",
                path=str(web_content),
                file_count=len(html_files),
                total_size_mb=round(total_size, 2),
                estimated_records=len(html_files),
                quality_tier=2,
                notes="Official Vista help documentation - business workflows"
            ))

        # Processed content (if available)
        processed = self.vista_kb / "data" / "processed_content"
        if processed.exists():
            md_files = list(processed.rglob("*.md"))
            if md_files:
                total_size = sum(f.stat().st_size for f in md_files) / (1024 * 1024)
                results.append(DataSourceInventory(
                    source_name="Trimble Help Articles (Processed)",
                    path=str(processed),
                    file_count=len(md_files),
                    total_size_mb=round(total_size, 2),
                    estimated_records=len(md_files),
                    quality_tier=2,
                    notes="Cleaned/extracted help content"
                ))

        return results

    # =========================================================================
    # TIER 3 INVENTORY METHODS
    # =========================================================================

    def _inventory_tier3_experts(self) -> List[DataSourceInventory]:
        """Inventory expert SQL examples."""
        if not self.experts_dir.exists():
            return []

        results = []

        # Expert SQL files
        sql_files = list(self.experts_dir.rglob("*.sql"))
        if sql_files:
            total_size = sum(f.stat().st_size for f in sql_files) / (1024 * 1024)
            results.append(DataSourceInventory(
                source_name="Expert SQL Examples",
                path=str(self.experts_dir),
                file_count=len(sql_files),
                total_size_mb=round(total_size, 2),
                estimated_records=len(sql_files),
                quality_tier=3,
                notes="Validated expert SQL queries - high quality but limited"
            ))

        return results

    def _inventory_tier3_reference(self) -> List[DataSourceInventory]:
        """Inventory reference documents."""
        ref_dir = self.ai_orchestration_dir / "reference"
        if not ref_dir.exists():
            return []

        results = []

        # Reference markdown files
        md_files = list(ref_dir.rglob("*.md"))
        if md_files:
            total_size = sum(f.stat().st_size for f in md_files) / (1024 * 1024)
            results.append(DataSourceInventory(
                source_name="Reference Documents",
                path=str(ref_dir),
                file_count=len(md_files),
                total_size_mb=round(total_size, 2),
                estimated_records=len(md_files) * 50,  # Multiple sections per doc
                quality_tier=3,
                notes="Module guides, naming conventions, business rules"
            ))

        return results

    # =========================================================================
    # DATA LOADING METHODS
    # =========================================================================

    def load_columns(self) -> Dict:
        """Load and cache columns.json."""
        if self._columns_cache is None:
            columns_file = self.metadata_dir / "columns.json"
            if columns_file.exists():
                with open(columns_file, 'r', encoding='utf-8') as f:
                    self._columns_cache = json.load(f)
                logger.info(f"Loaded {len(self._columns_cache)} column definitions")
            else:
                self._columns_cache = {}
        return self._columns_cache

    def load_ddfi(self) -> List[Dict]:
        """Load and cache DDFI.json."""
        if self._ddfi_cache is None:
            ddfi_file = self.metadata_dir / "DDFI.json"
            if ddfi_file.exists():
                with open(ddfi_file, 'r', encoding='utf-8') as f:
                    self._ddfi_cache = json.load(f)
                logger.info(f"Loaded {len(self._ddfi_cache)} DDFI field definitions")
            else:
                self._ddfi_cache = []
        return self._ddfi_cache

    def load_ddfh(self) -> List[Dict]:
        """Load and cache DDFH.json."""
        if self._ddfh_cache is None:
            ddfh_file = self.metadata_dir / "DDFH.json"
            if ddfh_file.exists():
                with open(ddfh_file, 'r', encoding='utf-8') as f:
                    self._ddfh_cache = json.load(f)
                logger.info(f"Loaded {len(self._ddfh_cache)} DDFH form definitions")
            else:
                self._ddfh_cache = []
        return self._ddfh_cache

    # =========================================================================
    # GENERATION METHODS
    # =========================================================================

    def generate_all(self, max_per_source: Optional[int] = None,
                     validate: bool = True, abort_on_failure: bool = True) -> List[TrainingRecord]:
        """
        Generate training records from all sources.

        Args:
            max_per_source: Maximum records per source (None = unlimited)
            validate: If True, run validation after generation
            abort_on_failure: If True, raise exception if validation fails

        Returns:
            List of TrainingRecord objects

        Raises:
            ValueError: If validation fails and abort_on_failure=True
        """
        all_records = []
        source_counts = {}  # Track counts per source for validation

        def _generate_and_track(source_name: str, generator_func, max_records):
            """Generate records and track source counts."""
            logger.info(f"Generating {source_name} examples...")
            records = generator_func(max_records)
            all_records.extend(records)
            source_counts[source_name] = len(records)
            logger.info(f"  -> {len(records)} records from {source_name}")
            return records

        # TIER 1 - Schema and Documentation
        _generate_and_track("Schema Metadata", self.generate_schema_queries, max_per_source)
        _generate_and_track("SP Documentation", self.generate_sp_examples, max_per_source)
        _generate_and_track("View Documentation", self.generate_view_examples, max_per_source)
        _generate_and_track("DDFI Forms", self.generate_ddfi_examples, max_per_source)
        _generate_and_track("JOIN Patterns", self.generate_join_pattern_examples, max_per_source)

        # TIER 2 - Crystal Reports and Rules (PREVIOUSLY MISSING)
        _generate_and_track("Crystal Report SQL", self.generate_crystal_report_examples, max_per_source)
        _generate_and_track("Canonical Rules", self.generate_canonical_rules_examples, max_per_source)
        _generate_and_track("Reference Documents", self.generate_reference_doc_examples, max_per_source)
        _generate_and_track("Heuristics", self.generate_heuristic_examples, max_per_source)
        _generate_and_track("Workflows", self.generate_workflow_examples, max_per_source)

        # TIER 3 - Expert SQL and Patterns
        _generate_and_track("Experts V2", self.generate_experts_v2_examples, max_per_source)
        _generate_and_track("Naming Conventions", self.generate_naming_convention_examples, max_per_source)
        _generate_and_track("Error Corrections", self.generate_error_correction_examples, max_per_source)
        _generate_and_track("Query Optimization", self.generate_query_optimization_examples, max_per_source)

        # Also include SQL generation examples (derived from views)
        logger.info("Generating SQL generation examples...")
        sql_gen_records = self.generate_sql_generation_examples(max_per_source)
        all_records.extend(sql_gen_records)
        # Note: These don't count toward a specific source since they're derived

        logger.info(f"Total records generated: {len(all_records)}")

        # Print source summary
        logger.info("=" * 60)
        logger.info("SOURCE SUMMARY:")
        for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            logger.info(f"  {source}: {count:,} records")
        logger.info("=" * 60)

        # Validation
        if validate:
            from training_data_validation import validate_before_training
            report = validate_before_training(
                all_records, source_counts, str(self.vgpt2),
                abort_on_failure=abort_on_failure
            )
            if not report.passed and not abort_on_failure:
                logger.warning("Validation FAILED but continuing (abort_on_failure=False)")

        return all_records

    def generate_schema_queries(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate schema query training examples."""
        records = []
        columns = self.load_columns()

        # columns.json is a list of column definitions
        # Group columns by ObjectName (table/view name)
        tables = {}
        for col in columns:
            if isinstance(col, dict):
                obj_name = col.get('ObjectName', 'unknown')
                schema = col.get('SchemaName', 'dbo')
                full_name = f"{schema}.{obj_name}" if schema != 'dbo' else obj_name

                if full_name not in tables:
                    tables[full_name] = {
                        'columns': [],
                        'module': col.get('Module', 'Unknown'),
                        'object_type': col.get('ObjectType', 'Table')
                    }
                tables[full_name]['columns'].append(col)

        # Generate examples for each table
        for table_name, table_info in tables.items():
            if max_records and len(records) >= max_records:
                break

            cols = table_info['columns']
            obj_type = table_info['object_type'].lower()
            module = table_info['module']

            # Example 1: "What columns are in TABLE?"
            col_names = [c.get('ColumnName', 'unknown') for c in cols[:15]]
            col_list = ", ".join(col_names)
            if len(cols) > 15:
                col_list += f"... ({len(cols)} total columns)"

            records.append(TrainingRecord(
                instruction=f"What columns are in the {table_name} {obj_type}?",
                input="",
                output=f"The {table_name} {obj_type} (Module: {module}) contains: {col_list}",
                category=DatasetCategory.SCHEMA_QUERY.value,
                source="columns.json",
                quality_score=1.0
            ))

            # Example 2: Column details for first few columns
            if len(cols) >= 3:
                detail_cols = cols[:3]
                details = []
                for c in detail_cols:
                    details.append(f"{c.get('ColumnName')} ({c.get('DataType')}, {'nullable' if c.get('IsNullable') == 'True' else 'not null'})")

                records.append(TrainingRecord(
                    instruction=f"Describe the key columns in {table_name}",
                    input="",
                    output=f"Key columns in {table_name}: " + "; ".join(details),
                    category=DatasetCategory.SCHEMA_QUERY.value,
                    source="columns.json",
                    quality_score=0.9
                ))

        logger.info(f"Generated {len(records)} schema query examples")
        return records

    def generate_sp_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate stored procedure training examples."""
        records = []

        if not self.sp_docs_dir.exists():
            return records

        for md_file in self.sp_docs_dir.glob("*.md"):
            if max_records and len(records) >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                sp_name = md_file.stem

                # Extract overview section
                overview = self._extract_section(content, "## Overview", "##")
                if overview:
                    records.append(TrainingRecord(
                        instruction=f"What does the stored procedure {sp_name} do?",
                        input="",
                        output=overview.strip(),
                        category=DatasetCategory.BUSINESS_CONTEXT.value,
                        source=f"SP_Documentation/{md_file.name}",
                        quality_score=0.9
                    ))
            except Exception as e:
                logger.warning(f"Error processing {md_file}: {e}")

        logger.info(f"Generated {len(records)} SP examples")
        return records

    def generate_view_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate view documentation training examples."""
        records = []

        if not self.view_docs_dir.exists():
            return records

        for md_file in self.view_docs_dir.glob("*.md"):
            if max_records and len(records) >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                view_name = md_file.stem

                # Extract overview
                overview = self._extract_section(content, "## Overview", "##")
                if overview:
                    records.append(TrainingRecord(
                        instruction=f"What is the purpose of the {view_name} view?",
                        input="",
                        output=overview.strip(),
                        category=DatasetCategory.BUSINESS_CONTEXT.value,
                        source=f"View_Documentation/{md_file.name}",
                        quality_score=0.9
                    ))
            except Exception as e:
                logger.warning(f"Error processing {md_file}: {e}")

        logger.info(f"Generated {len(records)} view examples")
        return records

    def generate_ddfi_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate DDFI field definition training examples."""
        records = []
        ddfi = self.load_ddfi()

        # Group by form
        forms = {}
        for field in ddfi:
            form = field.get('Form', 'unknown')
            if form not in forms:
                forms[form] = []
            forms[form].append(field)

        for form_name, fields in forms.items():
            if max_records and len(records) >= max_records:
                break

            # Skip forms with no useful descriptions
            useful_fields = [f for f in fields if f.get('Description') and f.get('Description') != 'NULL']
            if not useful_fields:
                continue

            # Generate field list example
            field_descs = [f"{f.get('Description', 'unknown')}" for f in useful_fields[:10]]

            records.append(TrainingRecord(
                instruction=f"What fields are available on the {form_name} form?",
                input="",
                output=f"The {form_name} form includes these fields: {', '.join(field_descs)}",
                category=DatasetCategory.BUSINESS_CONTEXT.value,
                source="DDFI.json",
                quality_score=0.8
            ))

        logger.info(f"Generated {len(records)} DDFI examples")
        return records

    def generate_join_pattern_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate JOIN pattern training examples from relationship validation data."""
        records = []

        join_recipes_dir = self.relationship_dir / "03_Join_Recipes"
        if not join_recipes_dir.exists():
            return records

        for json_file in join_recipes_dir.glob("*.json"):
            if max_records and len(records) >= max_records:
                break

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    recipe = json.load(f)

                view_name = recipe.get('view', json_file.stem)
                hops = recipe.get('hops', [])

                if not hops:
                    continue

                # Generate JOIN pattern examples
                for hop in hops:
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
                    join_condition = " AND ".join(conditions)

                    # Example: How to JOIN these tables
                    # Build proper SQL snippet
                    sql_snippet = f"FROM {from_table}\n{join_type} JOIN {to_table}\n  ON {join_condition}"

                    records.append(TrainingRecord(
                        instruction=f"How do I join {from_table} with {to_table} in Viewpoint Vista?",
                        input="",
                        output=f"To join {from_table} with {to_table}, use:\n\n```sql\n{sql_snippet}\n```\n\nThis pattern is used in the {view_name} view.",
                        category=DatasetCategory.JOIN_PATTERN.value,
                        source=f"03_Join_Recipes/{json_file.name}",
                        quality_score=1.0
                    ))

                    if max_records and len(records) >= max_records:
                        break

            except Exception as e:
                logger.warning(f"Error processing {json_file}: {e}")

        logger.info(f"Generated {len(records)} JOIN pattern examples")
        return records

    def generate_sql_generation_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate SQL generation training examples from SP and view documentation."""
        records = []

        # Generate from view documentation (simpler SQL)
        if self.view_docs_dir.exists():
            for md_file in self.view_docs_dir.glob("*.md"):
                if max_records and len(records) >= max_records:
                    break

                try:
                    content = md_file.read_text(encoding='utf-8')
                    view_name = md_file.stem

                    # Extract SQL definition
                    sql = self._extract_section(content, "```sql", "```")
                    overview = self._extract_section(content, "## Overview", "##")

                    if sql and overview and len(sql) < 2000:  # Skip very long SQL
                        # Clean up the SQL
                        sql = sql.strip()
                        if sql.startswith("SELECT") or sql.startswith("CREATE"):
                            records.append(TrainingRecord(
                                instruction=f"Write a SQL query to: {overview[:200]}",
                                input=f"Context: Viewpoint Vista database, view {view_name}",
                                output=sql,
                                category=DatasetCategory.SQL_GENERATION.value,
                                source=f"View_Documentation/{md_file.name}",
                                quality_score=0.85
                            ))
                except Exception as e:
                    logger.warning(f"Error processing {md_file}: {e}")

        logger.info(f"Generated {len(records)} SQL generation examples")
        return records

    def generate_expert_sql_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate training examples from validated expert SQL queries."""
        records = []
        experts_dir = self.vgpt2 / "Experts" / "04_Experts" / "experts"

        if not experts_dir.exists():
            logger.warning(f"Experts directory not found: {experts_dir}")
            return records

        for sql_file in experts_dir.rglob("*.sql"):
            if max_records and len(records) >= max_records:
                break

            # Skip validation scripts
            if sql_file.name.startswith("00_validate"):
                continue

            try:
                content = sql_file.read_text(encoding='utf-8')

                # Extract purpose/description from comments
                purpose = ""
                lines = content.split('\n')
                for line in lines[:30]:  # Check first 30 lines
                    if 'Purpose:' in line:
                        purpose = line.split('Purpose:')[1].strip()
                        break
                    elif line.strip().startswith('--') and not line.strip().startswith('----'):
                        # First comment line as purpose
                        if not purpose:
                            purpose = line.replace('--', '').strip()

                if not purpose or len(content) > 5000:  # Skip if no purpose or too long
                    continue

                # Clean SQL - remove excessive comments
                sql_lines = [l for l in lines if not l.strip().startswith('--') or 'PARAMETER' in l.upper()]
                clean_sql = '\n'.join(sql_lines).strip()

                # Get module from path
                parts = sql_file.parts
                module = "Unknown"
                for i, part in enumerate(parts):
                    if part in ["AP", "AR", "GL", "JC", "PR", "PM", "EM", "IN", "MS", "SM", "HR"]:
                        module = part
                        break

                records.append(TrainingRecord(
                    instruction=f"Write a SQL query for Viewpoint Vista: {purpose}",
                    input=f"Module: {module}",
                    output=clean_sql[:3000],  # Limit output size
                    category=DatasetCategory.SQL_GENERATION.value,
                    source=f"Experts/{sql_file.name}",
                    quality_score=0.95  # High quality validated SQL
                ))

            except Exception as e:
                logger.warning(f"Error processing {sql_file}: {e}")

        logger.info(f"Generated {len(records)} expert SQL examples")
        return records

    def generate_naming_convention_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate naming convention and best practice training examples."""
        records = []

        # Viewpoint naming conventions (hardcoded best practices)
        conventions = [
            {
                "q": "What is the correct way to reference tables in Viewpoint Vista SQL?",
                "a": "In Viewpoint Vista:\n- Use view names (APTH) not base tables (bAPTH) for SELECT queries\n- Don't use schema prefix (dbo.) for views - they default to dbo\n- Always use WITH (NOLOCK) after view names: FROM APTH WITH (NOLOCK)\n- Use exact column case from the database (APCo, not apco)"
            },
            {
                "q": "What naming convention do Viewpoint table prefixes follow?",
                "a": "Viewpoint table/view prefixes indicate the module:\n- AP = Accounts Payable\n- AR = Accounts Receivable\n- GL = General Ledger\n- JC = Job Cost\n- PR = Payroll\n- PM = Project Management\n- EM = Equipment Management\n- IN = Inventory\n- SM = Service Management\n- HR = Human Resources\n- HQ = Headquarters (company-wide settings)"
            },
            {
                "q": "What's the difference between b-prefixed and non-prefixed tables?",
                "a": "In Viewpoint Vista:\n- b-prefixed tables (bAPTH) are base/physical tables used for data modification\n- Non-prefixed names (APTH) are views built on base tables\n- Always use views for SELECT queries (better performance, security)\n- Use base tables only when inserting/updating data"
            },
            {
                "q": "How should I handle company context in Viewpoint queries?",
                "a": "Most Viewpoint tables use company columns:\n- APCo = AP Company\n- JCCo = Job Cost Company\n- PRCo = Payroll Company\n- GLCo = GL Company\n- HQCo = Headquarters Company\n\nAlways filter by company in WHERE clause or JOIN conditions to ensure data isolation between companies."
            },
            {
                "q": "What columns are commonly used for JOINs in Viewpoint?",
                "a": "Common JOIN columns in Viewpoint:\n- Company columns (APCo, JCCo, PRCo, GLCo)\n- Key sequences (KeyID, Seq, Line)\n- Reference numbers (Invoice, PO, Job, Contract)\n- Month columns (Mth - stored as datetime)\n\nAlways check foreign_keys.json or relationship cards for validated JOIN patterns."
            },
            {
                "q": "How are dates stored in Viewpoint Vista?",
                "a": "Viewpoint date handling:\n- Month (Mth) columns store first day of month as datetime\n- Date columns use datetime type\n- For month comparisons, use: WHERE Mth = '2024-01-01'\n- For date ranges: WHERE Date >= @StartDate AND Date < @EndDate"
            },
            {
                "q": "What are vrv* and brv* views in Viewpoint?",
                "a": "Viewpoint reporting views:\n- vrv* = Viewpoint Report Views (optimized for reporting)\n- brv* = Base Report Views\n\nThese are pre-built views designed for Crystal Reports. Always check if a vrv* view exists before writing custom SQL - they're optimized and validated."
            },
            {
                "q": "How do I find all invoices for a job in Viewpoint?",
                "a": "To find invoices for a job:\n```sql\nSELECT APTH.*, APTL.*\nFROM APTH WITH (NOLOCK)\nJOIN APTL WITH (NOLOCK) ON APTH.APCo = APTL.APCo AND APTH.Mth = APTL.Mth AND APTH.APTrans = APTL.APTrans\nWHERE APTL.JCCo = @JCCo AND APTL.Job = @Job\n```\n\nAPTH = AP Transaction Header, APTL = AP Transaction Line (detail)"
            }
        ]

        for conv in conventions:
            if max_records and len(records) >= max_records:
                break
            records.append(TrainingRecord(
                instruction=conv["q"],
                input="",
                output=conv["a"],
                category=DatasetCategory.RULE_ENFORCEMENT.value,
                source="naming_conventions",
                quality_score=1.0
            ))

        # Add more from NAMING_CONVENTIONS.md if it exists
        naming_file = self.vgpt2 / "Experts_V2" / "NAMING_CONVENTIONS.md"
        if naming_file.exists():
            try:
                content = naming_file.read_text(encoding='utf-8')
                # Extract table sections
                sections = content.split('##')
                for section in sections[1:]:  # Skip first empty section
                    if max_records and len(records) >= max_records:
                        break
                    lines = section.strip().split('\n')
                    if lines:
                        title = lines[0].strip()
                        body = '\n'.join(lines[1:]).strip()
                        if len(body) > 50:  # Meaningful content
                            records.append(TrainingRecord(
                                instruction=f"What are the Viewpoint Vista conventions for {title}?",
                                input="",
                                output=body[:1500],
                                category=DatasetCategory.RULE_ENFORCEMENT.value,
                                source="NAMING_CONVENTIONS.md",
                                quality_score=1.0
                            ))
            except Exception as e:
                logger.warning(f"Error processing naming conventions: {e}")

        logger.info(f"Generated {len(records)} naming convention examples")
        return records

    def generate_error_correction_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate SQL error correction training examples."""
        records = []

        # Common SQL errors and corrections for Viewpoint
        error_corrections = [
            {
                "wrong": "SELECT * FROM dbo.APTH",
                "right": "SELECT * FROM APTH WITH (NOLOCK)",
                "explanation": "Don't use 'dbo.' prefix for views. Always add WITH (NOLOCK) for read queries."
            },
            {
                "wrong": "SELECT * FROM bAPTH",
                "right": "SELECT * FROM APTH WITH (NOLOCK)",
                "explanation": "Use views (APTH) not base tables (bAPTH) for SELECT queries. Base tables are for INSERT/UPDATE only."
            },
            {
                "wrong": "SELECT apco, vendor, amount FROM APTH",
                "right": "SELECT APCo, Vendor, Amount FROM APTH WITH (NOLOCK)",
                "explanation": "Use exact column name case (APCo not apco). Viewpoint column names are case-sensitive in some contexts."
            },
            {
                "wrong": "WHERE Mth = '2024-01'",
                "right": "WHERE Mth = '2024-01-01'",
                "explanation": "Month (Mth) columns store the first day of month as full datetime. Use '2024-01-01' format."
            },
            {
                "wrong": "FROM APTH a JOIN APTL b ON a.APTrans = b.APTrans",
                "right": "FROM APTH a WITH (NOLOCK) JOIN APTL b WITH (NOLOCK) ON a.APCo = b.APCo AND a.Mth = b.Mth AND a.APTrans = b.APTrans",
                "explanation": "JOIN conditions must include company (APCo) and month (Mth) columns, not just transaction number. Add WITH (NOLOCK)."
            },
            {
                "wrong": "SELECT Job, Contract FROM JCCD WHERE Job LIKE '%100%'",
                "right": "SELECT Job, Contract FROM JCCD WITH (NOLOCK) WHERE JCCo = @JCCo AND Job LIKE '%100%'",
                "explanation": "Always filter by company column (JCCo) to ensure proper data isolation. Add WITH (NOLOCK)."
            },
            {
                "wrong": "SELECT * FROM PRTH WHERE Employee = 123",
                "right": "SELECT * FROM PRTH WITH (NOLOCK) WHERE PRCo = @PRCo AND Employee = 123",
                "explanation": "Filter by PRCo (Payroll Company) to ensure correct company context."
            },
            {
                "wrong": "FROM APTH INNER JOIN HQCO ON APTH.Co = HQCO.HQCo",
                "right": "FROM APTH WITH (NOLOCK) INNER JOIN HQCO WITH (NOLOCK) ON APTH.APCo = HQCO.HQCo",
                "explanation": "Use the correct company column name (APCo, not Co). Each module has its own company column prefix."
            }
        ]

        for ec in error_corrections:
            if max_records and len(records) >= max_records:
                break
            records.append(TrainingRecord(
                instruction="Fix this Viewpoint Vista SQL query:",
                input=ec["wrong"],
                output=f"Corrected SQL:\n```sql\n{ec['right']}\n```\n\nExplanation: {ec['explanation']}",
                category=DatasetCategory.SQL_VALIDATION.value,
                source="error_corrections",
                quality_score=1.0
            ))

        logger.info(f"Generated {len(records)} error correction examples")
        return records

    def generate_query_optimization_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate query optimization training examples."""
        records = []

        optimization_examples = [
            {
                "scenario": "Query running slow when selecting all columns",
                "before": "SELECT * FROM APTH WITH (NOLOCK) WHERE APCo = 1",
                "after": "SELECT APCo, Mth, APTrans, Vendor, InvNum, InvDate, GrossAmt\nFROM APTH WITH (NOLOCK)\nWHERE APCo = 1",
                "tip": "Only select columns you need. SELECT * retrieves all columns which increases I/O and network transfer."
            },
            {
                "scenario": "Filtering on non-indexed column causes table scan",
                "before": "SELECT * FROM APTL WITH (NOLOCK) WHERE Description LIKE '%concrete%'",
                "after": "SELECT * FROM APTL WITH (NOLOCK)\nWHERE APCo = @APCo AND Mth >= @StartMth AND Mth <= @EndMth\n  AND Description LIKE '%concrete%'",
                "tip": "Filter by indexed columns (company, month) first to reduce rows before applying text search."
            },
            {
                "scenario": "Using vrv* views instead of custom JOINs",
                "before": "SELECT h.*, d.*\nFROM APTH h WITH (NOLOCK)\nJOIN APTL d WITH (NOLOCK) ON h.APCo = d.APCo AND h.Mth = d.Mth AND h.APTrans = d.APTrans\nJOIN JCCD j WITH (NOLOCK) ON d.JCCo = j.JCCo AND d.Job = j.Job",
                "after": "SELECT *\nFROM vrvAPJobCost WITH (NOLOCK)\nWHERE APCo = @APCo AND Mth = @Mth",
                "tip": "Check for existing vrv* (Viewpoint Report Views) before writing complex JOINs. They're pre-optimized."
            },
            {
                "scenario": "Date range query not using index",
                "before": "SELECT * FROM GLDT WITH (NOLOCK) WHERE YEAR(ActDate) = 2024",
                "after": "SELECT * FROM GLDT WITH (NOLOCK)\nWHERE ActDate >= '2024-01-01' AND ActDate < '2025-01-01'",
                "tip": "Avoid functions on columns in WHERE clause - they prevent index usage. Use range comparisons instead."
            },
            {
                "scenario": "Subquery can be converted to JOIN",
                "before": "SELECT * FROM APTH WITH (NOLOCK)\nWHERE Vendor IN (SELECT Vendor FROM APVM WITH (NOLOCK) WHERE VendorGroup = 1)",
                "after": "SELECT h.*\nFROM APTH h WITH (NOLOCK)\nJOIN APVM v WITH (NOLOCK) ON h.VendorGroup = v.VendorGroup AND h.Vendor = v.Vendor\nWHERE v.VendorGroup = 1",
                "tip": "JOINs often perform better than IN subqueries, especially with proper indexes."
            }
        ]

        for opt in optimization_examples:
            if max_records and len(records) >= max_records:
                break
            records.append(TrainingRecord(
                instruction=f"Optimize this Viewpoint Vista SQL query. Scenario: {opt['scenario']}",
                input=opt["before"],
                output=f"Optimized SQL:\n```sql\n{opt['after']}\n```\n\nOptimization tip: {opt['tip']}",
                category=DatasetCategory.SQL_VALIDATION.value,
                source="query_optimization",
                quality_score=1.0
            ))

        logger.info(f"Generated {len(records)} query optimization examples")
        return records

    # =========================================================================
    # NEW GENERATORS (Previously Missing - Added 2024-12-28)
    # =========================================================================

    def generate_crystal_report_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate training examples from Crystal Report SQL files."""
        records = []
        crystal_dir = self.vgpt2 / "Crystal_Reports_Documentation" / "_Extracted_SQL" / "Reformatted"

        if not crystal_dir.exists():
            logger.warning(f"Crystal Reports SQL directory not found: {crystal_dir}")
            return records

        for sql_file in crystal_dir.glob("*.sql"):
            if max_records and len(records) >= max_records:
                break

            try:
                content = sql_file.read_text(encoding='utf-8')
                report_name = sql_file.stem

                # Skip empty or very short files
                if len(content.strip()) < 50:
                    continue

                # Extract tables used in the query
                tables_used = self._extract_tables_from_sql(content)

                # Determine report purpose from filename
                purpose = self._infer_report_purpose(report_name)

                # Create training record
                records.append(TrainingRecord(
                    instruction=f"Write a SQL query for a Crystal Report that {purpose}",
                    input=f"Report: {report_name}\nTables involved: {', '.join(tables_used[:5]) if tables_used else 'Unknown'}",
                    output=content.strip(),
                    category=DatasetCategory.SQL_GENERATION.value,
                    source="Crystal Report SQL",
                    quality_score=0.95  # Production SQL is high quality
                ))

                # Also create a "what view to use" example if brv/vrv views are present
                reporting_views = [t for t in tables_used if t.startswith('brv') or t.startswith('vrv')]
                if reporting_views:
                    records.append(TrainingRecord(
                        instruction=f"What reporting view should I use for {purpose}?",
                        input="",
                        output=f"For {purpose}, use the `{reporting_views[0]}` view. This is a Viewpoint reporting view optimized for this purpose.\n\nExample:\n```sql\nSELECT *\nFROM {reporting_views[0]} WITH (NOLOCK)\nWHERE {self._get_typical_filter(reporting_views[0])}\n```",
                        category=DatasetCategory.BUSINESS_CONTEXT.value,
                        source="Crystal Report SQL",
                        quality_score=1.0
                    ))

            except Exception as e:
                logger.warning(f"Error processing Crystal Report SQL {sql_file}: {e}")

        logger.info(f"Generated {len(records)} Crystal Report SQL examples")
        return records

    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table/view names from SQL query."""
        import re
        # Match FROM/JOIN followed by table name
        pattern = r'(?:FROM|JOIN)\s+(\w+)'
        matches = re.findall(pattern, sql, re.IGNORECASE)
        # Filter to likely Viewpoint tables (2-4 letter prefix)
        vp_tables = [m for m in matches if len(m) >= 3 and m.upper() not in ('SELECT', 'WHERE', 'AND', 'WITH')]
        return list(dict.fromkeys(vp_tables))  # Remove duplicates, preserve order

    def _infer_report_purpose(self, report_name: str) -> str:
        """Infer report purpose from filename."""
        # Common prefixes and their meanings
        prefixes = {
            'AP': 'Accounts Payable', 'AR': 'Accounts Receivable', 'GL': 'General Ledger',
            'JC': 'Job Cost', 'PR': 'Payroll', 'PM': 'Project Management',
            'EM': 'Equipment', 'IN': 'Inventory', 'SM': 'Service Management',
            'HR': 'Human Resources', 'PO': 'Purchase Order', 'SL': 'Subcontract',
            'MS': 'Material Sales', 'VA': 'Viewpoint Attachment'
        }

        for prefix, module in prefixes.items():
            if report_name.upper().startswith(prefix):
                # Clean up the rest of the name
                rest = report_name[len(prefix):].replace('_', ' ').strip()
                return f"generates {module} report data for {rest}" if rest else f"generates {module} report data"

        return f"generates report data for {report_name.replace('_', ' ')}"

    def _get_typical_filter(self, table_name: str) -> str:
        """Get typical WHERE clause filter for a table."""
        if table_name.startswith('brvJC') or table_name.startswith('vrvJC'):
            return "JCCo = @JCCo AND Job = @Job"
        elif table_name.startswith('brvAP') or table_name.startswith('vrvAP'):
            return "APCo = @APCo AND Mth = @Mth"
        elif table_name.startswith('brvGL') or table_name.startswith('vrvGL'):
            return "GLCo = @GLCo AND Mth = @Mth"
        elif table_name.startswith('brvPR') or table_name.startswith('vrvPR'):
            return "PRCo = @PRCo"
        else:
            return "1=1  -- Add appropriate filters"

    def generate_canonical_rules_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate training examples from canonical SQL rules."""
        records = []
        rules_dir = self.ai_orchestration_dir / "rules"

        if not rules_dir.exists():
            logger.warning(f"Rules directory not found: {rules_dir}")
            return records

        for md_file in rules_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')

                # Extract rules with examples
                rules = self._parse_rule_document(content)

                for rule in rules:
                    if max_records and len(records) >= max_records:
                        break

                    # Q&A about the rule
                    records.append(TrainingRecord(
                        instruction=rule.get('question', f"What is the rule for {rule.get('topic', 'SQL')}?"),
                        input="",
                        output=rule.get('answer', rule.get('explanation', '')),
                        category=DatasetCategory.RULE_ENFORCEMENT.value,
                        source="Canonical Rules",
                        quality_score=1.0
                    ))

                    # If there's wrong/right SQL, create correction example
                    if rule.get('wrong_sql') and rule.get('right_sql'):
                        records.append(TrainingRecord(
                            instruction="Fix this Viewpoint SQL query:",
                            input=rule['wrong_sql'],
                            output=f"Corrected SQL:\n```sql\n{rule['right_sql']}\n```\n\nExplanation: {rule.get('explanation', 'See Viewpoint SQL standards.')}",
                            category=DatasetCategory.SQL_VALIDATION.value,
                            source="Canonical Rules",
                            quality_score=1.0
                        ))

            except Exception as e:
                logger.warning(f"Error processing rules file {md_file}: {e}")

        logger.info(f"Generated {len(records)} canonical rules examples")
        return records

    def _parse_rule_document(self, content: str) -> List[Dict]:
        """Parse a rule markdown document into structured rules."""
        rules = []

        # Hardcoded key rules from RULE_CanonicalSQL.md
        key_rules = [
            {
                'topic': 'Case Sensitivity',
                'question': 'Why is case sensitivity important in Viewpoint SQL?',
                'answer': 'Viewpoint uses Latin1_General_BIN collation which is case-sensitive. Column and table names must match exactly as defined in the schema. Use `Job` not `job` or `JOB`. Check exact case in columns.json.',
                'wrong_sql': "SELECT jobnumber FROM jcjm WHERE jobnumber = '12345';",
                'right_sql': "SELECT Job FROM JCJM WITH (NOLOCK) WHERE Job = '12345';",
                'explanation': 'Column is `Job` not `jobnumber`, and table `JCJM` must be exact case.'
            },
            {
                'topic': 'No Table Aliases',
                'question': 'Should I use table aliases in Viewpoint SQL?',
                'answer': 'No. Viewpoint standards prohibit table aliases. Always use full table names. This makes queries easier to validate and prevents case sensitivity issues from being hidden.',
                'wrong_sql': "SELECT jc.JobNumber, jc.Description FROM JCJM jc WHERE jc.JCCo = 1;",
                'right_sql': "SELECT JCJM.Job, JCJM.Description FROM JCJM WITH (NOLOCK) WHERE JCJM.JCCo = 1;",
                'explanation': 'Removed alias `jc`, used full table name `JCJM`, and corrected column name to `Job`.'
            },
            {
                'topic': 'Views Over Base Tables',
                'question': 'Should I query views or base tables in Viewpoint?',
                'answer': 'Always use views (e.g., JCJM) for SELECT queries, not base tables (e.g., bJCJM). Views enforce Viewpoint\'s Data Type Security and Row-Level Security. Only use base tables for INSERT/UPDATE/DELETE operations.',
                'wrong_sql': "SELECT * FROM bJCJM WHERE JCCo = 1;",
                'right_sql': "SELECT * FROM JCJM WITH (NOLOCK) WHERE JCCo = 1;",
                'explanation': 'Use view `JCJM` not base table `bJCJM` for SELECT queries.'
            },
            {
                'topic': 'WITH NOLOCK',
                'question': 'When should I use WITH (NOLOCK) in Viewpoint queries?',
                'answer': 'Always include WITH (NOLOCK) after every table/view name in SELECT queries. This prevents blocking production transactions. Only omit NOLOCK when you specifically need transactional consistency.',
                'wrong_sql': "SELECT * FROM APTH WHERE APCo = 1;",
                'right_sql': "SELECT * FROM APTH WITH (NOLOCK) WHERE APCo = 1;",
                'explanation': 'Added WITH (NOLOCK) to prevent blocking.'
            },
            {
                'topic': 'Company Filtering',
                'question': 'Why must I filter by company in Viewpoint queries?',
                'answer': 'Most Viewpoint tables contain data for multiple companies. Always filter by the appropriate company column (APCo, JCCo, PRCo, GLCo, etc.) to ensure data isolation. This is both a security requirement and performance optimization.',
                'wrong_sql': "SELECT * FROM APTH WITH (NOLOCK);",
                'right_sql': "SELECT * FROM APTH WITH (NOLOCK) WHERE APCo = @APCo;",
                'explanation': 'Added company filter to ensure data isolation.'
            },
            {
                'topic': 'Reporting Views',
                'question': 'What are vrv* and brv* views in Viewpoint?',
                'answer': 'vrv* (Viewpoint Report Views) and brv* (Batch Report Views) are pre-built views optimized for reporting. Always check if one exists before writing custom JOINs. Examples: brvJCCostRevenue for job cost/revenue, vrvAPAgingDetail for AP aging.',
            },
            {
                'topic': 'Groups vs Companies',
                'question': 'How do Groups work in Viewpoint master tables?',
                'answer': 'Master tables like APVM (vendors), ARCM (customers) use Groups instead of companies. Multiple companies can share the same VendorGroup or CustGroup. Join through the transaction table or look up the Group from HQCO.',
                'wrong_sql': "SELECT * FROM APVM WHERE APCo = 1 AND Vendor = 12345;",
                'right_sql': "SELECT APVM.* FROM APTH WITH (NOLOCK) INNER JOIN APVM WITH (NOLOCK) ON APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor WHERE APTH.APCo = 1;",
                'explanation': 'APVM has no APCo column. Join through APTH which has VendorGroup.'
            },
        ]

        rules.extend(key_rules)
        return rules

    def generate_reference_doc_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate training examples from reference documents."""
        records = []
        ref_dir = self.ai_orchestration_dir / "reference"

        if not ref_dir.exists():
            logger.warning(f"Reference directory not found: {ref_dir}")
            return records

        # Process each reference document
        for md_file in ref_dir.glob("*.md"):
            if max_records and len(records) >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                doc_name = md_file.stem

                # Generate Q&A pairs based on document content
                qa_pairs = self._generate_reference_qa(doc_name, content)

                for qa in qa_pairs:
                    if max_records and len(records) >= max_records:
                        break
                    records.append(TrainingRecord(
                        instruction=qa['question'],
                        input="",
                        output=qa['answer'],
                        category=DatasetCategory.BUSINESS_CONTEXT.value,
                        source="Reference Documents",
                        quality_score=0.95
                    ))

            except Exception as e:
                logger.warning(f"Error processing reference doc {md_file}: {e}")

        logger.info(f"Generated {len(records)} reference document examples")
        return records

    def _generate_reference_qa(self, doc_name: str, content: str) -> List[Dict]:
        """Generate Q&A pairs from a reference document."""
        qa_pairs = []

        # Topic-specific Q&A generation
        if 'Groups' in doc_name:
            qa_pairs.extend([
                {'question': 'What is VendorGroup in Viewpoint?',
                 'answer': 'VendorGroup is how Viewpoint shares vendor master data across companies. Multiple companies can share the same VendorGroup, meaning they see the same vendors. The APVM (vendor master) table uses VendorGroup + Vendor as its key, not company. To find vendors, join through transaction tables or look up VendorGroup from HQCO.'},
                {'question': 'What is CustGroup in Viewpoint?',
                 'answer': 'CustGroup allows multiple companies to share customer master data. The ARCM (customer master) table uses CustGroup + Customer as its key. Similar to VendorGroup, you join through transaction tables like ARTH to access customer data in company context.'},
                {'question': 'How do I join to vendor master (APVM) from AP transactions?',
                 'answer': 'Join through the VendorGroup column that exists on AP transaction tables:\n```sql\nSELECT APVM.Name, APTH.*\nFROM APTH WITH (NOLOCK)\nINNER JOIN APVM WITH (NOLOCK)\n    ON APTH.VendorGroup = APVM.VendorGroup\n    AND APTH.Vendor = APVM.Vendor\nWHERE APTH.APCo = @APCo\n```'},
            ])
        elif 'Batch' in doc_name:
            qa_pairs.extend([
                {'question': 'How does batch processing work in Viewpoint AP?',
                 'answer': 'AP uses batch tables to stage transactions before posting. Transactions go into batch tables (bAPTB header, bAPTD detail) where they can be validated and approved. When posted, they move to production tables (APTH, APTL). The BatchId links header to detail records.'},
                {'question': 'What tables are used for AP batch entry?',
                 'answer': 'AP batch entry uses: bAPTB (batch header), bAPTD (batch detail/lines), bAPDS (batch distributions). After posting, data moves to APTH (transaction header) and APTL (transaction lines).'},
            ])
        elif 'Month' in doc_name:
            qa_pairs.extend([
                {'question': 'How are months stored in Viewpoint?',
                 'answer': 'Viewpoint stores months as datetime values representing the first day of the month. The column is typically named `Mth`. For example, January 2024 is stored as `2024-01-01 00:00:00`. Always compare Mth columns using date literals like `WHERE Mth = \'2024-01-01\'`.'},
                {'question': 'How do I filter by month range in Viewpoint?',
                 'answer': 'Use date comparisons on the Mth column:\n```sql\nSELECT *\nFROM APTH WITH (NOLOCK)\nWHERE APCo = @APCo\n  AND Mth >= \'2024-01-01\'\n  AND Mth <= \'2024-12-01\'\n```\nNote: Use first-of-month dates for Mth comparisons.'},
            ])
        elif 'KeyID' in doc_name:
            qa_pairs.extend([
                {'question': 'What is KeyID in Viewpoint?',
                 'answer': 'KeyID is an auto-incrementing unique identifier used in many Viewpoint tables. It provides a single-column key for tables that have composite natural keys. KeyID is useful for attachments, notes, and cross-references where you need a simple FK relationship.'},
                {'question': 'When should I use KeyID vs composite keys?',
                 'answer': 'Use composite keys (like APCo + Mth + APTrans) for joining transactional tables - these are the natural business keys. Use KeyID when linking to attachment tables (HQAT), notes, or custom tables that need a simple single-column reference.'},
            ])
        elif 'Company' in doc_name:
            qa_pairs.extend([
                {'question': 'What company columns are used in Viewpoint?',
                 'answer': 'Each module has its own company column: APCo (Accounts Payable), ARCo (Accounts Receivable), GLCo (General Ledger), JCCo (Job Cost), PRCo (Payroll), EMCo (Equipment), INCo (Inventory), SMCo (Service Management). Always filter by the appropriate company column.'},
                {'question': 'Can a company have different numbers across modules?',
                 'answer': 'Yes. Company 1 in AP (APCo=1) might be Company 5 in Job Cost (JCCo=5). The HQCO table shows which company numbers are used for each module. Always use the correct module-specific company column when joining across modules.'},
            ])
        elif 'SoftDelete' in doc_name:
            qa_pairs.extend([
                {'question': 'How does Viewpoint handle deleted records?',
                 'answer': 'Many Viewpoint tables use soft deletes with an ActiveYN or Status column. Records are marked inactive rather than physically deleted. Always check for ActiveYN = \'Y\' or appropriate Status values when querying to exclude "deleted" records.'},
            ])
        elif 'Status' in doc_name:
            qa_pairs.extend([
                {'question': 'What do status codes mean in Viewpoint AP?',
                 'answer': 'AP transaction status codes: 0=Open, 1=Fully Paid, 2=Cleared, 3=Voided. Filter by Status in APTH to find unpaid invoices (Status=0) or paid invoices (Status IN (1,2)).'},
            ])
        else:
            # Generic extraction - use document title
            clean_name = doc_name.replace('Viewpoint', '').replace('_', ' ').strip()
            qa_pairs.append({
                'question': f'How does {clean_name} work in Viewpoint?',
                'answer': content[:1500] if len(content) > 1500 else content
            })

        return qa_pairs

    def generate_heuristic_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate training examples from heuristics documents."""
        records = []
        heuristics_dir = self.ai_orchestration_dir / "heuristics"

        if not heuristics_dir.exists():
            logger.warning(f"Heuristics directory not found: {heuristics_dir}")
            return records

        for md_file in heuristics_dir.glob("*.md"):
            if max_records and len(records) >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                heuristic_name = md_file.stem

                # Generate Q&A based on heuristic type
                qa_pairs = self._generate_heuristic_qa(heuristic_name, content)

                for qa in qa_pairs:
                    if max_records and len(records) >= max_records:
                        break
                    records.append(TrainingRecord(
                        instruction=qa['question'],
                        input=qa.get('input', ''),
                        output=qa['answer'],
                        category=DatasetCategory.BUSINESS_CONTEXT.value,
                        source="Heuristics",
                        quality_score=0.9
                    ))

            except Exception as e:
                logger.warning(f"Error processing heuristic {md_file}: {e}")

        logger.info(f"Generated {len(records)} heuristic examples")
        return records

    def _generate_heuristic_qa(self, name: str, content: str) -> List[Dict]:
        """Generate Q&A pairs from a heuristic document."""
        qa_pairs = []

        if 'CompositeKey' in name:
            qa_pairs.extend([
                {'question': 'How do I find the correct JOIN columns between two Viewpoint tables?',
                 'answer': '1. Check foreign_keys.json for documented relationships\n2. Look at _Relationship_Validation/03_Join_Recipes/ for validated patterns\n3. Match composite keys - most Viewpoint JOINs use multiple columns (e.g., APCo + Mth + APTrans)\n4. Company columns must match module-to-module (JCCo to JCCo, not APCo to JCCo)'},
                {'question': 'Why do Viewpoint JOINs use multiple columns?',
                 'answer': 'Viewpoint uses composite keys for business meaning. APTH (AP Transaction Header) key is APCo + Mth + APTrans. This ensures data isolation by company, allows efficient date partitioning by month, and provides meaningful transaction numbering. Always include all key columns in JOINs.'},
            ])
        elif 'CSVToSQL' in name:
            qa_pairs.extend([
                {'question': 'How do I write a Viewpoint SQL query from a business question?',
                 'answer': '1. Identify the business domain (AP, AR, JC, GL, etc.)\n2. Find the primary table for that domain\n3. Add WITH (NOLOCK) to all tables\n4. Include company filter in WHERE clause\n5. Check for vrv*/brv* reporting views before writing complex JOINs\n6. Validate column names against columns.json'},
            ])
        elif 'SQLObjectVerification' in name:
            qa_pairs.extend([
                {'question': 'How do I verify a Viewpoint table or column exists?',
                 'answer': 'Check these sources:\n1. columns.json - complete column inventory\n2. _Viewpoint_ALL_Views_Tables_Complete.json - all tables/views\n3. The view/table must exist (case-sensitive!)\n4. Column must be exact case match\n\nExample verification:\n```python\ncolumns = json.load(open("columns.json"))\nvalid = any(c["COLUMN_NAME"] == "Job" and c["TABLE_NAME"] == "JCJM" for c in columns)\n```'},
            ])

        return qa_pairs

    def generate_workflow_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate training examples from workflow documents."""
        records = []
        workflows_dir = self.ai_orchestration_dir / "workflows"

        if not workflows_dir.exists():
            logger.warning(f"Workflows directory not found: {workflows_dir}")
            return records

        for md_file in workflows_dir.glob("*.md"):
            if max_records and len(records) >= max_records:
                break

            try:
                content = md_file.read_text(encoding='utf-8')
                workflow_name = md_file.stem

                # Generate Q&A based on workflow type
                qa_pairs = self._generate_workflow_qa(workflow_name, content)

                for qa in qa_pairs:
                    if max_records and len(records) >= max_records:
                        break
                    records.append(TrainingRecord(
                        instruction=qa['question'],
                        input=qa.get('input', ''),
                        output=qa['answer'],
                        category=DatasetCategory.BUSINESS_CONTEXT.value,
                        source="Workflows",
                        quality_score=0.9
                    ))

            except Exception as e:
                logger.warning(f"Error processing workflow {md_file}: {e}")

        logger.info(f"Generated {len(records)} workflow examples")
        return records

    def _generate_workflow_qa(self, name: str, content: str) -> List[Dict]:
        """Generate Q&A pairs from a workflow document."""
        qa_pairs = []

        if 'SQLGeneration' in name:
            qa_pairs.extend([
                {'question': 'What is the process for generating Viewpoint SQL?',
                 'answer': '''1. Understand the business question
2. Identify target module (AP, AR, JC, GL, etc.)
3. Check for existing vrv*/brv* reporting views
4. If no reporting view, identify primary tables
5. Use columns.json to verify column names (case-sensitive!)
6. Add WITH (NOLOCK) to all tables
7. Add company filter (APCo, JCCo, etc.)
8. Validate JOIN patterns against foreign_keys.json
9. Test with small result set first'''},
                {'question': 'What should I check before writing custom JOINs in Viewpoint?',
                 'answer': 'Before writing custom JOINs:\n1. Search Crystal_Reports_Documentation/_Extracted_SQL/ for similar reports\n2. Check vrv* and brv* views that might already combine the tables\n3. Review _Relationship_Validation/03_Join_Recipes/ for validated patterns\n4. Verify all column names in columns.json (case matters!)'},
            ])
        elif 'QuestionAnswering' in name:
            qa_pairs.extend([
                {'question': 'How should I answer questions about Viewpoint data?',
                 'answer': '1. Clarify which module the question relates to\n2. Identify if they need raw data or aggregated results\n3. Check if a reporting view exists for the purpose\n4. Provide SQL with proper conventions (NOLOCK, company filter, exact case)\n5. Explain what the query returns and any assumptions made'},
            ])
        elif 'CrystalReport' in name:
            qa_pairs.extend([
                {'question': 'How do I find Crystal Report SQL for a similar report?',
                 'answer': 'Search in Crystal_Reports_Documentation/_Extracted_SQL/:\n1. Reformatted/ has cleaned SQL\n2. Raw/ has original extracts\n3. Search by report prefix (AP, JC, etc.)\n4. Look for brv*/vrv* views used in reports'},
            ])

        return qa_pairs

    def generate_experts_v2_examples(self, max_records: Optional[int] = None) -> List[TrainingRecord]:
        """Generate training examples from Experts_V2 validated SQL."""
        records = []

        if not self.experts_dir.exists():
            logger.warning(f"Experts_V2 directory not found: {self.experts_dir}")
            return records

        # Search for SQL files in all subdirectories
        for sql_file in self.experts_dir.rglob("*.sql"):
            if max_records and len(records) >= max_records:
                break

            # Skip validation scripts
            if sql_file.name.startswith("00_validate"):
                continue

            try:
                content = sql_file.read_text(encoding='utf-8')

                # Skip very short or empty files
                if len(content.strip()) < 50:
                    continue

                # Extract expert name from path
                expert_name = None
                for part in sql_file.parts:
                    if part.startswith("Expert_"):
                        expert_name = part.replace("Expert_", "").replace("_", " ")
                        break

                # Extract purpose from filename or comments
                purpose = sql_file.stem.replace("_", " ")

                # Look for purpose in comments
                lines = content.split('\n')
                for line in lines[:20]:
                    if 'Purpose:' in line:
                        purpose = line.split('Purpose:')[1].strip()
                        break
                    elif line.strip().startswith('--') and len(line.strip()) > 5:
                        purpose = line.strip().lstrip('-').strip()
                        break

                # Create training record
                instruction = f"Write a SQL query for {expert_name}: {purpose}" if expert_name else f"Write a Viewpoint SQL query to: {purpose}"

                records.append(TrainingRecord(
                    instruction=instruction,
                    input="Viewpoint Vista database",
                    output=content.strip(),
                    category=DatasetCategory.SQL_GENERATION.value,
                    source="Experts V2",
                    quality_score=0.95
                ))

            except Exception as e:
                logger.warning(f"Error processing Expert SQL {sql_file}: {e}")

        logger.info(f"Generated {len(records)} Experts V2 examples")
        return records

    def _extract_section(self, content: str, start_marker: str, end_marker: str) -> Optional[str]:
        """Extract a section from markdown content."""
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return None

        start_idx += len(start_marker)
        end_idx = content.find(end_marker, start_idx)

        if end_idx == -1:
            return content[start_idx:].strip()

        return content[start_idx:end_idx].strip()

    # =========================================================================
    # OUTPUT METHODS
    # =========================================================================

    def save_dataset(self, records: List[TrainingRecord], output_path: str, format: str = "alpaca"):
        """Save training records to file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if format == "alpaca":
            # Alpaca format for LLaMA Factory
            data = [r.to_alpaca() for r in records]
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif format == "full":
            # Full format with metadata
            data = [asdict(r) for r in records]
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unknown format: {format}")

        logger.info(f"Saved {len(records)} records to {output_file}")

    def print_inventory_report(self, inventory: List[DataSourceInventory]):
        """Print a formatted inventory report."""
        print("\n" + "=" * 80)
        print("VGPT2 DATA SOURCE INVENTORY")
        print("=" * 80)

        total_files = 0
        total_size = 0.0
        total_records = 0

        for tier in [1, 2, 3]:
            tier_sources = [s for s in inventory if s.quality_tier == tier]
            if not tier_sources:
                continue

            print(f"\n{'─' * 40}")
            print(f"TIER {tier} SOURCES")
            print(f"{'─' * 40}")

            for source in tier_sources:
                print(f"\n  {source.source_name}")
                print(f"    Path: {source.path}")
                print(f"    Files: {source.file_count:,}")
                print(f"    Size: {source.total_size_mb:.2f} MB")
                print(f"    Est. Records: {source.estimated_records:,}")
                print(f"    Notes: {source.notes}")

                total_files += source.file_count
                total_size += source.total_size_mb
                total_records += source.estimated_records

        print(f"\n{'=' * 80}")
        print(f"TOTALS: {total_files:,} files, {total_size:.2f} MB, ~{total_records:,} potential records")
        print("=" * 80)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate VGPT2 training data for LLM fine-tuning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Inventory all data sources
  python generate_vgpt2_training_data.py --inventory

  # Generate training data (default paths)
  python generate_vgpt2_training_data.py --generate

  # Generate with custom paths
  python generate_vgpt2_training_data.py --generate --vgpt2 C:/Github/VGPT2 --output data/training.json

  # Generate limited sample
  python generate_vgpt2_training_data.py --generate --max-per-source 100
        """
    )

    parser.add_argument('--inventory', action='store_true',
                        help='Print inventory of all data sources')
    parser.add_argument('--generate', action='store_true',
                        help='Generate training dataset')
    parser.add_argument('--vgpt2', type=str, default='C:/Github/VGPT2',
                        help='Path to VGPT2 repository')
    parser.add_argument('--vista-kb', type=str, default='C:/Github/Vista_KB',
                        help='Path to Vista_KB repository (optional)')
    parser.add_argument('--output', type=str, default='data/vgpt2_training.json',
                        help='Output file path')
    parser.add_argument('--format', type=str, choices=['alpaca', 'full'], default='alpaca',
                        help='Output format (alpaca for LLaMA Factory, full with metadata)')
    parser.add_argument('--max-per-source', type=int, default=None,
                        help='Maximum records per source (for testing)')

    args = parser.parse_args()

    # Validate at least one action
    if not args.inventory and not args.generate:
        parser.print_help()
        print("\nError: Specify --inventory or --generate")
        return 1

    try:
        # Initialize generator
        vista_kb = args.vista_kb if Path(args.vista_kb).exists() else None
        generator = VGPT2DatasetGenerator(
            vgpt2_path=args.vgpt2,
            vista_kb_path=vista_kb
        )

        # Run inventory
        if args.inventory:
            inventory = generator.inventory_sources()
            generator.print_inventory_report(inventory)

        # Generate dataset
        if args.generate:
            records = generator.generate_all(max_per_source=args.max_per_source)
            generator.save_dataset(records, args.output, format=args.format)
            print(f"\nGenerated {len(records)} training records to {args.output}")

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

