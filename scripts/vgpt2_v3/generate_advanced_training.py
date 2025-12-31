#!/usr/bin/env python3
"""
Generate advanced training data targeting the gaps identified in the audit.

Generates:
1. Complex SQL examples with multi-table JOINs
2. JOIN pattern examples with proper relationships
3. Business logic explanations
4. Column semantic meaning
5. Hallucination rejection examples
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Any

# Paths
SCHEMA_PATH = Path("C:/Github/VGPT2/Viewpoint_Database/_MetadataV2/_data")
OUTPUT_PATH = Path("data/vgpt2_v3_advanced.json")

# Load schema data
def load_schema():
    """Load all schema metadata."""
    columns_file = SCHEMA_PATH / "columns.json"
    fks_file = SCHEMA_PATH / "foreign_keys.json"
    
    with open(columns_file, 'r', encoding='utf-8') as f:
        columns = json.load(f)
    
    fks = []
    if fks_file.exists():
        with open(fks_file, 'r', encoding='utf-8') as f:
            fks = json.load(f)
    
    # Build table -> columns map
    tables = {}
    for col in columns:
        table = col.get('ObjectName', '')
        if table not in tables:
            tables[table] = {'columns': [], 'module': col.get('Module', 'Other')}
        tables[table]['columns'].append(col)
    
    return tables, fks

# Critical business knowledge that's missing from training
BUSINESS_KNOWLEDGE = {
    "SLWI": {
        "description": "Subcontract Work Item (worksheet line items for SL billing)",
        "key_columns": {
            "WCRetAmt": "Work Completed Retainage - retainage held on labor/work in place",
            "SMRetAmt": "Stored Materials Retainage - retainage held on materials on-site but not installed",
            "WCCost": "Work Completed Cost - billable labor and installed work",
            "StoredMatls": "Stored Materials amount (Purchased - Installed)",
            "WCRetPct": "Work Completed Retainage Percentage",
            "SMRetPct": "Stored Materials Retainage Percentage",
        },
        "relationships": ["SLHD (header)", "SLIT (item)", "APTD (AP payment)"],
    },
    "APTD": {
        "description": "AP Transaction Detail - individual payment line items",
        "key_columns": {
            "PayType": "Payment type: 1=Regular, 2=Discount, 3=Retainage",
            "Amount": "Payment amount for this line",
            "Status": "0=Open, 1=Paid, 2=Void",
        },
        "relationships": ["APTH (header)", "APTL (line)", "APHD (hold detail)"],
    },
    "APHD": {
        "description": "AP Hold Detail - tracks holds on AP transactions",
        "key_columns": {
            "HoldCode": "Hold reason code - compare to APCO.RetHoldCode for retainage",
        },
        "relationships": ["APTH (header)", "APCO (company settings)"],
    },
    "JCJP": {
        "description": "JC Job Phase - phases within a job for billing/tracking",
        "key_columns": {
            "Phase": "Phase code within the job",
            "PhaseGroup": "Phase group for organizing phases",
            "Contract": "Linked contract number",
            "Item": "Contract item this phase bills to",
        },
        "relationships": ["JCJM (job)", "JCCP (cost phase)", "JCJI (job item)", "JCCM (contract)"],
    },
    "JCCP": {
        "description": "JC Cost Phase - cost tracking at phase level",
        "key_columns": {
            "OrigEstCost": "Original estimated cost",
            "CurrEstCost": "Current estimated cost (with changes)",
            "ActualCost": "Actual costs posted",
            "OrigEstHours": "Original estimated hours",
            "CurrEstHours": "Current estimated hours",
            "ActualHours": "Actual hours posted",
        },
        "relationships": ["JCJP (job phase)", "JCCH (cost header)", "JCCD (cost detail)"],
    },
    "JCCH": {
        "description": "JC Cost Header - cost type setup per job/phase",
        "key_columns": {
            "ItemUnitFlag": "Y=use item units, N=use phase units for UM",
            "PhaseUnitFlag": "Y=use phase units for posting",
            "CostType": "Cost type code (1=Labor, 2=Material, etc.)",
        },
        "relationships": ["JCCP (cost phase)", "JCCT (cost type master)", "JCCD (cost detail)"],
    },
    "APCO": {
        "description": "AP Company - company-level AP settings",
        "key_columns": {
            "RetHoldCode": "Default hold code for retainage - use to identify retainage holds",
            "RetPayType": "Retainage payment type (typically 3)",
        },
        "relationships": ["APTD (trans detail)", "APHD (hold detail)"],
    },
}

# JOIN patterns that should be taught
JOIN_PATTERNS = [
    {
        "tables": ["SLHD", "SLIT", "APVM"],
        "join_sql": """SELECT SLHD.SLCo, SLHD.SL, SLHD.Vendor, APVM.Name AS VendorName,
  SLIT.SLItem, SLIT.Description, SLIT.OrigCost, SLIT.CurCost, SLIT.InvCost
