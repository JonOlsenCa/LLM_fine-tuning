# Copyright 2024-2025 Viewpoint, Inc.
# Licensed under the Apache License, Version 2.0.

"""
V4 Scope Analysis

Analyzes the coverage and breadth of the V4 training data
against the full Vista schema.
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple


def load_training_data(path: str = "data/vgpt2_v4_sft.json") -> List[Dict]:
    """Load training data."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_vista_metadata(vgpt2_path: str = "C:/Github/VGPT2") -> Tuple[Set[str], Dict[str, str]]:
    """Load Vista metadata and return tables with their modules."""
    columns_file = Path(vgpt2_path) / "Viewpoint_Database" / "_Metadata" / "columns.json"
    
    with open(columns_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    
    tables = set()
    table_modules = {}
    
    for row in meta:
        obj_name = row.get("ObjectName", "")
        obj_type = row.get("ObjectType", "")
        module = row.get("Module", "Other")
        
        if obj_type in ("Table", "View") and obj_name:
            tables.add(obj_name)
            table_modules[obj_name] = module
    
    return tables, table_modules


def extract_tables_from_training(data: List[Dict]) -> Set[str]:
    """Extract all tables mentioned in training DDL."""
    tables = set()
    for ex in data:
        instr = ex.get("instruction", "")
        matches = re.findall(r'CREATE TABLE (\w+)', instr)
        tables.update(matches)
    return tables


def analyze_query_patterns(data: List[Dict]) -> Dict[str, int]:
    """Analyze SQL patterns in training data."""
    patterns = defaultdict(int)
    
    for ex in data:
        output = ex.get("output", "")
        
        # Check for various SQL patterns
        if "SELECT" in output.upper():
            patterns["SELECT queries"] += 1
        if "JOIN" in output.upper():
            patterns["JOIN queries"] += 1
        if "GROUP BY" in output.upper():
            patterns["GROUP BY queries"] += 1
        if "CASE WHEN" in output.upper():
            patterns["CASE WHEN expressions"] += 1
        if "DATEDIFF" in output.upper():
            patterns["Date calculations"] += 1
        if "SUM(" in output.upper() or "COUNT(" in output.upper():
            patterns["Aggregations"] += 1
        if "WITH (NOLOCK)" in output.upper():
            patterns["Vista NOLOCK pattern"] += 1
        if "cannot generate" in output.lower():
            patterns["Rejection examples"] += 1
    
    return dict(patterns)


def analyze_question_types(data: List[Dict]) -> Dict[str, int]:
    """Analyze question types in training data."""
    types = defaultdict(int)
    
    keywords = {
        "aging": "Aging analysis",
        "invoice": "Invoice queries",
        "payment": "Payment queries",
        "balance": "Balance queries",
        "job": "Job cost queries",
        "vendor": "Vendor queries",
        "customer": "Customer queries",
        "subcontract": "Subcontract queries",
        "budget": "Budget queries",
        "variance": "Variance analysis",
        "cost": "Cost queries",
    }
    
    for ex in data:
        instr = ex.get("instruction", "").lower()
        for keyword, qtype in keywords.items():
            if keyword in instr:
                types[qtype] += 1
                break
        else:
            types["Other queries"] += 1
    
    return dict(types)


def run_analysis():
    """Run full scope analysis."""
    print("=" * 70)
    print("VGPT2 V4 TRAINING DATA SCOPE ANALYSIS")
    print("=" * 70)
    print()
    
    # Load data
    training_data = load_training_data()
    all_tables, table_modules = load_vista_metadata()
    training_tables = extract_tables_from_training(training_data)
    
    # Basic stats
    print("1. BASIC STATISTICS")
    print("-" * 40)
    print(f"   Total training examples:    {len(training_data)}")
    print(f"   Vista tables/views total:   {len(all_tables)}")
    print(f"   Tables in training data:    {len(training_tables)}")
    print(f"   Table coverage:             {100 * len(training_tables) / len(all_tables):.1f}%")
    print()
    
    # Module coverage
    print("2. MODULE COVERAGE")
    print("-" * 40)
    
    # Group all tables by module
    vista_by_module = defaultdict(set)
    for table, module in table_modules.items():
        vista_by_module[module].add(table)
    
    # Group training tables by module
    training_by_module = defaultdict(set)
    for table in training_tables:
        module = table_modules.get(table, "Other")
        training_by_module[module].add(table)
    
    print(f"   {'Module':<12} {'Vista':<8} {'Training':<10} {'Coverage':<10} {'Tables in Training'}")
    print(f"   {'-'*12} {'-'*8} {'-'*10} {'-'*10} {'-'*30}")
    
    # Focus on key modules
    key_modules = ["AR", "AP", "JC", "SL", "PR", "GL", "PM", "SM", "EM", "HQ"]
    
    for module in key_modules:
        total = len(vista_by_module.get(module, set()))
        covered = len(training_by_module.get(module, set()))
        pct = 100 * covered / total if total > 0 else 0
        tables = ", ".join(sorted(training_by_module.get(module, set()))[:5])
        if len(training_by_module.get(module, set())) > 5:
            tables += "..."
        print(f"   {module:<12} {total:<8} {covered:<10} {pct:>6.1f}%    {tables}")
    
    print()
    
    # Query patterns
    print("3. SQL PATTERN COVERAGE")
    print("-" * 40)
    patterns = analyze_query_patterns(training_data)
    for pattern, count in sorted(patterns.items(), key=lambda x: -x[1]):
        print(f"   {pattern:<30} {count:>5} ({100*count/len(training_data):>5.1f}%)")
    print()
    
    # Question types
    print("4. BUSINESS QUERY TYPES")
    print("-" * 40)
    qtypes = analyze_question_types(training_data)
    for qtype, count in sorted(qtypes.items(), key=lambda x: -x[1]):
        print(f"   {qtype:<30} {count:>5} ({100*count/len(training_data):>5.1f}%)")
    print()
    
    # Gap analysis
    print("5. COVERAGE GAPS")
    print("-" * 40)
    
    critical_tables = {
        "AR": ["ARTH", "ARCM", "ARTI", "ARCO"],
        "AP": ["APTH", "APVM", "APTD", "APHD", "APCO"],
        "JC": ["JCJM", "JCJP", "JCCD", "JCCP", "JCCT", "JCCM", "JCCH"],
        "SL": ["SLHD", "SLIT", "SLWI"],
        "PR": ["PREH", "PRTH", "PRTB", "PRPC"],
        "GL": ["GLDT", "GLAC", "GLCO", "GLSM"],
        "PM": ["PMWC", "PMCO", "PMCH", "PMOI"],
        "SM": ["SMWorkOrder", "SMServiceSite", "SMEntity"],
    }
    
    print("   Critical tables NOT in training:")
    missing_critical = []
    for module, tables in critical_tables.items():
        missing = [t for t in tables if t not in training_tables]
        if missing:
            missing_critical.extend(missing)
            print(f"   {module}: {', '.join(missing)}")
    
    if not missing_critical:
        print("   None - all critical tables covered!")
    
    print()
    
    # Recommendations
    print("6. RECOMMENDATIONS")
    print("-" * 40)
    print(f"   Current coverage: {len(training_tables)}/21 core tables")
    print()
    print("   To improve coverage, consider adding templates for:")
    
    high_value_missing = [
        ("GL", "GLDT/GLAC", "General Ledger detail and accounts"),
        ("PM", "PMWC/PMOI", "Project Management work completed/original items"),
        ("PR", "PRTB/PRPC", "Payroll timecards and pay codes"),
        ("EM", "EMEM/EMCO", "Equipment master and company"),
        ("SM", "SMWorkOrder", "Service Management work orders"),
    ]
    
    for module, tables, desc in high_value_missing:
        if tables.split("/")[0] not in training_tables:
            print(f"   - {module}: {tables} ({desc})")
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"""
   Current State:
   - {len(training_data)} unique training examples
   - {len(training_tables)} tables covered ({100*len(training_tables)/len(all_tables):.2f}% of Vista)
   - Core AR/AP/JC/SL modules well represented
   
   For V4 Initial Training:
   - This coverage is SUFFICIENT for proof-of-concept
   - Focus is on quality SQL patterns, not table quantity
   - SQLCoder succeeded with ~20 table schemas
   
   For V5 Expansion:
   - Add GL, PM, PR, SM, EM modules
   - Target 50-100 tables for comprehensive coverage
   - Maintain quality > quantity approach
""")


if __name__ == "__main__":
    run_analysis()
