# Copyright 2024-2025 Viewpoint, Inc.
# Licensed under the Apache License, Version 2.0.

"""
V4 Pipeline Module

Main orchestration pipeline for V4 training data generation.
Coordinates DDL extraction, SQL example generation, and negative examples.
"""

import json
import logging
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .config import V4Config, TrainingCategory
from .ddl_extractor import DDLExtractor
from .sql_generator import SQLExampleGenerator, TrainingExample
from .negative_generator import NegativeExampleGenerator

logger = logging.getLogger(__name__)


class V4Pipeline:
    """
    Main pipeline for V4 training data generation.
    
    Usage:
        pipeline = V4Pipeline.from_config("config/v4_config.yaml")
        pipeline.run()
        
        # Or with defaults:
        pipeline = V4Pipeline(vgpt2_path="C:/Github/VGPT2")
        pipeline.run()
    """
    
    def __init__(
        self,
        vgpt2_path: str,
        output_path: Optional[str] = None,
        config: Optional[V4Config] = None
    ):
        self.vgpt2_path = vgpt2_path
        self.output_path = output_path or "data/vgpt2_v4_sft.json"
        
        # Use provided config or get defaults
        self.config = config or V4Config.get_default()
        self.config.vgpt2_path = vgpt2_path
        self.config.output_path = self.output_path
        
        # Initialize components
        self.ddl_extractor = DDLExtractor(vgpt2_path)
        self.sql_generator: Optional[SQLExampleGenerator] = None
        self.negative_generator: Optional[NegativeExampleGenerator] = None
        
        # Results
        self.examples: List[TrainingExample] = []
        self.stats: Dict = {}
        
        logger.info(f"V4Pipeline initialized")
        logger.info(f"  VGPT2 path: {vgpt2_path}")
        logger.info(f"  Output path: {self.output_path}")
    
    @classmethod
    def from_config(cls, config_path: str) -> "V4Pipeline":
        """Create pipeline from YAML config file."""
        config = V4Config.load_from_yaml(config_path)
        return cls(
            vgpt2_path=config.vgpt2_path,
            output_path=config.output_path,
            config=config
        )
    
    def run(self, save_output: bool = True) -> List[TrainingExample]:
        """
        Run the full V4 training data generation pipeline.
        
        Steps:
        1. Load DDL from VGPT2 metadata
        2. Generate SQL examples
        3. Generate negative examples
        4. Combine and shuffle
        5. Save output
        
        Returns:
            List of training examples
        """
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("Starting V4 Training Data Generation Pipeline")
        logger.info("=" * 60)
        
        # Step 1: Load DDL
        logger.info("\nStep 1: Loading DDL from VGPT2 metadata...")
        self._load_ddl()
        
        # Step 2: Generate SQL examples
        logger.info("\nStep 2: Generating SQL training examples...")
        self._generate_sql_examples()
        
        # Step 3: Generate negative examples
        logger.info("\nStep 3: Generating negative examples...")
        self._generate_negative_examples()
        
        # Step 4: Combine and shuffle
        logger.info("\nStep 4: Combining and shuffling examples...")
        self._combine_examples()
        
        # Step 5: Save output
        if save_output:
            logger.info("\nStep 5: Saving output...")
            self._save_output()
        
        # Calculate stats
        elapsed = (datetime.now() - start_time).total_seconds()
        self._calculate_stats(elapsed)
        
        logger.info("\n" + "=" * 60)
        logger.info("Pipeline Complete!")
        logger.info("=" * 60)
        self._print_stats()
        
        return self.examples
    
    def _load_ddl(self) -> None:
        """Load DDL from metadata."""
        self.ddl_extractor.load_all()
        
        table_count = len(self.ddl_extractor.get_all_table_names())
        logger.info(f"  Loaded DDL for {table_count} tables")
        
        # Log tables by module
        for module in ["AR", "AP", "JC", "SL", "PR", "GL"]:
            module_tables = self.ddl_extractor.get_tables_by_module(module)
            logger.info(f"    {module}: {len(module_tables)} tables")
    
    def _generate_sql_examples(self) -> None:
        """Generate SQL training examples."""
        self.sql_generator = SQLExampleGenerator(self.config, self.ddl_extractor)
        sql_examples = self.sql_generator.generate_all()
        
        self.examples.extend(sql_examples)
        logger.info(f"  Generated {len(sql_examples)} SQL examples")
        
        # Log by category
        category_counts = {}
        for ex in sql_examples:
            category_counts[ex.category] = category_counts.get(ex.category, 0) + 1
        
        for cat, count in sorted(category_counts.items()):
            logger.info(f"    {cat}: {count}")
    
    def _generate_negative_examples(self) -> None:
        """Generate negative/rejection examples."""
        self.negative_generator = NegativeExampleGenerator(self.config, self.ddl_extractor)
        negative_examples = self.negative_generator.generate_all()
        
        self.examples.extend(negative_examples)
        logger.info(f"  Generated {len(negative_examples)} negative examples")
    
    def _combine_examples(self) -> None:
        """Shuffle examples for better training."""
        import random
        random.shuffle(self.examples)
        logger.info(f"  Total examples: {len(self.examples)}")
    
    def _save_output(self) -> None:
        """Save examples to output file."""
        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to Alpaca format
        alpaca_data = [ex.to_alpaca() for ex in self.examples]
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(alpaca_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"  Saved {len(alpaca_data)} examples to {output_path}")
        
        # Also save detailed version with metadata
        detailed_path = output_path.with_suffix(".detailed.json")
        detailed_data = [
            {
                "instruction": ex.instruction,
                "input": ex.input,
                "output": ex.output,
                "metadata": {
                    "category": ex.category,
                    "complexity": ex.complexity,
                    "tables_used": ex.tables_used
                }
            }
            for ex in self.examples
        ]
        
        with open(detailed_path, "w", encoding="utf-8") as f:
            json.dump(detailed_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"  Saved detailed version to {detailed_path}")
    
    def _calculate_stats(self, elapsed_seconds: float) -> None:
        """Calculate pipeline statistics."""
        category_counts = {}
        complexity_counts = {}
        
        for ex in self.examples:
            category_counts[ex.category] = category_counts.get(ex.category, 0) + 1
            complexity_counts[ex.complexity] = complexity_counts.get(ex.complexity, 0) + 1
        
        self.stats = {
            "total_examples": len(self.examples),
            "elapsed_seconds": round(elapsed_seconds, 2),
            "examples_per_second": round(len(self.examples) / elapsed_seconds, 2) if elapsed_seconds > 0 else 0,
            "by_category": category_counts,
            "by_complexity": complexity_counts,
            "tables_loaded": len(self.ddl_extractor.get_all_table_names()),
            "negative_ratio": round(
                category_counts.get(TrainingCategory.NEGATIVE.value, 0) / len(self.examples), 3
            ) if self.examples else 0,
        }
    
    def _print_stats(self) -> None:
        """Print pipeline statistics."""
        logger.info(f"\nStatistics:")
        logger.info(f"  Total examples: {self.stats['total_examples']}")
        logger.info(f"  Elapsed time: {self.stats['elapsed_seconds']}s")
        logger.info(f"  Examples/second: {self.stats['examples_per_second']}")
        logger.info(f"  Negative ratio: {self.stats['negative_ratio']:.1%}")
        
        logger.info(f"\nBy Category:")
        for cat, count in sorted(self.stats['by_category'].items()):
            pct = count / self.stats['total_examples'] * 100
            logger.info(f"  {cat}: {count} ({pct:.1f}%)")
        
        logger.info(f"\nBy Complexity:")
        for comp, count in sorted(self.stats['by_complexity'].items()):
            pct = count / self.stats['total_examples'] * 100
            logger.info(f"  {comp}: {count} ({pct:.1f}%)")
    
    def save_config(self, path: str) -> None:
        """Save current configuration to YAML."""
        self.config.save_to_yaml(path)
        logger.info(f"Configuration saved to {path}")
    
    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        return self.stats


