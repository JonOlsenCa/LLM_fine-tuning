"""
Additional configuration generation utilities for parameter sweeps and presets
"""

from pathlib import Path
from typing import Iterator, Optional
from itertools import product
from datetime import datetime
from .config_generator import (
    TrainingJobConfig, ModelConfig, LoRAConfig, 
    DataConfig, TrainingConfig, OutputConfig
)


# ============== Model Presets ==============

MODEL_PRESETS = {
    "llama3-8b": ModelConfig(model_name_or_path="meta-llama/Meta-Llama-3-8B-Instruct"),
    "llama3-70b": ModelConfig(model_name_or_path="meta-llama/Meta-Llama-3-70B-Instruct"),
    "llama3.1-8b": ModelConfig(model_name_or_path="meta-llama/Llama-3.1-8B-Instruct"),
    "qwen2.5-7b": ModelConfig(model_name_or_path="Qwen/Qwen2.5-7B-Instruct"),
    "qwen2.5-14b": ModelConfig(model_name_or_path="Qwen/Qwen2.5-14B-Instruct"),
    "mistral-7b": ModelConfig(model_name_or_path="mistralai/Mistral-7B-Instruct-v0.3"),
    "deepseek-7b": ModelConfig(model_name_or_path="deepseek-ai/deepseek-llm-7b-chat"),
    "phi3-mini": ModelConfig(model_name_or_path="microsoft/Phi-3-mini-4k-instruct"),
    "gemma2-9b": ModelConfig(model_name_or_path="google/gemma-2-9b-it"),
}

TEMPLATE_MAP = {
    "llama3": ["llama3-8b", "llama3-70b", "llama3.1-8b"],
    "qwen": ["qwen2.5-7b", "qwen2.5-14b"],
    "mistral": ["mistral-7b"],
    "deepseek": ["deepseek-7b"],
    "phi": ["phi3-mini"],
    "gemma": ["gemma2-9b"],
}


def get_template_for_model(model_preset: str) -> str:
    """Get the appropriate template for a model preset"""
    for template, models in TEMPLATE_MAP.items():
        if model_preset in models:
            return template
    return "default"


# ============== Parameter Sweep Generator ==============

class ParameterSweep:
    """Generate configurations for hyperparameter sweeps"""
    
    def __init__(
        self,
        base_model: str,
        dataset: str,
        output_base: str = "saves/sweep",
    ):
        self.base_model = base_model
        self.dataset = dataset
        self.output_base = output_base
        self.model_config = MODEL_PRESETS.get(base_model, ModelConfig(model_name_or_path=base_model))
        self.template = get_template_for_model(base_model) if base_model in MODEL_PRESETS else "default"
    
    def generate_sweep(
        self,
        learning_rates: list[float] = [1e-4, 5e-5, 1e-5],
        lora_ranks: list[int] = [8, 16, 32],
        batch_sizes: list[int] = [1, 2, 4],
        epochs: list[float] = [3.0],
    ) -> Iterator[tuple[str, TrainingJobConfig]]:
        """
        Generate all combinations of hyperparameters
        
        Yields:
            Tuple of (config_name, TrainingJobConfig)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for lr, rank, batch, epoch in product(learning_rates, lora_ranks, batch_sizes, epochs):
            config_name = f"lr{lr}_rank{rank}_bs{batch}_ep{epoch}"
            output_dir = f"{self.output_base}/{timestamp}/{config_name}"
            
            config = TrainingJobConfig(
                model=self.model_config,
                lora=LoRAConfig(lora_rank=rank),
                data=DataConfig(dataset=self.dataset, template=self.template),
                training=TrainingConfig(
                    learning_rate=lr,
                    per_device_train_batch_size=batch,
                    num_train_epochs=epoch,
                ),
                output=OutputConfig(output_dir=output_dir),
            )
            yield config_name, config
    
    def save_all(self, output_dir: Path) -> list[Path]:
        """Save all sweep configurations to files"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_paths = []
        for name, config in self.generate_sweep():
            path = output_dir / f"{name}.yaml"
            config.save(path)
            saved_paths.append(path)
        
        return saved_paths


# ============== Quick Config Builders ==============

def create_sft_config(
    model: str,
    dataset: str,
    output_dir: str,
    learning_rate: float = 1e-4,
    epochs: float = 3.0,
    lora_rank: int = 8,
    max_samples: Optional[int] = None,
) -> TrainingJobConfig:
    """Create a quick SFT configuration"""
    model_config = MODEL_PRESETS.get(model, ModelConfig(model_name_or_path=model))
    template = get_template_for_model(model) if model in MODEL_PRESETS else "default"
    
    return TrainingJobConfig(
        model=model_config,
        lora=LoRAConfig(lora_rank=lora_rank),
        data=DataConfig(dataset=dataset, template=template, max_samples=max_samples),
        training=TrainingConfig(learning_rate=learning_rate, num_train_epochs=epochs),
        output=OutputConfig(output_dir=output_dir),
    )


def create_qlora_config(
    model: str,
    dataset: str,
    output_dir: str,
    quantization_bit: int = 4,
    **kwargs
) -> TrainingJobConfig:
    """Create a QLoRA configuration (4-bit or 8-bit quantization)"""
    config = create_sft_config(model, dataset, output_dir, **kwargs)
    config.model.quantization_bit = quantization_bit
    return config