FROM SLHD WITH (NOLOCK)
INNER JOIN SLIT WITH (NOLOCK) ON SLHD.SLCo = SLIT.SLCo AND SLHD.SL = SLIT.SL
INNER JOIN APVM WITH (NOLOCK) ON SLHD.SLCo = APVM.APCo AND SLHD.VendorGroup = APVM.VendorGroup AND SLHD.Vendor = APVM.Vendor
WHERE SLHD.SLCo = @SLCo""",
        "description": "Join SL Header to Items and Vendor Master for subcontract details with vendor names",
        "key_columns": ["SLCo", "SL", "VendorGroup", "Vendor", "SLItem"],
    },
    {
        "tables": ["SLWI", "APTL", "APTD"],
        "join_sql": """SELECT SLWI.SLCo, SLWI.SL, SLWI.SLItem, SLWI.WCRetAmt, SLWI.SMRetAmt,
  APTD.APTrans, APTD.PayType, APTD.Amount, APTD.Status
FROM SLWI WITH (NOLOCK)
INNER JOIN APTL WITH (NOLOCK) ON SLWI.SLCo = APTL.APCo AND SLWI.SL = APTL.SL AND SLWI.SLItem = APTL.SLItem
INNER JOIN APTD WITH (NOLOCK) ON APTL.APCo = APTD.APCo AND APTL.Mth = APTD.Mth AND APTL.APTrans = APTD.APTrans AND APTL.APLine = APTD.APLine
WHERE SLWI.SLCo = @SLCo AND APTD.PayType = 3  -- Retainage payments only""",
        "description": "Join SLWI worksheet items to AP payment details for retainage tracking",
        "key_columns": ["SLCo", "SL", "SLItem", "APCo", "Mth", "APTrans", "APLine", "PayType"],
    },
    {
        "tables": ["JCJP", "JCCP", "JCCH"],
        "join_sql": """SELECT JCJP.JCCo, JCJP.Job, JCJP.Phase, JCJP.Description AS PhaseDesc,
  JCCP.CostType, JCCP.OrigEstCost, JCCP.CurrEstCost, JCCP.ActualCost,
  JCCH.ItemUnitFlag, JCCH.PhaseUnitFlag
FROM JCJP WITH (NOLOCK)
INNER JOIN JCCP WITH (NOLOCK) ON JCJP.JCCo = JCCP.JCCo AND JCJP.Job = JCCP.Job AND JCJP.PhaseGroup = JCCP.PhaseGroup AND JCJP.Phase = JCCP.Phase
INNER JOIN JCCH WITH (NOLOCK) ON JCCP.JCCo = JCCH.JCCo AND JCCP.Job = JCCH.Job AND JCCP.PhaseGroup = JCCH.PhaseGroup AND JCCP.Phase = JCCH.Phase AND JCCP.CostType = JCCH.CostType
WHERE JCJP.JCCo = @JCCo AND JCJP.Job = @Job""",
        "description": "Join Job Phase to Cost Phase and Cost Header for budget vs actual analysis",
        "key_columns": ["JCCo", "Job", "PhaseGroup", "Phase", "CostType"],
    },
    {
        "tables": ["APTH", "APHD", "APCO"],
        "join_sql": """SELECT APTH.APCo, APTH.Mth, APTH.APTrans, APTH.Vendor, APTH.APRef,
  APHD.HoldCode, 
  CASE WHEN APHD.HoldCode = APCO.RetHoldCode THEN 'Retainage Hold' ELSE 'Non-Retainage Hold' END AS HoldType
