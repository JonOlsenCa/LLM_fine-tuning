# Copyright 2024-2025 Viewpoint, Inc.
# Licensed under the Apache License, Version 2.0.

"""
SQL Example Generator Module

Generates SQL training examples using schema-in-prompt format.
Each example includes:
1. A natural language question
2. Relevant DDL (CREATE TABLE statements)
3. Expected SQL output with explanation
"""

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import V4Config, TrainingCategory, CategoryConfig, TableConfig
from .ddl_extractor import DDLExtractor, create_ddl_for_question

logger = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    """A single training example in schema-in-prompt format."""
    instruction: str
    input: str
    output: str
    category: str = ""
    complexity: str = "basic"
    tables_used: List[str] = field(default_factory=list)
    
    def to_alpaca(self) -> Dict:
        """Convert to Alpaca format for LLaMA Factory."""
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output
        }


@dataclass
class QuestionTemplate:
    """Template for generating training questions."""
    template: str
    category: TrainingCategory
    primary_tables: List[str]
    required_columns: List[str] = field(default_factory=list)
    expected_patterns: List[str] = field(default_factory=list)
    complexity: str = "basic"
    sql_template: str = ""
    explanation_template: str = ""


class SQLExampleGenerator:
    """
    Generate SQL training examples using schema-in-prompt format.
    
    This follows the SQLCoder methodology:
    1. Question + DDL in prompt
    2. SQL answer with explanation
    3. Focus on SQL generation, not schema memorization
    """
    
    def __init__(self, config: V4Config, ddl_extractor: DDLExtractor):
        self.config = config
        self.ddl = ddl_extractor
        self.templates = self._load_question_templates()
        
        logger.info(f"SQLExampleGenerator initialized with {len(self.templates)} templates")
    
    def generate_all(self) -> List[TrainingExample]:
        """Generate all training examples based on config."""
        examples = []
        
        for cat_name, cat_config in self.config.categories.items():
            if cat_name == TrainingCategory.NEGATIVE.value:
                continue  # Handled by NegativeExampleGenerator
            
            cat_examples = self.generate_for_category(cat_config)
            examples.extend(cat_examples)
            logger.info(f"Generated {len(cat_examples)} examples for {cat_name}")
        
        logger.info(f"Total examples generated: {len(examples)}")
        return examples
    
    def generate_for_category(self, category: CategoryConfig) -> List[TrainingExample]:
        """Generate examples for a specific category."""
        examples = []
        
        # Get templates for this category
        cat_templates = [t for t in self.templates if t.category.value == category.name.lower().replace(" ", "_")]
        
        if not cat_templates:
            cat_templates = self._generate_templates_for_category(category)
        
        # Generate examples from templates
        target_per_complexity = category.target_count // len(category.complexity_levels)
        
        for complexity in category.complexity_levels:
            complexity_templates = [t for t in cat_templates if t.complexity == complexity]
            if not complexity_templates:
                complexity_templates = cat_templates
            
            count = 0
            while count < target_per_complexity and complexity_templates:
                template = random.choice(complexity_templates)
                example = self._generate_from_template(template, complexity)
                if example:
                    examples.append(example)
                    count += 1
        
        return examples
    
    def _generate_from_template(
        self, 
        template: QuestionTemplate, 
        complexity: str
    ) -> Optional[TrainingExample]:
        """Generate a single example from a template."""
        try:
            # Get DDL for the required tables
            ddl_text = create_ddl_for_question(
                self.ddl,
                template.primary_tables,
                include_related=True,
                max_tables=self.config.max_ddl_tables
            )
            
            if not ddl_text:
                logger.warning(f"Could not generate DDL for template: {template.template}")
                return None
            
            # Format the question
            question = self._format_question(template)
            
            # Build the instruction (question + DDL)
            instruction = self._build_instruction(question, ddl_text)
            
            # Generate the output (explanation + SQL)
            output = self._generate_output(template, complexity)
            
            return TrainingExample(
                instruction=instruction,
                input="",
                output=output,
                category=template.category.value,
                complexity=complexity,
                tables_used=template.primary_tables
            )
            
        except Exception as e:
            logger.error(f"Error generating from template: {e}")
            return None
    
    def _build_instruction(self, question: str, ddl: str) -> str:
        """Build the instruction with question and DDL."""
        return self.config.user_prompt_template.format(
            question=question,
            ddl_statements=ddl
        )
    
    def _format_question(self, template: QuestionTemplate) -> str:
        """Format the question template with any variable substitution."""
        question = template.template
        
        # Add variations to make questions more natural
        prefixes = [
            "",
            "Write SQL to ",
            "Create a query to ",
            "How do I ",
            "I need to ",
            "Generate SQL to ",
        ]
        
        # Only add prefix if template doesn't already start with a verb
        if not any(question.lower().startswith(p.lower()) for p in ["write", "create", "how", "get", "find", "calculate", "show", "list"]):
            question = random.choice(prefixes) + question.lower()
        
        return question
    
    def _generate_output(self, template: QuestionTemplate, complexity: str) -> str:
        """Generate the output with explanation and SQL."""
        lines = []
        
        # Add explanation
        if self.config.include_explanations and template.explanation_template:
            lines.append(template.explanation_template)
            lines.append("")
        
        # Add SQL
        if template.sql_template:
            sql = template.sql_template
            
            # Add Vista patterns if configured
            if self.config.include_vista_patterns:
                sql = self._add_vista_patterns(sql, template.primary_tables)
            
            lines.append("```sql")
            lines.append(sql)
            lines.append("```")
        
        return "\n".join(lines)
    
    def _add_vista_patterns(self, sql: str, tables: List[str]) -> str:
        """Add Vista-specific patterns to SQL."""
        # Add WITH (NOLOCK) if not present
        if "WITH (NOLOCK)" not in sql:
            for table in tables:
                sql = sql.replace(f"FROM {table}", f"FROM {table} WITH (NOLOCK)")
                sql = sql.replace(f"JOIN {table}", f"JOIN {table} WITH (NOLOCK)")
        
        return sql
    
    def _load_question_templates(self) -> List[QuestionTemplate]:
        """Load question templates from configuration."""
        return CORE_QUESTION_TEMPLATES
    
    def _generate_templates_for_category(self, category: CategoryConfig) -> List[QuestionTemplate]:
        """Generate templates dynamically for a category."""
        templates = []
        
        # Create basic templates based on primary tables
        for table in category.primary_tables:
            table_info = self.ddl.get_table(table)
            if not table_info:
                continue
            
            # Basic select template
            templates.append(QuestionTemplate(
                template=f"Get all records from {table}",
                category=TrainingCategory.AR_QUERIES,  # Will be overridden
                primary_tables=[table],
                complexity="basic",
                sql_template=f"SELECT *\nFROM {table}\nWHERE Co = @Co",
                explanation_template=f"Query all records from {table} ({table_info.description})."
            ))
            
            # Count template
            templates.append(QuestionTemplate(
                template=f"Count records in {table} by company",
                category=TrainingCategory.AR_QUERIES,
                primary_tables=[table],
                complexity="basic",
                sql_template=f"SELECT Co, COUNT(*) AS RecordCount\nFROM {table}\nGROUP BY Co",
                explanation_template=f"Count {table} records grouped by company."
            ))
        
        return templates


