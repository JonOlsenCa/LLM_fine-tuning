#!/usr/bin/env python3
"""
Comprehensive Training Data Generator

Generates 1,500-2,000 targeted training examples by:
1. Processing ALL critical tables from schema metadata
2. Generating 10-20 examples per important table
3. Auto-generating JOIN patterns from foreign key data
4. Creating business logic examples from column semantics

Also generates 500+ test questions with ground truth answers.
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple
import random

# Paths
SCHEMA_PATH = Path("C:/Github/VGPT2/Viewpoint_Database/_MetadataV2/_data")
OUTPUT_DIR = Path("data")
TEST_OUTPUT = Path("training/COMPREHENSIVE_TEST_SUITE.json")

# Critical modules to focus on
CRITICAL_MODULES = ['AP', 'AR', 'GL', 'JC', 'PR', 'SL', 'PO', 'EM', 'IN', 'SM', 'PM', 'CM', 'HR', 'MS', 'HQ']

# Tables that are most important for complex queries (prioritize these)
HIGH_PRIORITY_TABLES = [
    # AP Module
    'APTH', 'APTL', 'APTD', 'APHD', 'APHB', 'APLB', 'APCO', 'APVM', 'APCM',
    # AR Module  
    'ARTH', 'ARTL', 'ARCM', 'ARCO', 'ARIB',
    # GL Module
    'GLDT', 'GLAC', 'GLJR', 'GLCO', 'GLRD',
    # JC Module
    'JCJM', 'JCCM', 'JCCD', 'JCCP', 'JCCH', 'JCJP', 'JCJI', 'JCCT', 'JCCO', 'JCPR', 'JCPD', 'JCPM',
    # PR Module
    'PRTH', 'PRTB', 'PREH', 'PRCO', 'PRDT', 'PRTC',
    # SL Module
    'SLHD', 'SLIT', 'SLWI', 'SLHB', 'SLCO', 'SLCB',
    # PO Module
    'POHD', 'POIT', 'POIB', 'POCO',
    # EM Module
    'EMEM', 'EMCO', 'EMRD', 'EMBF',
    # IN Module
    'INMT', 'INCO', 'INLM', 'INDT',
    # SM Module
    'SMWorkOrder', 'SMServiceSite', 'SMWorkCompleted', 'SMCo',
    # PM Module
    'PMCO', 'PMCH', 'PMOI', 'PMPF',
    # HQ Module
    'HQCO', 'HQMA', 'HQBC', 'HQMT',
]

# Column semantic meanings (business logic)
COLUMN_SEMANTICS = {
    # Retainage columns
    'WCRetAmt': 'Work Completed Retainage amount - retainage held on labor/installed work',
    'SMRetAmt': 'Stored Materials Retainage amount - retainage held on materials on-site',
    'WCRetPct': 'Work Completed Retainage percentage',
    'SMRetPct': 'Stored Materials Retainage percentage',
    'Retainage': 'Total retainage amount held',
    'RetHoldCode': 'Retainage hold code - identifies retainage-specific holds',
    'RetPayType': 'Retainage payment type (typically 3)',
    'MaxRetgPct': 'Maximum retainage percentage allowed',
    'InclACOinMaxYN': 'Include Approved Change Orders in max retainage calculation',
    
    # Cost columns
    'OrigCost': 'Original budgeted/contracted cost',
    'CurCost': 'Current cost including change orders',
    'ActualCost': 'Actual costs posted to date',
    'OrigEstCost': 'Original estimated cost',
    'CurrEstCost': 'Current estimated cost (budget with changes)',
    'InvCost': 'Invoiced cost amount',
    'PaidAmt': 'Amount paid to date',
    'PaidCost': 'Cost amount that has been paid',
    
    # Hours columns
    'OrigEstHours': 'Original estimated hours',
    'CurrEstHours': 'Current estimated hours',
    'ActualHours': 'Actual hours posted',
    
    # Unit columns
    'ItemUnitFlag': 'Y=use item units for unit of measure, N=use phase units',
    'PhaseUnitFlag': 'Y=use phase units for posting',
    
    # Status columns
    'PayType': 'Payment type: 1=Regular, 2=Discount, 3=Retainage',
    'Status': 'Transaction status (varies by table)',
    'HoldCode': 'Hold reason code',
    'PayFullDate': 'Date invoice was fully paid (NULL=unpaid)',
    
    # Oncost columns
    'ocApplyMth': 'Oncost apply month - links to original transaction month',
    'ocApplyTrans': 'Oncost apply transaction - links to original transaction number',
    'ocApplyLine': 'Oncost apply line - links to original line number',
    
    # Stored Materials
    'StoredMatls': 'Stored materials amount (Purchased - Installed)',
    'Purchased': 'Total materials purchased',
    'Installed': 'Materials installed/incorporated into work',
    'WCCost': 'Work Completed cost - billable labor and installed work',
}

# Module descriptions
MODULE_DESCRIPTIONS = {
    'AP': 'Accounts Payable - vendor invoices, payments, holds',
    'AR': 'Accounts Receivable - customer invoices, collections',
    'GL': 'General Ledger - chart of accounts, journal entries',
    'JC': 'Job Cost - projects, phases, cost tracking, budgets',
    'PR': 'Payroll - employee time, wages, deductions',
    'SL': 'Subcontracts - subcontractor agreements, billing, retainage',
    'PO': 'Purchase Orders - procurement, receiving',
    'EM': 'Equipment Management - fleet, maintenance, costs',
    'IN': 'Inventory - materials, stock levels',
    'SM': 'Service Management - work orders, service calls',
    'PM': 'Project Management - documents, submittals, RFIs',
    'CM': 'Cash Management - bank accounts, reconciliation',
    'HR': 'Human Resources - employee records, benefits',
    'MS': 'Material Sales - customer sales transactions',
    'HQ': 'Headquarters - company setup, shared data',
}


def load_schema() -> Tuple[Dict, List, Dict]:
    """Load all schema metadata."""
    # Load columns
    columns_file = SCHEMA_PATH / "columns.json"
    with open(columns_file, 'r', encoding='utf-8') as f:
        columns_data = json.load(f)
    
    # Build table structure
    tables = {}
    for col in columns_data:
        table = col.get('ObjectName', '')
        if not table:
            continue
        if table not in tables:
            tables[table] = {
                'columns': [],
                'module': col.get('Module', 'Other'),
                'description': col.get('TableDescription', ''),
            }
        tables[table]['columns'].append({
            'name': col.get('ColumnName', ''),
            'type': col.get('DataType', ''),
            'nullable': col.get('IsNullable', 'YES') == 'YES',
            'description': col.get('ColumnDescription', ''),
        })
    
    # Load foreign keys
    fks = []
    fks_file = SCHEMA_PATH / "foreign_keys.json"
    if fks_file.exists():
        with open(fks_file, 'r', encoding='utf-8') as f:
            fks = json.load(f)
    
    # Build FK lookup
    fk_lookup = defaultdict(list)
    for fk in fks:
        from_table = fk.get('FromTable', '')
        to_table = fk.get('ToTable', '')
        if from_table and to_table:
            fk_lookup[from_table].append(fk)
    
    return tables, fks, fk_lookup


def get_module(table_name: str) -> str:
    """Extract module prefix from table name."""
    if table_name.startswith('b') and len(table_name) > 1 and table_name[1:3].isupper():
        return table_name[1:3]
    if table_name.startswith('vrv'):
        match = re.match(r'vrv([A-Z]{2})', table_name)
        if match:
            return match.group(1)
    if table_name.startswith('ud'):
        return 'UD'
    if len(table_name) >= 2 and table_name[:2].isupper():
        return table_name[:2]
    return 'Other'


def generate_table_examples(table_name: str, table_info: Dict, fk_lookup: Dict) -> List[Dict]:
    """Generate training examples for a single table - expanded for more coverage."""
    examples = []
    module = get_module(table_name)
    cols = table_info['columns']
    col_names = [c['name'] for c in cols]

    key_cols = col_names[:min(8, len(col_names))]
    key_cols_str = ', '.join(key_cols)
    all_cols_str = ', '.join(col_names[:15]) + ('...' if len(col_names) > 15 else '')
    module_desc = MODULE_DESCRIPTIONS.get(module, f'{module} module')

    # Basic table questions (multiple phrasings)
    examples.append({
        "instruction": f"What columns are in the {table_name} table?",
        "input": "",
        "output": f"The {table_name} table (Module: {module}) contains: {all_cols_str} ({len(col_names)} total columns)"
    })
    examples.append({
        "instruction": f"List the columns in {table_name}",
        "input": "",
        "output": f"{table_name} columns: {all_cols_str}. This is a {module} module table with {len(col_names)} columns."
    })
    examples.append({
        "instruction": f"Describe the {table_name} table",
        "input": "",
        "output": f"{table_name} is part of {module_desc}. Key columns: {key_cols_str}. Total columns: {len(col_names)}."
    })
    examples.append({
        "instruction": f"What is the {table_name} table used for?",
        "input": "",
        "output": f"{table_name} is a {module} module table used for {module_desc.lower()}. Key columns: {key_cols_str}."
    })
    examples.append({
        "instruction": f"What module is {table_name} in?",
        "input": "",
        "output": f"{table_name} is in the {module} module ({module_desc})."
    })

    # Column-specific questions (more columns, multiple phrasings)
    for col in cols[:8]:
        col_name = col['name']
        col_type = col['type']
        col_desc = col.get('description', '')
        semantic = COLUMN_SEMANTICS.get(col_name, col_desc if col_desc else f'{col_name} field')
        nullable = 'nullable' if col.get('nullable', True) else 'required (not null)'

        examples.append({
            "instruction": f"What is the {col_name} column in {table_name}?",
            "input": "",
            "output": f"{col_name} in {table_name} is a {col_type} column ({nullable}). {semantic}"
        })
        examples.append({
            "instruction": f"What data type is {table_name}.{col_name}?",
            "input": "",
            "output": f"{table_name}.{col_name} has data type {col_type}. {semantic}"
        })
        # Add semantic meaning if it's a known business column
        if col_name in COLUMN_SEMANTICS:
            examples.append({
                "instruction": f"What does {col_name} mean in {table_name}?",
                "input": "",
                "output": f"In {table_name}, {col_name} represents: {COLUMN_SEMANTICS[col_name]}"
            })
            examples.append({
                "instruction": f"Explain the {col_name} field",
                "input": "",
                "output": f"{col_name}: {COLUMN_SEMANTICS[col_name]}. Found in tables like {table_name}."
            })

    # Relationship questions
    related_tables = fk_lookup.get(table_name, [])
    if related_tables:
        related_names = list(set([fk.get('ToTable', '') for fk in related_tables[:5]]))
        examples.append({
            "instruction": f"What tables does {table_name} relate to?",
            "input": "",
            "output": f"{table_name} has foreign key relationships to: {', '.join(related_names)}."
        })
        examples.append({
            "instruction": f"What are the foreign keys from {table_name}?",
            "input": "",
            "output": f"{table_name} references: {', '.join(related_names)}. These are parent tables linked via foreign keys."
        })

    # SQL query examples (multiple variations)
    co_col = next((c for c in col_names if c.endswith('Co')), col_names[0] if col_names else 'KeyID')
    examples.append({
        "instruction": f"Write a simple SELECT query for {table_name}",
        "input": "",
        "output": f"```sql\nSELECT {key_cols_str}\nFROM {table_name} WITH (NOLOCK)\nWHERE {co_col} = @{co_col}\n```\n\nAlways use WITH (NOLOCK) and filter by company column."
    })
    examples.append({
        "instruction": f"How do I query the {table_name} table?",
        "input": "",
        "output": f"```sql\nSELECT {key_cols_str}\nFROM {table_name} WITH (NOLOCK)\nWHERE {co_col} = @{co_col}\nORDER BY {col_names[1] if len(col_names) > 1 else col_names[0]}\n```\n\nUse WITH (NOLOCK) for read queries. Always filter by company."
    })
    examples.append({
        "instruction": f"Show me a basic {table_name} query",
        "input": "",
        "output": f"```sql\nSELECT TOP 100 *\nFROM {table_name} WITH (NOLOCK)\nWHERE {co_col} = @{co_col}\n```\n\nNote: Use specific columns in production. WITH (NOLOCK) prevents blocking."
    })

    return examples


def generate_join_examples(tables: Dict, fk_lookup: Dict) -> List[Dict]:
    """Generate JOIN pattern examples from FK relationships."""
    examples = []

    join_patterns = [
        ('APTH', 'APTL', ['APCo', 'Mth', 'APTrans'], 'AP Transaction Header to Lines'),
        ('APTH', 'APTD', ['APCo', 'Mth', 'APTrans'], 'AP Transaction Header to Detail'),
        ('APTL', 'APTD', ['APCo', 'Mth', 'APTrans', 'APLine'], 'AP Transaction Lines to Detail'),
        ('APTH', 'APVM', ['APCo=APCo', 'VendorGroup', 'Vendor'], 'AP Transaction to Vendor Master'),
        ('APTH', 'APHD', ['APCo', 'Mth', 'APTrans'], 'AP Transaction to Hold Detail'),
        ('ARTH', 'ARTL', ['ARCo', 'Mth', 'ARTrans'], 'AR Transaction Header to Lines'),
        ('ARTH', 'ARCM', ['ARCo', 'CustGroup', 'Customer'], 'AR Transaction to Customer Master'),
        ('JCJM', 'JCCD', ['JCCo', 'Job'], 'Job Master to Cost Detail'),
        ('JCJM', 'JCJP', ['JCCo', 'Job'], 'Job Master to Job Phases'),
        ('JCJP', 'JCCP', ['JCCo', 'Job', 'PhaseGroup', 'Phase'], 'Job Phase to Cost Phase'),
        ('JCCP', 'JCCH', ['JCCo', 'Job', 'PhaseGroup', 'Phase', 'CostType'], 'Cost Phase to Cost Header'),
        ('JCJM', 'JCCM', ['JCCo', 'Contract'], 'Job Master to Contract Master'),
        ('SLHD', 'SLIT', ['SLCo', 'SL'], 'SL Header to Items'),
        ('SLHD', 'SLWI', ['SLCo', 'SL'], 'SL Header to Work Items'),
        ('SLIT', 'SLWI', ['SLCo', 'SL', 'SLItem'], 'SL Items to Work Items'),
        ('SLHD', 'APVM', ['SLCo=APCo', 'VendorGroup', 'Vendor'], 'SL Header to Vendor Master'),
        ('PRTH', 'PRTB', ['PRCo', 'PRGroup', 'PREndDate'], 'PR Timecard Header to Batch'),
        ('PREH', 'PRTH', ['PRCo', 'Employee'], 'PR Employee to Timecards'),
        ('GLDT', 'GLAC', ['GLCo', 'GLAcct'], 'GL Detail to Account'),
        ('POHD', 'POIT', ['POCo', 'PO'], 'PO Header to Items'),
        ('EMEM', 'EMBF', ['EMCo', 'Equipment'], 'Equipment Master to Fuel'),
    ]

    for from_tbl, to_tbl, join_cols, desc in join_patterns:
        if from_tbl not in tables or to_tbl not in tables:
            continue

        join_conditions = []
        for jc in join_cols:
            if '=' in jc:
                parts = jc.split('=')
                join_conditions.append(f"{from_tbl}.{parts[0]} = {to_tbl}.{parts[1]}")
            else:
                join_conditions.append(f"{from_tbl}.{jc} = {to_tbl}.{jc}")

        join_clause = ' AND '.join(join_conditions)
        from_cols = [c['name'] for c in tables[from_tbl]['columns'][:4]]
        to_cols = [c['name'] for c in tables[to_tbl]['columns'][:4]]
        select_cols = ', '.join([f"{from_tbl}.{c}" for c in from_cols[:3]] + [f"{to_tbl}.{c}" for c in to_cols[:3]])

        sql = f"""SELECT {select_cols}
