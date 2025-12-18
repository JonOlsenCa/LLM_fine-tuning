# LLaMA Factory Automation System

Comprehensive automation suite for fine-tuning LLMs using LLaMA Factory.

## Features

- **Configuration Generator**: Programmatic YAML config generation with model presets
- **CLI Automation**: PowerShell scripts for batch training and parameter sweeps
- **Web UI Automation**: Playwright-based LLaMA Board interaction
- **Training Monitor**: Real-time log parsing with Windows notifications
- **Experiment Manager**: Track, compare, and analyze training experiments

## Quick Start

### 1. Single Training Job

```powershell
# Using PowerShell script
.\automation\scripts\train_single.ps1 -ConfigPath "examples\train_lora\llama3_lora_sft.yaml"

# Using Python CLI
python -m automation.cli train --model llama3-8b --dataset alpaca_en_demo
```

### 2. Hyperparameter Sweep

```powershell
# Using PowerShell
.\automation\scripts\parameter_sweep.ps1 -Model "llama3-8b" -Dataset "alpaca_en_demo" `
    -LearningRates "1e-4,5e-5,1e-5" -LoraRanks "8,16"

# Using Python CLI
python -m automation.cli sweep --model llama3-8b --dataset alpaca_en_demo `
    --learning-rates "1e-4,5e-5" --lora-ranks "8,16,32"
```

### 3. Launch Web UI

```powershell
# Using PowerShell
.\automation\scripts\launch_webui.ps1 -OpenBrowser

# Using Python CLI
python -m automation.cli webui
```

### 4. Monitor Training

```python
from automation.monitor_extras import monitor_training_job

# Start monitoring a training job
monitor = monitor_training_job(
    output_dir="saves/my_experiment",
    notifications=True,  # Windows toast notifications
)
```

### 5. Manage Experiments

```powershell
# List all experiments
python -m automation.cli experiments list

# Compare experiments
python -m automation.cli experiments compare --ids "exp1,exp2,exp3"

# Find best experiment
python -m automation.cli experiments best

# Export to CSV
python -m automation.cli experiments export --output results.csv
```

## Python API

```python
from automation.orchestrator_extras import ExtendedOrchestrator

# Initialize orchestrator
orchestrator = ExtendedOrchestrator()

# Create and run a training job
config_path, config = orchestrator.create_training_config(
    model="llama3-8b",
    dataset="alpaca_en_demo",
    learning_rate=1e-4,
    epochs=3.0,
    lora_rank=8,
)

exp_id = orchestrator.run_training_cli(
    config_path=config_path,
    experiment_name="my_experiment",
    tags=["lora", "llama3"],
)

# Run a parameter sweep
exp_ids = orchestrator.run_parameter_sweep(
    model="llama3-8b",
    dataset="alpaca_en_demo",
    learning_rates=[1e-4, 5e-5, 1e-5],
    lora_ranks=[8, 16, 32],
)

# Compare results
comparison = orchestrator.experiment_manager.compare_experiments(exp_ids)
best = orchestrator.experiment_manager.get_best_experiment()
```

## Model Presets

Available model presets in `config_generator_extras.py`:
- `llama3-8b`, `llama3-70b`, `llama3.1-8b`
- `qwen2.5-7b`, `qwen2.5-14b`
- `mistral-7b`
- `deepseek-7b`
- `phi3-mini`
- `gemma2-9b`

## Directory Structure

```
automation/
├── __init__.py           # Package initialization
├── cli.py                # Command-line interface
├── config_generator.py   # YAML config generation
├── config_generator_extras.py  # Presets and sweeps
├── experiment_manager.py # Experiment tracking
├── experiment_manager_extras.py  # Comparison utilities
├── monitor.py            # Log parsing and monitoring
├── monitor_extras.py     # Background monitoring
├── orchestrator.py       # Main automation controller
├── orchestrator_extras.py  # Extended functionality
├── webui_automation.py   # Playwright Web UI automation
├── webui_automation_extras.py  # Monitoring via Web UI
├── configs/              # Generated config files
├── experiments/          # Experiment tracking data
└── scripts/              # PowerShell automation scripts
    ├── train_single.ps1
    ├── train_batch.ps1
    ├── parameter_sweep.ps1
    └── launch_webui.ps1
```

