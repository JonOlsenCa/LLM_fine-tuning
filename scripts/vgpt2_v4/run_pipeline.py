#!/usr/bin/env python3
# Copyright 2024-2025 Viewpoint, Inc.
# Licensed under the Apache License, Version 2.0.

"""
Run V4 Training Data Generation Pipeline

This is the main entry point for generating V4 training data.
Designed to be run from the project root directory.

Usage:
    python scripts/vgpt2_v4/run_pipeline.py
    python scripts/vgpt2_v4/run_pipeline.py --vgpt2-path C:/Github/VGPT2
    python scripts/vgpt2_v4/run_pipeline.py --config config/v4_config.yaml
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root / "scripts"))

from vgpt2_v4.pipeline import V4Pipeline, run_pipeline
from vgpt2_v4.config import V4Config


def main():
    parser = argparse.ArgumentParser(
        description="V4 Training Data Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with defaults (requires VGPT2 repo at C:/Github/VGPT2)
    python run_pipeline.py
    
    # Specify custom paths
    python run_pipeline.py --vgpt2-path /path/to/VGPT2 --output data/custom.json
    
    # Use configuration file
    python run_pipeline.py --config config/v4_config.yaml
    
    # Generate default config file
    python run_pipeline.py --save-config config/v4_default.yaml
        """
    )
    
    parser.add_argument(
        "--vgpt2-path",
        default=os.environ.get("VGPT2_PATH", "C:/Github/VGPT2"),
        help="Path to VGPT2 repository (default: $VGPT2_PATH or C:/Github/VGPT2)"
    )
    parser.add_argument(
        "--output",
        default="data/vgpt2_v4_sft.json",
        help="Output file path (default: data/vgpt2_v4_sft.json)"
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline without saving output"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Save config and exit if requested
    if args.save_config:
        config = V4Config.get_default()
        config.vgpt2_path = args.vgpt2_path
        config.output_path = args.output
        config.save_to_yaml(args.save_config)
        print(f"Default configuration saved to {args.save_config}")
        return 0
    
    # Validate VGPT2 path
    vgpt2_path = Path(args.vgpt2_path)
    if not vgpt2_path.exists():
        logger.error(f"VGPT2 path does not exist: {vgpt2_path}")
        logger.error("Please specify --vgpt2-path or set VGPT2_PATH environment variable")
        return 1
    
    metadata_dir = vgpt2_path / "Viewpoint_Database" / "_Metadata"
    if not metadata_dir.exists():
        logger.error(f"Metadata directory not found: {metadata_dir}")
        logger.error("Make sure you're pointing to the correct VGPT2 repository")
        return 1
    
    # Run pipeline
    try:
        if args.config and Path(args.config).exists():
            pipeline = V4Pipeline.from_config(args.config)
        else:
            pipeline = V4Pipeline(
                vgpt2_path=str(vgpt2_path),
                output_path=args.output
            )
        
        examples = pipeline.run(save_output=not args.dry_run)
        
        print(f"\n✅ Successfully generated {len(examples)} training examples")
        if not args.dry_run:
            print(f"📁 Output saved to: {args.output}")
        
        return 0
        
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
