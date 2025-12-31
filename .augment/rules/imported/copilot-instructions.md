---
type: "always_apply"
---

# GitHub Copilot Instructions for LLaMA Factory

## Project Overview

LLaMA Factory is an efficient fine-tuning framework for 100+ large language models (LLMs). It provides:
- Support for various models: LLaMA, LLaVA, Mistral, Qwen, DeepSeek, Yi, Gemma, ChatGLM, Phi, etc.
- Multiple training methods: pre-training, supervised fine-tuning, reward modeling, PPO, DPO, KTO, ORPO
- Scalable resources: 16-bit full-tuning, freeze-tuning, LoRA and QLoRA variants
- Advanced algorithms: GaLore, BAdam, APOLLO, Adam-mini, Muon, OFT, DoRA, etc.
- Web UI (LLaMA Board) and CLI interfaces

### Architecture Versions

LLaMA Factory has two parallel architectures that can be switched via the `USE_V1` environment variable:

**v0 (default)** - File hierarchy:
- `api`, `webui` → `chat`, `eval`, `train` → `data`, `model` → `hparams` → `extras`

**v1** - File hierarchy:
- `trainers` → `core` → `accelerator`, `plugins`, `config` → `utils`

Set `USE_V1=1` to enable v1 architecture.

## Code Structure

### v0 Architecture (Default)

- `src/llamafactory/` - Main package directory
  - `api/` - OpenAI-style API implementation
  - `chat/` - Chat interface implementation
  - `cli.py` - Command-line interface
  - `data/` - Data processing and dataset handling
  - `eval/` - Model evaluation utilities
  - `extras/` - Additional utilities and helpers
  - `hparams/` - Hyperparameter definitions
  - `model/` - Model loading, patching, and utilities
  - `train/` - Training pipeline implementation
  - `webui/` - Gradio-based web interface
- `src/train.py` - Training entry script (delegates to `llamafactory.train.tuner`)
- `src/webui.py` - Web UI entry script (delegates to `llamafactory.webui.interface`)
- `src/api.py` - API server entry script (delegates to `llamafactory.api.app`)
- `tests/` - Test suite
- `examples/` - Example configurations for various training scenarios
- `data/` - Dataset definitions and examples

### v1 Architecture (USE_V1=1)

- `src/llamafactory/v1/` - Version 1 package directory
  - `trainers/` - Training implementations
  - `core/` - Core training utilities
  - `accelerator/` - Acceleration and distributed training
  - `plugins/` - Pluggable components (model, data, sampler, trainer)
  - `config/` - Configuration management
  - `utils/` - Utility functions

## Development Practices

### Code Style

- Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- Use ruff for linting and formatting
- Line length: 119 characters
- Indentation: 4 spaces
- Quote style: double quotes
- Use Google-style docstrings for documentation

### Import Organization

- Known first-party: `llamafactory`
- Known third-party: `accelerate`, `datasets`, `gradio`, `numpy`, `peft`, `torch`, `transformers`, `trl`
- Use 2 blank lines after imports

### Quality Checks

Before committing code, run:
```bash
make style      # Auto-fix style issues
make quality    # Check code quality
make test       # Run test suite
```

Or use the combined command:
```bash
make commit     # Run pre-commit hooks
```

### Testing

- Use pytest for testing
- Tests are located in `tests/` and `tests_v1/` directories
- Run tests with: `make test` (which runs `WANDB_DISABLED=true pytest -vv --import-mode=importlib tests/ tests_v1/`)
- Disable wandb during testing to avoid external dependencies
- **Note**: Training configurations require GPU machines, so training is typically not tested end-to-end. Use `make test` to validate file-level functionality.

### Building

Build the package with:
```bash
pip3 install build && python3 -m build
```

### License

- All source files must include the Apache 2.0 license header
- Check license headers with: `make license`

## Common Patterns

### Configuration Files

- Training configurations are typically YAML or JSON files in `examples/` directory
- Hyperparameters are defined using dataclasses in `src/llamafactory/hparams/`

### Model Support

- New model support is added through model patches in `src/llamafactory/model/`
- Visual models use the visual utilities in `src/llamafactory/model/model_utils/visual.py`
- Quantization support is in `src/llamafactory/model/model_utils/quantization.py`

### Data Processing

- Dataset definitions are in `data/dataset_info.json`
- Data templates and processors are in `src/llamafactory/data/`

### Training

- Training pipelines are in `src/llamafactory/train/`
- Support for different training methods: SFT, DPO, PPO, RM, PT, KTO, ORPO

## Key Dependencies

- Python >= 3.9.0
- PyTorch and transformers for model handling
- datasets for data processing
- peft for parameter-efficient fine-tuning
- accelerate for distributed training
- gradio for web UI
- trl for reinforcement learning
- Optional: vllm/sglang for inference, flash-attention-2, unsloth, liger-kernel

## Entry Points

- **CLI Training**: `llamafactory-cli train --config examples/train_lora/llama3_lora_sft.yaml`
- **Web UI**: `llamafactory-cli webui` or `python src/webui.py`
- **API Server**: `llamafactory-cli api` or `python src/api.py`
- **Chat Interface**: `llamafactory-cli chat --model_name_or_path MODEL_PATH`

