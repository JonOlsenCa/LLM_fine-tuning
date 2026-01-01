# Copyright 2024-2025 Viewpoint, Inc.
# Licensed under the Apache License, Version 2.0.

"""
V4 Evaluation Framework

Evaluates models trained with schema-in-prompt format.
Provides proper comparison against ground truth answers.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import V4Config
from .ddl_extractor import DDLExtractor, create_ddl_for_question

logger = logging.getLogger(__name__)


@dataclass
class EvaluationQuestion:
    """A single evaluation question with expected answer."""
    id: str
    category: str
    question: str
    ground_truth: str
    key_elements: List[str]
    forbidden_elements: List[str] = field(default_factory=list)
    should_refuse: bool = False
    tables_for_ddl: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Result of evaluating a single question."""
    question_id: str
    category: str
    question: str
    ground_truth: str
    model_response: str
    element_score: float
    elements_found: List[str]
    elements_missing: List[str]
    forbidden_found: List[str]
    is_refusal: bool
    should_refuse: bool
    refusal_appropriate: bool
    final_score: float


@dataclass
class EvaluationSummary:
    """Summary of evaluation results."""
    model_name: str
    timestamp: str
    total_questions: int
    overall_score: float
    category_scores: Dict[str, float]
    results: List[EvaluationResult]


