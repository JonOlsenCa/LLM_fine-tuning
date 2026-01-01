# Copyright 2024-2025 Viewpoint, Inc.
# Licensed under the Apache License, Version 2.0.

"""
Negative Example Generator Module

Generates training examples for hallucination prevention.
These teach the model to:
1. Reject queries for non-existent tables
2. Reject queries for tables not in the provided schema
3. Suggest correct alternatives when possible
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .config import V4Config, TrainingCategory
from .ddl_extractor import DDLExtractor
from .sql_generator import TrainingExample

logger = logging.getLogger(__name__)


@dataclass
class FakeTableDefinition:
    """Definition of a fake table that doesn't exist in Vista."""
    name: str
    description: str  # What someone might think it is
    correct_alternative: str  # The actual Vista table to use
    correct_explanation: str  # Why the alternative is correct


# Common fake table names that LLMs might hallucinate
FAKE_TABLES = [
    FakeTableDefinition(
        name="ARAgingReport",
        description="AR aging report table",
        correct_alternative="ARTH",
        correct_explanation="Use ARTH (AR Transaction Header) with DATEDIFF calculations for aging. There is no pre-built ARAgingReport table in Vista."
    ),
    FakeTableDefinition(
        name="Customers",
        description="Customer master table",
        correct_alternative="ARCM",
        correct_explanation="Use ARCM (AR Customer Master) for customer information. Vista uses abbreviated table names."
    ),
    FakeTableDefinition(
        name="Customer",
        description="Customer table",
        correct_alternative="ARCM",
        correct_explanation="Use ARCM (AR Customer Master) for customer information."
    ),
    FakeTableDefinition(
        name="Vendors",
        description="Vendor master table",
        correct_alternative="APVM",
        correct_explanation="Use APVM (AP Vendor Master) for vendor information. Vista uses abbreviated table names."
    ),
    FakeTableDefinition(
        name="Vendor",
        description="Vendor table",
        correct_alternative="APVM",
        correct_explanation="Use APVM (AP Vendor Master) for vendor information."
    ),
    FakeTableDefinition(
        name="Employees",
        description="Employee master table",
        correct_alternative="PREH",
        correct_explanation="Use PREH (PR Employee Header) for employee information."
    ),
    FakeTableDefinition(
        name="Employee",
        description="Employee table",
        correct_alternative="PREH",
        correct_explanation="Use PREH (PR Employee Header) for employee information."
    ),
    FakeTableDefinition(
        name="Jobs",
        description="Jobs table",
        correct_alternative="JCJM",
        correct_explanation="Use JCJM (JC Job Master) for job/project information."
    ),
    FakeTableDefinition(
        name="Projects",
        description="Projects table",
        correct_alternative="JCJM",
        correct_explanation="Use JCJM (JC Job Master) for project information. Vista calls projects 'Jobs'."
    ),
    FakeTableDefinition(
        name="Invoices",
        description="Invoices table",
        correct_alternative="ARTH/APTH",
        correct_explanation="For AR invoices, use ARTH (AR Transaction Header). For AP invoices, use APTH (AP Transaction Header)."
    ),
    FakeTableDefinition(
        name="ARInvoice",
        description="AR Invoice table",
        correct_alternative="ARTH",
        correct_explanation="Use ARTH (AR Transaction Header) for AR invoices."
    ),
    FakeTableDefinition(
        name="APInvoice",
        description="AP Invoice table",
        correct_alternative="APTH",
        correct_explanation="Use APTH (AP Transaction Header) for AP invoices."
    ),
    FakeTableDefinition(
        name="TimeCards",
        description="Timecards table",
        correct_alternative="PRTH",
        correct_explanation="Use PRTH (PR Timecard Header) for timecard information."
    ),
    FakeTableDefinition(
        name="TimeCard",
        description="Timecard table",
        correct_alternative="PRTH",
        correct_explanation="Use PRTH (PR Timecard Header) for timecard information."
    ),
    FakeTableDefinition(
        name="TimecardHeader",
        description="Timecard header table",
        correct_alternative="PRTH",
        correct_explanation="Use PRTH (PR Timecard Header) for timecard headers."
    ),
    FakeTableDefinition(
        name="Departments",
        description="Departments table",
        correct_alternative="JCDP",
        correct_explanation="Use JCDP (JC Department) for department information."
    ),
    FakeTableDefinition(
        name="Locations",
        description="Locations table",
        correct_alternative="HQLC",
        correct_explanation="Use HQLC (HQ Location) for location information."
    ),
    FakeTableDefinition(
        name="Companies",
        description="Companies table",
        correct_alternative="HQCO",
        correct_explanation="Use HQCO (HQ Company) for company information."
    ),
    FakeTableDefinition(
        name="ChangeOrders",
        description="Change orders table",
        correct_alternative="JCOI",
        correct_explanation="Use JCOI (JC Change Order Item) for change order details."
    ),
    FakeTableDefinition(
        name="ChangeOrder",
        description="Change order table",
        correct_alternative="JCOI",
        correct_explanation="Use JCOI (JC Change Order Item) for change order details."
    ),
    FakeTableDefinition(
        name="Transactions",
        description="Generic transactions table",
        correct_alternative="GLDT",
        correct_explanation="Use GLDT (GL Detail) for GL transactions, or module-specific tables like APTH, ARTH, JCCD."
    ),
    FakeTableDefinition(
        name="GLTransactions",
        description="GL transactions table",
        correct_alternative="GLDT",
        correct_explanation="Use GLDT (GL Detail) for GL transaction details."
    ),
    FakeTableDefinition(
        name="Subcontracts",
        description="Subcontracts table",
        correct_alternative="SLHD",
        correct_explanation="Use SLHD (SL Header) for subcontract headers."
    ),
    FakeTableDefinition(
        name="SubcontractHeader",
        description="Subcontract header table",
        correct_alternative="SLHD",
        correct_explanation="Use SLHD (SL Header) for subcontract headers."
    ),
    FakeTableDefinition(
        name="Contracts",
        description="Contracts table",
        correct_alternative="JCCM",
        correct_explanation="Use JCCM (JC Contract Master) for contract information."
    ),
    FakeTableDefinition(
        name="ContractMaster",
        description="Contract master table",
        correct_alternative="JCCM",
        correct_explanation="Use JCCM (JC Contract Master) for contract master information."
    ),
    FakeTableDefinition(
        name="Payments",
        description="Payments table",
        correct_alternative="APTD/ARTH",
        correct_explanation="For AP payments, use APTD (AP Transaction Detail). For AR payments, use ARTH with appropriate ARTransType."
    ),
    FakeTableDefinition(
        name="Retainage",
        description="Retainage table",
        correct_alternative="APTD/SLWI",
        correct_explanation="Retainage is stored in APTD (PayType column) for AP and SLWI (WCRetAmt, SMRetAmt) for subcontracts."
    ),
    FakeTableDefinition(
        name="CostCodes",
        description="Cost codes table",
        correct_alternative="JCCP",
        correct_explanation="Use JCCP (JC Cost Phase) for cost code/phase information with cost details."
    ),
    FakeTableDefinition(
        name="Phases",
        description="Phases table",
        correct_alternative="JCJP",
        correct_explanation="Use JCJP (JC Job Phase) for phase definitions."
    ),
    FakeTableDefinition(
        name="ClientMaster",
        description="Client master table",
        correct_alternative="ARCM",
        correct_explanation="Use ARCM (AR Customer Master) for client/customer information."
    ),
    FakeTableDefinition(
        name="VendorMaster",
        description="Vendor master table",
        correct_alternative="APVM",
        correct_explanation="Use APVM (AP Vendor Master) for vendor information."
    ),
    FakeTableDefinition(
        name="EmployeeMaster",
        description="Employee master table",
        correct_alternative="PREH",
        correct_explanation="Use PREH (PR Employee Header) for employee master information."
    ),
    FakeTableDefinition(
        name="WorkOrders",
        description="Work orders table",
        correct_alternative="SMWorkOrder",
        correct_explanation="Use SMWorkOrder for service management work orders."
    ),
    FakeTableDefinition(
        name="Accounts",
        description="Chart of accounts table",
        correct_alternative="GLAC",
        correct_explanation="Use GLAC (GL Account) for chart of accounts."
    ),
    FakeTableDefinition(
        name="ChartOfAccounts",
        description="Chart of accounts table",
        correct_alternative="GLAC",
        correct_explanation="Use GLAC (GL Account) for chart of accounts."
    ),
]


