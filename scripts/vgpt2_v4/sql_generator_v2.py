# Copyright 2024-2025 Viewpoint, Inc.
# Licensed under the Apache License, Version 2.0.

"""
SQL Example Generator Module V2

Generates UNIQUE SQL training examples with proper variation:
1. Question phrasing variations
2. Schema subset variations  
3. Parameter variations (company codes, dates, etc.)
4. Deduplication to ensure uniqueness
"""

import json
import logging
import random
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .config import V4Config, TrainingCategory, CategoryConfig
from .ddl_extractor import DDLExtractor, create_ddl_for_question

logger = logging.getLogger(__name__)


# =============================================================================
# VARIATION DATA
# =============================================================================

# Question phrasing variations
QUESTION_PREFIXES = [
    "",
    "Write a SQL query to ",
    "Create a query that will ",
    "Generate SQL to ",
    "I need SQL to ",
    "Help me ",
    "Show me how to ",
    "Can you write SQL to ",
]

QUESTION_SUFFIXES = [
    "",
    " Please include all relevant columns.",
    " Use Vista best practices.",
    " Order results appropriately.",
]

# Company code variations for parameterization
COMPANY_CODES = [1, 2, 5, 10, 50, 100]

# Date range variations
DATE_RANGES = [
    ("last 30 days", "DATEADD(day, -30, GETDATE())", "GETDATE()"),
    ("last 60 days", "DATEADD(day, -60, GETDATE())", "GETDATE()"),
    ("last 90 days", "DATEADD(day, -90, GETDATE())", "GETDATE()"),
    ("this month", "DATEADD(month, DATEDIFF(month, 0, GETDATE()), 0)", "GETDATE()"),
    ("this year", "DATEADD(year, DATEDIFF(year, 0, GETDATE()), 0)", "GETDATE()"),
    ("last month", "DATEADD(month, DATEDIFF(month, 0, GETDATE()) - 1, 0)", "DATEADD(month, DATEDIFF(month, 0, GETDATE()), 0)"),
    ("year to date", "DATEADD(year, DATEDIFF(year, 0, GETDATE()), 0)", "GETDATE()"),
]

# Module-specific company column names
MODULE_COMPANY_COLS = {
    "AR": "ARCo",
    "AP": "APCo", 
    "JC": "JCCo",
    "SL": "SLCo",
    "PR": "PRCo",
    "GL": "GLCo",
    "HQ": "HQCo",
    "SM": "SMCo",
    "EM": "EMCo",
    "IN": "INCo",
    "PO": "POCo",
    "MS": "MSCo",
}


@dataclass
class TrainingExample:
    """A single training example in schema-in-prompt format."""
    instruction: str
    input: str
    output: str
    category: str = ""
    complexity: str = "basic"
    tables_used: List[str] = field(default_factory=list)
    unique_id: str = ""
    
    def to_alpaca(self) -> Dict:
        """Convert to Alpaca format for LLaMA Factory."""
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output
        }
    
    def compute_hash(self) -> str:
        """Compute a hash for deduplication based on instruction only."""
        # Only hash the instruction - that's what the model sees as input
        return hashlib.md5(self.instruction.encode()).hexdigest()[:16]


@dataclass
class QueryTemplate:
    """Enhanced template with variation support."""
    id: str
    base_question: str
    question_variants: List[str]
    category: TrainingCategory
    primary_tables: List[str]
    optional_tables: List[str] = field(default_factory=list)
    sql_template: str = ""
    explanation_template: str = ""
    complexity: str = "basic"
    supports_company_filter: bool = True
    supports_date_filter: bool = False
    module: str = ""


