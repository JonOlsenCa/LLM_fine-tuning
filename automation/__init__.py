"""
LLaMA Factory Automation System

A comprehensive automation suite for fine-tuning LLMs using:
- Windows MCP for desktop automation
- Playwright for web UI automation
- PowerShell for CLI batch processing
- Python for configuration management

Modules:
- config_generator: Generate YAML training configurations
- cli_automation: PowerShell-based batch training scripts
- webui_automation: Playwright-based LLaMA Board automation
- monitor: Training progress monitoring and notifications
- experiment_manager: Track and compare experiments
- orchestrator: Central automation controller
"""

__version__ = "1.0.0"
__author__ = "LLaMA Factory Automation"

from pathlib import Path

# Automation root directory
AUTOMATION_ROOT = Path(__file__).parent
PROJECT_ROOT = AUTOMATION_ROOT.parent

# Default paths
DEFAULT_CONFIG_DIR = AUTOMATION_ROOT / "configs"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "saves"
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_EXPERIMENTS_DIR = AUTOMATION_ROOT / "experiments"

# Ensure directories exist
for dir_path in [DEFAULT_CONFIG_DIR, DEFAULT_EXPERIMENTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

