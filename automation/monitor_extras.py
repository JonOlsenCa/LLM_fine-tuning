"""
Additional monitoring utilities - background monitoring and notifications
"""

import os
import json
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import asdict

from .monitor import TrainingMonitor, TrainingJob, TrainingMetrics


class BackgroundMonitor(TrainingMonitor):
    """Training monitor with background thread support"""
    
    def start(self) -> None:
        """Start monitoring in background thread"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop(self) -> None:
        """Stop background monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        import time
        while self._monitoring:
            for job in list(self.jobs.values()):
                self._check_job(job)
            time.sleep(self.poll_interval)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()


def create_console_callback(show_loss: bool = True, show_progress: bool = True):
    """Create a callback that prints to console"""
    def callback(job: TrainingJob, metrics: TrainingMetrics):
        parts = [f"[{job.job_id}]"]
        
        if show_progress:
            parts.append(f"Step {metrics.step}")
            if metrics.epoch > 0:
                parts.append(f"Epoch {metrics.epoch:.2f}")
        
        if show_loss and metrics.loss > 0:
            parts.append(f"Loss: {metrics.loss:.4f}")
        
        if metrics.learning_rate > 0:
            parts.append(f"LR: {metrics.learning_rate:.2e}")
        
        print(" | ".join(parts))
    
    return callback


def create_notification_callback(notify_every: int = 100, notify_on_complete: bool = True):
    """Create a callback that sends Windows notifications"""
    last_notified = {}
    
    def callback(job: TrainingJob, metrics: TrainingMetrics):
        job_last = last_notified.get(job.job_id, -notify_every)
        
        # Periodic notification
        if metrics.step - job_last >= notify_every:
            send_windows_notification(
                title=f"Training Progress: {job.job_id}",
                message=f"Step {metrics.step} | Loss: {metrics.loss:.4f}"
            )
            last_notified[job.job_id] = metrics.step
        
        # Completion notification
        if notify_on_complete and not job.is_running:
            send_windows_notification(
                title=f"Training Complete: {job.job_id}",
                message=f"Final loss: {metrics.loss:.4f}"
            )
    
    return callback


def send_windows_notification(title: str, message: str):
    """Send a Windows toast notification using PowerShell"""
    try:
        ps_script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        
        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{title}</text>
                    <text id="2">{message}</text>
                </binding>
            </visual>
        </toast>
"@
        
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("LLaMA Factory").Show($toast)
        '''
        
        subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            timeout=5
        )
    except Exception as e:
        print(f"Failed to send notification: {e}")


def create_json_logger_callback(log_dir: Path):
    """Create a callback that logs metrics to JSON file"""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    def callback(job: TrainingJob, metrics: TrainingMetrics):
        log_file = log_dir / f"{job.job_id}_metrics.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(metrics.to_dict()) + '\n')
    
    return callback


def monitor_training_job(
    output_dir: str,
    job_id: str = None,
    show_console: bool = True,
    notifications: bool = False,
    notify_every: int = 100,
) -> BackgroundMonitor:
    """
    Convenience function to set up and start monitoring a training job
    
    Args:
        output_dir: Training output directory to monitor
        job_id: Optional job identifier (defaults to output_dir name)
        show_console: Print progress to console
        notifications: Send Windows notifications
        notify_every: Steps between notifications
    
    Returns:
        Started BackgroundMonitor instance
    """
    output_path = Path(output_dir)
    job_id = job_id or output_path.name
    
    job = TrainingJob(
        job_id=job_id,
        output_dir=output_path,
    )
    
    monitor = BackgroundMonitor()
    monitor.add_job(job)
    
    if show_console:
        monitor.add_callback(create_console_callback())
    
    if notifications:
        monitor.add_callback(create_notification_callback(notify_every=notify_every))
    
    monitor.start()
    return monitor

