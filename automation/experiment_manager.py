"""
Experiment Manager for LLaMA Factory

Track, compare, and manage training experiments:
- Experiment versioning and metadata
- Results comparison
- Model artifact management
- Hyperparameter analysis
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
import hashlib


@dataclass
class ExperimentConfig:
    """Configuration snapshot for an experiment"""
    model_name: str
    dataset: str
    finetuning_type: str
    learning_rate: float
    lora_rank: Optional[int] = None
    batch_size: int = 1
    epochs: float = 3.0
    extra_params: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_yaml_file(cls, path: Path) -> "ExperimentConfig":
        """Load config from YAML file"""
        import yaml
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            model_name=data.get('model_name_or_path', ''),
            dataset=data.get('dataset', ''),
            finetuning_type=data.get('finetuning_type', 'lora'),
            learning_rate=data.get('learning_rate', 1e-4),
            lora_rank=data.get('lora_rank'),
            batch_size=data.get('per_device_train_batch_size', 1),
            epochs=data.get('num_train_epochs', 3.0),
            extra_params={k: v for k, v in data.items() 
                         if k not in ['model_name_or_path', 'dataset', 'finetuning_type',
                                     'learning_rate', 'lora_rank', 'per_device_train_batch_size',
                                     'num_train_epochs']}
        )


@dataclass
class ExperimentResult:
    """Results from a training experiment"""
    final_loss: float = 0.0
    best_loss: float = 0.0
    total_steps: int = 0
    training_time_seconds: float = 0.0
    eval_metrics: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass 
class Experiment:
    """A training experiment record"""
    id: str
    name: str
    config: ExperimentConfig
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "created"  # created, running, completed, failed
    output_dir: Optional[str] = None
    result: Optional[ExperimentResult] = None
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        d = {
            'id': self.id,
            'name': self.name,
            'config': self.config.to_dict(),
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'output_dir': self.output_dir,
            'result': self.result.to_dict() if self.result else None,
            'notes': self.notes,
            'tags': self.tags,
        }
        return d
    
    @classmethod
    def from_dict(cls, d: dict) -> "Experiment":
        config = ExperimentConfig(**d['config'])
        result = ExperimentResult(**d['result']) if d.get('result') else None
        return cls(
            id=d['id'],
            name=d['name'],
            config=config,
            created_at=datetime.fromisoformat(d['created_at']),
            completed_at=datetime.fromisoformat(d['completed_at']) if d.get('completed_at') else None,
            status=d['status'],
            output_dir=d.get('output_dir'),
            result=result,
            notes=d.get('notes', ''),
            tags=d.get('tags', []),
        )


class ExperimentManager:
    """
    Manage training experiments with tracking and comparison
    """
    
    def __init__(self, experiments_dir: Optional[Path] = None):
        from . import DEFAULT_EXPERIMENTS_DIR
        self.experiments_dir = Path(experiments_dir) if experiments_dir else DEFAULT_EXPERIMENTS_DIR
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.experiments_dir / "experiments_index.json"
        self.experiments: dict[str, Experiment] = {}
        self._load_index()
    
    def _load_index(self) -> None:
        """Load experiments index from disk"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                data = json.load(f)
                for exp_dict in data.get('experiments', []):
                    exp = Experiment.from_dict(exp_dict)
                    self.experiments[exp.id] = exp
    
    def _save_index(self) -> None:
        """Save experiments index to disk"""
        data = {
            'version': '1.0',
            'updated_at': datetime.now().isoformat(),
            'experiments': [exp.to_dict() for exp in self.experiments.values()]
        }
        with open(self.index_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _generate_id(self, config: ExperimentConfig) -> str:
        """Generate unique experiment ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_hash = hashlib.md5(json.dumps(config.to_dict(), sort_keys=True).encode()).hexdigest()[:8]
        return f"{timestamp}_{config_hash}"
    
    def create_experiment(
        self,
        name: str,
        config: ExperimentConfig,
        output_dir: Optional[str] = None,
        tags: Optional[list[str]] = None,
        notes: str = "",
    ) -> Experiment:
        """Create a new experiment"""
        exp_id = self._generate_id(config)
        
        if output_dir is None:
            output_dir = str(self.experiments_dir / exp_id / "output")
        
        experiment = Experiment(
            id=exp_id,
            name=name,
            config=config,
            output_dir=output_dir,
            tags=tags or [],
            notes=notes,
        )
        
        self.experiments[exp_id] = experiment
        self._save_index()
        
        return experiment
    
    def get_experiment(self, exp_id: str) -> Optional[Experiment]:
        """Get experiment by ID"""
        return self.experiments.get(exp_id)
    
    def list_experiments(
        self,
        status: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[Experiment]:
        """List experiments with optional filters"""
        results = list(self.experiments.values())
        
        if status:
            results = [e for e in results if e.status == status]
        
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        
        return sorted(results, key=lambda e: e.created_at, reverse=True)

