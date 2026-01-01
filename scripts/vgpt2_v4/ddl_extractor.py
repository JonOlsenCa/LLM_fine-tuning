# Copyright 2024-2025 Viewpoint, Inc.
# Licensed under the Apache License, Version 2.0.

"""
DDL Extractor Module

Extracts CREATE TABLE statements from VGPT2 metadata for use in
schema-in-prompt training examples.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Information about a single column."""
    name: str
    data_type: str
    is_nullable: bool
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    description: str = ""


@dataclass
class TableInfo:
    """Information about a table including its DDL."""
    name: str
    schema: str = "dbo"
    module: str = ""
    description: str = ""
    columns: List[ColumnInfo] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[Dict] = field(default_factory=list)
    
    def to_ddl(self, include_description: bool = True, max_columns: int = 20) -> str:
        """
        Generate CREATE TABLE DDL statement.
        
        Args:
            include_description: Add table description as comment
            max_columns: Limit columns to avoid overly long DDL
        """
        lines = []
        
        if include_description and self.description:
            lines.append(f"-- {self.description}")
        
        lines.append(f"CREATE TABLE {self.name} (")
        
        # Add columns
        col_lines = []
        columns_to_show = self.columns[:max_columns]
        
        for col in columns_to_show:
            col_def = f"  {col.name} {self._format_data_type(col)}"
            if not col.is_nullable:
                col_def += " NOT NULL"
            col_lines.append(col_def)
        
        # Add truncation note if needed
        if len(self.columns) > max_columns:
            col_lines.append(f"  -- ... {len(self.columns) - max_columns} more columns")
        
        # Add primary key constraint
        if self.primary_keys:
            pk_cols = ", ".join(self.primary_keys)
            col_lines.append(f"  PRIMARY KEY ({pk_cols})")
        
        lines.append(",\n".join(col_lines))
        lines.append(");")
        
        return "\n".join(lines)
    
    def _format_data_type(self, col: ColumnInfo) -> str:
        """Format column data type with precision/length."""
        dt = col.data_type.lower()
        
        # Types with max_length
        if dt in ("varchar", "nvarchar", "char", "nchar", "varbinary", "binary"):
            if col.max_length:
                if col.max_length == -1:
                    return f"{dt}(max)"
                return f"{dt}({col.max_length})"
            return dt
        
        # Types with precision and scale
        if dt in ("decimal", "numeric"):
            if col.precision and col.scale is not None:
                return f"{dt}({col.precision},{col.scale})"
            elif col.precision:
                return f"{dt}({col.precision})"
            return dt
        
        # Other types as-is
        return dt


