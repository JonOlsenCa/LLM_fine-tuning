"""
Configuration Generator for LLaMA Factory Training

Generates YAML training configurations programmatically with support for:
- Multiple training stages (SFT, DPO, PPO, KTO, RM)
- Different finetuning types (LoRA, QLoRA, Full)
- Hyperparameter sweeps
- Template-based configuration
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Literal
from datetime import datetime


@dataclass
class ModelConfig:
    """Model configuration settings"""
    model_name_or_path: str
    trust_remote_code: bool = True
    quantization_bit: Optional[int] = None  # 4 or 8 for QLoRA


@dataclass
class LoRAConfig:
    """LoRA-specific configuration"""
    finetuning_type: Literal["lora", "full", "freeze"] = "lora"
    lora_rank: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.1
    lora_target: str = "all"


@dataclass  
class DataConfig:
    """Dataset configuration"""
    dataset: str = "alpaca_en_demo"
    template: str = "llama3"
    cutoff_len: int = 2048
    max_samples: Optional[int] = None
    overwrite_cache: bool = True
    preprocessing_num_workers: int = 16
    dataloader_num_workers: int = 4


@dataclass
class TrainingConfig:
    """Training hyperparameters"""
    stage: Literal["sft", "pt", "rm", "ppo", "dpo", "kto"] = "sft"
    do_train: bool = True
    per_device_train_batch_size: int = 2
    gradient_accumulation_steps: int = 4
    learning_rate: float = 1e-4
    num_train_epochs: float = 3.0
    lr_scheduler_type: str = "cosine"
    warmup_ratio: float = 0.1
    bf16: bool = True
    fp16: bool = False
    ddp_timeout: int = 180000000
    resume_from_checkpoint: Optional[str] = None


@dataclass
class OutputConfig:
    """Output and logging configuration"""
    output_dir: str = "saves/experiment"
    logging_steps: int = 10
    save_steps: int = 500
    plot_loss: bool = True
    overwrite_output_dir: bool = True
    save_only_model: bool = False
    report_to: str = "none"  # none, wandb, tensorboard


@dataclass
class TrainingJobConfig:
    """Complete training job configuration"""
    model: ModelConfig
    lora: LoRAConfig = field(default_factory=LoRAConfig)
    data: DataConfig = field(default_factory=DataConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    
    def to_yaml_dict(self) -> dict:
        """Convert to flat YAML-compatible dictionary"""
        config = {}
        # Model settings
        config["model_name_or_path"] = self.model.model_name_or_path
        config["trust_remote_code"] = self.model.trust_remote_code
        if self.model.quantization_bit:
            config["quantization_bit"] = self.model.quantization_bit
        
        # LoRA settings
        config["finetuning_type"] = self.lora.finetuning_type
        if self.lora.finetuning_type == "lora":
            config["lora_rank"] = self.lora.lora_rank
            config["lora_alpha"] = self.lora.lora_alpha
            config["lora_dropout"] = self.lora.lora_dropout
            config["lora_target"] = self.lora.lora_target
        
        # Training settings
        config["stage"] = self.training.stage
        config["do_train"] = self.training.do_train
        config["per_device_train_batch_size"] = self.training.per_device_train_batch_size
        config["gradient_accumulation_steps"] = self.training.gradient_accumulation_steps
        config["learning_rate"] = self.training.learning_rate
        config["num_train_epochs"] = self.training.num_train_epochs
        config["lr_scheduler_type"] = self.training.lr_scheduler_type
        config["warmup_ratio"] = self.training.warmup_ratio
        config["bf16"] = self.training.bf16
        config["ddp_timeout"] = self.training.ddp_timeout
        if self.training.resume_from_checkpoint:
            config["resume_from_checkpoint"] = self.training.resume_from_checkpoint
        
        # Data settings
        config["dataset"] = self.data.dataset
        config["template"] = self.data.template
        config["cutoff_len"] = self.data.cutoff_len
        if self.data.max_samples:
            config["max_samples"] = self.data.max_samples
        config["overwrite_cache"] = self.data.overwrite_cache
        config["preprocessing_num_workers"] = self.data.preprocessing_num_workers
        config["dataloader_num_workers"] = self.data.dataloader_num_workers
        
        # Output settings
        config["output_dir"] = self.output.output_dir
        config["logging_steps"] = self.output.logging_steps
        config["save_steps"] = self.output.save_steps
        config["plot_loss"] = self.output.plot_loss
        config["overwrite_output_dir"] = self.output.overwrite_output_dir
        config["save_only_model"] = self.output.save_only_model
        config["report_to"] = self.output.report_to
        
        return config
    
    def save(self, path: Path) -> Path:
        """Save configuration to YAML file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(self.to_yaml_dict(), f, default_flow_style=False, sort_keys=False)
        return path