FROM APTH WITH (NOLOCK)
INNER JOIN APHD WITH (NOLOCK) ON APTH.APCo = APHD.APCo AND APTH.Mth = APHD.Mth AND APTH.APTrans = APHD.APTrans
INNER JOIN APCO WITH (NOLOCK) ON APTH.APCo = APCO.APCo
WHERE APTH.APCo = @APCo AND APHD.HoldCode IS NOT NULL""",
        "description": "Join AP Trans Header to Hold Detail and Company to distinguish retainage vs non-retainage holds",
        "key_columns": ["APCo", "Mth", "APTrans", "HoldCode", "RetHoldCode"],
    },
]

# Fake tables for hallucination training
FAKE_TABLES = [
    ("ARAgingReport", "Use ARTH/ARTL with DATEDIFF for aging, or VPShared_CustomerAging view"),
    ("SubcontractorPayments", "Use APTD joined to APTL with SL reference, or SLWI for worksheet tracking"),
    ("JobCostSummary", "Use JCCP for phase-level summaries or JCCD for transaction detail"),
    ("VendorInvoices", "Use APTH for AP transaction headers, joined to APVM for vendor info"),
    ("EmployeeTimesheet", "Use PRTH for PR timecard headers or PRTB for timecard batches"),
    ("GLTransactions", "Use GLDT for GL detail transactions"),
    ("CustomerInvoices", "Use ARTH for AR transaction headers"),
    ("PurchaseOrders", "Use POHD for PO headers, POIT for PO items"),
    ("InventoryItems", "Use INMT for inventory material master"),
    ("ProjectBudget", "Use JCCP for job cost phase budgets (OrigEstCost, CurrEstCost)"),
]

def main():
    print("Loading schema...")
    tables, fks = load_schema()
    print(f"Loaded {len(tables)} tables")
    
    training_examples = []
    
    # 1. Generate business logic explanations
    print("\nGenerating business logic examples...")
    for table, info in BUSINESS_KNOWLEDGE.items():
        # Table description
        training_examples.append({
            "instruction": f"What is the purpose of the {table} table in Viewpoint Vista?",
            "input": "",
            "output": f"{table} - {info['description']}. Key relationships: {', '.join(info['relationships'])}."
        })

        # Column semantic meanings
        for col, meaning in info['key_columns'].items():
            training_examples.append({
                "instruction": f"What does the {col} column mean in {table}?",
                "input": "",
                "output": f"In {table}, {col} represents: {meaning}"
            })
            training_examples.append({
                "instruction": f"Explain the {col} field in {table}",
                "input": "",
                "output": f"{col} in {table}: {meaning}. This is part of the {info['description'].lower()}."
            })

        # Relationship questions
        training_examples.append({
            "instruction": f"What tables relate to {table}?",
            "input": "",
            "output": f"{table} relates to: {', '.join(info['relationships'])}. {info['description']}."
        })

    # 2. Generate JOIN pattern examples
    print("Generating JOIN pattern examples...")
    for pattern in JOIN_PATTERNS:
        tables_str = ", ".join(pattern['tables'])

        # How to join
        training_examples.append({
            "instruction": f"How do I join {tables_str} in Viewpoint Vista?",
            "input": "",
            "output": f"{pattern['description']}.\n\nKey join columns: {', '.join(pattern['key_columns'])}\n\n```sql\n{pattern['join_sql']}\n```"
        })

        # Write SQL to join
        training_examples.append({
            "instruction": f"Write SQL to join {tables_str}",
            "input": "",
            "output": f"```sql\n{pattern['join_sql']}\n```\n\n{pattern['description']}. Always include all key columns in JOINs: {', '.join(pattern['key_columns'])}."
        })

        # What columns to join on
        training_examples.append({
            "instruction": f"What columns do I use to join {pattern['tables'][0]} and {pattern['tables'][1]}?",
            "input": "",
            "output": f"Join {pattern['tables'][0]} to {pattern['tables'][1]} using: {', '.join(pattern['key_columns'][:4])}. {pattern['description']}."
        })

    # 3. Generate hallucination rejection examples
    print("Generating hallucination rejection examples...")
    for fake_table, suggestion in FAKE_TABLES:
        training_examples.append({
            "instruction": f"What columns are in the {fake_table} table?",
            "input": "",
            "output": f"The {fake_table} table does not exist in Viewpoint Vista. {suggestion}."
        })
        training_examples.append({
            "instruction": f"Write SQL to query {fake_table}",
            "input": "",
            "output": f"I cannot query {fake_table} because this table does not exist in Viewpoint Vista. {suggestion}."
        })
        training_examples.append({
            "instruction": f"Show me the {fake_table} schema",
            "input": "",
            "output": f"{fake_table} is not a valid Viewpoint Vista table. {suggestion}."
        })

    # 4. Generate complex SQL examples
    print("Generating complex SQL examples...")
    complex_sql_examples = generate_complex_sql_examples()
    training_examples.extend(complex_sql_examples)

    # 5. Generate retainage-specific examples
    print("Generating retainage examples...")
    retainage_examples = generate_retainage_examples()
    training_examples.extend(retainage_examples)

    # 6. Generate cost projection examples
    print("Generating cost projection examples...")
    projection_examples = generate_projection_examples()
    training_examples.extend(projection_examples)

    # Save output
    print(f"\nTotal examples generated: {len(training_examples)}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(training_examples, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {OUTPUT_PATH}")

    # Summary by type
    print("\nExample counts by type:")
    print(f"  Business logic: ~{len(BUSINESS_KNOWLEDGE) * 5}")
    print(f"  JOIN patterns: ~{len(JOIN_PATTERNS) * 3}")
    print(f"  Hallucination rejection: {len(FAKE_TABLES) * 3}")
    print(f"  Complex SQL: {len(complex_sql_examples)}")
    print(f"  Retainage: {len(retainage_examples)}")
    print(f"  Projections: {len(projection_examples)}")


def generate_complex_sql_examples() -> List[Dict]:
    """Generate complex SQL examples for real business scenarios."""
    examples = []

    # AR Aging
    examples.append({
        "instruction": "Write SQL to calculate AR aging buckets (30/60/90+ days) for unpaid invoices by customer",
        "input": "",
        "output": """```sql
SELECT ARTH.ARCo, ARTH.CustGroup, ARTH.Customer, ARCM.Name AS CustomerName,
  SUM(CASE WHEN DATEDIFF(day, ARTH.InvDate, GETDATE()) <= 30 THEN ARTH.AmountDue ELSE 0 END) AS Current_0_30,
  SUM(CASE WHEN DATEDIFF(day, ARTH.InvDate, GETDATE()) BETWEEN 31 AND 60 THEN ARTH.AmountDue ELSE 0 END) AS Days_31_60,
  SUM(CASE WHEN DATEDIFF(day, ARTH.InvDate, GETDATE()) BETWEEN 61 AND 90 THEN ARTH.AmountDue ELSE 0 END) AS Days_61_90,
  SUM(CASE WHEN DATEDIFF(day, ARTH.InvDate, GETDATE()) > 90 THEN ARTH.AmountDue ELSE 0 END) AS Over_90
FROM ARTH WITH (NOLOCK)
INNER JOIN ARCM WITH (NOLOCK) ON ARTH.ARCo = ARCM.ARCo AND ARTH.CustGroup = ARCM.CustGroup AND ARTH.Customer = ARCM.Customer
WHERE ARTH.ARCo = @ARCo AND ARTH.PayFullDate IS NULL  -- Unpaid invoices only
GROUP BY ARTH.ARCo, ARTH.CustGroup, ARTH.Customer, ARCM.Name
ORDER BY ARCM.Name
```