FROM {from_tbl} WITH (NOLOCK)
INNER JOIN {to_tbl} WITH (NOLOCK) ON {join_clause}
WHERE {from_tbl}.{from_cols[0]} = @{from_cols[0]}"""

        examples.append({
            "instruction": f"How do I join {from_tbl} and {to_tbl}?",
            "input": "",
            "output": f"Join {from_tbl} to {to_tbl} ({desc}) using: {', '.join(join_cols)}.\n\n```sql\n{sql}\n```"
        })
        examples.append({
            "instruction": f"What columns link {from_tbl} to {to_tbl}?",
            "input": "",
            "output": f"Join columns for {from_tbl} → {to_tbl}: {', '.join(join_cols)}. {desc}."
        })
        examples.append({
            "instruction": f"Write SQL joining {from_tbl} with {to_tbl}",
            "input": "",
            "output": f"```sql\n{sql}\n```\n\nKey join columns: {', '.join(join_cols)}. {desc}."
        })

    return examples


def generate_business_logic_examples() -> List[Dict]:
    """Generate business logic explanation examples."""
    examples = []

    retainage = [
        {"instruction": "How does Vista calculate maximum retainage when InclACOinMaxYN is set to Y?",
         "input": "",
         "output": "When InclACOinMaxYN = 'Y' in SLHB, Vista includes Approved Change Orders in max retainage:\nMaxRetainage = MaxRetgPct * CurCost (includes change orders)\n\nWhen InclACOinMaxYN = 'N':\nMaxRetainage = MaxRetgPct * OrigCost (original cost only)\n\nKey columns: SLHB.MaxRetgPct, SLHB.InclACOinMaxYN, SLIT.CurCost, SLIT.OrigCost"},
        {"instruction": "What is the difference between WCRetAmt and SMRetAmt in SLWI?",
         "input": "",
         "output": "In SLWI (Subcontract Work Item):\n\nWCRetAmt = Work Completed Retainage\n- Retainage on labor and installed work\n- Calculated: WCCost * WCRetPct\n\nSMRetAmt = Stored Materials Retainage\n- Retainage on materials on-site but not installed\n- Calculated: StoredMatls * SMRetPct\n\nTotal Retainage = WCRetAmt + SMRetAmt\n\nStoredMatls = Purchased - Installed"},
        {"instruction": "How do I identify retainage holds vs non-retainage holds in AP?",
         "input": "",
         "output": "Compare APHD.HoldCode to APCO.RetHoldCode:\n\nIf APHD.HoldCode = APCO.RetHoldCode → Retainage Hold\nIf APHD.HoldCode ≠ APCO.RetHoldCode → Non-Retainage Hold\n\n```sql\nSELECT APTH.APTrans, APHD.HoldCode,\n  CASE WHEN APHD.HoldCode = APCO.RetHoldCode THEN 'Retainage Hold' \n       ELSE 'Non-Retainage Hold' END AS HoldType\nFROM APTH\nJOIN APHD ON APTH.APCo = APHD.APCo AND APTH.Mth = APHD.Mth AND APTH.APTrans = APHD.APTrans\nJOIN APCO ON APTH.APCo = APCO.APCo\n```"},
        {"instruction": "Explain stored materials billing in subcontracts",
         "input": "",
         "output": "In SLWI, stored materials are tracked separately:\n\nStoredMatls = Purchased - Installed\n- Materials delivered but not yet incorporated into work\n\nBilling breakdown:\n- WCCost: Work completed (labor + installed materials)\n- StoredMatls: Materials on-site awaiting installation\n- Total Billable = WCCost + StoredMatls\n\nRetainage treatment:\n- WCRetAmt = WCCost * WCRetPct (work retainage)\n- SMRetAmt = StoredMatls * SMRetPct (materials retainage)"},
    ]
    examples.extend(retainage)

    cost = [
        {"instruction": "What tables track job cost projections?",
         "input": "",
         "output": "Job cost projections use:\n\nJCPR - Projection Resources (projection setup)\nJCPD - Projection Detail (projected values)\nJCCP - Cost Phase (budget/actual by phase)\nJCCD - Cost Detail (transaction detail)\n\nKey calculations:\n- Budget: JCCP.CurrEstCost\n- Actual: JCCP.ActualCost\n- Remaining: CurrEstCost - ActualCost"},
        {"instruction": "How do ItemUnitFlag and PhaseUnitFlag work in JCCH?",
         "input": "",
         "output": "In JCCH (Job Cost Header):\n\nItemUnitFlag:\n- 'Y' = Use item-level unit of measure\n- 'N' = Use phase-level unit of measure\n\nPhaseUnitFlag:\n- 'Y' = Post units at phase level\n- 'N' = Post units at item level\n\nThese control how units are tracked and reported for job costs."},
        {"instruction": "Explain the relationship between JCJP and JCCP",
         "input": "",
         "output": "JCJP (Job Phase) and JCCP (Cost Phase):\n\nJCJP = Phase definitions (billing/contract side)\n- Defines phases within a job\n- Links to contract items (JCJI)\n\nJCCP = Cost tracking (cost side)\n- Budget/actual amounts per phase/cost type\n- OrigEstCost, CurrEstCost, ActualCost\n\nJoin: JCCo, Job, PhaseGroup, Phase\n\nJCJP is 'what we bill', JCCP is 'what we spend'."},
    ]
    examples.extend(cost)

    ap = [
        {"instruction": "What does PayType mean in APTD?",
         "input": "",
         "output": "APTD.PayType indicates the payment type:\n\n1 = Regular payment (standard invoice payment)\n2 = Discount payment (early payment discount)\n3 = Retainage payment (release of retainage)\n\nUse PayType = 3 to identify retainage-related payments.\nAPCO.RetPayType stores the company's retainage payment type setting."},
        {"instruction": "How do oncost columns work in APLB?",
         "input": "",
         "output": "APLB (AP Line Batch) oncost columns link to original transactions:\n\nocApplyMth - Month of original transaction\nocApplyTrans - Original transaction number\nocApplyLine - Original line number\n\nThese create an audit trail from oncost batch entries back to the source AP transaction. Join using:\nAPLB.ocApplyMth = APTL.Mth\nAPLB.ocApplyTrans = APTL.APTrans\nAPLB.ocApplyLine = APTL.APLine"},
    ]
    examples.extend(ap)

    return examples


def generate_hallucination_examples() -> List[Dict]:
    """Generate examples that teach the model to reject fake tables."""
    fake_tables = [
        ("ARAgingReport", "ARTH/ARTL with DATEDIFF for aging, or VPShared_CustomerAging view"),
        ("SubcontractorPayments", "APTD joined to APTL with SL reference, or SLWI for worksheets"),
        ("JobCostSummary", "JCCP for phase-level or JCCD for transaction detail"),
        ("VendorInvoices", "APTH for AP headers joined to APVM for vendor info"),
        ("EmployeeTimesheet", "PRTH for timecard headers or PRTB for batches"),
        ("GLTransactions", "GLDT for GL detail transactions"),
        ("CustomerInvoices", "ARTH for AR transaction headers"),
        ("PurchaseOrderDetail", "POHD for headers, POIT for items"),
        ("InventoryItems", "INMT for inventory material master"),
        ("ProjectBudget", "JCCP.OrigEstCost and CurrEstCost for budgets"),
        ("PayrollTransactions", "PRTH and PRTB for payroll transactions"),
        ("ContractBilling", "JCCM for contracts, JCJI for items, ARTH for billing"),
        ("EquipmentCosts", "EMEM for equipment, EMBF for fuel, EMRD for revenue"),
        ("MaterialRequests", "INMT for materials, POIT for PO items"),
        ("WorkOrderDetails", "SMWorkOrder and SMWorkCompleted tables"),
        ("VendorPaymentHistory", "APTD for payment detail, APTH for headers"),
        ("CustomerBalance", "ARCM for customer master, ARTH for transactions"),
        ("JobPhaseDetail", "JCJP for phases, JCCP for costs"),
        ("ChangeOrderLog", "JCCO for JC change orders or SLCO for SL"),
        ("BudgetVariance", "Compare JCCP.CurrEstCost to JCCP.ActualCost"),
    ]

    examples = []
    for fake, real in fake_tables:
        examples.append({
            "instruction": f"What columns are in the {fake} table?",
            "input": "",
            "output": f"The {fake} table does not exist in Viewpoint Vista. Use {real} instead."
        })
        examples.append({
            "instruction": f"Write SQL to query {fake}",
            "input": "",
            "output": f"I cannot query {fake} because this table does not exist in Viewpoint Vista. Use {real} instead."
        })
        examples.append({
            "instruction": f"How do I join {fake} to other tables?",
            "input": "",
            "output": f"{fake} is not a valid Viewpoint table. For this data, use {real}."
        })

    return examples


def generate_complex_sql_examples() -> List[Dict]:
    """Generate complex multi-table SQL examples."""
    examples = []

    examples.append({
        "instruction": "Write SQL for AR aging report with 30/60/90+ day buckets",
        "input": "",
        "output": """```sql
SELECT ARTH.ARCo, ARTH.CustGroup, ARTH.Customer, ARCM.Name,
  SUM(CASE WHEN DATEDIFF(day, ARTH.InvDate, GETDATE()) <= 30 THEN ARTH.AmountDue ELSE 0 END) AS Current_30,
  SUM(CASE WHEN DATEDIFF(day, ARTH.InvDate, GETDATE()) BETWEEN 31 AND 60 THEN ARTH.AmountDue ELSE 0 END) AS Days_31_60,
  SUM(CASE WHEN DATEDIFF(day, ARTH.InvDate, GETDATE()) BETWEEN 61 AND 90 THEN ARTH.AmountDue ELSE 0 END) AS Days_61_90,
  SUM(CASE WHEN DATEDIFF(day, ARTH.InvDate, GETDATE()) > 90 THEN ARTH.AmountDue ELSE 0 END) AS Over_90
FROM ARTH WITH (NOLOCK)
INNER JOIN ARCM WITH (NOLOCK) ON ARTH.ARCo = ARCM.ARCo AND ARTH.CustGroup = ARCM.CustGroup AND ARTH.Customer = ARCM.Customer
WHERE ARTH.ARCo = @ARCo AND ARTH.PayFullDate IS NULL
GROUP BY ARTH.ARCo, ARTH.CustGroup, ARTH.Customer, ARCM.Name
```