class SQLExampleGeneratorV2:
    """
    Generate SQL training examples with proper variation.
    
    Key improvements over V1:
    1. Each template has multiple question phrasings
    2. DDL varies by including/excluding optional tables
    3. SQL varies by company code and date parameters
    4. Strict deduplication ensures uniqueness
    """
    
    def __init__(self, config: V4Config, ddl_extractor: DDLExtractor):
        self.config = config
        self.ddl = ddl_extractor
        self.templates = self._build_templates()
        self._seen_hashes: Set[str] = set()
        
        logger.info(f"SQLExampleGeneratorV2 initialized with {len(self.templates)} templates")
    
    def generate_all(self, target_count: int = 500) -> List[TrainingExample]:
        """Generate unique training examples."""
        examples = []
        attempts = 0
        max_attempts = target_count * 10  # Prevent infinite loops
        
        while len(examples) < target_count and attempts < max_attempts:
            attempts += 1
            template = random.choice(self.templates)
            example = self._generate_variation(template)
            
            if example:
                hash_id = example.compute_hash()
                if hash_id not in self._seen_hashes:
                    self._seen_hashes.add(hash_id)
                    example.unique_id = hash_id
                    examples.append(example)
        
        logger.info(f"Generated {len(examples)} unique examples ({attempts} attempts)")
        return examples
    
    def _generate_variation(self, template: QueryTemplate) -> Optional[TrainingExample]:
        """Generate a unique variation of a template."""
        try:
            # 1. Pick a question variant
            question = self._vary_question(template)
            
            # 2. Generate DDL with optional table variation
            ddl = self._vary_ddl(template)
            if not ddl:
                return None
            
            # 3. Generate SQL with parameter variation
            sql, explanation = self._vary_sql(template)
            
            # 4. Build the example
            instruction = self._build_instruction(question, ddl)
            output = self._build_output(explanation, sql)
            
            return TrainingExample(
                instruction=instruction,
                input="",
                output=output,
                category=template.category.value,
                complexity=template.complexity,
                tables_used=template.primary_tables
            )
            
        except Exception as e:
            logger.debug(f"Error generating variation: {e}")
            return None
    
    def _vary_question(self, template: QueryTemplate) -> str:
        """Generate a varied question phrasing."""
        # Pick from template variants or base question
        if template.question_variants:
            base = random.choice([template.base_question] + template.question_variants)
        else:
            base = template.base_question
        
        # Add random prefix/suffix
        prefix = random.choice(QUESTION_PREFIXES)
        suffix = random.choice(QUESTION_SUFFIXES)
        
        # Avoid double prefixes
        if base[0].isupper() and prefix:
            base = base[0].lower() + base[1:]
        
        return f"{prefix}{base}{suffix}".strip()
    
    def _vary_ddl(self, template: QueryTemplate) -> Optional[str]:
        """Generate DDL with table variation."""
        # Always include primary tables
        tables = list(template.primary_tables)
        
        # Randomly include 0-2 optional tables
        if template.optional_tables:
            num_optional = random.randint(0, min(2, len(template.optional_tables)))
            tables.extend(random.sample(template.optional_tables, num_optional))
        
        # Random column limit for variety
        max_cols = random.choice([15, 20, 25])
        
        ddl_parts = []
        for table_name in tables:
            table = self.ddl.get_table(table_name)
            if table:
                ddl_parts.append(table.to_ddl(max_columns=max_cols))
        
        return "\n\n".join(ddl_parts) if ddl_parts else None
    
    def _vary_sql(self, template: QueryTemplate) -> Tuple[str, str]:
        """Generate SQL with parameter variation."""
        sql = template.sql_template
        explanation = template.explanation_template
        
        # Substitute company parameter
        if template.supports_company_filter and template.module:
            co_col = MODULE_COMPANY_COLS.get(template.module, "Co")
            co_val = random.choice(COMPANY_CODES)
            
            # Use either parameter or literal
            if random.random() < 0.5:
                sql = sql.replace("@Co", str(co_val))
                sql = sql.replace(f"@{co_col}", str(co_val))
            # else leave as parameter
        
        # Substitute date range
        if template.supports_date_filter and "{date_range}" in sql:
            date_desc, start_expr, end_expr = random.choice(DATE_RANGES)
            sql = sql.replace("{date_range_start}", start_expr)
            sql = sql.replace("{date_range_end}", end_expr)
            explanation = explanation.replace("{date_range}", date_desc)
        
        # Add Vista hints randomly
        if random.random() < 0.7:
            sql = self._add_vista_hints(sql, template.primary_tables)
        
        return sql, explanation
    
    def _add_vista_hints(self, sql: str, tables: List[str]) -> str:
        """Add WITH (NOLOCK) hints."""
        for table in tables:
            if f"FROM {table}" in sql and "WITH (NOLOCK)" not in sql:
                sql = sql.replace(f"FROM {table}", f"FROM {table} WITH (NOLOCK)")
            if f"JOIN {table}" in sql and f"JOIN {table} WITH" not in sql:
                sql = sql.replace(f"JOIN {table}", f"JOIN {table} WITH (NOLOCK)")
        return sql
    
    def _build_instruction(self, question: str, ddl: str) -> str:
        """Build the instruction with question and DDL."""
        return self.config.user_prompt_template.format(
            question=question,
            ddl_statements=ddl
        )
    
    def _build_output(self, explanation: str, sql: str) -> str:
        """Build the output with explanation and SQL."""
        parts = []
        if explanation:
            parts.append(explanation)
            parts.append("")
        parts.append("```sql")
        parts.append(sql)
        parts.append("```")
        return "\n".join(parts)
    
    def _build_templates(self) -> List[QueryTemplate]:
        """Build the template library with variations."""
        return QUERY_TEMPLATES


# =============================================================================
# QUERY TEMPLATES WITH VARIATIONS
# =============================================================================