Key points:
- ARTH (AR Transaction Header) contains invoice data
- ARCM (AR Customer Master) has customer names
- PayFullDate IS NULL filters to unpaid invoices only
- CASE WHEN creates the aging buckets
- Always join on ARCo, CustGroup, Customer"""
    })

    # SL Cost Summary
    examples.append({
        "instruction": "Write SQL to get subcontractor costs with original, change orders, invoiced, and retainage by vendor",
        "input": "",
        "output": """```sql
SELECT SLHD.SLCo, SLHD.VendorGroup, SLHD.Vendor, APVM.Name AS VendorName,
  SUM(SLIT.OrigCost) AS OriginalCost,
  SUM(SLIT.CurCost - SLIT.OrigCost) AS ChangeOrders,
  SUM(SLIT.CurCost) AS CurrentCost,
  SUM(SLIT.InvCost) AS InvoicedCost,
  SUM(SLIT.InvCost - SLIT.PaidAmt) AS OutstandingAP,
  SUM(SLIT.Retainage) AS RetainageHeld
FROM SLHD WITH (NOLOCK)
INNER JOIN SLIT WITH (NOLOCK) ON SLHD.SLCo = SLIT.SLCo AND SLHD.SL = SLIT.SL
INNER JOIN APVM WITH (NOLOCK) ON SLHD.SLCo = APVM.APCo AND SLHD.VendorGroup = APVM.VendorGroup AND SLHD.Vendor = APVM.Vendor
WHERE SLHD.SLCo = @SLCo
GROUP BY SLHD.SLCo, SLHD.VendorGroup, SLHD.Vendor, APVM.Name
ORDER BY APVM.Name
```