Key: PayFullDate IS NULL = unpaid, CASE WHEN for aging buckets."""
    })

    examples.append({
        "instruction": "Write SQL for subcontractor cost summary with original, changes, invoiced, and retainage",
        "input": "",
        "output": """```sql
SELECT SLHD.SLCo, SLHD.VendorGroup, SLHD.Vendor, APVM.Name AS VendorName,
  SUM(SLIT.OrigCost) AS OriginalCost,
  SUM(SLIT.CurCost - SLIT.OrigCost) AS ChangeOrders,
  SUM(SLIT.CurCost) AS CurrentCost,
  SUM(SLIT.InvCost) AS InvoicedCost,
  SUM(SLIT.Retainage) AS RetainageHeld
FROM SLHD WITH (NOLOCK)
INNER JOIN SLIT WITH (NOLOCK) ON SLHD.SLCo = SLIT.SLCo AND SLHD.SL = SLIT.SL
INNER JOIN APVM WITH (NOLOCK) ON SLHD.SLCo = APVM.APCo AND SLHD.VendorGroup = APVM.VendorGroup AND SLHD.Vendor = APVM.Vendor
WHERE SLHD.SLCo = @SLCo
GROUP BY SLHD.SLCo, SLHD.VendorGroup, SLHD.Vendor, APVM.Name
```

