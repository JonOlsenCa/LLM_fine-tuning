"""
Extended orchestrator functionality - sweeps, async operations, Web UI automation
"""

import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

from .orchestrator import TrainingOrchestrator, AutomationConfig
from .config_generator_extras import ParameterSweep
from .experiment_manager import ExperimentConfig, ExperimentResult
from .webui_automation import WebUIConfig, TrainingParams
from .webui_automation_extras import LLaMABoardMonitor, run_automated_training


class ExtendedOrchestrator(TrainingOrchestrator):
    """Extended orchestrator with parameter sweeps and Web UI automation"""
    
    def run_parameter_sweep(
        self,
        model: str,
        dataset: str,
        learning_rates: Optional[list[float]] = None,
        lora_ranks: Optional[list[int]] = None,
        batch_sizes: Optional[list[int]] = None,
        sequential: bool = True,
        tags: Optional[list[str]] = None,
    ) -> list[str]:
        """
        Run a hyperparameter sweep
        
        Args:
            model: Model name or preset
            dataset: Dataset to train on
            learning_rates: Learning rates to try
            lora_ranks: LoRA ranks to try
            batch_sizes: Batch sizes to try
            sequential: Run jobs sequentially (True) or parallel (False)
            tags: Tags for all experiments
        
        Returns:
            List of experiment IDs
        """
        learning_rates = learning_rates or [1e-4, 5e-5]
        lora_ranks = lora_ranks or [8, 16]
        batch_sizes = batch_sizes or [2]
        
        sweep = ParameterSweep(
            base_model=model,
            dataset=dataset,
            output_base=str(self.config.output_base / "sweep"),
        )
        
        experiment_ids = []
        sweep_tags = (tags or []) + ["sweep"]
        
        for name, config in sweep.generate_sweep(
            learning_rates=learning_rates,
            lora_ranks=lora_ranks,
            batch_sizes=batch_sizes,
        ):
            config_path = self.config.config_dir / f"sweep_{name}.yaml"
            config.save(config_path)
            
            if sequential:
                exp_id = self.run_training_cli(
                    config_path=config_path,
                    experiment_name=f"sweep_{name}",
                    monitor=True,
                    tags=sweep_tags,
                )
                experiment_ids.append(exp_id)
            else:
                # For parallel, just create the configs
                exp_config = ExperimentConfig(
                    model_name=config.model.model_name_or_path,
                    dataset=config.data.dataset,
                    finetuning_type=config.lora.finetuning_type,
                    learning_rate=config.training.learning_rate,
                    lora_rank=config.lora.lora_rank,
                    batch_size=config.training.per_device_train_batch_size,
                    epochs=config.training.num_train_epochs,
                )
                experiment = self.experiment_manager.create_experiment(
                    name=f"sweep_{name}",
                    config=exp_config,
                    tags=sweep_tags,
                )
                experiment_ids.append(experiment.id)
        
        return experiment_ids
    
    def launch_webui(self, open_browser: bool = True) -> subprocess.Popen:
        """Launch the LLaMA Board Web UI"""
        import os
        
        env = os.environ.copy()
        env["GRADIO_SERVER_NAME"] = self.config.webui_host
        env["GRADIO_SERVER_PORT"] = str(self.config.webui_port)
        
        cmd = self._get_python_cmd() + ["-m", "llamafactory.cli", "webui"]
        
        process = subprocess.Popen(
            cmd,
            cwd=str(self.config.project_root),
            env=env,
        )
        
        print(f"LLaMA Board starting at http://{self.config.webui_host}:{self.config.webui_port}")
        
        if open_browser:
            import time
            import webbrowser
            time.sleep(3)
            webbrowser.open(f"http://{self.config.webui_host}:{self.config.webui_port}")
        
        return process
    
    async def run_training_webui(
        self,
        params: TrainingParams,
        experiment_name: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> str:
        """
        Run training via Web UI automation
        
        Args:
            params: Training parameters
            experiment_name: Name for experiment tracking
            tags: Tags for experiment
        
        Returns:
            Experiment ID
        """
        # Create experiment record
        exp_config = ExperimentConfig(
            model_name=params.model_name,
            dataset=params.dataset,
            finetuning_type=params.finetuning_type,
            learning_rate=params.learning_rate,
            lora_rank=params.lora_rank if params.finetuning_type == "lora" else None,
            batch_size=params.batch_size,
            epochs=params.num_epochs,
        )
        
        experiment = self.experiment_manager.create_experiment(
            name=experiment_name or f"webui_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            config=exp_config,
            output_dir=params.output_dir,
            tags=(tags or []) + ["webui"],
        )
        
        # Update status
        self.experiment_manager.update_experiment(experiment.id, status="running")
        
        # Run automated training
        webui_config = WebUIConfig(
            host=self.config.webui_host,
            port=self.config.webui_port,
        )
        
        def on_status(status):
            if status.loss:
                print(f"[{experiment.id}] Loss: {status.loss:.4f}")
        
        success = await run_automated_training(
            params=params,
            webui_config=webui_config,
            monitor=True,
            on_status=on_status,
        )
        
        # Update status
        status = "completed" if success else "failed"
        self.experiment_manager.update_experiment(experiment.id, status=status)
        
        return experiment.id
    
    def get_best_config(self) -> Optional[Path]:
        """Get the config file for the best performing experiment"""
        best = self.experiment_manager.get_best_experiment()
        if best and best.output_dir:
            config_files = list(self.config.config_dir.glob(f"*{best.id}*"))
            if config_files:
                return config_files[0]
        return None
    
    def export_model(self, experiment_id: str, output_path: str) -> bool:
        """Export/merge a trained model"""
        exp = self.experiment_manager.get_experiment(experiment_id)
        if not exp or not exp.output_dir:
            return False
        
        # Create export config
        export_config = {
            "model_name_or_path": exp.config.model_name,
            "adapter_name_or_path": exp.output_dir,
            "export_dir": output_path,
            "template": exp.config.extra_params.get("template", "default"),
        }
        
        # TODO: Generate and run export command
        print(f"Export config: {export_config}")
        return True