def run_pipeline(
    vgpt2_path: str = "C:/Github/VGPT2",
    output_path: str = "data/vgpt2_v4_sft.json",
    config_path: Optional[str] = None
) -> V4Pipeline:
    """
    Convenience function to run the V4 pipeline.
    
    Args:
        vgpt2_path: Path to VGPT2 repository
        output_path: Path for output JSON file
        config_path: Optional path to YAML config
        
    Returns:
        V4Pipeline instance with results
    """
    if config_path and Path(config_path).exists():
        pipeline = V4Pipeline.from_config(config_path)
    else:
        pipeline = V4Pipeline(
            vgpt2_path=vgpt2_path,
            output_path=output_path
        )
    
    pipeline.run()
    return pipeline


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="V4 Training Data Generation Pipeline")
    parser.add_argument(
        "--vgpt2-path",
        default="C:/Github/VGPT2",
        help="Path to VGPT2 repository"
    )
    parser.add_argument(
        "--output",
        default="data/vgpt2_v4_sft.json",
        help="Output file path"
    )
    parser.add_argument(
        "--config",
        help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--save-config",
        help="Save default configuration to specified path and exit"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Save config and exit if requested
    if args.save_config:
        config = V4Config.get_default()
        config.vgpt2_path = args.vgpt2_path
        config.output_path = args.output
        config.save_to_yaml(args.save_config)
        print(f"Default configuration saved to {args.save_config}")
        exit(0)
    
    # Run pipeline
    pipeline = run_pipeline(
        vgpt2_path=args.vgpt2_path,
        output_path=args.output,
        config_path=args.config
    )