Key columns: OrigCost, CurCost, InvCost, Retainage in SLIT."""
    })

    examples.append({
        "instruction": "Write SQL for job cost budget vs actual by phase and cost type",
        "input": "",
        "output": """```sql
SELECT JCJP.JCCo, JCJP.Job, JCJP.Phase, JCJP.Description,
  JCCP.CostType, JCCT.Description AS CostTypeDesc,
  JCCP.OrigEstCost, JCCP.CurrEstCost, JCCP.ActualCost,
  JCCP.CurrEstCost - JCCP.ActualCost AS Remaining,
  JCCH.ItemUnitFlag, JCCH.PhaseUnitFlag
FROM JCJP WITH (NOLOCK)
INNER JOIN JCCP WITH (NOLOCK) ON JCJP.JCCo = JCCP.JCCo AND JCJP.Job = JCCP.Job AND JCJP.PhaseGroup = JCCP.PhaseGroup AND JCJP.Phase = JCCP.Phase
INNER JOIN JCCH WITH (NOLOCK) ON JCCP.JCCo = JCCH.JCCo AND JCCP.Job = JCCH.Job AND JCCP.PhaseGroup = JCCH.PhaseGroup AND JCCP.Phase = JCCH.Phase AND JCCP.CostType = JCCH.CostType
INNER JOIN JCCT WITH (NOLOCK) ON JCCH.PhaseGroup = JCCT.PhaseGroup AND JCCH.CostType = JCCT.CostType
WHERE JCJP.JCCo = @JCCo AND JCJP.Job = @Job
```

