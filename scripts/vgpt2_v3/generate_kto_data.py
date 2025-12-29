#!/usr/bin/env python3
"""
VGPT2 v3 KTO Binary Feedback Generator
=======================================
Generates binary feedback data for Kahneman-Tversky Optimization (KTO) training.

KTO uses thumbs_up/thumbs_down labels for each response, unlike DPO which uses
paired chosen/rejected responses. This is particularly useful for reinforcing
correct patterns and penalizing bad ones.

Usage:
    python scripts/vgpt2_v3/generate_kto_data.py --output data/vgpt2_v3_kto.json
"""

import json
import logging
import random
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class KTOExample:
    """A KTO binary feedback example."""
    instruction: str
    input: str
    output: str
    label: bool  # True = thumbs_up, False = thumbs_down

    def to_dict(self) -> Dict:
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output,
            "label": "true" if self.label else "false"  # LLaMA-Factory expects string
        }


class KTOGenerator:
    """
    Generates KTO binary feedback data for VGPT2.

    Creates both positive (thumbs_up) examples of correct SQL
    and negative (thumbs_down) examples of incorrect patterns.

    NOTE: KTO focuses on DIFFERENT patterns than DPO to reduce overlap:
    - KTO: Response format, explanation quality, uncertainty handling
    - DPO: SQL correctness (NOLOCK, JOINs, company filters)
    """

    def __init__(self, vgpt2_path: str):
        self.vgpt2 = Path(vgpt2_path)
        self.columns_data = {}
        self.tables = []
        self._load_schema()

    def _load_schema(self):
        """Load schema data from VGPT2 repository."""
        columns_paths = [
            self.vgpt2 / "Viewpoint_Database" / "_MetadataV2" / "_data" / "columns.json",
            self.vgpt2 / "Viewpoint_Database" / "_Metadata" / "columns.json",
        ]

        for columns_file in columns_paths:
            if columns_file.exists():
                with open(columns_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)

                if isinstance(raw_data, list):
                    from collections import defaultdict
                    table_columns = defaultdict(list)
                    for item in raw_data:
                        table_name = item.get('ObjectName', '')
                        if table_name:
                            table_columns[table_name].append({
                                'column_name': item.get('ColumnName', ''),
                                'data_type': item.get('DataType', ''),
                            })
                    self.columns_data = dict(table_columns)
                else:
                    self.columns_data = raw_data

                self.tables = list(self.columns_data.keys())
                logger.info(f"Loaded {len(self.tables)} tables from {columns_file}")
                break

    def _get_company_col(self, table: str) -> str:
        """Get company column for a table."""
        prefix_map = {
            "AP": "APCo", "AR": "ARCo", "GL": "GLCo", "JC": "JCCo",
            "PR": "PRCo", "EM": "EMCo", "IN": "INCo", "SM": "SMCo",
            "PM": "PMCo", "MS": "MSCo", "MR": "MRCo", "DC": "DCCo",
            "PO": "POCo", "SL": "SLCo", "WD": "WDCo", "HR": "HRCo",
        }
        for prefix, col in prefix_map.items():
            if table.startswith(prefix) or table.startswith("b" + prefix):
                return col
        return "Co"

    def generate_all(self) -> List[KTOExample]:
        """Generate all KTO examples.

        KTO focuses on response QUALITY and FORMAT patterns that differ from DPO:
        - DPO: SQL correctness (NOLOCK, JOINs, company filters)
        - KTO: Response quality, explanations, uncertainty, format
        """
        examples = []

        # ========== KTO-SPECIFIC PATTERNS (NOT in DPO) ==========

        # Response quality patterns
        logger.info("Generating positive explanation quality examples...")
        examples.extend(self.generate_positive_explanations())

        logger.info("Generating positive uncertainty handling examples...")
        examples.extend(self.generate_positive_uncertainty())

        logger.info("Generating positive code block formatting examples...")
        examples.extend(self.generate_positive_formatting())

        logger.info("Generating positive documentation reference examples...")
        examples.extend(self.generate_positive_doc_references())

        logger.info("Generating positive multi-step examples...")
        examples.extend(self.generate_positive_multi_step())

        # Negative response patterns
        logger.info("Generating negative vague responses...")
        examples.extend(self.generate_negative_vague())

        logger.info("Generating negative overconfident hallucinations...")
        examples.extend(self.generate_negative_overconfident())

        logger.info("Generating negative poor formatting examples...")
        examples.extend(self.generate_negative_formatting())

        logger.info("Generating negative incomplete responses...")
        examples.extend(self.generate_negative_incomplete())

        # ========== MINIMAL OVERLAP PATTERNS ==========
        # (Keep some basic correctness but different framing than DPO)

        logger.info("Generating positive view usage examples...")
        examples.extend(self.generate_positive_view_usage())

        logger.info("Generating negative hallucination examples...")
        examples.extend(self.generate_negative_hallucinations())

        logger.info(f"Generated {len(examples)} total KTO examples")

        # Count labels
        positive = sum(1 for e in examples if e.label)
        negative = len(examples) - positive
        logger.info(f"  Positive (thumbs_up): {positive}")
        logger.info(f"  Negative (thumbs_down): {negative}")

        return examples

    # ========== NEW KTO-SPECIFIC GENERATORS ==========

    def generate_positive_explanations(self) -> List[KTOExample]:
        """Generate positive examples with good explanations."""
        examples = []

        explanation_patterns = [
            {
                "instruction": "How do I query AP invoices?",
                "output": """To query AP invoices in Viewpoint Vista, use the APTH (AP Transaction Header) table:

```sql
SELECT
  APCo,
  Mth,
  APTrans,
  Vendor,
  InvNum,
  InvDate,
  GrossAmt
FROM APTH WITH (NOLOCK)
WHERE APCo = @APCo
```

**Key points:**
- APTH stores invoice headers; APTL stores line details
- Always include WITH (NOLOCK) for read queries
- Filter by APCo to ensure company isolation
- The Mth column stores the accounting month (first day format: '2024-01-01')"""
            },
            {
                "instruction": "Explain the job costing tables",
                "output": """Viewpoint Vista job costing uses several related tables:

**Primary Tables:**
- **JCJM** (Job Master) - Main job information: Job number, description, status
- **JCCD** (Cost Detail) - Cost transactions: Actual costs, committed costs, units
- **JCCH** (Cost/Phase Header) - Phase and cost type definitions

**Relationships:**
```sql
-- Join job master with cost details
SELECT
  JCJM.Job,
  JCJM.Description,
  JCCD.CostType,
  JCCD.ActualCost
FROM JCJM WITH (NOLOCK)
INNER JOIN JCCD WITH (NOLOCK)
  ON JCJM.JCCo = JCCD.JCCo
  AND JCJM.Job = JCCD.Job
WHERE JCJM.JCCo = @JCCo
```

**Note:** Always join on ALL key columns (JCCo + Job), not just Job."""
            },
            {
                "instruction": "What's the difference between APTH and bAPTH?",
                "output": """In Viewpoint Vista, the 'b' prefix indicates a base table vs. a view:

**bAPTH** - Base table (the actual underlying table)
- Use for INSERT, UPDATE, DELETE operations
- Direct access to data without security filtering

**APTH** - View (sits on top of bAPTH)
- Use for SELECT queries
- Includes row-level security
- Better performance due to indexing optimization

**Best Practice:**
```sql
-- Reading data - use the view
SELECT * FROM APTH WITH (NOLOCK) WHERE APCo = @APCo

-- Writing data - use the base table
INSERT INTO bAPTH (APCo, Mth, ...) VALUES (...)
```

This pattern applies to all 'b' prefixed tables: bJCJM/JCJM, bPRTH/PRTH, etc."""
            },
            {
                "instruction": "How do vendor groups work?",
                "output": """Vendor Groups in Viewpoint Vista provide a way to segment vendors across companies:

**Key Table:** APVM (AP Vendor Master)
- VendorGroup: Groups vendors (often 1:1 with company, but can be shared)
- Vendor: Vendor number within the group

**Querying Vendors:**
```sql
SELECT
  VendorGroup,
  Vendor,
  Name,
  Address,
  City,
  State,
  Zip
FROM APVM WITH (NOLOCK)
WHERE VendorGroup = @VendorGroup
```

**Joining with Transactions:**
```sql
SELECT APTH.InvNum, APVM.Name
FROM APTH WITH (NOLOCK)
INNER JOIN APVM WITH (NOLOCK)
  ON APTH.VendorGroup = APVM.VendorGroup
  AND APTH.Vendor = APVM.Vendor
WHERE APTH.APCo = @APCo
```

**Important:** Always join on BOTH VendorGroup AND Vendor columns."""
            },
        ]

        for pattern in explanation_patterns:
            examples.append(KTOExample(
                instruction=pattern["instruction"],
                input="",
                output=pattern["output"],
                label=True
            ))

        # Generate more from schema - expanded for more coverage
        sample_tables = random.sample(self.tables, min(500, len(self.tables)))
        for table in sample_tables:
            if table in self.columns_data and len(self.columns_data[table]) >= 3:
                cols = self.columns_data[table][:5]
                col_names = [c.get('column_name', '') for c in cols if c.get('column_name')]
                co_col = self._get_company_col(table)

                examples.append(KTOExample(
                    instruction=f"What columns are in {table}?",
                    input="",
                    output=f"""The {table} table contains these commonly used columns:

- {chr(10).join(['**' + c + '**' for c in col_names[:5]])}

**Example Query:**
```sql
SELECT {', '.join(col_names[:3])}
FROM {table} WITH (NOLOCK)
WHERE {co_col} = @{co_col}
```

Refer to the schema documentation for the complete column list and data types.""",
                    label=True
                ))

        return examples

    def generate_positive_uncertainty(self) -> List[KTOExample]:
        """Generate positive examples showing appropriate uncertainty."""
        examples = []

        uncertainty_patterns = [
            {
                "instruction": "What's the best way to calculate job profitability?",
                "output": """There are several approaches to calculate job profitability in Viewpoint Vista, depending on your needs:

**Option 1: Use Reporting Views (Recommended)**
```sql
SELECT *
FROM brvJCJobProfitability WITH (NOLOCK)
WHERE JCCo = @JCCo
```
Check if this view exists in your installation - it's pre-built for this purpose.

**Option 2: Direct Calculation**
```sql
SELECT
  JCJM.Job,
  SUM(JCCD.ActualRevenue) - SUM(JCCD.ActualCost) AS Profit
FROM JCJM WITH (NOLOCK)
INNER JOIN JCCD WITH (NOLOCK)
  ON JCJM.JCCo = JCCD.JCCo
  AND JCJM.Job = JCCD.Job
WHERE JCJM.JCCo = @JCCo
GROUP BY JCJM.Job
```

**Note:** Your implementation may have custom fields or calculations. Verify with your Viewpoint administrator for company-specific requirements."""
            },
            {
                "instruction": "Query the customer payments table",
                "output": """I'm not certain which specific table you're looking for. Viewpoint Vista has several payment-related tables:

**For AR (Accounts Receivable) payments:**
- **ARCM** - Customer Master
- **ARTH** - AR Transaction Header (includes payments received)
- **ARTL** - AR Transaction Line

**Example for customer payments:**
```sql
SELECT
  ARTH.Customer,
  ARTH.TransType,
  ARTH.Amount,
  ARTH.TransDate
FROM ARTH WITH (NOLOCK)
WHERE ARTH.ARCo = @ARCo
  AND ARTH.TransType = 'P'  -- Payment type
```

Could you clarify which module (AR, AP, etc.) you're working with?"""
            },
            {
                "instruction": "How do I get equipment utilization reports?",
                "output": """Equipment utilization reporting in Viewpoint depends on your specific configuration. Here are the main options:

**1. Standard EM Tables:**
```sql
SELECT
  EMEM.Equipment,
  EMEM.Description,
  EMUD.PostedDate,
  EMUD.Hours
FROM EMEM WITH (NOLOCK)
LEFT JOIN EMUD WITH (NOLOCK)
  ON EMEM.EMCo = EMUD.EMCo
  AND EMEM.Equipment = EMUD.Equipment
WHERE EMEM.EMCo = @EMCo
```

**2. Check for Reporting Views:**
Look for `vrvEM*` or `brvEM*` views that may have pre-built utilization calculations.

**3. Custom Reports:**
Many organizations have custom utilization reports. Check with your Viewpoint administrator for company-specific implementations.

What specific utilization metrics are you looking for?"""
            },
        ]

        for pattern in uncertainty_patterns:
            examples.append(KTOExample(
                instruction=pattern["instruction"],
                input="",
                output=pattern["output"],
                label=True
            ))

        return examples

    def generate_positive_formatting(self) -> List[KTOExample]:
        """Generate positive examples with proper code formatting."""
        examples = []

        formatting_patterns = [
            {
                "instruction": "Show me how to query GL transactions",
                "output": """```sql
SELECT
  GLCo,
  GLAcct,
  Mth,
  Trans,
  Amount,
  Description
FROM GLDT WITH (NOLOCK)
WHERE GLCo = @GLCo
  AND Mth >= '2024-01-01'
  AND Mth < '2025-01-01'
ORDER BY Mth, Trans
```

This query retrieves GL detail transactions for a specific company and date range."""
            },
            {
                "instruction": "Complex join example",
                "output": """Here's a complex join combining AP invoices with vendor and GL data:

```sql
SELECT
  APTH.APCo,
  APTH.InvNum,
  APTH.InvDate,
  APTH.GrossAmt,
  APVM.Name AS VendorName,
  APVM.Address,
  APTL.GLCo,
  APTL.GLAcct
FROM APTH WITH (NOLOCK)
INNER JOIN APVM WITH (NOLOCK)
  ON APTH.VendorGroup = APVM.VendorGroup
  AND APTH.Vendor = APVM.Vendor
INNER JOIN APTL WITH (NOLOCK)
  ON APTH.APCo = APTL.APCo
  AND APTH.Mth = APTL.Mth
  AND APTH.APTrans = APTL.APTrans
WHERE APTH.APCo = @APCo
  AND APTH.InvDate >= @StartDate
ORDER BY APTH.InvDate DESC
```

**Notes:**
- All tables use WITH (NOLOCK) for read consistency
- JOINs use complete key columns
- Results sorted by invoice date descending"""
            },
        ]

        for pattern in formatting_patterns:
            examples.append(KTOExample(
                instruction=pattern["instruction"],
                input="",
                output=pattern["output"],
                label=True
            ))

        # Generate from schema with good formatting - expanded
        sample_tables = random.sample(self.tables, min(400, len(self.tables)))
        for table in sample_tables:
            if table in self.columns_data:
                cols = self.columns_data[table][:4]
                col_names = [c.get('column_name', '') for c in cols if c.get('column_name')]
                co_col = self._get_company_col(table)

                if len(col_names) >= 2:
                    formatted_cols = ",\n  ".join(col_names)
                    examples.append(KTOExample(
                        instruction=f"Query {table}",
                        input="",
                        output=f"""```sql
SELECT
  {formatted_cols}
FROM {table} WITH (NOLOCK)
WHERE {co_col} = @{co_col}
```""",
                        label=True
                    ))

        return examples

    def generate_positive_doc_references(self) -> List[KTOExample]:
        """Generate positive examples that reference documentation."""
        examples = []

        doc_patterns = [
            {
                "instruction": "Where can I find information about the JCCD table structure?",
                "output": """The JCCD (JC Cost Detail) table documentation can be found in:

1. **Schema Browser:** Check the Viewpoint Vista Schema documentation for complete column definitions
2. **Database Views:** Query `INFORMATION_SCHEMA.COLUMNS` for live schema:
```sql
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS WITH (NOLOCK)
WHERE TABLE_NAME = 'JCCD'
ORDER BY ORDINAL_POSITION
```

**Key JCCD columns:**
- JCCo, Job, PhaseGroup, Phase, CostType (primary key)
- ActualCost, ActualRevenue, ActualUnits
- CommittedCost, CommittedUnits

Refer to the Viewpoint Help documentation for detailed field descriptions."""
            },
            {
                "instruction": "What's the Month format in Viewpoint?",
                "output": """Viewpoint Vista stores 'Month' (Mth) columns as the **first day of the month**:

**Format:** `YYYY-MM-01` (e.g., '2024-01-01' for January 2024)

**Correct Usage:**
```sql
-- Filter for January 2024
WHERE Mth = '2024-01-01'

-- Filter for year 2024
WHERE Mth >= '2024-01-01' AND Mth < '2025-01-01'

-- Get month from date
WHERE Mth = DATEADD(MONTH, DATEDIFF(MONTH, 0, @Date), 0)
```

**Common Mistakes:**
- ❌ `WHERE Mth = '2024-01'` (wrong format)
- ❌ `WHERE Mth = '01/2024'` (wrong format)
- ✅ `WHERE Mth = '2024-01-01'` (correct)

This applies to all Mth columns: APTH.Mth, JCCD.Mth, GLDT.Mth, etc."""
            },
        ]

        for pattern in doc_patterns:
            examples.append(KTOExample(
                instruction=pattern["instruction"],
                input="",
                output=pattern["output"],
                label=True
            ))

        return examples

    def generate_positive_multi_step(self) -> List[KTOExample]:
        """Generate positive examples with multi-step solutions."""
        examples = []

        multi_step_patterns = [
            {
                "instruction": "How do I find all unpaid invoices for a vendor?",
                "output": """To find unpaid invoices for a specific vendor, follow these steps:

**Step 1: Identify the vendor**
```sql
SELECT VendorGroup, Vendor, Name
FROM APVM WITH (NOLOCK)
WHERE Name LIKE '%VendorName%'
```

**Step 2: Query unpaid invoices**
```sql
SELECT
  APTH.APCo,
  APTH.Vendor,
  APVM.Name AS VendorName,
  APTH.InvNum,
  APTH.InvDate,
  APTH.GrossAmt,
  APTH.PaidDate
FROM APTH WITH (NOLOCK)
INNER JOIN APVM WITH (NOLOCK)
  ON APTH.VendorGroup = APVM.VendorGroup
  AND APTH.Vendor = APVM.Vendor
WHERE APTH.APCo = @APCo
  AND APTH.Vendor = @Vendor
  AND APTH.Status = 0  -- 0 = Open/Unpaid
ORDER BY APTH.InvDate
```

**Status values:**
- 0 = Open
- 1 = Paid
- 2 = Void"""
            },
            {
                "instruction": "How do I compare actual vs budget for a job?",
                "output": """Comparing actual vs budget costs requires data from multiple sources:

**Step 1: Get budget data from JCCH**
```sql
SELECT
  JCCo, Job, PhaseGroup, Phase, CostType,
  OrigEstCost, CurrEstCost
FROM JCCH WITH (NOLOCK)
WHERE JCCo = @JCCo AND Job = @Job
```

**Step 2: Get actual costs from JCCD**
```sql
SELECT
  JCCo, Job, PhaseGroup, Phase, CostType,
  SUM(ActualCost) AS ActualCost
FROM JCCD WITH (NOLOCK)
WHERE JCCo = @JCCo AND Job = @Job
GROUP BY JCCo, Job, PhaseGroup, Phase, CostType
```

**Step 3: Combined comparison**
```sql
SELECT
  JCCH.Job,
  JCCH.Phase,
  JCCH.CostType,
  JCCH.CurrEstCost AS Budget,
  COALESCE(SUM(JCCD.ActualCost), 0) AS Actual,
  JCCH.CurrEstCost - COALESCE(SUM(JCCD.ActualCost), 0) AS Variance
FROM JCCH WITH (NOLOCK)
LEFT JOIN JCCD WITH (NOLOCK)
  ON JCCH.JCCo = JCCD.JCCo
  AND JCCH.Job = JCCD.Job
  AND JCCH.PhaseGroup = JCCD.PhaseGroup
  AND JCCH.Phase = JCCD.Phase
  AND JCCH.CostType = JCCD.CostType
WHERE JCCH.JCCo = @JCCo AND JCCH.Job = @Job
GROUP BY JCCH.Job, JCCH.Phase, JCCH.CostType, JCCH.CurrEstCost
```

**Note:** Check for `brvJC*` reporting views that may already have this calculation."""
            },
        ]

        for pattern in multi_step_patterns:
            examples.append(KTOExample(
                instruction=pattern["instruction"],
                input="",
                output=pattern["output"],
                label=True
            ))

        return examples

    def generate_negative_vague(self) -> List[KTOExample]:
        """Generate negative examples with vague, unhelpful responses."""
        examples = []

        vague_patterns = [
            {"instruction": "How do I query AP invoices?", "output": "You can use SELECT to get invoices from the database."},
            {"instruction": "What tables are related to jobs?", "output": "There are several job tables in the system."},
            {"instruction": "How do I join APTH and APTL?", "output": "Use a JOIN statement to combine the tables."},
            {"instruction": "What columns does JCJM have?", "output": "JCJM has various columns for job information."},
            {"instruction": "How do I filter by company?", "output": "Add a WHERE clause with the company column."},
            {"instruction": "What's the GL account structure?", "output": "GL accounts store financial data."},
            {"instruction": "How do I get vendor details?", "output": "Query the vendor table for details."},
            {"instruction": "Explain cost types", "output": "Cost types categorize costs."},
            {"instruction": "How do I find employee pay rates?", "output": "Check the payroll tables."},
            {"instruction": "What's the difference between actual and committed cost?", "output": "They are different types of costs."},
            {"instruction": "How do I query purchase orders?", "output": "Use the PO tables."},
            {"instruction": "What's the primary key for APTH?", "output": "It has multiple key columns."},
            {"instruction": "How do I get equipment history?", "output": "Query the equipment tables."},
            {"instruction": "What date format does Viewpoint use?", "output": "It uses standard date formats."},
            {"instruction": "How do I calculate job margin?", "output": "Use the job cost tables."},
            {"instruction": "What's the relationship between JCJM and JCCD?", "output": "They are related tables."},
            {"instruction": "How do I find subcontract payments?", "output": "Query the SL module tables."},
            {"instruction": "What's in the ARTH table?", "output": "AR transaction data."},
            {"instruction": "How do I query by month?", "output": "Use the Mth column."},
            {"instruction": "What modules does Viewpoint have?", "output": "It has several modules."},
        ]

        for pattern in vague_patterns:
            examples.append(KTOExample(
                instruction=pattern["instruction"],
                input="",
                output=pattern["output"],
                label=False  # Thumbs down - too vague
            ))

        # Generate more vague responses from schema
        sample_tables = random.sample(self.tables, min(200, len(self.tables)))
        for table in sample_tables:
            examples.append(KTOExample(
                instruction=f"What's in {table}?",
                input="",
                output=f"The {table} table contains data.",
                label=False
            ))
            examples.append(KTOExample(
                instruction=f"How do I query {table}?",
                input="",
                output=f"Use SELECT on {table}.",
                label=False
            ))

        return examples

    def generate_negative_overconfident(self) -> List[KTOExample]:
        """Generate negative examples with overconfident hallucinations."""
        examples = []

        overconfident_patterns = [
            {"instruction": "Query the InvoiceHeader table", "output": "```sql\nSELECT InvoiceID, CustomerID, TotalAmount, Status\nFROM InvoiceHeader WITH (NOLOCK)\nWHERE CompanyID = @CompanyID\n```\nThis returns all invoice headers with their status and amounts."},
            {"instruction": "What's in the CustomerMaster table?", "output": "The CustomerMaster table contains:\n- CustomerID (primary key)\n- CustomerName\n- BillingAddress\n- ContactEmail\n- CreditLimit\n- AccountStatus\n\nQuery example:\n```sql\nSELECT * FROM CustomerMaster WHERE Active = 1\n```"},
            {"instruction": "How do I query employee timecards?", "output": "```sql\nSELECT EmployeeID, WorkDate, HoursWorked, ProjectCode\nFROM TimeCardEntries\nWHERE PayPeriod = @PayPeriod\n```\nThis gets all timecard entries for the specified pay period."},
            {"instruction": "Get all projects", "output": "```sql\nSELECT ProjectID, ProjectName, StartDate, EndDate, Status\nFROM Projects WITH (NOLOCK)\nWHERE IsActive = 1\nORDER BY StartDate DESC\n```"},
            {"instruction": "Query the WorkOrder table", "output": "```sql\nSELECT WorkOrderID, Description, AssignedTo, DueDate, Priority\nFROM WorkOrder\nWHERE Status = 'Open'\n```\nThis returns all open work orders sorted by priority."},
            {"instruction": "Get billing information", "output": "```sql\nSELECT BillingID, InvoiceNumber, CustomerID, Amount\nFROM BillingRecords\nWHERE Status = 'Pending'\n```"},
            {"instruction": "Query the PayrollDetail table", "output": "```sql\nSELECT PayrollID, EmployeeID, PayDate, GrossPay, NetPay\nFROM PayrollDetail\nWHERE PayPeriod = @Period\n```"},
            {"instruction": "Get all active contracts", "output": "```sql\nSELECT ContractID, ClientName, StartDate, Value\nFROM Contracts\nWHERE Status = 'Active'\n```"},
            {"instruction": "Query change orders", "output": "```sql\nSELECT ChangeOrderID, ProjectID, Amount, Status\nFROM ChangeOrders\nWHERE ApprovalStatus = 'Pending'\n```"},
            {"instruction": "Get inventory levels", "output": "```sql\nSELECT ItemID, ItemName, Quantity, Location\nFROM Inventory\nWHERE Quantity > 0\n```"},
        ]

        for pattern in overconfident_patterns:
            examples.append(KTOExample(
                instruction=pattern["instruction"],
                input="",
                output=pattern["output"],
                label=False  # Thumbs down - confidently wrong
            ))

        # More fake table hallucinations with detailed false information
        fake_details = [
            ("UserAccounts", "UserID, Username, Email, Role, LastLogin"),
            ("ProjectTasks", "TaskID, ProjectID, TaskName, AssignedTo, DueDate"),
            ("BudgetItems", "BudgetID, Category, Amount, Remaining, Status"),
            ("Departments", "DeptID, DeptName, Manager, Location, Budget"),
            ("Locations", "LocationID, LocationName, Address, Manager"),
            ("Categories", "CategoryID, CategoryName, ParentID, Description"),
            ("PaymentHistory", "PaymentID, InvoiceID, Amount, PayDate, Method"),
            ("AuditLog", "LogID, TableName, Action, UserID, Timestamp"),
            ("Notifications", "NotifyID, UserID, Message, ReadStatus, CreatedAt"),
            ("Reports", "ReportID, ReportName, CreatedBy, LastRun, Parameters"),
        ]

        for fake_table, fake_cols in fake_details:
            examples.append(KTOExample(
                instruction=f"What columns are in {fake_table}?",
                input="",
                output=f"The {fake_table} table has columns: {fake_cols}.",
                label=False
            ))

        return examples

    def generate_negative_formatting(self) -> List[KTOExample]:
        """Generate negative examples with poor formatting."""
        examples = []

        poor_formatting = [
            {
                "instruction": "Query APTH for company 1",
                "output": "select * from apth where apco=1"
            },
            {
                "instruction": "Get job costs",
                "output": "SELECT JCCo,Job,ActualCost FROM JCCD WHERE JCCo=@JCCo"
            },
            {
                "instruction": "List all vendors",
                "output": "select vendorgroup,vendor,name,address,city,state,zip,phone,fax,email from apvm with(nolock) where vendorgroup=@vendorgroup"
            },
            {
                "instruction": "Complex AP query",
                "output": "select apth.invnum,apth.grossamt,apvm.name from apth join apvm on apth.vendor=apvm.vendor where apth.apco=1"
            },
            {
                "instruction": "Get employee data",
                "output": "SELECT PREH.Employee PREH.FirstName PREH.LastName FROM PREH"
            },
        ]

        for pattern in poor_formatting:
            examples.append(KTOExample(
                instruction=pattern["instruction"],
                input="",
                output=pattern["output"],
                label=False  # Thumbs down - poor formatting
            ))

        return examples

    def generate_negative_incomplete(self) -> List[KTOExample]:
        """Generate negative examples with incomplete responses."""
        examples = []

        incomplete_patterns = [
            {
                "instruction": "How do I join job tables to get cost summary?",
                "output": """```sql
SELECT JCJM.Job, JCCD.ActualCost
FROM JCJM
JOIN JCCD ON JCJM.Job = JCCD.Job
```"""
            },
            {
                "instruction": "Get AP aging data",
                "output": "Query the APTH table and check the due date."
            },
            {
                "instruction": "What's the relationship between APTH and APTL?",
                "output": "APTH is the header and APTL is the line detail."
            },
            {
                "instruction": "How do I calculate job profit margin?",
                "output": """```sql
SELECT Job, ActualRevenue - ActualCost
FROM JCCD
```"""
            },
            {
                "instruction": "Query purchase orders with vendor info",
                "output": """```sql
SELECT * FROM POHD
```"""
            },
        ]

        for pattern in incomplete_patterns:
            examples.append(KTOExample(
                instruction=pattern["instruction"],
                input="",
                output=pattern["output"],
                label=False  # Thumbs down - incomplete
            ))

        return examples

    # ========== ORIGINAL GENERATORS (kept for compatibility) ==========

    def generate_positive_nolock(self) -> List[KTOExample]:
        """Generate positive examples with correct NOLOCK usage."""
        # This is now replaced by generate_positive_formatting
        return []

    def generate_positive_company_filter(self) -> List[KTOExample]:
        """Generate positive examples with company filtering."""
        # This is now covered in generate_positive_explanations
        return []

    def generate_positive_view_usage(self) -> List[KTOExample]:
        """Generate positive examples using views correctly."""
        examples = []

        view_mappings = [
            ("bAPTH", "APTH", "APCo"),
            ("bAPTL", "APTL", "APCo"),
            ("bJCJM", "JCJM", "JCCo"),
            ("bJCCD", "JCCD", "JCCo"),
            ("bPRTH", "PRTH", "PRCo"),
            ("bPREH", "PREH", "PRCo"),
            ("bGLDT", "GLDT", "GLCo"),
            ("bARCM", "ARCM", "CustGroup"),
            ("bAPVM", "APVM", "VendorGroup"),
        ]

        for base, view, co_col in view_mappings:
            examples.append(KTOExample(
                instruction=f"Read from {base}",
                input="",
                output=f"For SELECT queries, use the view {view} instead of base table {base}:\n\n```sql\nSELECT *\nFROM {view} WITH (NOLOCK)\nWHERE {co_col} = @{co_col}\n```\n\nBase tables (b-prefix) should only be used for INSERT/UPDATE/DELETE operations.",
                label=True
            ))

        return examples

    # Removed: generate_positive_case_examples - covered by DPO
    # Removed: generate_negative_missing_nolock - covered by DPO

    def generate_negative_hallucinations(self) -> List[KTOExample]:
        """Generate negative examples with fake tables."""
        examples = []

        fake_tables = [
            "Invoice", "Invoices", "Customer", "Customers", "Vendor", "Vendors",
            "Employee", "Employees", "Job", "Jobs", "Project", "Projects",
            "Transaction", "Transactions", "Account", "Accounts", "Material",
            "Equipment", "Timecard", "Timecards", "Contract", "Contracts",
            "PurchaseOrder", "WorkOrder", "ChangeOrder", "CostCode",
            "APInvoice", "ARInvoice", "GLTransaction", "PRTimecard",
            "JCJob", "JCCost", "EMEquipment", "INMaterial",
        ]

        for fake in fake_tables:
            examples.append(KTOExample(
                instruction=f"Query the {fake} table",
                input="",
                output=f"```sql\nSELECT *\nFROM {fake} WITH (NOLOCK)\n```",
                label=False  # Thumbs down - fake table
            ))

            examples.append(KTOExample(
                instruction=f"What is in {fake}?",
                input="",
                output=f"The {fake} table contains columns like ID, Name, Description, Status, CreateDate, ModifyDate.",
                label=False  # Thumbs down - hallucinated response
            ))

        return examples

    # Removed: generate_negative_wrong_case - covered by DPO
    # Removed: generate_negative_aliases - covered by DPO
    # Removed: generate_negative_missing_company - covered by DPO

    def save_dataset(self, examples: List[KTOExample], output_path: str):
        """Save examples to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        data = [e.to_dict() for e in examples]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(examples)} KTO examples to {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate KTO binary feedback data")
    parser.add_argument('--vgpt2', type=str, default='C:/Github/VGPT2',
                        help='Path to VGPT2 repository')
    parser.add_argument('--output', type=str, default='data/vgpt2_v3_kto.json',
                        help='Output file path')

    args = parser.parse_args()

    generator = KTOGenerator(args.vgpt2)
    examples = generator.generate_all()
    generator.save_dataset(examples, args.output)

    print(f"\nGenerated {len(examples)} KTO examples to {args.output}")


if __name__ == "__main__":
    main()
