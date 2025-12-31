#!/usr/bin/env python3
"""
Audit training data to identify coverage gaps.

Analyzes:
1. Which tables are mentioned in training data
2. Which tables exist in schema but are NOT in training
3. What types of questions are covered (schema, SQL, business logic, etc.)
4. Column coverage per table
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def extract_table_mentions(text: str) -> set:
    """Extract Viewpoint table names from text."""
    # Common Viewpoint table patterns: 2-4 letter prefix + rest
    # Examples: APTH, JCJM, GLAC, PREH, SLWI, vrvAP_*, bAPTH
    patterns = [
        r'\b(AP[A-Z]{1,4})\b',  # AP module
        r'\b(AR[A-Z]{1,4})\b',  # AR module
        r'\b(GL[A-Z]{1,4})\b',  # GL module
        r'\b(JC[A-Z]{1,4})\b',  # JC module
        r'\b(PR[A-Z]{1,4})\b',  # PR module
        r'\b(EM[A-Z]{1,4})\b',  # EM module
        r'\b(IN[A-Z]{1,4})\b',  # IN module
        r'\b(SL[A-Z]{1,4})\b',  # SL module
        r'\b(PO[A-Z]{1,4})\b',  # PO module
        r'\b(SM[A-Z]{1,4})\b',  # SM module
        r'\b(PM[A-Z]{1,4})\b',  # PM module
        r'\b(HR[A-Z]{1,4})\b',  # HR module
        r'\b(DC[A-Z]{1,4})\b',  # DC module
        r'\b(MS[A-Z]{1,4})\b',  # MS module
        r'\b(HQ[A-Z]{1,4})\b',  # HQ module
        r'\b(DD[A-Z]{1,4})\b',  # DD module
        r'\b(CM[A-Z]{1,4})\b',  # CM module
        r'\b(b[A-Z]{3,6})\b',   # Base tables (bAPTH, bJCJM)
        r'\b(vrv[A-Z_]+)\b',    # Report views
        r'\b(ud[A-Z][A-Za-z]+)\b',  # User-defined
    ]
    
    tables = set()
    for pattern in patterns:
        matches = re.findall(pattern, text)
        tables.update(matches)
    return tables

def categorize_question(instruction: str) -> str:
    """Categorize the type of question."""
    inst_lower = instruction.lower()
    
    if 'write sql' in inst_lower or 'query' in inst_lower:
        return 'sql_generation'
    elif 'join' in inst_lower:
        return 'join_pattern'
    elif 'fix' in inst_lower or 'correct' in inst_lower:
        return 'error_correction'
    elif 'column' in inst_lower or 'data type' in inst_lower:
        return 'column_info'
    elif 'describe' in inst_lower or 'what is' in inst_lower:
        return 'schema_description'
    elif 'primary key' in inst_lower or 'foreign key' in inst_lower:
        return 'key_info'
    elif 'relationship' in inst_lower or 'link' in inst_lower:
        return 'relationships'
    elif 'module' in inst_lower or 'tables in' in inst_lower:
        return 'module_info'
    else:
        return 'other'

def load_schema_tables(schema_path: str) -> set:
    """Load all table names from schema metadata."""
    tables = set()
    columns_file = Path(schema_path) / "Viewpoint_Database" / "_MetadataV2" / "_data" / "columns.json"
    
    if columns_file.exists():
        with open(columns_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            table = item.get('ObjectName', '')
            if table:
                tables.add(table)
    return tables

def main():
    # Load training data
    training_file = "data/vgpt2_v3_sft.json"
    schema_path = "C:/Github/VGPT2"
    
    print("Loading training data...")
    with open(training_file, 'r', encoding='utf-8') as f:
        training_data = json.load(f)
    
    print(f"Total training examples: {len(training_data)}")
    
    # Analyze coverage
    table_mentions = defaultdict(int)
    question_types = defaultdict(int)
    tables_per_example = []
    
    for item in training_data:
        instruction = item.get('instruction', '')
        output = item.get('output', '')
        full_text = instruction + ' ' + output
        
        # Extract tables
        tables = extract_table_mentions(full_text)
        for t in tables:
            table_mentions[t] += 1
        tables_per_example.append(len(tables))
        
        # Categorize question
        qtype = categorize_question(instruction)
        question_types[qtype] += 1
    
    # Load schema tables
    print("\nLoading schema tables...")
    schema_tables = load_schema_tables(schema_path)
    print(f"Total tables in schema: {len(schema_tables)}")
    
    # Find gaps
    mentioned_tables = set(table_mentions.keys())
    missing_tables = schema_tables - mentioned_tables
    
    # Report
    print("\n" + "="*60)
    print("TRAINING DATA AUDIT REPORT")
    print("="*60)
    
    print(f"\n## Coverage Summary")
    print(f"- Training examples: {len(training_data)}")
    print(f"- Unique tables mentioned: {len(mentioned_tables)}")
    print(f"- Tables in schema: {len(schema_tables)}")
    print(f"- Tables MISSING from training: {len(missing_tables)}")
    print(f"- Coverage: {100*len(mentioned_tables)/len(schema_tables):.1f}%")
    
    print(f"\n## Question Type Distribution")
    for qtype, count in sorted(question_types.items(), key=lambda x: -x[1]):
        print(f"- {qtype}: {count} ({100*count/len(training_data):.1f}%)")
    
    print(f"\n## Top 30 Most Mentioned Tables")
    for table, count in sorted(table_mentions.items(), key=lambda x: -x[1])[:30]:
        print(f"- {table}: {count}")
    
    print(f"\n## Critical Missing Tables (SL/JC/AP advanced)")
    critical = ['SLWI', 'SLIT', 'SLHB', 'JCJP', 'JCCH', 'JCCP', 'JCCT', 'JCPR', 'JCPD',
                'APTD', 'APHD', 'APHB', 'APLB', 'APCO', 'ARCO', 'JCCO', 'PRCO']
    for t in critical:
        status = "MISSING" if t in missing_tables else f"OK ({table_mentions.get(t, 0)} mentions)"
        print(f"- {t}: {status}")
    
    # Save full report
    report = {
        "total_examples": len(training_data),
        "unique_tables_mentioned": len(mentioned_tables),
        "schema_tables": len(schema_tables),
        "missing_count": len(missing_tables),
        "coverage_pct": 100*len(mentioned_tables)/len(schema_tables),
        "question_types": dict(question_types),
        "table_mentions": dict(table_mentions),
        "missing_tables": sorted(list(missing_tables))
    }
    
    with open("output/training_audit.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nFull report saved to: output/training_audit.json")

if __name__ == "__main__":
    main()

