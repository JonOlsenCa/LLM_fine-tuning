"""
LLaMA Factory Automation Orchestrator

Central controller that coordinates all automation components:
- Configuration generation
- Training job execution (CLI or Web UI)
- Progress monitoring
- Experiment tracking
- Results analysis

Provides both programmatic API and interactive CLI.
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Literal, Callable

from . import PROJECT_ROOT, DEFAULT_CONFIG_DIR, DEFAULT_OUTPUT_DIR
from .config_generator import TrainingJobConfig, ModelConfig, LoRAConfig, DataConfig, TrainingConfig, OutputConfig
from .config_generator_extras import MODEL_PRESETS, create_sft_config, ParameterSweep
from .experiment_manager import ExperimentConfig, ExperimentResult
from .experiment_manager_extras import ExperimentManagerExtended
from .monitor import TrainingJob, TrainingMetrics
from .monitor_extras import BackgroundMonitor, create_console_callback, create_notification_callback


@dataclass
class AutomationConfig:
    """Global automation configuration"""
    project_root: Path = PROJECT_ROOT
    config_dir: Path = DEFAULT_CONFIG_DIR
    output_base: Path = DEFAULT_OUTPUT_DIR
    python_executable: str = "python"
    use_venv: bool = True
    venv_path: str = "venv"
    webui_host: str = "127.0.0.1"
    webui_port: int = 7860
    enable_notifications: bool = True
    notification_interval: int = 100


class TrainingOrchestrator:
    """
    Main orchestrator for LLaMA Factory automation
    
    Coordinates training jobs through CLI or Web UI with
    full experiment tracking and monitoring.
    """
    
    def __init__(self, config: Optional[AutomationConfig] = None):
        self.config = config or AutomationConfig()
        self.experiment_manager = ExperimentManagerExtended()
        self.active_monitors: dict[str, BackgroundMonitor] = {}
    
    def _get_python_cmd(self) -> list[str]:
        """Get the Python command to use"""
        if self.config.use_venv:
            venv_python = self.config.project_root / self.config.venv_path / "Scripts" / "python.exe"
            if venv_python.exists():
                return [str(venv_python)]
        return [self.config.python_executable]
    
    def create_training_config(
        self,
        model: str,
        dataset: str,
        output_name: Optional[str] = None,
        learning_rate: float = 1e-4,
        epochs: float = 3.0,
        lora_rank: int = 8,
        batch_size: int = 2,
        max_samples: Optional[int] = None,
        **kwargs
    ) -> tuple[Path, TrainingJobConfig]:
        """
        Create a training configuration file
        
        Returns:
            Tuple of (config_path, TrainingJobConfig)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = output_name or f"{model.replace('/', '_')}_{timestamp}"
        output_dir = str(self.config.output_base / output_name)
        
        config = create_sft_config(
            model=model,
            dataset=dataset,
            output_dir=output_dir,
            learning_rate=learning_rate,
            epochs=epochs,
            lora_rank=lora_rank,
            max_samples=max_samples,
        )
        config.training.per_device_train_batch_size = batch_size
        
        # Apply any extra kwargs
        for key, value in kwargs.items():
            if hasattr(config.training, key):
                setattr(config.training, key, value)
            elif hasattr(config.lora, key):
                setattr(config.lora, key, value)
            elif hasattr(config.data, key):
                setattr(config.data, key, value)
        
        config_path = self.config.config_dir / f"{output_name}.yaml"
        config.save(config_path)
        
        return config_path, config
    
    def run_training_cli(
        self,
        config_path: Path,
        experiment_name: Optional[str] = None,
        monitor: bool = True,
        tags: Optional[list[str]] = None,
    ) -> str:
        """
        Run training via CLI
        
        Args:
            config_path: Path to YAML config file
            experiment_name: Name for experiment tracking
            monitor: Enable background monitoring
            tags: Tags for experiment
        
        Returns:
            Experiment ID
        """
        config_path = Path(config_path)
        
        # Create experiment record
        exp_config = ExperimentConfig.from_yaml_file(config_path)
        experiment = self.experiment_manager.create_experiment(
            name=experiment_name or config_path.stem,
            config=exp_config,
            tags=tags or [],
        )
        
        # Update status to running
        self.experiment_manager.update_experiment(experiment.id, status="running")
        
        # Set up monitoring if requested
        if monitor and experiment.output_dir:
            job = TrainingJob(
                job_id=experiment.id,
                output_dir=Path(experiment.output_dir),
                config_path=config_path,
            )
            
            bg_monitor = BackgroundMonitor()
            bg_monitor.add_job(job)
            bg_monitor.add_callback(create_console_callback())
            
            if self.config.enable_notifications:
                bg_monitor.add_callback(
                    create_notification_callback(notify_every=self.config.notification_interval)
                )
            
            bg_monitor.start()
            self.active_monitors[experiment.id] = bg_monitor
        
        # Run training command
        cmd = self._get_python_cmd() + ["-m", "llamafactory.cli", "train", str(config_path)]
        
        print(f"Starting training: {' '.join(cmd)}")
        print(f"Experiment ID: {experiment.id}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.config.project_root),
                capture_output=False,
            )
            
            # Update experiment status
            if result.returncode == 0:
                self.experiment_manager.update_experiment(experiment.id, status="completed")
                # Load results from logs
                exp_result = self.experiment_manager.load_results_from_logs(experiment.id)
                if exp_result:
                    self.experiment_manager.update_experiment(experiment.id, result=exp_result)
            else:
                self.experiment_manager.update_experiment(experiment.id, status="failed")
                
        except Exception as e:
            print(f"Training error: {e}")
            self.experiment_manager.update_experiment(experiment.id, status="failed")
        finally:
            # Stop monitoring
            if experiment.id in self.active_monitors:
                self.active_monitors[experiment.id].stop()
                del self.active_monitors[experiment.id]
        
        return experiment.id