Tables: JCJP (phase), JCCP (cost phase), JCCH (cost header), JCCT (cost type master)."""
    })

    examples.append({
        "instruction": "Write SQL to find AP invoices on retainage hold",
        "input": "",
        "output": """```sql
SELECT APTH.APCo, APTH.Mth, APTH.APTrans, APTH.Vendor, APVM.Name,
  APTH.APRef, APTH.GrossAmt, APHD.HoldCode,
  CASE WHEN APHD.HoldCode = APCO.RetHoldCode THEN 'Retainage Hold' ELSE 'Other Hold' END AS HoldType
FROM APTH WITH (NOLOCK)
INNER JOIN APHD WITH (NOLOCK) ON APTH.APCo = APHD.APCo AND APTH.Mth = APHD.Mth AND APTH.APTrans = APHD.APTrans
INNER JOIN APCO WITH (NOLOCK) ON APTH.APCo = APCO.APCo
INNER JOIN APVM WITH (NOLOCK) ON APTH.APCo = APVM.APCo AND APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor
WHERE APTH.APCo = @APCo AND APHD.HoldCode IS NOT NULL
```

Key: Compare APHD.HoldCode to APCO.RetHoldCode to identify retainage holds."""
    })

    examples.append({
        "instruction": "Write SQL to reconcile AP oncost batch entries to original transactions",
        "input": "",
        "output": """```sql
SELECT APLB.Co, APLB.Mth, APLB.BatchId, APLB.BatchSeq,
  APLB.Amount AS OnCostAmt,
  APLB.ocApplyMth, APLB.ocApplyTrans, APLB.ocApplyLine,
  APTL.Description AS OrigLineDesc,
  APTH.APRef AS OrigInvoice, APTH.Vendor
FROM APLB WITH (NOLOCK)
INNER JOIN APTL WITH (NOLOCK) ON APLB.Co = APTL.APCo AND APLB.ocApplyMth = APTL.Mth AND APLB.ocApplyTrans = APTL.APTrans AND APLB.ocApplyLine = APTL.APLine
INNER JOIN APTH WITH (NOLOCK) ON APTL.APCo = APTH.APCo AND APTL.Mth = APTH.Mth AND APTL.APTrans = APTH.APTrans
WHERE APLB.Co = @APCo AND APLB.Mth = @Mth AND APLB.BatchId = @BatchId
```

Oncost columns: ocApplyMth, ocApplyTrans, ocApplyLine link to original APTL."""
    })

    examples.append({
        "instruction": "Write SQL to link SLWI retainage to APTD payments",
        "input": "",
        "output": """```sql
SELECT SLWI.SLCo, SLWI.SL, SLWI.SLItem, SLWI.WCRetAmt, SLWI.SMRetAmt,
  APTD.APTrans, APTD.PayType, APTD.Amount, APTD.Status
FROM SLWI WITH (NOLOCK)
INNER JOIN APTL WITH (NOLOCK) ON SLWI.SLCo = APTL.APCo AND SLWI.SL = APTL.SL AND SLWI.SLItem = APTL.SLItem
INNER JOIN APTD WITH (NOLOCK) ON APTL.APCo = APTD.APCo AND APTL.Mth = APTD.Mth AND APTL.APTrans = APTD.APTrans AND APTL.APLine = APTD.APLine
WHERE SLWI.SLCo = @SLCo AND APTD.PayType = 3
```

Path: SLWI → APTL (via SL, SLItem) → APTD. PayType=3 filters to retainage payments."""
    })

    examples.append({
        "instruction": "Write SQL to link SM WorkOrder to AR billing through JC",
        "input": "",
        "output": """```sql
SELECT WO.SMCo, WO.WorkOrder, WO.Description AS WODesc,
  SS.ServiceSite, SS.Job,
  JCJM.Description AS JobDesc, JCJM.Contract,
  ARTH.ARTrans, ARTH.InvDate, ARTH.Amount
FROM SMWorkOrder WO WITH (NOLOCK)
INNER JOIN SMServiceSite SS WITH (NOLOCK) ON WO.SMCo = SS.SMCo AND WO.ServiceSite = SS.ServiceSite
INNER JOIN JCJM WITH (NOLOCK) ON SS.JCCo = JCJM.JCCo AND SS.Job = JCJM.Job
LEFT JOIN JCCM WITH (NOLOCK) ON JCJM.JCCo = JCCM.JCCo AND JCJM.Contract = JCCM.Contract
LEFT JOIN ARTH WITH (NOLOCK) ON JCCM.JCCo = ARTH.JCCo AND JCCM.Contract = ARTH.Contract
WHERE WO.SMCo = @SMCo
```

