"""
Training Monitor for LLaMA Factory

Provides real-time monitoring of training jobs:
- Log file watching
- Metrics extraction
- Progress tracking
- Desktop notifications
- Training status dashboard
"""

import os
import re
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable, Iterator
from collections import deque


@dataclass
class TrainingMetrics:
    """Training metrics extracted from logs"""
    timestamp: datetime = field(default_factory=datetime.now)
    step: int = 0
    epoch: float = 0.0
    loss: float = 0.0
    learning_rate: float = 0.0
    grad_norm: Optional[float] = None
    throughput: Optional[float] = None  # samples/sec
    eta: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d


@dataclass
class TrainingJob:
    """Represents a training job being monitored"""
    job_id: str
    output_dir: Path
    config_path: Optional[Path] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "running"  # running, completed, failed, stopped
    metrics_history: list[TrainingMetrics] = field(default_factory=list)
    
    @property
    def log_file(self) -> Path:
        return self.output_dir / "trainer_log.jsonl"
    
    @property
    def is_running(self) -> bool:
        return self.status == "running"
    
    @property
    def latest_metrics(self) -> Optional[TrainingMetrics]:
        return self.metrics_history[-1] if self.metrics_history else None


class LogParser:
    """Parse LLaMA Factory training logs"""
    
    # Regex patterns for log parsing
    PATTERNS = {
        'step': re.compile(r'step[:\s]+(\d+)', re.IGNORECASE),
        'epoch': re.compile(r'epoch[:\s]+([0-9.]+)', re.IGNORECASE),
        'loss': re.compile(r'loss[:\s]+([0-9.]+)', re.IGNORECASE),
        'lr': re.compile(r'(?:lr|learning_rate)[:\s]+([0-9.e-]+)', re.IGNORECASE),
        'grad_norm': re.compile(r'grad_norm[:\s]+([0-9.]+)', re.IGNORECASE),
    }
    
    @classmethod
    def parse_line(cls, line: str) -> Optional[TrainingMetrics]:
        """Parse a single log line into metrics"""
        metrics = TrainingMetrics()
        found_any = False
        
        # Try JSON format first (trainer_log.jsonl)
        try:
            data = json.loads(line)
            if 'loss' in data:
                metrics.loss = float(data['loss'])
                found_any = True
            if 'learning_rate' in data:
                metrics.learning_rate = float(data['learning_rate'])
                found_any = True
            if 'step' in data:
                metrics.step = int(data['step'])
                found_any = True
            if 'epoch' in data:
                metrics.epoch = float(data['epoch'])
                found_any = True
            if 'grad_norm' in data:
                metrics.grad_norm = float(data['grad_norm'])
                found_any = True
            return metrics if found_any else None
        except json.JSONDecodeError:
            pass
        
        # Fall back to regex parsing for plain text logs
        for name, pattern in cls.PATTERNS.items():
            match = pattern.search(line)
            if match:
                found_any = True
                value = match.group(1)
                if name == 'step':
                    metrics.step = int(value)
                elif name == 'epoch':
                    metrics.epoch = float(value)
                elif name == 'loss':
                    metrics.loss = float(value)
                elif name == 'lr':
                    metrics.learning_rate = float(value)
                elif name == 'grad_norm':
                    metrics.grad_norm = float(value)
        
        return metrics if found_any else None
    
    @classmethod
    def parse_file(cls, log_path: Path) -> Iterator[TrainingMetrics]:
        """Parse entire log file"""
        if not log_path.exists():
            return
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                metrics = cls.parse_line(line.strip())
                if metrics:
                    yield metrics


class TrainingMonitor:
    """
    Monitor training jobs in real-time
    
    Watches log files and extracts metrics for tracking progress.
    """
    
    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self.jobs: dict[str, TrainingJob] = {}
        self.callbacks: list[Callable[[TrainingJob, TrainingMetrics], None]] = []
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
    
    def add_job(self, job: TrainingJob) -> None:
        """Add a job to monitor"""
        self.jobs[job.job_id] = job
    
    def remove_job(self, job_id: str) -> None:
        """Remove a job from monitoring"""
        if job_id in self.jobs:
            del self.jobs[job_id]
    
    def add_callback(self, callback: Callable[[TrainingJob, TrainingMetrics], None]) -> None:
        """Add callback for metrics updates"""
        self.callbacks.append(callback)
    
    def _notify(self, job: TrainingJob, metrics: TrainingMetrics) -> None:
        """Notify all callbacks of new metrics"""
        for callback in self.callbacks:
            try:
                callback(job, metrics)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def _check_job(self, job: TrainingJob) -> None:
        """Check a single job for new metrics"""
        if not job.is_running:
            return
        
        log_file = job.log_file
        if not log_file.exists():
            return
        
        # Get current position
        last_step = job.latest_metrics.step if job.latest_metrics else -1
        
        # Parse new entries
        for metrics in LogParser.parse_file(log_file):
            if metrics.step > last_step:
                job.metrics_history.append(metrics)
                self._notify(job, metrics)
                last_step = metrics.step