## Environment Setup

For development:
```bash
pip install -e ".[dev]"
```

## Important Notes

- The project supports multiple backends: default PyTorch, vLLM, SGLang
- Megatron-core training is supported via mcore_adapter
- SwanLab and W&B are supported for experiment tracking
- Docker support is available with pre-built images
- Day-0/Day-1 support for latest cutting-edge models
- Multi-modal support for vision and audio understanding tasks

## Contribution Guidelines

1. Fork the repository
2. Create a development branch
3. Set up development environment with `pip install -e ".[dev]"`
4. Make changes following the style guide
5. Run quality checks: `make style && make quality`
6. Run tests: `make test`
7. Submit a pull request

## Common Commands

- `make style` - Format code
- `make quality` - Run linters
- `make test` - Run tests
- `make commit` - Install and run pre-commit hooks
- `make license` - Check license headers
## Windows/Python File Encoding

**CRITICAL**: This project runs on Windows. Always use explicit UTF-8 encoding when opening files:

```python
# CORRECT - Always do this
with open('file.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# WRONG - Will fail on Windows with non-ASCII characters
with open('file.json', 'r') as f:
    data = json.load(f)
```

## File Path Verification

**CRITICAL**: Before referencing any file path in commands or instructions:
1. Use `view` tool to verify the file/directory exists
2. Never assume file paths - always check first
3. Use `view` on the parent directory to see what files actually exist

```python
# WRONG - Assuming a path exists
cat training/vgpt2_v3_sft.yaml

# CORRECT - First check what exists
view path="training" type="directory"
# Then reference the actual file found
```

## PowerShell Command Syntax

**CRITICAL**: This project uses PowerShell on Windows, NOT bash. Key differences:

```powershell
# Rename files - use -NewName with filename only (no path)
Rename-Item -Path old/path/file.txt -NewName newname.txt

# Copy files
Copy-Item -Path source.txt -Destination dest.txt

# Move files
Move-Item -Path source.txt -Destination dest/path/
```

## File Operation Pre-checks

**CRITICAL**: Before any file operation that creates or overwrites a file, ALWAYS check if the target already exists:

```powershell
# WRONG - Assuming target doesn't exist
Rename-Item -Path old.json -NewName new.json

# CORRECT - Check first
Test-Path data/new.json  # Returns True/False
Get-ChildItem data/*pattern* | Select-Object Name, Length, LastWriteTime

# Then decide: overwrite with -Force, use different name, or ask user
```

## Training Objective: Perfect Model, Cost No Object

**CRITICAL**: The objective is to create a PERFECT fine-tuned model. Cost is no object.

**System Resources (MUST fully utilize):**
- GPU: NVIDIA RTX A6000 (48GB VRAM)
- RAM: 128GB System Memory
- CPU: AMD Threadripper 7960X (24 cores / 48 threads)

**Decision Framework:**
- Accept 10x cost for 2x benefit - ALWAYS choose the higher quality option
- Maximize batch sizes to fill GPU memory
- Use highest LoRA ranks that fit (256+)
- Use longest context lengths practical (8192+)
- Run more epochs rather than fewer
- Include ALL available training data
- Generate MORE synthetic examples when in doubt

**When in doubt:** Choose the option that produces better model quality, regardless of:
- Training time
- Compute cost
- Storage space
- Complexity

## Recommendation Requirements

**CRITICAL**: When presenting options or recommendations, ALWAYS:

1. **State the objective first** - Remind what we're optimizing for (model quality)
2. **Present ALL viable options** - Not just the "safe" or "easy" ones
3. **Rank by expected quality** - Best outcome first, not cheapest/fastest
4. **Include resource utilization** - Show how each option uses system resources
5. **Make a clear recommendation** - Don't be neutral; advocate for the best outcome
6. **Default to maximum** - When unsure, recommend the larger/longer/more thorough option

**Never:**
- Recommend a "lighter" option to save time/resources
- Present a conservative option as the default
- Omit high-quality options because they're complex

## LLM Training Checkpoint Requirements

**CRITICAL**: All LLM fine-tuning configurations MUST include checkpoint saving:

```yaml
# REQUIRED in every training config
save_steps: 250              # Save every 250 steps (adjust based on training time)
save_total_limit: 5          # Keep at least 3-5 checkpoints
save_only_model: false       # Save optimizer state for resume capability
resume_from_checkpoint: false # Set to true/path to resume interrupted training

## PowerShell Execution Policy

**CRITICAL**: Never execute PowerShell commands directly. Always provide commands for the user to run.

**Requirements:**
1. **Never use `launch-process` for PowerShell commands** - Always give the user the command to copy/paste
2. **Always provide full paths** - Use absolute paths from workspace root, not relative paths
3. **State admin requirements explicitly** - If a command requires Administrator/elevated privileges, state: "⚠️ REQUIRES ADMIN: Run PowerShell as Administrator"

**Format for providing commands:**
```powershell
# Description of what this does
cd c:\Github\LLM_fine-tuning
.\full\path\to\script.ps1