# =============================================================================
# CORE QUESTION TEMPLATES
# =============================================================================

CORE_QUESTION_TEMPLATES = [
    # =========================================================================
    # AR QUERIES
    # =========================================================================
    QuestionTemplate(
        template="Calculate AR aging buckets (30/60/90+ days) for unpaid invoices by customer",
        category=TrainingCategory.AR_QUERIES,
        primary_tables=["ARTH", "ARCM"],
        required_columns=["PayFullDate", "TransDate", "Amount", "Customer", "CustGroup"],
        expected_patterns=["DATEDIFF", "CASE WHEN", "PayFullDate IS NULL", "GROUP BY"],
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
1. Use ARTH for transaction data and ARCM for customer names
2. Filter PayFullDate IS NULL to get only unpaid invoices
3. Use DATEDIFF and CASE WHEN to bucket by age
4. Group by customer for the summary"""
    ),
    
    QuestionTemplate(
        template="Find all unpaid AR invoices older than 60 days",
        category=TrainingCategory.AR_QUERIES,
        primary_tables=["ARTH", "ARCM"],
        required_columns=["PayFullDate", "TransDate", "Amount"],
        complexity="intermediate",
        sql_template="""SELECT 
  ARTH.ARCo,
  ARTH.Mth,
  ARTH.ARTrans,
  ARCM.Name AS CustomerName,
  ARTH.TransDate,
  ARTH.Amount,
  DATEDIFF(day, ARTH.TransDate, GETDATE()) AS DaysOutstanding
FROM ARTH
INNER JOIN ARCM ON ARTH.CustGroup = ARCM.CustGroup AND ARTH.Customer = ARCM.Customer
WHERE ARTH.ARCo = @ARCo
  AND ARTH.PayFullDate IS NULL
  AND DATEDIFF(day, ARTH.TransDate, GETDATE()) > 60
ORDER BY ARTH.TransDate""",
        explanation_template="""To find unpaid invoices over 60 days:
1. Join ARTH to ARCM for customer information
2. Filter PayFullDate IS NULL (unpaid)
3. Use DATEDIFF to calculate age and filter > 60 days"""
    ),
    
    QuestionTemplate(
        template="Get customer balance summary by customer group",
        category=TrainingCategory.AR_QUERIES,
        primary_tables=["ARTH", "ARCM"],
        complexity="intermediate",
        sql_template="""SELECT 
  ARTH.CustGroup,
  COUNT(DISTINCT ARTH.Customer) AS CustomerCount,
  SUM(CASE WHEN ARTH.PayFullDate IS NULL THEN ARTH.Amount ELSE 0 END) AS OpenBalance,
  SUM(ARTH.Amount) AS TotalBilled
FROM ARTH
INNER JOIN ARCM ON ARTH.CustGroup = ARCM.CustGroup AND ARTH.Customer = ARCM.Customer
WHERE ARTH.ARCo = @ARCo
GROUP BY ARTH.CustGroup
ORDER BY OpenBalance DESC""",
        explanation_template="""Customer balance summary by group:
1. Join ARTH to ARCM for customer details
2. Use conditional SUM for open vs total balances
3. Group by CustGroup for summary"""
    ),
    
    # =========================================================================
    # AP QUERIES
    # =========================================================================
    QuestionTemplate(
        template="Track AP hold status distinguishing retainage vs non-retainage holds",
        category=TrainingCategory.AP_QUERIES,
        primary_tables=["APTD", "APHD", "APCO"],
        required_columns=["HoldCode", "RetHoldCode", "PayType"],
        complexity="advanced",
        sql_template="""SELECT 
  APTD.APCo,
  APTD.Vendor,
  APTD.Mth,
  APTD.APTrans,
  APHD.HoldCode,
  CASE WHEN APHD.HoldCode = APCO.RetHoldCode 
       THEN 'Retainage Hold' 
       ELSE 'Non-Retainage Hold' END AS HoldType,
  APTD.Amount
FROM APTD
INNER JOIN APHD ON APTD.APCo = APHD.APCo 
  AND APTD.Mth = APHD.Mth 
  AND APTD.APTrans = APHD.APTrans 
  AND APTD.APLine = APHD.APLine
INNER JOIN APCO ON APTD.APCo = APCO.APCo
WHERE APTD.APCo = @APCo
  AND APHD.HoldCode IS NOT NULL
ORDER BY APTD.Vendor, APTD.Mth""",
        explanation_template="""To distinguish retainage vs non-retainage holds:
1. Join APTD to APHD for hold details
2. Join APCO to get RetHoldCode setting
3. Compare APHD.HoldCode to APCO.RetHoldCode
4. If equal, it's a retainage hold; otherwise non-retainage"""
    ),
    
    QuestionTemplate(
        template="Get vendor invoice totals with discounts and retainage",
        category=TrainingCategory.AP_QUERIES,
        primary_tables=["APTH", "APVM"],
        complexity="intermediate",
        sql_template="""SELECT 
  APVM.Vendor,
  APVM.Name AS VendorName,
  COUNT(APTH.APTrans) AS InvoiceCount,
  SUM(APTH.GrossAmt) AS GrossAmount,
  SUM(APTH.DiscOffer) AS DiscountsOffered,
  SUM(APTH.Retainage) AS RetainageHeld,
  SUM(APTH.Balance) AS OpenBalance
FROM APTH
INNER JOIN APVM ON APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor
WHERE APTH.APCo = @APCo
GROUP BY APVM.Vendor, APVM.Name
ORDER BY OpenBalance DESC""",
        explanation_template="""Vendor invoice summary with discounts and retainage:
1. Join APTH to APVM for vendor details
2. Aggregate by vendor
3. Include GrossAmt, DiscOffer, Retainage, and Balance"""
    ),
    
    QuestionTemplate(
        template="Reconcile AP oncost batch lines with original transactions",
        category=TrainingCategory.AP_QUERIES,
        primary_tables=["APLB", "APHB", "APTL", "APTH", "APVM"],
        required_columns=["ocApplyMth", "ocApplyTrans", "ocApplyLine"],
        complexity="advanced",
        sql_template="""SELECT 
  APLB.Co AS BatchCo,
  APLB.Mth AS BatchMth,
  APLB.BatchId,
  APLB.BatchSeq,
  APLB.ocApplyMth,
  APLB.ocApplyTrans,
  APLB.ocApplyLine,
  APTL.APCo AS OrigCo,
  APTL.Mth AS OrigMth,
  APTL.APTrans AS OrigTrans,
  APTL.APLine AS OrigLine,
  APTL.GrossAmt AS OrigAmount,
  APLB.GrossAmt AS BatchAmount,
  APVM.Name AS VendorName
FROM APLB
INNER JOIN APHB ON APLB.Co = APHB.Co AND APLB.Mth = APHB.Mth AND APLB.BatchId = APHB.BatchId
INNER JOIN APTL ON APLB.ocApplyMth = APTL.Mth 
  AND APLB.ocApplyTrans = APTL.APTrans 
  AND APLB.ocApplyLine = APTL.APLine
  AND APLB.Co = APTL.APCo
INNER JOIN APTH ON APTL.APCo = APTH.APCo AND APTL.Mth = APTH.Mth AND APTL.APTrans = APTH.APTrans
INNER JOIN APVM ON APTH.VendorGroup = APVM.VendorGroup AND APTH.Vendor = APVM.Vendor
WHERE APLB.Co = @Co
ORDER BY APLB.BatchId, APLB.BatchSeq""",
        explanation_template="""To reconcile AP oncost batches with original transactions:
1. Join APLB (batch lines) to APTL (original lines) using ocApplyMth, ocApplyTrans, ocApplyLine
2. Include APHB for batch header info
3. Join to APTH and APVM for vendor context
4. Compare batch vs original amounts"""
    ),
    
    # =========================================================================
    # JC QUERIES
    # =========================================================================
    QuestionTemplate(
        template="Aggregate job cost estimates by phase and cost type with item vs phase unit distinctions",
        category=TrainingCategory.JC_QUERIES,
        primary_tables=["JCJP", "JCCH", "JCCP", "JCCT"],
        required_columns=["ItemUnitFlag", "PhaseUnitFlag", "OrigEstCost", "CurrEstCost", "CurrEstHours"],
        complexity="advanced",
        sql_template="""SELECT 
  JCJP.JCCo,
  JCJP.Job,
  JCJP.Phase,
  JCCT.Description AS CostTypeDesc,
  JCCH.ItemUnitFlag,
  JCCH.PhaseUnitFlag,
  CASE WHEN JCCH.ItemUnitFlag = 'Y' THEN 'Item Units'
       WHEN JCCH.PhaseUnitFlag = 'Y' THEN 'Phase Units'
       ELSE 'No Units' END AS UnitType,
  JCCP.OrigEstCost,
  JCCP.CurrEstCost,
  JCCP.CurrEstHours,
  JCCP.ActualCost,
  JCCP.CurrEstCost - JCCP.ActualCost AS RemainingBudget
FROM JCJP
INNER JOIN JCCP ON JCJP.JCCo = JCCP.JCCo 
  AND JCJP.Job = JCCP.Job 
  AND JCJP.PhaseGroup = JCCP.PhaseGroup 
  AND JCJP.Phase = JCCP.Phase
INNER JOIN JCCH ON JCCP.JCCo = JCCH.JCCo 
  AND JCCP.Job = JCCH.Job 
  AND JCCP.PhaseGroup = JCCH.PhaseGroup 
  AND JCCP.Phase = JCCH.Phase 
  AND JCCP.CostType = JCCH.CostType
INNER JOIN JCCT ON JCCP.PhaseGroup = JCCT.PhaseGroup AND JCCP.CostType = JCCT.CostType
WHERE JCJP.JCCo = @JCCo
  AND JCJP.Job = @Job
ORDER BY JCJP.Phase, JCCT.CostType""",
        explanation_template="""To aggregate job cost estimates with unit type distinctions:
1. Start with JCJP (Job Phase) for phase definitions
2. Join JCCP (Cost Phase) for estimate and actual amounts
3. Join JCCH (Cost Header) for ItemUnitFlag/PhaseUnitFlag settings
4. Join JCCT for cost type descriptions
5. Use CASE WHEN to label unit types"""
    ),
    
    QuestionTemplate(
        template="Get job cost variance by phase comparing budget to actual",
        category=TrainingCategory.JC_QUERIES,
        primary_tables=["JCJM", "JCCP"],
        complexity="intermediate",
        sql_template="""SELECT 
  JCJM.Job,
  JCJM.Description AS JobDescription,
  JCCP.Phase,
  JCCP.CostType,
  JCCP.OrigEstCost AS OriginalBudget,
  JCCP.CurrEstCost AS CurrentBudget,
  JCCP.ActualCost,
  JCCP.CurrEstCost - JCCP.ActualCost AS Variance,
  CASE WHEN JCCP.CurrEstCost <> 0 
       THEN (JCCP.ActualCost / JCCP.CurrEstCost) * 100 
       ELSE 0 END AS PercentComplete
FROM JCJM
INNER JOIN JCCP ON JCJM.JCCo = JCCP.JCCo AND JCJM.Job = JCCP.Job
WHERE JCJM.JCCo = @JCCo
  AND JCJM.Job = @Job
ORDER BY JCCP.Phase, JCCP.CostType""",
        explanation_template="""Job cost variance by phase:
1. Join JCJM (Job Master) to JCCP (Cost Phase)
2. Calculate variance as CurrEstCost - ActualCost
3. Calculate percent complete from actuals vs budget"""
    ),
    
    QuestionTemplate(
        template="Find jobs over budget with remaining cost projection",
        category=TrainingCategory.JC_QUERIES,
        primary_tables=["JCJM", "JCCD", "JCCP"],
        complexity="intermediate",
        sql_template="""SELECT 
  JCJM.Job,
  JCJM.Description,
  SUM(JCCP.CurrEstCost) AS TotalBudget,
  SUM(JCCP.ActualCost) AS TotalActual,
  SUM(JCCP.CurrEstCost) - SUM(JCCP.ActualCost) AS RemainingBudget,
  CASE WHEN SUM(JCCP.CurrEstCost) < SUM(JCCP.ActualCost) 
       THEN 'OVER BUDGET' ELSE 'OK' END AS Status
FROM JCJM
INNER JOIN JCCP ON JCJM.JCCo = JCCP.JCCo AND JCJM.Job = JCCP.Job
WHERE JCJM.JCCo = @JCCo
GROUP BY JCJM.Job, JCJM.Description
HAVING SUM(JCCP.ActualCost) > SUM(JCCP.CurrEstCost)
ORDER BY (SUM(JCCP.ActualCost) - SUM(JCCP.CurrEstCost)) DESC""",
        explanation_template="""Find jobs over budget:
1. Aggregate JCCP by job from JCJM
2. Compare total ActualCost to CurrEstCost
3. Use HAVING to filter only over-budget jobs
4. Sort by amount over budget"""
    ),
    
    # =========================================================================
    # SL QUERIES
    # =========================================================================
    QuestionTemplate(
        template="Get subcontractor costs with original, change orders, invoiced, paid, and retainage by vendor",
        category=TrainingCategory.SL_QUERIES,
        primary_tables=["SLHD", "SLIT", "APVM"],
        required_columns=["OrigCost", "CurCost", "InvCost", "Retainage", "VendorGroup"],
        complexity="advanced",
        sql_template="""SELECT 
  APVM.Vendor,
  APVM.Name AS VendorName,
  SLHD.SL AS SubcontractNum,
  SLHD.Description AS SubcontractDesc,
  SUM(SLIT.OrigCost) AS OriginalCost,
  SUM(SLIT.CurCost - SLIT.OrigCost) AS ChangeOrderCost,
  SUM(SLIT.CurCost) AS CurrentCost,
  SUM(SLIT.InvCost) AS InvoicedCost,
  SUM(SLIT.Retainage) AS RetainageHeld,
  SUM(SLIT.CurCost - SLIT.InvCost) AS RemainingToBill
FROM SLHD
INNER JOIN SLIT ON SLHD.SLCo = SLIT.SLCo AND SLHD.SL = SLIT.SL
INNER JOIN APVM ON SLHD.VendorGroup = APVM.VendorGroup AND SLHD.Vendor = APVM.Vendor
WHERE SLHD.SLCo = @SLCo
GROUP BY APVM.Vendor, APVM.Name, SLHD.SL, SLHD.Description
ORDER BY APVM.Name, SLHD.SL""",
        explanation_template="""Subcontractor cost breakdown by vendor:
1. Join SLHD (Header) to SLIT (Items) for subcontract details
2. Join APVM for vendor names
3. OrigCost = original contract amount
4. CurCost - OrigCost = change order amounts
5. InvCost = amounts invoiced
6. Retainage = amounts held back"""
    ),
    
    QuestionTemplate(
        template="Calculate stored materials (Purchased - Installed) for SL billing",
        category=TrainingCategory.SL_QUERIES,
        primary_tables=["SLWI", "SLIT"],
        required_columns=["StoredMatls", "WCCost", "SMRetPct", "WCRetPct"],
        complexity="advanced",
        sql_template="""SELECT 
  SLWI.SLCo,
  SLWI.SL,
  SLWI.SLItem,
  SLIT.Description AS ItemDescription,
  SLWI.StoredMatls,
  SLWI.WCCost AS WorkCompletedCost,
  SLWI.StoredMatls + SLWI.WCCost AS TotalBillable,
  SLWI.WCRetAmt AS WorkRetainage,
  SLWI.SMRetAmt AS MaterialsRetainage,
  SLWI.WCRetAmt + SLWI.SMRetAmt AS TotalRetainage
FROM SLWI
INNER JOIN SLIT ON SLWI.SLCo = SLIT.SLCo AND SLWI.SL = SLIT.SL AND SLWI.SLItem = SLIT.SLItem
WHERE SLWI.SLCo = @SLCo
  AND SLWI.StoredMatls <> 0
ORDER BY SLWI.SL, SLWI.SLItem""",
        explanation_template="""Stored materials for SL billing:
1. SLWI contains work item/billing details
2. StoredMatls = Purchased - Installed (materials on-site but not yet used)
3. WCCost = Work Completed Cost
4. WCRetAmt and SMRetAmt = separate retainage for work vs materials
5. Total billable = WCCost + StoredMatls"""
    ),
    
    # =========================================================================
    # CROSS-MODULE QUERIES
    # =========================================================================
    QuestionTemplate(
        template="Join SLWI retainage amounts to matching APTD transactions",
        category=TrainingCategory.CROSS_MODULE,
        primary_tables=["SLWI", "APTL", "APTD", "APCO"],
        required_columns=["RetPayType", "SL", "SLItem"],
        complexity="advanced",
        sql_template="""SELECT 
  SLWI.SLCo,
  SLWI.SL,
  SLWI.SLItem,
  SLWI.WCRetAmt + SLWI.SMRetAmt AS TotalRetainage,
  APTL.APCo,
  APTL.Mth,
  APTL.APTrans,
  APTL.APLine,
  APTD.PayType,
  APTD.Amount AS APAmount,
  CASE WHEN APTD.PayType = APCO.RetPayType 
       THEN 'Retainage Payment' 
       ELSE 'Regular Payment' END AS PaymentType
FROM SLWI
INNER JOIN APTL ON SLWI.SLCo = APTL.APCo 
  AND SLWI.SL = APTL.SL 
  AND SLWI.SLItem = APTL.SLItem
INNER JOIN APTD ON APTL.APCo = APTD.APCo 
  AND APTL.Mth = APTD.Mth 
  AND APTL.APTrans = APTD.APTrans 
  AND APTL.APLine = APTD.APLine
INNER JOIN APCO ON APTD.APCo = APCO.APCo
WHERE SLWI.SLCo = @SLCo
  AND APTD.PayType = APCO.RetPayType
ORDER BY SLWI.SL, SLWI.SLItem, APTL.Mth""",
        explanation_template="""Join SL retainage to AP payments:
1. SLWI → APTL: Join on SLCo=APCo, SL, SLItem
2. APTL → APTD: Full key join for payment details
3. Check APTD.PayType against APCO.RetPayType
4. If PayType = RetPayType, it's a retainage payment"""
    ),
    
    QuestionTemplate(
        template="What is the relationship between JCJP (Job Phase) and JCCP (Cost Code Phase)?",
        category=TrainingCategory.CROSS_MODULE,
        primary_tables=["JCJP", "JCCP", "JCCH", "JCJI"],
        complexity="intermediate",
        sql_template="""-- JCJP = Job/Contract Phase (billing-oriented)
-- JCCP = Cost Code Phase (cost tracking)
-- They link on JCCo, Job, PhaseGroup, Phase

SELECT 
  JCJP.JCCo,
  JCJP.Job,
  JCJP.Phase,
  JCJP.Description AS PhaseDescription,
  JCCP.CostType,
  JCCP.OrigEstCost,
  JCCP.ActualCost,
  JCCH.ItemUnitFlag,
  JCCH.PhaseUnitFlag
FROM JCJP
INNER JOIN JCCP ON JCJP.JCCo = JCCP.JCCo 
  AND JCJP.Job = JCCP.Job 
  AND JCJP.PhaseGroup = JCCP.PhaseGroup 
  AND JCJP.Phase = JCCP.Phase
INNER JOIN JCCH ON JCCP.JCCo = JCCH.JCCo 
  AND JCCP.Job = JCCH.Job 
  AND JCCP.PhaseGroup = JCCH.PhaseGroup 
  AND JCCP.Phase = JCCH.Phase 
  AND JCCP.CostType = JCCH.CostType
WHERE JCJP.JCCo = @JCCo
  AND JCJP.Job = @Job""",
        explanation_template="""JCJP vs JCCP relationship:
- JCJP (Job Phase) = Phase definitions for billing purposes, links to JCJI for contract items
- JCCP (Cost Code Phase) = Cost tracking by phase/cost type, links to JCCH for cost headers
- Join key: JCCo, Job, PhaseGroup, Phase
- JCJP is billing-oriented; JCCP is cost-oriented
- JCCH provides the ItemUnitFlag/PhaseUnitFlag settings for unit tracking"""
    ),
    
    QuestionTemplate(
        template="Link SM WorkOrder to AR billing through JC contracts",
        category=TrainingCategory.CROSS_MODULE,
        primary_tables=["SMWorkOrder", "SMServiceSite", "JCJM", "JCCM", "ARTH"],
        complexity="advanced",
        sql_template="""SELECT 
  SMWorkOrder.WorkOrder,
  SMWorkOrder.Description AS WODescription,
  SMServiceSite.ServiceSite,
  JCJM.Job,
  JCJM.Description AS JobDescription,
  JCCM.Contract,
  JCCM.Description AS ContractDescription,
  ARTH.ARCo,
  ARTH.Mth,
  ARTH.ARTrans,
  ARTH.Amount AS BilledAmount
FROM SMWorkOrder
INNER JOIN SMServiceSite ON SMWorkOrder.SMCo = SMServiceSite.SMCo 
  AND SMWorkOrder.ServiceSite = SMServiceSite.ServiceSite
INNER JOIN JCJM ON SMServiceSite.JCCo = JCJM.JCCo 
  AND SMServiceSite.Job = JCJM.Job
INNER JOIN JCCM ON JCJM.JCCo = JCCM.JCCo 
  AND JCJM.Contract = JCCM.Contract
INNER JOIN ARTH ON JCCM.JCCo = ARTH.JCCo 
  AND JCCM.Contract = ARTH.Contract
WHERE SMWorkOrder.SMCo = @SMCo
ORDER BY SMWorkOrder.WorkOrder, ARTH.Mth""",
        explanation_template="""SM WorkOrder to AR billing path:
1. SMWorkOrder → SMServiceSite (via ServiceSite)
2. SMServiceSite → JCJM (via JCCo, Job)
3. JCJM → JCCM (via JCCo, Contract)
4. JCCM → ARTH (via JCCo, Contract for billing)
Alternative: Use SMWorkOrderInvoice for direct invoice references"""
    ),
]