QUERY_TEMPLATES = [
    # =========================================================================
    # AR QUERIES
    # =========================================================================
    QueryTemplate(
        id="ar_aging_buckets",
        base_question="Calculate AR aging buckets (30/60/90+ days) for unpaid invoices by customer",
        question_variants=[
            "Show AR aging report with 30, 60, 90+ day buckets",
            "Get customer aging analysis for accounts receivable",
            "Generate an AR aging summary grouped by customer",
            "List unpaid invoices categorized by age (30/60/90 days)",
            "Create aging buckets for outstanding AR invoices",
        ],
        category=TrainingCategory.AR_QUERIES,
        primary_tables=["ARTH", "ARCM"],
        optional_tables=["ARCO"],
        module="AR",
        complexity="advanced",
        sql_template="""SELECT 
  ARCM.Name AS CustomerName,
  ARTH.CustGroup,
  ARTH.Customer,
  SUM(CASE WHEN DATEDIFF(day, ARTH.TransDate, GETDATE()) <= 30 
      THEN ARTH.Amount ELSE 0 END) AS Current_0_30,
  SUM(CASE WHEN DATEDIFF(day, ARTH.TransDate, GETDATE()) BETWEEN 31 AND 60 
      THEN ARTH.Amount ELSE 0 END) AS Days_31_60,
  SUM(CASE WHEN DATEDIFF(day, ARTH.TransDate, GETDATE()) BETWEEN 61 AND 90 
      THEN ARTH.Amount ELSE 0 END) AS Days_61_90,
  SUM(CASE WHEN DATEDIFF(day, ARTH.TransDate, GETDATE()) > 90 
      THEN ARTH.Amount ELSE 0 END) AS Over_90
FROM ARTH
INNER JOIN ARCM ON ARTH.CustGroup = ARCM.CustGroup AND ARTH.Customer = ARCM.Customer
WHERE ARTH.ARCo = @ARCo
  AND ARTH.PayFullDate IS NULL
GROUP BY ARCM.Name, ARTH.CustGroup, ARTH.Customer
ORDER BY ARCM.Name""",
        explanation_template="""To calculate AR aging buckets for unpaid invoices:
1. Join ARTH (AR transactions) with ARCM (customers) on CustGroup and Customer
2. Filter to unpaid invoices using PayFullDate IS NULL
3. Use DATEDIFF with CASE WHEN to bucket by age
4. Group by customer for the summary"""
    ),
    
    QueryTemplate(
        id="ar_unpaid_invoices",
        base_question="Find all unpaid AR invoices older than 60 days",
        question_variants=[
            "List overdue AR invoices past 60 days",
            "Get AR invoices that are more than 60 days old and unpaid",
            "Show outstanding AR transactions over 60 days",
            "Retrieve past-due invoices exceeding 60 days",
        ],
        category=TrainingCategory.AR_QUERIES,
        primary_tables=["ARTH", "ARCM"],
        optional_tables=["ARCO", "JCCM"],
        module="AR",
        complexity="intermediate",
        sql_template="""SELECT 
  ARTH.ARCo,
  ARTH.Mth,
  ARTH.ARTrans,
  ARTH.Invoice,
  ARTH.TransDate,
  ARTH.Amount,
  DATEDIFF(day, ARTH.TransDate, GETDATE()) AS DaysOutstanding,
  ARCM.Name AS CustomerName
FROM ARTH
INNER JOIN ARCM ON ARTH.CustGroup = ARCM.CustGroup AND ARTH.Customer = ARCM.Customer
WHERE ARTH.ARCo = @ARCo
  AND ARTH.PayFullDate IS NULL
  AND DATEDIFF(day, ARTH.TransDate, GETDATE()) > 60
ORDER BY DaysOutstanding DESC""",
        explanation_template="""To find unpaid AR invoices older than 60 days:
1. Query ARTH for transaction details, join ARCM for customer name
2. Filter PayFullDate IS NULL for unpaid invoices
3. Use DATEDIFF to calculate days outstanding
4. Filter where days > 60"""
    ),
    
    QueryTemplate(
        id="ar_customer_balance",
        base_question="Get customer balance summary by customer group",
        question_variants=[
            "Show customer balances grouped by customer group",
            "Calculate total AR balance per customer group",
            "Summarize receivables by customer group",
            "List AR balances summarized by customer group",
        ],
        category=TrainingCategory.AR_QUERIES,
        primary_tables=["ARTH", "ARCM"],
        module="AR",
        complexity="intermediate",
        sql_template="""SELECT 
  ARTH.CustGroup,
  COUNT(DISTINCT ARTH.Customer) AS CustomerCount,
  SUM(CASE WHEN ARTH.ARTransType = 'I' THEN ARTH.Amount ELSE 0 END) AS TotalInvoiced,
  SUM(CASE WHEN ARTH.ARTransType = 'P' THEN ARTH.Amount ELSE 0 END) AS TotalPayments,
  SUM(ARTH.Amount) AS NetBalance
FROM ARTH
WHERE ARTH.ARCo = @ARCo
  AND ARTH.PayFullDate IS NULL
GROUP BY ARTH.CustGroup
ORDER BY ARTH.CustGroup""",
        explanation_template="""To get customer balance by customer group:
1. Sum amounts from ARTH grouped by CustGroup
2. Use ARTransType to separate invoices ('I') from payments ('P')
3. Calculate net balance as total of all transactions"""
    ),
    
    QueryTemplate(
        id="ar_invoice_details",
        base_question="Get invoice details with line items for a customer",
        question_variants=[
            "Show detailed invoice breakdown with line items",
            "List invoice header and details for a specific customer",
            "Retrieve full invoice information including all lines",
            "Get complete invoice data with breakdown",
        ],
        category=TrainingCategory.AR_QUERIES,
        primary_tables=["ARTH", "ARTI", "ARCM"],
        module="AR",
        complexity="intermediate",
        sql_template="""SELECT 
  ARTH.ARCo,
  ARTH.Invoice,
  ARTH.TransDate,
  ARCM.Name AS CustomerName,
  ARTI.ARLine,
  ARTI.Description,
  ARTI.Amount AS LineAmount,
  ARTH.Amount AS InvoiceTotal
FROM ARTH
INNER JOIN ARCM ON ARTH.CustGroup = ARCM.CustGroup AND ARTH.Customer = ARCM.Customer
LEFT JOIN ARTI ON ARTH.ARCo = ARTI.ARCo AND ARTH.Mth = ARTI.Mth AND ARTH.ARTrans = ARTI.ARTrans
WHERE ARTH.ARCo = @ARCo
  AND ARTH.Customer = @Customer
ORDER BY ARTH.TransDate DESC, ARTI.ARLine""",
        explanation_template="""To get invoice details with line items:
1. Join ARTH (header) with ARTI (items) on ARCo, Mth, ARTrans
2. Include ARCM for customer name
3. Filter by company and optionally by customer"""
    ),

    # =========================================================================
    # AP QUERIES
    # =========================================================================
    QueryTemplate(
        id="ap_vendor_invoices",
        base_question="Get vendor invoice totals with discounts and retainage",
        question_variants=[
            "List AP invoices by vendor with discount and retainage amounts",
            "Show vendor invoices including discounts taken and retainage held",
            "Calculate total invoices per vendor with discount and retainage detail",
            "Summarize AP invoices by vendor with discount and retainage breakdown",
        ],
        category=TrainingCategory.AP_QUERIES,
        primary_tables=["APTH", "APVM"],
        optional_tables=["APTD", "APCO"],
        module="AP",
        complexity="advanced",
        sql_template="""SELECT 
  APVM.Vendor,
  APVM.Name AS VendorName,
  COUNT(*) AS InvoiceCount,
  SUM(APTH.GrossAmt) AS TotalGross,
  SUM(APTH.DiscTaken) AS TotalDiscounts,
  SUM(APTH.Retainage) AS TotalRetainage,
  SUM(APTH.GrossAmt - ISNULL(APTH.DiscTaken, 0) - ISNULL(APTH.Retainage, 0)) AS NetPayable
FROM APTH
INNER JOIN APVM ON APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor
WHERE APTH.APCo = @APCo
GROUP BY APVM.Vendor, APVM.Name
ORDER BY TotalGross DESC""",
        explanation_template="""To get vendor invoice totals with discounts and retainage:
1. Join APTH (transactions) with APVM (vendors) on VendorGroup and Vendor
2. Sum GrossAmt for total invoiced
3. Include DiscTaken and Retainage columns
4. Calculate net as gross minus discounts minus retainage"""
    ),
    
    QueryTemplate(
        id="ap_open_invoices",
        base_question="Find open AP invoices pending payment",
        question_variants=[
            "List unpaid AP invoices awaiting payment",
            "Get AP invoices not yet fully paid",
            "Show outstanding vendor invoices pending payment",
            "Retrieve AP transactions with open balance",
        ],
        category=TrainingCategory.AP_QUERIES,
        primary_tables=["APTH", "APVM"],
        module="AP",
        complexity="intermediate",
        sql_template="""SELECT 
  APTH.APCo,
  APTH.Mth,
  APTH.APTrans,
  APVM.Name AS VendorName,
  APTH.APRef,
  APTH.InvDate,
  APTH.DueDate,
  APTH.GrossAmt,
  APTH.AmtPaid,
  APTH.GrossAmt - ISNULL(APTH.AmtPaid, 0) AS OpenBalance,
  DATEDIFF(day, APTH.DueDate, GETDATE()) AS DaysPastDue
FROM APTH
INNER JOIN APVM ON APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor
WHERE APTH.APCo = @APCo
  AND APTH.Status < 3  -- Not fully paid
  AND APTH.GrossAmt > ISNULL(APTH.AmtPaid, 0)
ORDER BY APTH.DueDate""",
        explanation_template="""To find open AP invoices:
1. Query APTH for invoice details, join APVM for vendor name
2. Filter by Status < 3 (not fully paid) or where GrossAmt > AmtPaid
3. Calculate open balance as GrossAmt minus AmtPaid
4. Include DaysPastDue for prioritization"""
    ),
    
    QueryTemplate(
        id="ap_hold_invoices",
        base_question="Find invoices on hold with hold reason",
        question_variants=[
            "List AP invoices currently on hold",
            "Get held vendor invoices with hold codes",
            "Show AP transactions with payment hold status",
            "Retrieve invoices blocked from payment with reason",
        ],
        category=TrainingCategory.AP_QUERIES,
        primary_tables=["APTH", "APVM", "APHD"],
        module="AP",
        complexity="intermediate",
        sql_template="""SELECT 
  APTH.APCo,
  APTH.Mth,
  APTH.APTrans,
  APVM.Name AS VendorName,
  APTH.APRef,
  APTH.GrossAmt,
  APTH.HoldCode,
  APHD.Description AS HoldReason
FROM APTH
INNER JOIN APVM ON APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor
LEFT JOIN APHD ON APTH.APCo = APHD.APCo AND APTH.HoldCode = APHD.HoldCode
WHERE APTH.APCo = @APCo
  AND APTH.HoldCode IS NOT NULL
ORDER BY APVM.Name, APTH.InvDate""",
        explanation_template="""To find invoices on hold:
1. Query APTH filtered where HoldCode IS NOT NULL
2. Join APVM for vendor name
3. Join APHD for hold code description
4. Useful for reviewing blocked payments"""
    ),

    # =========================================================================
    # JC QUERIES  
    # =========================================================================
    QueryTemplate(
        id="jc_job_cost_variance",
        base_question="Get job cost variance by phase comparing budget to actual",
        question_variants=[
            "Calculate cost variance between budget and actual by job phase",
            "Show budget vs actual comparison for job phases",
            "Analyze job cost overruns and underruns by phase",
            "Compare estimated to actual costs for each job phase",
            "List job phases with budget variance analysis",
        ],
        category=TrainingCategory.JC_QUERIES,
        primary_tables=["JCJP", "JCCP"],
        optional_tables=["JCJM", "JCCH"],
        module="JC",
        complexity="advanced",
        sql_template="""SELECT 
  JCJP.JCCo,
  JCJP.Job,
  JCJP.Phase,
  JCJP.Description AS PhaseDescription,
  JCCP.OrigEstCost AS BudgetCost,
  JCCP.ActualCost,
  JCCP.OrigEstCost - JCCP.ActualCost AS CostVariance,
  CASE 
    WHEN JCCP.OrigEstCost = 0 THEN 0
    ELSE (JCCP.ActualCost - JCCP.OrigEstCost) / JCCP.OrigEstCost * 100 
  END AS VariancePct
FROM JCJP
INNER JOIN JCCP ON JCJP.JCCo = JCCP.JCCo AND JCJP.Job = JCCP.Job AND JCJP.Phase = JCCP.Phase
WHERE JCJP.JCCo = @JCCo
  AND JCJP.Job = @Job
ORDER BY JCJP.Phase""",
        explanation_template="""To get job cost variance by phase:
1. Join JCJP (job phases) with JCCP (cost projections) on JCCo, Job, Phase
2. Compare OrigEstCost (budget) to ActualCost
3. Calculate variance as budget minus actual
4. Include percentage variance for analysis"""
    ),
    
    QueryTemplate(
        id="jc_jobs_over_budget",
        base_question="Find jobs over budget with remaining cost projection",
        question_variants=[
            "List jobs exceeding their budget",
            "Show jobs where actual costs exceed estimates",
            "Get over-budget jobs with projected final cost",
            "Identify jobs running over budget with cost to complete",
        ],
        category=TrainingCategory.JC_QUERIES,
        primary_tables=["JCJM", "JCCP"],
        module="JC",
        complexity="advanced",
        sql_template="""SELECT 
  JCJM.JCCo,
  JCJM.Job,
  JCJM.Description AS JobDescription,
  SUM(JCCP.OrigEstCost) AS TotalBudget,
  SUM(JCCP.ActualCost) AS TotalActual,
  SUM(JCCP.RemainCmtdCost) AS RemainingCommitted,
  SUM(JCCP.ProjCost) AS ProjectedFinal,
  SUM(JCCP.ProjCost) - SUM(JCCP.OrigEstCost) AS ProjectedOverrun
FROM JCJM
INNER JOIN JCCP ON JCJM.JCCo = JCCP.JCCo AND JCJM.Job = JCCP.Job
WHERE JCJM.JCCo = @JCCo
  AND JCJM.JobStatus = 1  -- Active jobs
GROUP BY JCJM.JCCo, JCJM.Job, JCJM.Description
HAVING SUM(JCCP.ActualCost) > SUM(JCCP.OrigEstCost)
ORDER BY ProjectedOverrun DESC""",
        explanation_template="""To find jobs over budget:
1. Join JCJM (job master) with JCCP (cost projections)
2. Sum OrigEstCost for budget, ActualCost for spent
3. Use HAVING to filter where actual exceeds budget
4. Include ProjCost for final cost projection"""
    ),
    
    QueryTemplate(
        id="jc_cost_detail",
        base_question="Get detailed job cost transactions by cost type",
        question_variants=[
            "List all job cost entries with cost type breakdown",
            "Show job cost detail grouped by cost type",
            "Retrieve JC transactions by labor, material, equipment",
            "Get cost detail by cost type for a job",
        ],
        category=TrainingCategory.JC_QUERIES,
        primary_tables=["JCCD", "JCJP", "JCCT"],
        module="JC",
        complexity="intermediate",
        sql_template="""SELECT 
  JCCD.JCCo,
  JCCD.Job,
  JCCD.Phase,
  JCCD.CostType,
  JCCT.Description AS CostTypeDesc,
  SUM(JCCD.ActualCost) AS TotalCost,
  SUM(JCCD.ActualUnits) AS TotalUnits,
  COUNT(*) AS TransactionCount
FROM JCCD
INNER JOIN JCJP ON JCCD.JCCo = JCJP.JCCo AND JCCD.Job = JCJP.Job AND JCCD.Phase = JCJP.Phase
LEFT JOIN JCCT ON JCCD.JCCo = JCCT.JCCo AND JCCD.CostType = JCCT.CostType
WHERE JCCD.JCCo = @JCCo
  AND JCCD.Job = @Job
GROUP BY JCCD.JCCo, JCCD.Job, JCCD.Phase, JCCD.CostType, JCCT.Description
ORDER BY JCCD.Phase, JCCD.CostType""",
        explanation_template="""To get job cost detail by cost type:
1. Query JCCD for cost detail records
2. Join JCCT for cost type descriptions
3. Group by phase and cost type
4. Sum ActualCost and ActualUnits"""
    ),
    
    QueryTemplate(
        id="jc_revenue_recognition",
        base_question="Calculate job revenue recognition with billing and cost",
        question_variants=[
            "Get revenue recognition status for jobs",
            "Show job billing vs cost for revenue analysis",
            "Calculate earned revenue by job",
            "Analyze job profitability with revenue and cost",
        ],
        category=TrainingCategory.JC_QUERIES,
        primary_tables=["JCJM", "JCCP"],
        module="JC",
        complexity="advanced",
        sql_template="""SELECT 
  JCJM.JCCo,
  JCJM.Job,
  JCJM.Description,
  JCJM.Contract,
  SUM(JCCP.OrigEstCost) AS TotalBudgetCost,
  SUM(JCCP.ActualCost) AS TotalActualCost,
  SUM(JCCP.BilledAmt) AS TotalBilled,
  SUM(JCCP.ActualCost) - SUM(JCCP.BilledAmt) AS UnbilledCost,
  CASE 
    WHEN SUM(JCCP.OrigEstCost) = 0 THEN 0
    ELSE SUM(JCCP.ActualCost) / SUM(JCCP.OrigEstCost) * 100 
  END AS PctComplete
FROM JCJM
INNER JOIN JCCP ON JCJM.JCCo = JCCP.JCCo AND JCJM.Job = JCCP.Job
WHERE JCJM.JCCo = @JCCo
GROUP BY JCJM.JCCo, JCJM.Job, JCJM.Description, JCJM.Contract
ORDER BY JCJM.Job""",
        explanation_template="""To calculate job revenue recognition:
1. Join JCJM with JCCP for cost and billing data
2. Sum ActualCost for costs incurred
3. Sum BilledAmt for amounts billed
4. Calculate percent complete for revenue recognition"""
    ),

    # =========================================================================
    # SL QUERIES
    # =========================================================================
    QueryTemplate(
        id="sl_subcontract_costs",
        base_question="Get subcontractor costs with original, change orders, invoiced, paid, and retainage",
        question_variants=[
            "Show subcontract summary with CO, invoiced and paid amounts",
            "List SL costs including change orders and retainage",
            "Calculate subcontract totals with all components",
            "Get complete subcontract cost breakdown",
        ],
        category=TrainingCategory.SL_QUERIES,
        primary_tables=["SLHD", "SLIT"],
        optional_tables=["APVM", "JCJM"],
        module="SL",
        complexity="advanced",
        sql_template="""SELECT 
  SLHD.SLCo,
  SLHD.SL AS Subcontract,
  SLHD.Description AS SubcontractDesc,
  SLHD.Vendor,
  SUM(SLIT.OrigCost) AS OriginalAmount,
  SUM(SLIT.CurCost) - SUM(SLIT.OrigCost) AS ChangeOrders,
  SUM(SLIT.CurCost) AS CurrentAmount,
  SUM(SLIT.InvCost) AS InvoicedAmount,
  SUM(SLIT.PaidCost) AS PaidAmount,
  SUM(SLIT.Retainage) AS RetainageHeld,
  SUM(SLIT.CurCost) - SUM(SLIT.InvCost) AS RemainingToBill
FROM SLHD
INNER JOIN SLIT ON SLHD.SLCo = SLIT.SLCo AND SLHD.SL = SLIT.SL
WHERE SLHD.SLCo = @SLCo
GROUP BY SLHD.SLCo, SLHD.SL, SLHD.Description, SLHD.Vendor
ORDER BY SLHD.SL""",
        explanation_template="""To get subcontract cost breakdown:
1. Join SLHD (header) with SLIT (items) on SLCo and SL
2. Sum OrigCost for original contract
3. Calculate change orders as CurCost - OrigCost
4. Include InvCost, PaidCost, and Retainage"""
    ),
    
    QueryTemplate(
        id="sl_work_in_progress",
        base_question="Calculate stored materials (Purchased - Installed) for SL billing",
        question_variants=[
            "Get SL work in progress for billing purposes",
            "Calculate materials purchased but not installed",
            "Show subcontract stored materials balance",
            "List SL items with WIP amount",
        ],
        category=TrainingCategory.SL_QUERIES,
        primary_tables=["SLWI", "SLIT"],
        module="SL",
        complexity="advanced",
        sql_template="""SELECT 
  SLWI.SLCo,
  SLWI.SL,
  SLWI.SLItem,
  SLIT.Description,
  SUM(SLWI.GrossAmt) AS PurchasedAmt,
  SUM(SLWI.InstalledAmt) AS InstalledAmt,
  SUM(SLWI.GrossAmt) - SUM(SLWI.InstalledAmt) AS StoredMaterials
FROM SLWI
INNER JOIN SLIT ON SLWI.SLCo = SLIT.SLCo AND SLWI.SL = SLIT.SL AND SLWI.SLItem = SLIT.SLItem
WHERE SLWI.SLCo = @SLCo
GROUP BY SLWI.SLCo, SLWI.SL, SLWI.SLItem, SLIT.Description
HAVING SUM(SLWI.GrossAmt) - SUM(SLWI.InstalledAmt) > 0
ORDER BY StoredMaterials DESC""",
        explanation_template="""To calculate stored materials for SL billing:
1. Query SLWI for work item details
2. Join SLIT for item description
3. Sum GrossAmt (purchased) and InstalledAmt
4. Stored materials = Purchased - Installed"""
    ),

    # =========================================================================
    # CROSS-MODULE QUERIES
    # =========================================================================
    QueryTemplate(
        id="cross_job_ap_invoices",
        base_question="Get AP invoices linked to job costs",
        question_variants=[
            "Show vendor invoices with job cost detail",
            "List AP transactions tied to JC",
            "Find job-related AP invoices",
            "Get AP invoices distributed to jobs",
        ],
        category=TrainingCategory.CROSS_MODULE,
        primary_tables=["APTH", "APTD", "JCCD"],
        optional_tables=["APVM", "JCJM"],
        module="AP",
        complexity="advanced",
        sql_template="""SELECT 
  APTH.APCo,
  APTH.APRef,
  APTH.InvDate,
  APTD.Job,
  APTD.Phase,
  APTD.CostType,
  APTD.GrossAmt AS DistributedAmt,
  APVM.Name AS VendorName
FROM APTH
INNER JOIN APTD ON APTH.APCo = APTD.APCo AND APTH.Mth = APTD.Mth AND APTH.APTrans = APTD.APTrans
INNER JOIN APVM ON APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor
WHERE APTH.APCo = @APCo
  AND APTD.Job IS NOT NULL
ORDER BY APTH.InvDate DESC, APTD.Job""",
        explanation_template="""To get AP invoices linked to job costs:
1. Join APTH (header) with APTD (detail) for distributions
2. Filter where APTD.Job IS NOT NULL
3. Include APVM for vendor name
4. Shows job cost impact of AP invoices"""
    ),
    
    QueryTemplate(
        id="cross_ar_job_billing",
        base_question="Get AR invoices by job with contract details",
        question_variants=[
            "Show customer invoices linked to jobs",
            "List AR billing by job and contract",
            "Get AR transactions with job reference",
            "Find invoices associated with contracts",
        ],
        category=TrainingCategory.CROSS_MODULE,
        primary_tables=["ARTH", "JCCM", "ARCM"],
        module="AR",
        complexity="intermediate",
        sql_template="""SELECT 
  ARTH.ARCo,
  ARTH.Invoice,
  ARTH.TransDate,
  ARTH.Amount,
  ARTH.Contract,
  JCCM.Description AS ContractDesc,
  ARCM.Name AS CustomerName
FROM ARTH
LEFT JOIN JCCM ON ARTH.JCCo = JCCM.JCCo AND ARTH.Contract = JCCM.Contract
INNER JOIN ARCM ON ARTH.CustGroup = ARCM.CustGroup AND ARTH.Customer = ARCM.Customer
WHERE ARTH.ARCo = @ARCo
  AND ARTH.Contract IS NOT NULL
ORDER BY ARTH.TransDate DESC""",
        explanation_template="""To get AR invoices by job/contract:
1. Query ARTH for invoice data
2. Join JCCM for contract description
3. Include ARCM for customer name
4. Filter where Contract IS NOT NULL"""
    ),
    
    QueryTemplate(
        id="cross_sl_ap_payments",
        base_question="Get SL invoices with AP payment status",
        question_variants=[
            "Show subcontract invoices and AP payment detail",
            "List SL billing with AP transaction links",
            "Get subcontract payment status from AP",
            "Find SL invoices matched to AP payments",
        ],
        category=TrainingCategory.CROSS_MODULE,
        primary_tables=["SLWI", "APTL", "APTD"],
        optional_tables=["APTH", "SLHD"],
        module="SL",
        complexity="advanced",
        sql_template="""SELECT 
  SLWI.SLCo,
  SLWI.SL,
  SLWI.SLItem,
  APTL.APCo,
  APTL.Mth,
  APTL.APTrans,
  APTL.APLine,
  APTD.GrossAmt,
  APTD.PaidAmt,
  APTD.GrossAmt - ISNULL(APTD.PaidAmt, 0) AS OpenAmt
FROM SLWI
INNER JOIN APTL ON SLWI.SLCo = APTL.SLCo AND SLWI.SL = APTL.SL AND SLWI.SLItem = APTL.SLItem
INNER JOIN APTD ON APTL.APCo = APTD.APCo AND APTL.Mth = APTD.Mth AND APTL.APTrans = APTD.APTrans AND APTL.APLine = APTD.APLine
WHERE SLWI.SLCo = @SLCo
ORDER BY SLWI.SL, SLWI.SLItem""",
        explanation_template="""To get SL invoices with AP payment status:
1. Start from SLWI (work items)
2. Join APTL to link SL to AP transactions
3. Join APTD for payment details
4. Calculate open amount as GrossAmt - PaidAmt"""
    ),

    # =========================================================================
    # BASIC TABLE QUERIES (for variety)
    # =========================================================================
    QueryTemplate(
        id="basic_ar_customers",
        base_question="List all customers with contact information",
        question_variants=[
            "Get customer master list with phone and email",
            "Show customer contact details",
            "Retrieve customer addresses and contacts",
            "List AR customers with full details",
        ],
        category=TrainingCategory.AR_QUERIES,
        primary_tables=["ARCM"],
        module="AR",
        complexity="basic",
        sql_template="""SELECT 
  CustGroup,
  Customer,
  Name,
  SortName,
  Phone,
  Fax,
  EMail,
  Contact,
  Address,
  City,
  State,
  Zip
FROM ARCM
WHERE CustGroup = @CustGroup
ORDER BY Name""",
        explanation_template="""To list customers with contact info:
1. Query ARCM for customer master data
2. Include Phone, Email, Contact fields
3. Include Address fields
4. Filter by CustGroup if needed"""
    ),
    
    QueryTemplate(
        id="basic_ap_vendors",
        base_question="List all vendors with payment terms",
        question_variants=[
            "Get vendor master list with terms",
            "Show vendor details with payment information",
            "Retrieve vendor addresses and payment terms",
            "List AP vendors with full details",
        ],
        category=TrainingCategory.AP_QUERIES,
        primary_tables=["APVM"],
        module="AP",
        complexity="basic",
        sql_template="""SELECT 
  VendorGroup,
  Vendor,
  Name,
  SortName,
  Phone,
  Fax,
  EMail,
  PayTerms,
  Address,
  City,
  State,
  Zip
FROM APVM
WHERE VendorGroup = @VendorGroup
ORDER BY Name""",
        explanation_template="""To list vendors with payment terms:
1. Query APVM for vendor master data
2. Include PayTerms for payment terms
3. Include contact and address fields
4. Filter by VendorGroup if needed"""
    ),
    
    QueryTemplate(
        id="basic_jc_jobs",
        base_question="List active jobs with status and dates",
        question_variants=[
            "Get job master list with project details",
            "Show all active jobs",
            "Retrieve job list with start and end dates",
            "List jobs by status",
        ],
        category=TrainingCategory.JC_QUERIES,
        primary_tables=["JCJM"],
        module="JC",
        complexity="basic",
        sql_template="""SELECT 
  JCCo,
  Job,
  Description,
  Contract,
  JobStatus,
  StartDate,
  ProjectedCloseDate,
  ActualCloseDate,
  BidDate,
  ProjectMgr
FROM JCJM
WHERE JCCo = @JCCo
  AND JobStatus = 1  -- Active
ORDER BY Job""",
        explanation_template="""To list active jobs:
1. Query JCJM for job master data
2. Filter JobStatus = 1 for active jobs
3. Include key dates and project manager
4. Optionally include Contract reference"""
    ),
]