class DDLExtractor:
    """
    Extract DDL from VGPT2 metadata files.
    
    Uses columns.json, foreign_keys.json, and indexes.json from
    the _Metadata directory to build CREATE TABLE statements.
    """
    
    def __init__(self, vgpt2_path: str):
        self.vgpt2_path = Path(vgpt2_path)
        self.metadata_dir = self.vgpt2_path / "Viewpoint_Database" / "_Metadata"
        
        # Caches
        self._tables: Dict[str, TableInfo] = {}
        self._columns_loaded = False
        self._fk_loaded = False
        
        logger.info(f"DDLExtractor initialized with path: {vgpt2_path}")
    
    def load_all(self) -> None:
        """Load all metadata files."""
        self._load_columns()
        self._load_foreign_keys()
        self._infer_primary_keys()
        logger.info(f"Loaded {len(self._tables)} tables")
    
    def get_table(self, table_name: str) -> Optional[TableInfo]:
        """Get table info by name."""
        if not self._columns_loaded:
            self._load_columns()
        return self._tables.get(table_name.upper()) or self._tables.get(table_name)
    
    def get_tables(self, table_names: List[str]) -> List[TableInfo]:
        """Get multiple tables by name."""
        return [t for name in table_names if (t := self.get_table(name))]
    
    def get_ddl(self, table_names: List[str], include_descriptions: bool = True) -> str:
        """
        Generate combined DDL for multiple tables.
        
        Args:
            table_names: List of table names to include
            include_descriptions: Add table descriptions as comments
            
        Returns:
            Combined CREATE TABLE statements
        """
        tables = self.get_tables(table_names)
        ddl_parts = []
        
        for table in tables:
            ddl_parts.append(table.to_ddl(include_description=include_descriptions))
        
        return "\n\n".join(ddl_parts)
    
    def get_all_table_names(self) -> List[str]:
        """Get list of all available table names."""
        if not self._columns_loaded:
            self._load_columns()
        return sorted(self._tables.keys())
    
    def get_tables_by_module(self, module: str) -> List[str]:
        """Get tables belonging to a specific module."""
        if not self._columns_loaded:
            self._load_columns()
        return [
            name for name, table in self._tables.items()
            if table.module.upper() == module.upper()
        ]
    
    def _load_columns(self) -> None:
        """Load columns.json and build table structures."""
        columns_file = self.metadata_dir / "columns.json"
        
        if not columns_file.exists():
            logger.warning(f"columns.json not found at {columns_file}")
            return
        
        logger.info(f"Loading columns from {columns_file}")
        
        with open(columns_file, "r", encoding="utf-8") as f:
            columns_data = json.load(f)
        
        # Group columns by table
        for col_data in columns_data:
            table_name = col_data.get("TABLE_NAME", "")
            if not table_name:
                continue
            
            # Create table if not exists
            if table_name not in self._tables:
                self._tables[table_name] = TableInfo(
                    name=table_name,
                    schema=col_data.get("TABLE_SCHEMA", "dbo"),
                    module=self._infer_module(table_name)
                )
            
            # Add column
            col = ColumnInfo(
                name=col_data.get("COLUMN_NAME", ""),
                data_type=col_data.get("DATA_TYPE", ""),
                is_nullable=col_data.get("IS_NULLABLE", "YES") == "YES",
                max_length=col_data.get("CHARACTER_MAXIMUM_LENGTH"),
                precision=col_data.get("NUMERIC_PRECISION"),
                scale=col_data.get("NUMERIC_SCALE"),
            )
            self._tables[table_name].columns.append(col)
        
        self._columns_loaded = True
        logger.info(f"Loaded columns for {len(self._tables)} tables")
    
    def _load_foreign_keys(self) -> None:
        """Load foreign_keys.json."""
        fk_file = self.metadata_dir / "foreign_keys.json"
        
        if not fk_file.exists():
            logger.warning(f"foreign_keys.json not found at {fk_file}")
            return
        
        logger.info(f"Loading foreign keys from {fk_file}")
        
        with open(fk_file, "r", encoding="utf-8") as f:
            fk_data = json.load(f)
        
        for fk in fk_data:
            parent_table = fk.get("ParentTable", "")
            if parent_table in self._tables:
                self._tables[parent_table].foreign_keys.append(fk)
        
        self._fk_loaded = True
    
    def _infer_primary_keys(self) -> None:
        """
        Infer primary keys from Vista naming conventions.
        
        Vista tables typically have PK columns following patterns:
        - {Module}Co (e.g., APCo, ARCo, JCCo)
        - Mth (for transactional tables)
        - {Table}Trans or KeyID
        """
        for table_name, table in self._tables.items():
            pk_candidates = []
            col_names = {c.name.upper(): c.name for c in table.columns}
            
            # Check for common PK patterns
            module = table.module.upper() if table.module else ""
            
            # Company columns
            co_patterns = [f"{module}Co", "Co", "HQCo", "GLCo"]
            for pattern in co_patterns:
                if pattern.upper() in col_names:
                    pk_candidates.append(col_names[pattern.upper()])
                    break
            
            # Month column (transactional tables)
            if "MTH" in col_names:
                pk_candidates.append(col_names["MTH"])
            
            # Transaction ID patterns
            trans_patterns = [
                f"{table_name}Trans",
                f"{module}Trans",
                "Trans",
                "KeyID",
                f"{table_name}Id",
            ]
            for pattern in trans_patterns:
                if pattern.upper() in col_names:
                    pk_candidates.append(col_names[pattern.upper()])
                    break
            
            # Line number for detail tables
            if table_name.endswith("L") or "Line" in table_name:
                line_patterns = [f"{module}Line", "Line", "APLine", "ARLine", "SLItem"]
                for pattern in line_patterns:
                    if pattern.upper() in col_names:
                        pk_candidates.append(col_names[pattern.upper()])
                        break
            
            table.primary_keys = pk_candidates
    
    def _infer_module(self, table_name: str) -> str:
        """Infer module from table name prefix."""
        # Common module prefixes
        prefixes = {
            "AP": "AP",  # Accounts Payable
            "AR": "AR",  # Accounts Receivable
            "JC": "JC",  # Job Cost
            "SL": "SL",  # Subcontracts
            "PR": "PR",  # Payroll
            "GL": "GL",  # General Ledger
            "HQ": "HQ",  # Headquarters/Common
            "PM": "PM",  # Project Management
            "SM": "SM",  # Service Management
            "EM": "EM",  # Equipment Management
            "IN": "IN",  # Inventory
            "PO": "PO",  # Purchase Orders
            "MS": "MS",  # Material Sales
            "DD": "DD",  # Data Dictionary
            "RP": "RP",  # Reports
        }
        
        # Check first 2 characters
        if len(table_name) >= 2:
            prefix = table_name[:2].upper()
            if prefix in prefixes:
                return prefixes[prefix]
        
        return ""


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_ddl_for_question(
    extractor: DDLExtractor,
    primary_tables: List[str],
    include_related: bool = True,
    max_tables: int = 6
) -> str:
    """
    Create DDL context for a training question.
    
    Args:
        extractor: DDLExtractor instance
        primary_tables: Main tables needed for the query
        include_related: Include commonly joined tables
        max_tables: Maximum number of tables in DDL
        
    Returns:
        Combined DDL string
    """
    tables_to_include = set(primary_tables)
    
    if include_related:
        for table_name in primary_tables:
            table = extractor.get_table(table_name)
            if table:
                # Add tables from foreign keys
                for fk in table.foreign_keys[:2]:  # Limit to 2 per table
                    ref_table = fk.get("ReferencedTable", "")
                    if ref_table and len(tables_to_include) < max_tables:
                        tables_to_include.add(ref_table)
    
    # Limit total tables
    tables_list = list(tables_to_include)[:max_tables]
    
    return extractor.get_ddl(tables_list)