class NegativeExampleGenerator:
    """
    Generate negative examples for hallucination prevention.
    
    Types of negative examples:
    1. Fake table rejection - "ARAgingReport does not exist"
    2. Missing table in schema - "The requested table is not in the provided schema"
    3. Partial schema - Query asks about tables not included in DDL
    """
    
    def __init__(self, config: V4Config, ddl_extractor: DDLExtractor):
        self.config = config
        self.ddl = ddl_extractor
        self.fake_tables = FAKE_TABLES
        
        logger.info(f"NegativeExampleGenerator initialized with {len(self.fake_tables)} fake tables")
    
    def generate_all(self) -> List[TrainingExample]:
        """Generate all negative examples."""
        examples = []
        
        # Calculate target count
        target_count = int(self.config.total_target_examples * self.config.negative_example_ratio)
        
        # Type 1: Fake table rejection (50% of negatives)
        fake_count = target_count // 2
        examples.extend(self._generate_fake_table_examples(fake_count))
        
        # Type 2: Schema mismatch (30% of negatives)
        mismatch_count = int(target_count * 0.3)
        examples.extend(self._generate_schema_mismatch_examples(mismatch_count))
        
        # Type 3: Partial schema (20% of negatives)
        partial_count = target_count - fake_count - mismatch_count
        examples.extend(self._generate_partial_schema_examples(partial_count))
        
        logger.info(f"Generated {len(examples)} negative examples")
        return examples
    
    def _generate_fake_table_examples(self, count: int) -> List[TrainingExample]:
        """Generate examples for fake/non-existent tables."""
        examples = []
        
        # Get some real tables for context DDL
        real_tables = ["ARTH", "ARCM", "APTH", "APVM", "JCJM"]
        context_ddl = self.ddl.get_ddl(real_tables)
        
        question_templates = [
            "What columns are in the {table} table?",
            "Get all records from {table}",
            "SELECT * FROM {table}",
            "Write SQL to query {table}",
            "Describe the {table} table",
            "How is {table} structured?",
            "Join {table} with other tables",
            "What is the schema for {table}?",
            "List all fields in {table}",
        ]
        
        for fake in self.fake_tables:
            if len(examples) >= count:
                break
            
            # Generate 1-2 examples per fake table
            num_variations = min(2, count - len(examples))
            
            for _ in range(num_variations):
                template = random.choice(question_templates)
                question = template.format(table=fake.name)
                
                instruction = self.config.user_prompt_template.format(
                    question=question,
                    ddl_statements=context_ddl
                )
                
                output = self._format_rejection_response(fake)
                
                examples.append(TrainingExample(
                    instruction=instruction,
                    input="",
                    output=output,
                    category=TrainingCategory.NEGATIVE.value,
                    complexity="basic",
                    tables_used=[]
                ))
        
        return examples
    
    def _generate_schema_mismatch_examples(self, count: int) -> List[TrainingExample]:
        """Generate examples where query asks for table not in provided schema."""
        examples = []
        
        # Pairs of tables where one might be asked for but other is in schema
        table_pairs = [
            (["ARTH", "ARCM"], "JCJM"),  # AR schema, JC query
            (["APTH", "APVM"], "ARCM"),  # AP schema, AR query
            (["JCJM", "JCCD"], "SLHD"),  # JC schema, SL query
            (["SLHD", "SLIT"], "PREH"),  # SL schema, PR query
            (["PREH", "PRTH"], "GLDT"),  # PR schema, GL query
        ]
        
        questions = [
            "Write SQL to join {table} with the available tables",
            "Query {table} along with the schema tables",
            "Get data from {table} for analysis",
            "Include {table} in the query",
        ]
        
        for i in range(count):
            schema_tables, missing_table = random.choice(table_pairs)
            question = random.choice(questions).format(table=missing_table)
            
            context_ddl = self.ddl.get_ddl(schema_tables)
            
            instruction = self.config.user_prompt_template.format(
                question=question,
                ddl_statements=context_ddl
            )
            
            output = f"""I cannot generate this query. The table '{missing_table}' is not present in the provided database schema.

The available tables in the provided schema are:
{', '.join(schema_tables)}

To include {missing_table} in your query, please provide its DDL in the schema context.

Alternatively, I can help you write a query using only the available tables. Would you like me to do that?"""
            
            examples.append(TrainingExample(
                instruction=instruction,
                input="",
                output=output,
                category=TrainingCategory.NEGATIVE.value,
                complexity="intermediate",
                tables_used=[]
            ))
        
        return examples
    
    def _generate_partial_schema_examples(self, count: int) -> List[TrainingExample]:
        """Generate examples with partial schema requiring clarification."""
        examples = []
        
        # Queries that need more tables than provided
        scenarios = [
            {
                "question": "Calculate AR aging with customer contact information",
                "provided": ["ARTH"],
                "missing": "ARCM",
                "explanation": "The query requires ARCM (AR Customer Master) for customer details, but only ARTH is provided in the schema."
            },
            {
                "question": "Get vendor invoices with their subcontract details",
                "provided": ["APTH"],
                "missing": "SLHD",
                "explanation": "To include subcontract details, the SLHD table is needed but not provided in the schema."
            },
            {
                "question": "Show job costs with GL account descriptions",
                "provided": ["JCCD"],
                "missing": "GLAC",
                "explanation": "The query requires GLAC for GL account descriptions, which is not in the provided schema."
            },
        ]
        
        for i in range(count):
            scenario = random.choice(scenarios)
            
            context_ddl = self.ddl.get_ddl(scenario["provided"])
            
            instruction = self.config.user_prompt_template.format(
                question=scenario["question"],
                ddl_statements=context_ddl
            )
            
            output = f"""I can partially answer this query, but the schema is incomplete.

{scenario['explanation']}

Here's what I can provide with the available schema:

```sql
SELECT *
FROM {scenario['provided'][0]} WITH (NOLOCK)
WHERE Co = @Co
-- Note: Additional joins for {scenario['missing']} would be needed for complete results
```

To get the complete data you requested, please provide the DDL for {scenario['missing']}."""
            
            examples.append(TrainingExample(
                instruction=instruction,
                input="",
                output=output,
                category=TrainingCategory.NEGATIVE.value,
                complexity="intermediate",
                tables_used=scenario["provided"]
            ))
        
        return examples
    
    def _format_rejection_response(self, fake: FakeTableDefinition) -> str:
        """Format a rejection response for a fake table."""
        return f"""I cannot generate this query. The table '{fake.name}' does not exist in Viewpoint Vista.

{fake.correct_explanation}

Here's the correct approach:

```sql
SELECT *
FROM {fake.correct_alternative.split('/')[0]} WITH (NOLOCK)
WHERE Co = @Co
```

Would you like me to provide a more specific query for your use case?"""