Key columns:
- OrigCost: Original subcontract amount
- CurCost: Current amount including change orders
- InvCost: Amount invoiced by vendor
- PaidAmt: Amount paid to vendor
- Retainage: Retainage held"""
    })

    # JC Budget vs Actual
    examples.append({
        "instruction": "Write SQL to aggregate job cost estimates by phase and cost type with budget vs actual comparison",
        "input": "",
        "output": """```sql
SELECT JCJP.JCCo, JCJP.Job, JCJP.PhaseGroup, JCJP.Phase, JCJP.Description AS PhaseDescription,
  JCCP.CostType, JCCT.Description AS CostTypeDescription,
  JCCP.OrigEstCost, JCCP.CurrEstCost, JCCP.ActualCost,
  JCCP.CurrEstCost - JCCP.ActualCost AS RemainingBudget,
  JCCP.OrigEstHours, JCCP.CurrEstHours, JCCP.ActualHours,
  JCCH.ItemUnitFlag, JCCH.PhaseUnitFlag
FROM JCJP WITH (NOLOCK)
INNER JOIN JCCP WITH (NOLOCK) ON JCJP.JCCo = JCCP.JCCo AND JCJP.Job = JCCP.Job
  AND JCJP.PhaseGroup = JCCP.PhaseGroup AND JCJP.Phase = JCCP.Phase
INNER JOIN JCCH WITH (NOLOCK) ON JCCP.JCCo = JCCH.JCCo AND JCCP.Job = JCCH.Job
  AND JCCP.PhaseGroup = JCCH.PhaseGroup AND JCCP.Phase = JCCH.Phase AND JCCP.CostType = JCCH.CostType
INNER JOIN JCCT WITH (NOLOCK) ON JCCH.PhaseGroup = JCCT.PhaseGroup AND JCCH.CostType = JCCT.CostType
WHERE JCJP.JCCo = @JCCo AND JCJP.Job = @Job
ORDER BY JCJP.Phase, JCCP.CostType
```

Key tables:
- JCJP: Job Phase - phase definitions
- JCCP: Cost Phase - budget/actual amounts per phase/cost type
- JCCH: Cost Header - unit flags and settings
- JCCT: Cost Type master - cost type descriptions
- ItemUnitFlag/PhaseUnitFlag determine which unit of measure to use"""
    })

    # AP Hold Status
    examples.append({
        "instruction": "Write SQL to track AP hold status distinguishing retainage vs non-retainage holds",
        "input": "",
        "output": """```sql
SELECT APTH.APCo, APTH.Mth, APTH.APTrans, APTH.Vendor, APVM.Name AS VendorName,
  APTH.APRef, APTH.InvDate, APTH.GrossAmt,
  APHD.HoldCode,
  CASE WHEN APHD.HoldCode = APCO.RetHoldCode THEN 'Retainage Hold'
       ELSE 'Non-Retainage Hold' END AS HoldType,
  APTD.PayType, APTD.Amount, APTD.Status
FROM APTH WITH (NOLOCK)
INNER JOIN APHD WITH (NOLOCK) ON APTH.APCo = APHD.APCo AND APTH.Mth = APHD.Mth AND APTH.APTrans = APHD.APTrans
INNER JOIN APCO WITH (NOLOCK) ON APTH.APCo = APCO.APCo
INNER JOIN APTD WITH (NOLOCK) ON APTH.APCo = APTD.APCo AND APTH.Mth = APTD.Mth AND APTH.APTrans = APTD.APTrans
INNER JOIN APVM WITH (NOLOCK) ON APTH.APCo = APVM.APCo AND APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor
WHERE APTH.APCo = @APCo AND APHD.HoldCode IS NOT NULL
ORDER BY APTH.Mth DESC, APTH.APTrans
```