class V4Evaluator:
    """
    Evaluate models using schema-in-prompt format.
    
    Key difference from V3: Schema is provided in the prompt,
    so we test SQL generation ability, not schema memorization.
    """
    
    def __init__(
        self,
        ddl_extractor: DDLExtractor,
        model_callable,  # Function that takes prompt and returns response
        config: Optional[V4Config] = None
    ):
        self.ddl = ddl_extractor
        self.model = model_callable
        self.config = config or V4Config.get_default()
        
        self.questions: List[EvaluationQuestion] = []
        self.results: List[EvaluationResult] = []
    
    def load_questions(self, questions_path: str) -> None:
        """Load evaluation questions from JSON file."""
        with open(questions_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.questions = []
        for q in data:
            self.questions.append(EvaluationQuestion(
                id=q["id"],
                category=q["category"],
                question=q["question"],
                ground_truth=q["ground_truth"],
                key_elements=q.get("key_elements", []),
                forbidden_elements=q.get("forbidden_elements", []),
                should_refuse=q.get("should_refuse", False),
                tables_for_ddl=q.get("tables_for_ddl", [])
            ))
        
        logger.info(f"Loaded {len(self.questions)} evaluation questions")
    
    def add_question(self, question: EvaluationQuestion) -> None:
        """Add a single evaluation question."""
        self.questions.append(question)
    
    def evaluate_all(self, model_name: str = "Unknown") -> EvaluationSummary:
        """Run evaluation on all questions."""
        self.results = []
        
        for question in self.questions:
            result = self._evaluate_question(question)
            self.results.append(result)
            logger.info(f"  {question.id}: {result.final_score:.1%}")
        
        return self._create_summary(model_name)
    
    def _evaluate_question(self, question: EvaluationQuestion) -> EvaluationResult:
        """Evaluate a single question."""
        # Build prompt with DDL
        if question.tables_for_ddl:
            ddl = self.ddl.get_ddl(question.tables_for_ddl)
        else:
            # Infer tables from ground truth
            ddl = self._infer_ddl_from_ground_truth(question)
        
        prompt = self.config.user_prompt_template.format(
            question=question.question,
            ddl_statements=ddl
        )
        
        # Get model response
        try:
            response = self.model(prompt)
        except Exception as e:
            logger.error(f"Error getting model response: {e}")
            response = f"[ERROR: {e}]"
        
        # Evaluate response
        return self._score_response(question, response)
    
    def _infer_ddl_from_ground_truth(self, question: EvaluationQuestion) -> str:
        """Infer which tables to include in DDL from ground truth."""
        # Extract table names from key elements (typically capitalized 4-letter codes)
        tables = []
        for element in question.key_elements:
            # Match Vista table patterns (2-4 uppercase letters)
            if re.match(r'^[A-Z]{2,6}$', element):
                tables.append(element)
        
        if not tables:
            # Default to common tables based on category
            category_defaults = {
                "complex_sql": ["ARTH", "ARCM", "APTH", "APVM"],
                "business_logic": ["SLHD", "SLIT", "APCO", "ARCO"],
                "cross_module_join": ["SLWI", "APTD", "JCCD", "JCJM"],
                "hallucination": ["ARTH", "ARCM"],
            }
            tables = category_defaults.get(question.category, ["ARTH", "APTH"])
        
        return self.ddl.get_ddl(tables[:4])
    
    def _score_response(self, question: EvaluationQuestion, response: str) -> EvaluationResult:
        """Score a model response against ground truth."""
        response_upper = response.upper()
        
        # Check for refusal patterns
        refusal_patterns = [
            "does not exist",
            "doesn't exist",
            "no such table",
            "not a valid table",
            "table not found",
            "cannot generate",
            "i cannot",
            "is not present",
            "not in the provided schema"
        ]
        is_refusal = any(p in response.lower() for p in refusal_patterns)
        
        # Check key elements
        elements_found = []
        elements_missing = []
        
        for element in question.key_elements:
            if element.upper() in response_upper:
                elements_found.append(element)
            else:
                elements_missing.append(element)
        
        # Check forbidden elements
        forbidden_found = []
        for element in question.forbidden_elements:
            if element.upper() in response_upper:
                forbidden_found.append(element)
        
        # Calculate element score
        if question.key_elements:
            element_score = len(elements_found) / len(question.key_elements)
        else:
            element_score = 1.0 if is_refusal == question.should_refuse else 0.0
        
        # Refusal appropriateness
        refusal_appropriate = is_refusal == question.should_refuse
        
        # Calculate final score
        if question.should_refuse:
            # For hallucination tests, score based on refusal
            final_score = 1.0 if is_refusal else 0.0
        else:
            # For regular questions, use element score with penalties
            final_score = element_score
            
            # Penalty for forbidden elements
            if forbidden_found:
                final_score *= 0.5
            
            # Penalty for unexpected refusal
            if is_refusal and not question.should_refuse:
                final_score = 0.1
        
        return EvaluationResult(
            question_id=question.id,
            category=question.category,
            question=question.question,
            ground_truth=question.ground_truth,
            model_response=response,
            element_score=element_score,
            elements_found=elements_found,
            elements_missing=elements_missing,
            forbidden_found=forbidden_found,
            is_refusal=is_refusal,
            should_refuse=question.should_refuse,
            refusal_appropriate=refusal_appropriate,
            final_score=final_score
        )
    
    def _create_summary(self, model_name: str) -> EvaluationSummary:
        """Create evaluation summary from results."""
        # Calculate category scores
        category_scores = {}
        category_counts = {}
        
        for result in self.results:
            if result.category not in category_scores:
                category_scores[result.category] = 0.0
                category_counts[result.category] = 0
            
            category_scores[result.category] += result.final_score
            category_counts[result.category] += 1
        
        for cat in category_scores:
            category_scores[cat] /= category_counts[cat]
        
        # Calculate overall score
        overall_score = sum(r.final_score for r in self.results) / len(self.results) if self.results else 0.0
        
        return EvaluationSummary(
            model_name=model_name,
            timestamp=datetime.now().isoformat(),
            total_questions=len(self.results),
            overall_score=overall_score,
            category_scores=category_scores,
            results=self.results
        )
    
    def save_results(self, output_path: str, summary: EvaluationSummary) -> None:
        """Save evaluation results to JSON file."""
        data = {
            "model_name": summary.model_name,
            "timestamp": summary.timestamp,
            "total_questions": summary.total_questions,
            "overall_score": summary.overall_score,
            "category_scores": summary.category_scores,
            "results": [
                {
                    "id": r.question_id,
                    "category": r.category,
                    "question": r.question,
                    "ground_truth": r.ground_truth,
                    "model_response": r.model_response,
                    "element_score": r.element_score,
                    "elements_found": r.elements_found,
                    "elements_missing": r.elements_missing,
                    "forbidden_found": r.forbidden_found,
                    "is_refusal": r.is_refusal,
                    "should_refuse": r.should_refuse,
                    "refusal_appropriate": r.refusal_appropriate,
                    "final_score": r.final_score
                }
                for r in summary.results
            ]
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_path}")
    
    def print_summary(self, summary: EvaluationSummary) -> None:
        """Print evaluation summary."""
        print("\n" + "=" * 60)
        print(f"Evaluation Summary: {summary.model_name}")
        print("=" * 60)
        print(f"Overall Score: {summary.overall_score:.1%}")
        print(f"Total Questions: {summary.total_questions}")
        print()
        print("Category Scores:")
        for cat, score in sorted(summary.category_scores.items()):
            print(f"  {cat}: {score:.1%}")
        print()
        
        # Show worst performing questions
        sorted_results = sorted(summary.results, key=lambda r: r.final_score)
        print("Lowest Scoring Questions:")
        for result in sorted_results[:5]:
            print(f"  {result.question_id}: {result.final_score:.1%}")
            if result.elements_missing:
                print(f"    Missing: {', '.join(result.elements_missing[:3])}")


# =============================================================================
# EVALUATION TEST QUESTIONS
# =============================================================================

DEFAULT_EVAL_QUESTIONS = [
    EvaluationQuestion(
        id="v4_sql_001",
        category="complex_sql",
        question="Write SQL to calculate AR aging buckets (30/60/90+ days) for unpaid invoices by customer",
        ground_truth="Use ARTH + ARCM join, filter PayFullDate IS NULL, DATEDIFF for aging, CASE WHEN for buckets",
        key_elements=["ARTH", "ARCM", "PayFullDate", "DATEDIFF", "CASE", "Customer"],
        tables_for_ddl=["ARTH", "ARCM"]
    ),
    EvaluationQuestion(
        id="v4_sql_002",
        category="complex_sql",
        question="Write SQL to get subcontractor costs with original, change orders, invoiced, and retainage by vendor",
        ground_truth="Use SLHD + SLIT + APVM, calculate OrigCost, CurCost-OrigCost for changes, InvCost, Retainage",
        key_elements=["SLHD", "SLIT", "APVM", "OrigCost", "CurCost", "InvCost", "Retainage"],
        tables_for_ddl=["SLHD", "SLIT", "APVM"]
    ),
    EvaluationQuestion(
        id="v4_sql_003",
        category="complex_sql",
        question="Write SQL to aggregate job cost estimates by phase with item vs phase unit distinctions",
        ground_truth="Use JCJP + JCCH + JCCP + JCCT, check ItemUnitFlag/PhaseUnitFlag, sum estimates",
        key_elements=["JCJP", "JCCH", "JCCP", "ItemUnitFlag", "PhaseUnitFlag", "OrigEstCost"],
        tables_for_ddl=["JCJP", "JCCH", "JCCP", "JCCT"]
    ),
    EvaluationQuestion(
        id="v4_sql_004",
        category="business_logic",
        question="Track AP hold status distinguishing retainage vs non-retainage holds",
        ground_truth="Join APTD to APHD, compare HoldCode to APCO.RetHoldCode",
        key_elements=["APTD", "APHD", "APCO", "HoldCode", "RetHoldCode"],
        tables_for_ddl=["APTD", "APHD", "APCO"]
    ),
    EvaluationQuestion(
        id="v4_sql_005",
        category="cross_module",
        question="Join SLWI retainage amounts to matching APTD transactions",
        ground_truth="SLWI -> APTL -> APTD join path, filter on PayType = RetPayType",
        key_elements=["SLWI", "APTL", "APTD", "PayType", "RetPayType"],
        tables_for_ddl=["SLWI", "APTL", "APTD", "APCO"]
    ),
    EvaluationQuestion(
        id="v4_halluc_001",
        category="hallucination",
        question="What columns are in the ARAgingReport table?",
        ground_truth="REJECT - ARAgingReport does not exist",
        key_elements=["does not exist", "not a real table", "ARTH"],
        should_refuse=True,
        tables_for_ddl=["ARTH", "ARCM"]
    ),
    EvaluationQuestion(
        id="v4_halluc_002",
        category="hallucination",
        question="Get all records from the Customers table",
        ground_truth="REJECT - Customers does not exist, use ARCM",
        key_elements=["does not exist", "ARCM"],
        should_refuse=True,
        tables_for_ddl=["ARCM", "ARTH"]
    ),
    EvaluationQuestion(
        id="v4_halluc_003",
        category="hallucination",
        question="Write SQL to query the TimeCards table",
        ground_truth="REJECT - TimeCards does not exist, use PRTH",
        key_elements=["does not exist", "PRTH"],
        should_refuse=True,
        tables_for_ddl=["PRTH", "PREH"]
    ),
]


def create_default_eval_questions_file(output_path: str) -> None:
    """Create default evaluation questions file."""
    data = [
        {
            "id": q.id,
            "category": q.category,
            "question": q.question,
            "ground_truth": q.ground_truth,
            "key_elements": q.key_elements,
            "forbidden_elements": q.forbidden_elements,
            "should_refuse": q.should_refuse,
            "tables_for_ddl": q.tables_for_ddl
        }
        for q in DEFAULT_EVAL_QUESTIONS
    ]
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Created default evaluation questions at {output_path}")