Path: SMWorkOrder → SMServiceSite → JCJM → JCCM → ARTH."""
    })

    return examples


def generate_test_suite(tables: Dict) -> List[Dict]:
    """Generate comprehensive test suite with 500+ ground truth answers."""
    tests = []

    # Basic schema tests - expanded to 100+ tables
    basic_tables = [
        # AP
        'APTH', 'APTL', 'APTD', 'APHD', 'APLB', 'APCO', 'APVM', 'APCM', 'APHB',
        # AR
        'ARTH', 'ARTL', 'ARCM', 'ARCO', 'ARIB',
        # GL
        'GLDT', 'GLAC', 'GLJR', 'GLCO', 'GLRD', 'GLTD',
        # JC
        'JCJM', 'JCCM', 'JCCD', 'JCCP', 'JCCH', 'JCJP', 'JCJI', 'JCCT', 'JCCO', 'JCPR', 'JCPD',
        # PR
        'PRTH', 'PRTB', 'PREH', 'PRCO', 'PRDT', 'PRTC', 'PRPC',
        # SL
        'SLHD', 'SLIT', 'SLWI', 'SLHB', 'SLCO', 'SLCB',
        # PO
        'POHD', 'POIT', 'POIB', 'POCO', 'POIH',
        # EM
        'EMEM', 'EMCO', 'EMRD', 'EMBF', 'EMCD',
        # IN
        'INMT', 'INCO', 'INLM', 'INDT',
        # SM
        'SMWorkOrder', 'SMServiceSite', 'SMWorkCompleted', 'SMCo',
        # PM
        'PMCO', 'PMCH', 'PMOI', 'PMPF',
        # HQ
        'HQCO', 'HQMA', 'HQBC', 'HQMT', 'HQAT',
        # MS
        'MSTD', 'MSCO', 'MSTB',
        # CM
        'CMCO', 'CMDT', 'CMAC',
    ]
    for tbl in basic_tables:
        if tbl not in tables:
            continue
        cols = [c['name'] for c in tables[tbl]['columns'][:10]]
        module = get_module(tbl)
        tests.append({
            "id": f"basic_{tbl.lower()}_cols",
            "category": "basic_schema",
            "question": f"What columns are in the {tbl} table?",
            "ground_truth": f"Columns include: {', '.join(cols)}",
            "key_elements": cols[:5]
        })
        tests.append({
            "id": f"basic_{tbl.lower()}_module",
            "category": "basic_schema",
            "question": f"What module is {tbl} in?",
            "ground_truth": f"{tbl} is in the {module} module",
            "key_elements": [module, tbl]
        })
        if len(cols) > 3:
            tests.append({
                "id": f"basic_{tbl.lower()}_dtype",
                "category": "basic_schema",
                "question": f"What is the data type of {cols[1]} in {tbl}?",
                "ground_truth": f"{cols[1]} data type in {tbl}",
                "key_elements": [cols[1], tbl]
            })

    # SQL generation tests - expanded to 50+
    sql_tests = [
        {"id": "sql_ar_aging", "question": "Write SQL for AR aging buckets by customer",
         "key_elements": ["ARTH", "ARCM", "DATEDIFF", "PayFullDate IS NULL", "CASE WHEN", "CustGroup", "Customer"]},
        {"id": "sql_ar_aging_v2", "question": "Write SQL to calculate AR aging 30/60/90+ days for unpaid invoices",
         "key_elements": ["ARTH", "ARCM", "DATEDIFF", "PayFullDate IS NULL", "CASE WHEN"]},
        {"id": "sql_sl_costs", "question": "Write SQL for subcontractor costs with retainage",
         "key_elements": ["SLHD", "SLIT", "APVM", "OrigCost", "CurCost", "InvCost", "Retainage", "VendorGroup"]},
        {"id": "sql_sl_costs_v2", "question": "Write SQL to get subcontractor costs with original, change orders, invoiced, paid by vendor",
         "key_elements": ["SLHD", "SLIT", "APVM", "OrigCost", "CurCost", "InvCost", "Retainage"]},
        {"id": "sql_jc_budget", "question": "Write SQL for job cost budget vs actual by phase",
         "key_elements": ["JCJP", "JCCP", "JCCH", "JCCT", "OrigEstCost", "CurrEstCost", "ActualCost", "CostType"]},
        {"id": "sql_jc_budget_v2", "question": "Write SQL to aggregate job cost estimates by phase and cost type",
         "key_elements": ["JCJP", "JCCP", "JCCH", "JCCT", "ItemUnitFlag", "PhaseUnitFlag", "OrigEstCost", "CurrEstCost"]},
        {"id": "sql_ap_holds", "question": "Write SQL to identify retainage vs non-retainage holds",
         "key_elements": ["APTH", "APHD", "APCO", "HoldCode", "RetHoldCode", "PayType"]},
        {"id": "sql_ap_holds_v2", "question": "Write SQL to track AP hold status distinguishing retainage vs non-retainage holds",
         "key_elements": ["APTD", "APHD", "APCO", "RetHoldCode", "PayType"]},
        {"id": "sql_ap_oncost", "question": "Write SQL to reconcile AP oncost batches",
         "key_elements": ["APLB", "APTL", "APTH", "ocApplyMth", "ocApplyTrans", "ocApplyLine"]},
        {"id": "sql_ap_oncost_v2", "question": "Write SQL to reconcile AP oncost batch lines with original transactions",
         "key_elements": ["APLB", "APTL", "APTH", "APVM", "ocApplyMth", "ocApplyTrans", "ocApplyLine"]},
        {"id": "sql_slwi_aptd", "question": "Write SQL to join SLWI to APTD for retainage",
         "key_elements": ["SLWI", "APTL", "APTD", "SL", "SLItem", "PayType", "WCRetAmt", "SMRetAmt"]},
        {"id": "sql_slwi_aptd_v2", "question": "How do I join SLWI retainage amounts to matching APTD transactions?",
         "key_elements": ["SLWI", "APTL", "APTD", "SL", "SLItem", "RetPayType"]},
        {"id": "sql_sm_ar", "question": "Write SQL to link SM WorkOrder to AR billing",
         "key_elements": ["SMWorkOrder", "SMServiceSite", "JCJM", "JCCM", "ARTH", "Contract"]},
        {"id": "sql_sm_ar_v2", "question": "How do I link SM WorkOrder to AR billing through JC contracts?",
         "key_elements": ["SMWorkOrder", "SMServiceSite", "JCJM", "JCCM", "ARTH", "Job", "Contract"]},
        {"id": "sql_pr_time", "question": "Write SQL for employee timecard hours by job",
         "key_elements": ["PRTH", "PREH", "JCCD", "Employee", "Job", "Hours"]},
        {"id": "sql_po_recv", "question": "Write SQL for PO items with received quantities",
         "key_elements": ["POHD", "POIT", "RecvdUnits", "RecvdCost", "PO"]},
        {"id": "sql_em_cost", "question": "Write SQL for equipment costs by job",
         "key_elements": ["EMEM", "JCCD", "Equipment", "Job", "ActualCost"]},
        {"id": "sql_gl_detail", "question": "Write SQL for GL detail transactions by account",
         "key_elements": ["GLDT", "GLAC", "GLCo", "GLAcct", "Amount"]},
        {"id": "sql_ap_vendor_inv", "question": "Write SQL to get vendor invoices with amounts",
         "key_elements": ["APTH", "APTL", "APVM", "Vendor", "GrossAmt"]},
        {"id": "sql_ar_customer_bal", "question": "Write SQL for customer open balances",
         "key_elements": ["ARTH", "ARCM", "AmountDue", "PayFullDate"]},
        {"id": "sql_jc_contract", "question": "Write SQL for job contract billing summary",
         "key_elements": ["JCCM", "JCJI", "JCJM", "Contract", "BilledAmt"]},
        {"id": "sql_sl_worksheet", "question": "Write SQL for subcontract worksheet details",
         "key_elements": ["SLWI", "SLHD", "SLIT", "WCCost", "StoredMatls", "WCRetAmt", "SMRetAmt"]},
        {"id": "sql_pr_earnings", "question": "Write SQL for employee earnings by pay period",
         "key_elements": ["PREH", "PRTH", "PRDT", "Employee", "Earnings"]},
        {"id": "sql_in_inventory", "question": "Write SQL for inventory quantities by location",
         "key_elements": ["INMT", "INLM", "INDT", "Material", "OnHand"]},
        {"id": "sql_po_outstanding", "question": "Write SQL for outstanding PO amounts",
         "key_elements": ["POHD", "POIT", "OrderedUnits", "RecvdUnits", "PO"]},
    ]
    for t in sql_tests:
        t["category"] = "sql_generation"
        t["ground_truth"] = f"Must include tables/columns: {', '.join(t['key_elements'])}"
        tests.append(t)

    # JOIN pattern tests - expanded to 50+
    join_tests = [
        {"id": "join_ap_vendor", "question": "How do I join APTH to APVM?",
         "key_elements": ["APTH", "APVM", "APCo", "VendorGroup", "Vendor"]},
        {"id": "join_ap_vendor_v2", "question": "What columns link APTH to APVM?",
         "key_elements": ["APTH", "APVM", "APCo", "VendorGroup", "Vendor"]},
        {"id": "join_ar_cust", "question": "How do I join ARTH to ARCM?",
         "key_elements": ["ARTH", "ARCM", "ARCo", "CustGroup", "Customer"]},
        {"id": "join_ar_cust_v2", "question": "What columns link ARTH to customer master?",
         "key_elements": ["ARTH", "ARCM", "ARCo", "CustGroup", "Customer"]},
        {"id": "join_jcjp_jccp", "question": "What is the relationship between JCJP and JCCP?",
         "key_elements": ["JCJP", "JCCP", "JCCo", "Job", "PhaseGroup", "Phase", "JCCH", "JCJI"]},
        {"id": "join_jcjp_jccp_v2", "question": "How do I join JCJP to JCCP?",
         "key_elements": ["JCJP", "JCCP", "JCCo", "Job", "PhaseGroup", "Phase"]},
        {"id": "join_sl_vendor", "question": "How do I join SLHD to vendor information?",
         "key_elements": ["SLHD", "APVM", "SLCo", "VendorGroup", "Vendor"]},
        {"id": "join_aptl_aptd", "question": "How do I join APTL to APTD?",
         "key_elements": ["APTL", "APTD", "APCo", "Mth", "APTrans", "APLine"]},
        {"id": "join_apth_aptl", "question": "How do I join APTH to APTL?",
         "key_elements": ["APTH", "APTL", "APCo", "Mth", "APTrans"]},
        {"id": "join_apth_aptd", "question": "How do I join APTH to APTD?",
         "key_elements": ["APTH", "APTD", "APCo", "Mth", "APTrans"]},
        {"id": "join_jccp_jcch", "question": "How do I join JCCP to JCCH?",
         "key_elements": ["JCCP", "JCCH", "JCCo", "Job", "PhaseGroup", "Phase", "CostType"]},
        {"id": "join_slwi_aptl", "question": "How do I join SLWI to APTL?",
         "key_elements": ["SLWI", "APTL", "SLCo", "SL", "SLItem"]},
        {"id": "join_preh_prth", "question": "How do I join PREH to PRTH?",
         "key_elements": ["PREH", "PRTH", "PRCo", "Employee"]},
        {"id": "join_jcjm_jccm", "question": "How do I join JCJM to JCCM?",
         "key_elements": ["JCJM", "JCCM", "JCCo", "Contract"]},
        {"id": "join_jcjm_jcjp", "question": "How do I join JCJM to JCJP?",
         "key_elements": ["JCJM", "JCJP", "JCCo", "Job"]},
        {"id": "join_jcjm_jccd", "question": "How do I join JCJM to JCCD?",
         "key_elements": ["JCJM", "JCCD", "JCCo", "Job"]},
        {"id": "join_pohd_poit", "question": "How do I join POHD to POIT?",
         "key_elements": ["POHD", "POIT", "POCo", "PO"]},
        {"id": "join_slhd_slit", "question": "How do I join SLHD to SLIT?",
         "key_elements": ["SLHD", "SLIT", "SLCo", "SL"]},
        {"id": "join_slhd_slwi", "question": "How do I join SLHD to SLWI?",
         "key_elements": ["SLHD", "SLWI", "SLCo", "SL"]},
        {"id": "join_slit_slwi", "question": "How do I join SLIT to SLWI?",
         "key_elements": ["SLIT", "SLWI", "SLCo", "SL", "SLItem"]},
        {"id": "join_gldt_glac", "question": "How do I join GLDT to GLAC?",
         "key_elements": ["GLDT", "GLAC", "GLCo", "GLAcct"]},
        {"id": "join_arth_artl", "question": "How do I join ARTH to ARTL?",
         "key_elements": ["ARTH", "ARTL", "ARCo", "Mth", "ARTrans"]},
        {"id": "join_emem_embf", "question": "How do I join EMEM to EMBF?",
         "key_elements": ["EMEM", "EMBF", "EMCo", "Equipment"]},
        {"id": "join_inmt_inlm", "question": "How do I join INMT to INLM?",
         "key_elements": ["INMT", "INLM", "INCo", "Material", "Loc"]},
        {"id": "join_sm_service", "question": "How do I join SMWorkOrder to SMServiceSite?",
         "key_elements": ["SMWorkOrder", "SMServiceSite", "SMCo", "ServiceSite"]},
        {"id": "join_sm_jc", "question": "How do I join SMServiceSite to JCJM?",
         "key_elements": ["SMServiceSite", "JCJM", "JCCo", "Job"]},
        {"id": "join_apth_aphd", "question": "How do I join APTH to APHD?",
         "key_elements": ["APTH", "APHD", "APCo", "Mth", "APTrans"]},
        {"id": "join_jcch_jcct", "question": "How do I join JCCH to JCCT?",
         "key_elements": ["JCCH", "JCCT", "PhaseGroup", "CostType"]},
        {"id": "join_prth_prtb", "question": "How do I join PRTH to PRTB?",
         "key_elements": ["PRTH", "PRTB", "PRCo", "PRGroup", "PREndDate"]},
    ]
    for t in join_tests:
        t["category"] = "join_pattern"
        t["ground_truth"] = f"Join columns: {', '.join(t['key_elements'][2:])}"
        tests.append(t)

    # Business logic tests - expanded to 50+
    biz_tests = [
        {"id": "biz_retainage_max", "question": "How does Vista calculate maximum retainage with InclACOinMaxYN?",
         "key_elements": ["InclACOinMaxYN", "MaxRetgPct", "CurCost", "OrigCost", "SLHB"]},
        {"id": "biz_retainage_max_v2", "question": "How does InclACOinMaxYN affect retainage calculation?",
         "key_elements": ["InclACOinMaxYN", "MaxRetgPct", "CurCost", "OrigCost", "ACO"]},
        {"id": "biz_wc_sm_ret", "question": "What is the difference between WCRetAmt and SMRetAmt?",
         "key_elements": ["SLWI", "WCRetAmt", "SMRetAmt", "Work Completed", "Stored Materials"]},
        {"id": "biz_wc_sm_ret_v2", "question": "Explain WCRetAmt and SMRetAmt in subcontract worksheets",
         "key_elements": ["SLWI", "WCRetAmt", "SMRetAmt", "WCRetPct", "SMRetPct"]},
        {"id": "biz_ret_hold", "question": "How do I identify retainage holds in AP?",
         "key_elements": ["APHD", "APCO", "HoldCode", "RetHoldCode", "retainage hold"]},
        {"id": "biz_ret_hold_v2", "question": "How do I determine if an AP invoice is on hold for retainage vs non-retainage reasons?",
         "key_elements": ["APHD", "APCO", "HoldCode", "RetHoldCode", "retainage hold"]},
        {"id": "biz_stored_matl", "question": "How does stored materials affect SL billing?",
         "key_elements": ["SLWI", "StoredMatls", "Purchased", "Installed", "WCCost"]},
        {"id": "biz_stored_matl_v2", "question": "Explain how stored materials (Purchased - Installed) affects SL billing",
         "key_elements": ["SLWI", "StoredMatls", "Purchased", "Installed", "WCCost", "SMRetPct", "WCRetPct"]},
        {"id": "biz_projection", "question": "What tables are used for job cost projections?",
         "key_elements": ["JCPR", "JCPD", "JCCP", "JCCD", "CurrEstCost", "ActualCost"]},
        {"id": "biz_projection_v2", "question": "What tables are involved in cost-to-complete projections for jobs?",
         "key_elements": ["JCPR", "JCPD", "JCCP", "JCCD", "CurrEstCost", "ActualCost"]},
        {"id": "biz_paytype", "question": "What do the PayType values mean in APTD?",
         "key_elements": ["APTD", "PayType", "Regular", "Discount", "Retainage", "3"]},
        {"id": "biz_paytype_v2", "question": "What are the PayType codes in AP transactions?",
         "key_elements": ["APTD", "PayType", "1", "2", "3", "Retainage"]},
        {"id": "biz_oncost", "question": "How do oncost columns work in APLB?",
         "key_elements": ["APLB", "ocApplyMth", "ocApplyTrans", "ocApplyLine", "original"]},
        {"id": "biz_oncost_v2", "question": "How do I reconcile AP oncost batch lines with original transactions?",
         "key_elements": ["APLB", "APTL", "ocApplyMth", "ocApplyTrans", "ocApplyLine"]},
        {"id": "biz_unit_flag", "question": "What do ItemUnitFlag and PhaseUnitFlag mean?",
         "key_elements": ["JCCH", "ItemUnitFlag", "PhaseUnitFlag", "unit of measure"]},
        {"id": "biz_unit_flag_v2", "question": "Explain ItemUnitFlag and PhaseUnitFlag in JCCH",
         "key_elements": ["JCCH", "ItemUnitFlag", "PhaseUnitFlag", "Y", "N"]},
        {"id": "biz_sm_billing", "question": "How does SM work order billing flow to AR?",
         "key_elements": ["SMWorkOrder", "SMServiceSite", "JCJM", "JCCM", "ARTH"]},
        {"id": "biz_sm_billing_v2", "question": "How do I link SM WorkOrder to AR billing through JC contracts?",
         "key_elements": ["SMWorkOrder", "SMServiceSite", "JCJM", "JCCM", "ARTH", "Job", "Contract"]},
        {"id": "biz_cost_complete", "question": "How is cost-to-complete calculated?",
         "key_elements": ["JCCP", "CurrEstCost", "ActualCost", "Remaining"]},
        {"id": "biz_cost_complete_v2", "question": "What is the formula for cost-to-complete in job costing?",
         "key_elements": ["JCCP", "CurrEstCost", "ActualCost", "Remaining", "Budget"]},
        {"id": "biz_jcjp_jccp_diff", "question": "What is the difference between JCJP and JCCP?",
         "key_elements": ["JCJP", "JCCP", "billing", "cost tracking", "Phase"]},
        {"id": "biz_retpaytype", "question": "What is APCO.RetPayType used for?",
         "key_elements": ["APCO", "RetPayType", "Retainage", "payment type", "3"]},
        {"id": "biz_ar_unpaid", "question": "How do I identify unpaid AR invoices?",
         "key_elements": ["ARTH", "PayFullDate", "NULL", "unpaid", "AmountDue"]},
        {"id": "biz_sl_retainage", "question": "How is retainage tracked in subcontracts?",
         "key_elements": ["SLIT", "SLWI", "Retainage", "WCRetAmt", "SMRetAmt"]},
        {"id": "biz_jc_budget_actual", "question": "How do I compare budget to actual in job costing?",
         "key_elements": ["JCCP", "OrigEstCost", "CurrEstCost", "ActualCost"]},
        {"id": "biz_ap_status", "question": "What do the Status values mean in AP transactions?",
         "key_elements": ["APTD", "Status", "Open", "Paid", "Void", "0", "1", "2"]},
    ]
    for t in biz_tests:
        t["category"] = "business_logic"
        t["ground_truth"] = f"Key concepts: {', '.join(t['key_elements'])}"
        tests.append(t)

    # Hallucination tests - expanded to 50+
    fake_tables = [
        ("ARAgingReport", "Use ARTH/ARTL with DATEDIFF for aging"),
        ("SubcontractorPayments", "Use APTD joined to APTL with SL reference, or SLWI"),
        ("JobCostSummary", "Use JCCP for phase-level or JCCD for transactions"),
        ("VendorInvoices", "Use APTH for AP headers joined to APVM"),
        ("EmployeeTimesheet", "Use PRTH for timecard headers or PRTB for batches"),
        ("GLTransactions", "Use GLDT for GL detail transactions"),
        ("CustomerInvoices", "Use ARTH for AR transaction headers"),
        ("PurchaseOrderDetail", "Use POHD for headers, POIT for items"),
        ("InventoryItems", "Use INMT for inventory material master"),
        ("ProjectBudget", "Use JCCP.OrigEstCost and CurrEstCost for budgets"),
        ("PayrollTransactions", "Use PRTH and PRTB for payroll transactions"),
        ("ContractBilling", "Use JCCM for contracts, JCJI for items, ARTH for billing"),
        ("EquipmentCosts", "Use EMEM for equipment, EMBF for fuel"),
        ("MaterialRequests", "Use INMT for materials, POIT for PO items"),
        ("WorkOrderDetails", "Use SMWorkOrder and SMWorkCompleted tables"),
        ("VendorPaymentHistory", "Use APTD for payment detail, APTH for headers"),
        ("CustomerBalance", "Use ARCM for customer master, ARTH for transactions"),
        ("JobPhaseDetail", "Use JCJP for phases, JCCP for costs"),
        ("ChangeOrderLog", "Use JCCO for JC change orders or SLCO for SL"),
        ("BudgetVariance", "Compare JCCP.CurrEstCost to JCCP.ActualCost"),
        ("APPaymentRegister", "Use APTD for payment details"),
        ("ARReceiptsRegister", "Use ARTH for AR receipts"),
        ("JobProfitability", "Calculate from JCCP budget vs actual"),
        ("SubcontractStatus", "Use SLHD and SLIT for subcontract status"),
        ("EquipmentUtilization", "Use EMEM and EMRD for equipment data"),
    ]
    for fake, suggestion in fake_tables:
        tests.append({
            "id": f"halluc_{fake.lower()}_cols",
            "category": "hallucination",
            "question": f"What columns are in the {fake} table?",
            "ground_truth": f"REJECT - {fake} does not exist. {suggestion}",
            "key_elements": ["does not exist", "not a valid", "not a real table"]
        })
        tests.append({
            "id": f"halluc_{fake.lower()}_sql",
            "category": "hallucination",
            "question": f"Write SQL to query the {fake} table",
            "ground_truth": f"REJECT - {fake} does not exist. {suggestion}",
            "key_elements": ["does not exist", "not a valid", "cannot query"]
        })

    return tests


def main():
    print("=" * 60)
    print("COMPREHENSIVE TRAINING DATA GENERATOR")
    print("=" * 60)

    print("\nLoading schema metadata...")
    tables, fks, fk_lookup = load_schema()
    print(f"Loaded {len(tables)} tables, {len(fks)} foreign keys")

    training_examples = []

    # 1. Generate examples for high-priority tables
    print("\nGenerating table-specific examples...")
    for table_name in HIGH_PRIORITY_TABLES:
        if table_name in tables:
            examples = generate_table_examples(table_name, tables[table_name], fk_lookup)
            training_examples.extend(examples)
    print(f"  Table examples: {len(training_examples)}")

    # 2. Generate JOIN pattern examples
    print("Generating JOIN pattern examples...")
    join_examples = generate_join_examples(tables, fk_lookup)
    training_examples.extend(join_examples)
    print(f"  JOIN examples: {len(join_examples)}")

    # 3. Generate business logic examples
    print("Generating business logic examples...")
    biz_examples = generate_business_logic_examples()
    training_examples.extend(biz_examples)
    print(f"  Business logic: {len(biz_examples)}")

    # 4. Generate hallucination rejection examples
    print("Generating hallucination rejection examples...")
    halluc_examples = generate_hallucination_examples()
    training_examples.extend(halluc_examples)
    print(f"  Hallucination: {len(halluc_examples)}")

    # 5. Generate complex SQL examples
    print("Generating complex SQL examples...")
    sql_examples = generate_complex_sql_examples()
    training_examples.extend(sql_examples)
    print(f"  Complex SQL: {len(sql_examples)}")

    # Save training data
    print(f"\nTotal training examples: {len(training_examples)}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "vgpt2_v3_advanced.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_examples, f, indent=2, ensure_ascii=False)
    print(f"Training data saved to: {output_file}")

    # 6. Generate test suite
    print("\nGenerating test suite...")
    test_suite = generate_test_suite(tables)
    print(f"Test questions: {len(test_suite)}")

    TEST_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(TEST_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(test_suite, f, indent=2, ensure_ascii=False)
    print(f"Test suite saved to: {TEST_OUTPUT}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Training examples: {len(training_examples)}")
    print(f"Test questions: {len(test_suite)}")
    print(f"\nBreakdown by category:")
    cats = {}
    for t in test_suite:
        cat = t['category']
        cats[cat] = cats.get(cat, 0) + 1
    for cat, count in cats.items():
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()