Key logic:
- APHD.HoldCode contains the hold reason
- APCO.RetHoldCode is the company's retainage hold code
- When HoldCode = RetHoldCode, it's a retainage hold
- APTD.PayType: 1=Regular, 2=Discount, 3=Retainage"""
    })

    # AP Oncost Reconciliation
    examples.append({
        "instruction": "Write SQL to reconcile AP oncost batch lines with original transactions",
        "input": "",
        "output": """```sql
SELECT APLB.Co AS APCo, APLB.Mth, APLB.BatchId, APLB.BatchSeq, APLB.APLine,
  APLB.Amount AS OnCostAmount,
  APLB.ocApplyMth AS OriginalMth, APLB.ocApplyTrans AS OriginalTrans, APLB.ocApplyLine AS OriginalLine,
  APTL.Vendor, APTL.Description AS LineDescription,
  APTH.APRef AS OriginalInvoice, APTH.InvDate AS OriginalInvDate,
  APVM.Name AS VendorName
FROM APLB WITH (NOLOCK)
INNER JOIN APTL WITH (NOLOCK) ON APLB.Co = APTL.APCo AND APLB.ocApplyMth = APTL.Mth
  AND APLB.ocApplyTrans = APTL.APTrans AND APLB.ocApplyLine = APTL.APLine
INNER JOIN APTH WITH (NOLOCK) ON APTL.APCo = APTH.APCo AND APTL.Mth = APTH.Mth AND APTL.APTrans = APTH.APTrans
INNER JOIN APVM WITH (NOLOCK) ON APTH.APCo = APVM.APCo AND APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor
WHERE APLB.Co = @APCo AND APLB.Mth = @Mth AND APLB.BatchId = @BatchId
ORDER BY APLB.BatchSeq
```

Key oncost columns in APLB:
- ocApplyMth: Month of original transaction
- ocApplyTrans: Original transaction number
- ocApplyLine: Original line number
These link the oncost batch line back to the source AP transaction."""
    })

    return examples


def generate_retainage_examples() -> List[Dict]:
    """Generate retainage-specific training examples."""
    examples = []

    examples.append({
        "instruction": "How does Vista calculate maximum retainage when InclACOinMaxYN is set to Y?",
        "input": "",
        "output": """When InclACOinMaxYN = 'Y' in SLHB (SL Header Billing), Vista includes Approved Change Orders in the maximum retainage calculation:

MaxRetainage = MaxRetgPct * CurCost

When InclACOinMaxYN = 'N', it uses only the original cost:
MaxRetainage = MaxRetgPct * OrigCost

Key columns in SLHB:
- MaxRetgPct: Maximum retainage percentage
- InclACOinMaxYN: Include ACO in max calculation flag
- CurCost: Current cost including change orders
- OrigCost: Original subcontract cost

This is important for subcontracts where change orders increase the contract value and you want retainage calculated on the full current amount."""
    })

    examples.append({
        "instruction": "What is the difference between WCRetAmt and SMRetAmt in subcontract worksheets?",
        "input": "",
        "output": """In SLWI (Subcontract Work Item), there are two types of retainage:

**WCRetAmt** - Work Completed Retainage
- Retainage held on labor and installed work
- Calculated as: WCCost * WCRetPct
- Represents work that is in place and billable

**SMRetAmt** - Stored Materials Retainage
- Retainage held on materials stored on-site but not yet installed
- Calculated as: StoredMatls * SMRetPct
- StoredMatls = Purchased - Installed

**Total Retainage** = WCRetAmt + SMRetAmt

Different retainage rates may apply:
- WCRetPct: Work Completed retainage percentage
- SMRetPct: Stored Materials retainage percentage

This distinction allows for different retainage treatment of work vs materials."""
    })

    examples.append({
        "instruction": "How do I determine if an AP invoice is on hold for retainage vs non-retainage reasons?",
        "input": "",
        "output": """To distinguish retainage holds from other holds in AP:

1. Check APHD.HoldCode against APCO.RetHoldCode
2. If HoldCode = RetHoldCode → Retainage Hold
3. If HoldCode ≠ RetHoldCode → Non-Retainage Hold

```sql
SELECT APTH.APCo, APTH.APTrans, APTH.APRef,
  APHD.HoldCode,
  APCO.RetHoldCode,
  CASE WHEN APHD.HoldCode = APCO.RetHoldCode
       THEN 'Retainage Hold'
       ELSE 'Non-Retainage Hold' END AS HoldType
FROM APTH WITH (NOLOCK)
INNER JOIN APHD WITH (NOLOCK) ON APTH.APCo = APHD.APCo AND APTH.Mth = APHD.Mth AND APTH.APTrans = APHD.APTrans
INNER JOIN APCO WITH (NOLOCK) ON APTH.APCo = APCO.APCo
WHERE APTH.APCo = @APCo
```

