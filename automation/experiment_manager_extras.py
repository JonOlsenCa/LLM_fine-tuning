"""
Additional experiment management utilities - comparison and analysis
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from .experiment_manager import ExperimentManager, Experiment, ExperimentResult, ExperimentConfig
from .monitor import LogParser


class ExperimentManagerExtended(ExperimentManager):
    """Extended experiment manager with comparison and analysis"""
    
    def update_experiment(
        self,
        exp_id: str,
        status: Optional[str] = None,
        result: Optional[ExperimentResult] = None,
        notes: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[Experiment]:
        """Update an existing experiment"""
        exp = self.get_experiment(exp_id)
        if not exp:
            return None
        
        if status:
            exp.status = status
            if status == "completed":
                exp.completed_at = datetime.now()
        
        if result:
            exp.result = result
        
        if notes is not None:
            exp.notes = notes
        
        if tags is not None:
            exp.tags = tags
        
        self._save_index()
        return exp
    
    def delete_experiment(self, exp_id: str, delete_files: bool = False) -> bool:
        """Delete an experiment"""
        exp = self.get_experiment(exp_id)
        if not exp:
            return False
        
        if delete_files and exp.output_dir:
            import shutil
            output_path = Path(exp.output_dir)
            if output_path.exists():
                shutil.rmtree(output_path)
        
        del self.experiments[exp_id]
        self._save_index()
        return True
    
    def load_results_from_logs(self, exp_id: str) -> Optional[ExperimentResult]:
        """Load experiment results from training logs"""
        exp = self.get_experiment(exp_id)
        if not exp or not exp.output_dir:
            return None
        
        output_path = Path(exp.output_dir)
        log_file = output_path / "trainer_log.jsonl"
        
        if not log_file.exists():
            return None
        
        losses = []
        total_steps = 0
        
        for metrics in LogParser.parse_file(log_file):
            if metrics.loss > 0:
                losses.append(metrics.loss)
            total_steps = max(total_steps, metrics.step)
        
        if not losses:
            return None
        
        result = ExperimentResult(
            final_loss=losses[-1] if losses else 0.0,
            best_loss=min(losses) if losses else 0.0,
            total_steps=total_steps,
        )
        
        # Try to load eval metrics if available
        eval_file = output_path / "all_results.json"
        if eval_file.exists():
            with open(eval_file, 'r') as f:
                result.eval_metrics = json.load(f)
        
        return result
    
    def compare_experiments(self, exp_ids: list[str]) -> dict:
        """
        Compare multiple experiments side by side
        
        Returns a comparison dictionary with configs and results
        """
        comparison = {
            'experiments': [],
            'config_diff': {},
            'results_comparison': {},
        }
        
        experiments = [self.get_experiment(eid) for eid in exp_ids]
        experiments = [e for e in experiments if e is not None]
        
        if len(experiments) < 2:
            return comparison
        
        # Get all config keys
        all_config_keys = set()
        for exp in experiments:
            all_config_keys.update(exp.config.to_dict().keys())
        
        # Find differing config values
        for key in all_config_keys:
            values = [exp.config.to_dict().get(key) for exp in experiments]
            if len(set(str(v) for v in values)) > 1:
                comparison['config_diff'][key] = {
                    exp.id: exp.config.to_dict().get(key)
                    for exp in experiments
                }
        
        # Compare results
        for exp in experiments:
            exp_data = {
                'id': exp.id,
                'name': exp.name,
                'status': exp.status,
                'config': exp.config.to_dict(),
            }
            
            if exp.result:
                exp_data['final_loss'] = exp.result.final_loss
                exp_data['best_loss'] = exp.result.best_loss
                exp_data['total_steps'] = exp.result.total_steps
            
            comparison['experiments'].append(exp_data)
        
        # Rank by final loss if available
        completed = [e for e in experiments if e.result and e.result.final_loss > 0]
        if completed:
            ranked = sorted(completed, key=lambda e: e.result.final_loss)
            comparison['results_comparison']['ranking_by_loss'] = [
                {'id': e.id, 'name': e.name, 'loss': e.result.final_loss}
                for e in ranked
            ]
        
        return comparison
    
    def export_to_csv(self, output_path: Path) -> Path:
        """Export all experiments to CSV"""
        import csv
        
        output_path = Path(output_path)
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'ID', 'Name', 'Status', 'Model', 'Dataset', 'Finetuning Type',
                'Learning Rate', 'LoRA Rank', 'Batch Size', 'Epochs',
                'Final Loss', 'Best Loss', 'Total Steps', 'Created', 'Completed', 'Tags'
            ])
            
            for exp in self.experiments.values():
                writer.writerow([
                    exp.id,
                    exp.name,
                    exp.status,
                    exp.config.model_name,
                    exp.config.dataset,
                    exp.config.finetuning_type,
                    exp.config.learning_rate,
                    exp.config.lora_rank or '',
                    exp.config.batch_size,
                    exp.config.epochs,
                    exp.result.final_loss if exp.result else '',
                    exp.result.best_loss if exp.result else '',
                    exp.result.total_steps if exp.result else '',
                    exp.created_at.isoformat(),
                    exp.completed_at.isoformat() if exp.completed_at else '',
                    ','.join(exp.tags),
                ])
        
        return output_path
    
    def get_best_experiment(self, metric: str = "final_loss") -> Optional[Experiment]:
        """Get the best experiment by a given metric"""
        completed = [e for e in self.experiments.values() 
                     if e.status == "completed" and e.result]
        
        if not completed:
            return None
        
        if metric == "final_loss":
            return min(completed, key=lambda e: e.result.final_loss)
        elif metric == "best_loss":
            return min(completed, key=lambda e: e.result.best_loss)
        
        return None