Key tables:
- APHD: AP Hold Detail - contains the hold codes
- APCO: AP Company - contains RetHoldCode setting"""
    })

    examples.append({
        "instruction": "Explain how stored materials (Purchased - Installed) affects SL billing",
        "input": "",
        "output": """In SLWI (Subcontract Work Item), stored materials tracking affects billing:

**StoredMatls** = Purchased - Installed
- Materials delivered to site but not yet incorporated into work
- Billed separately from Work Completed (WCCost)

**Billing Impact:**
- Total Billable = WCCost + StoredMatls
- WCCost: Work in place (labor + installed materials)
- StoredMatls: Materials on-site awaiting installation

**Retainage Treatment:**
- WCRetAmt = WCCost * WCRetPct (Work Completed retainage)
- SMRetAmt = StoredMatls * SMRetPct (Stored Materials retainage)

**Key SLWI Columns:**
- Purchased: Total materials purchased for this item
- Installed: Materials incorporated into work
- StoredMatls: Calculated (Purchased - Installed)
- WCRetPct/SMRetPct: Separate retainage percentages

This allows billing for materials on-site while tracking them separately from completed work."""
    })

    return examples


def generate_projection_examples() -> List[Dict]:
    """Generate cost projection training examples."""
    examples = []

    examples.append({
        "instruction": "What tables are involved in cost-to-complete projections for jobs?",
        "input": "",
        "output": """Job cost projections in Vista use these key tables:

**JCPR** - JC Projection Resources
- Defines projection codes and methods
- Links to phases for projection calculations

**JCPD** - JC Projection Detail
- Stores projection detail records
- Contains projected costs by phase/cost type

**JCCP** - JC Cost Phase
- CurrEstCost: Current estimated cost (budget)
- ActualCost: Costs posted to date
- CurrEstHours: Current estimated hours

**JCCD** - JC Cost Detail
- Transaction-level cost detail
- ActualCost per transaction

**Cost-to-Complete Calculation:**
```
Remaining = CurrEstCost - ActualCost
```

Query for projection comparison:
```sql
SELECT JCCP.JCCo, JCCP.Job, JCCP.Phase, JCCP.CostType,
  JCCP.CurrEstCost AS Budget,
  JCCP.ActualCost AS Actual,
  JCCP.CurrEstCost - JCCP.ActualCost AS Remaining
FROM JCCP WITH (NOLOCK)
WHERE JCCP.JCCo = @JCCo AND JCCP.Job = @Job
```"""
    })

    examples.append({
        "instruction": "How do I link SM WorkOrder to AR billing through JC contracts?",
        "input": "",
        "output": """To link SM WorkOrder to AR billing through JC:

**Join Path:**
SMWorkOrder → SMServiceSite → JCJM (Job) → JCCM (Contract) → ARTH (AR billing)

Or use SMWorkOrderInvoice for direct invoice links.

```sql
SELECT WO.SMCo, WO.WorkOrder, WO.Description,
  SS.ServiceSite, SS.Job,
  JCJM.Description AS JobDescription,
  JCJM.Contract,
  JCCM.Description AS ContractDescription,
  ARTH.ARTrans, ARTH.InvDate, ARTH.Amount
FROM SMWorkOrder WO WITH (NOLOCK)
INNER JOIN SMServiceSite SS WITH (NOLOCK) ON WO.SMCo = SS.SMCo AND WO.ServiceSite = SS.ServiceSite
INNER JOIN JCJM WITH (NOLOCK) ON SS.JCCo = JCJM.JCCo AND SS.Job = JCJM.Job
INNER JOIN JCCM WITH (NOLOCK) ON JCJM.JCCo = JCCM.JCCo AND JCJM.Contract = JCCM.Contract
LEFT JOIN ARTH WITH (NOLOCK) ON JCCM.JCCo = ARTH.JCCo AND JCCM.Contract = ARTH.Contract
WHERE WO.SMCo = @SMCo
```

Key relationships:
- SMServiceSite links work orders to JC jobs
- JCJM.Contract links jobs to contracts
- ARTH can be joined via JCCo/Contract for billing"""
    })

    return examples


if __name__ == "__main__":
    main()

