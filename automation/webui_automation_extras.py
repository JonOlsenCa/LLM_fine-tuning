"""
Additional Web UI automation utilities - monitoring and MCP integration
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from .webui_automation import LLaMABoardAutomation, WebUIConfig, TrainingParams


@dataclass
class TrainingStatus:
    """Current training status from the UI"""
    is_running: bool = False
    current_step: int = 0
    total_steps: int = 0
    current_epoch: float = 0.0
    total_epochs: float = 0.0
    loss: Optional[float] = None
    learning_rate: Optional[float] = None
    eta: Optional[str] = None
    log_text: str = ""


class LLaMABoardMonitor(LLaMABoardAutomation):
    """
    Extended automation with monitoring capabilities
    """
    
    def __init__(self, config: Optional[WebUIConfig] = None):
        super().__init__(config)
        self.status_callbacks: list[Callable[[TrainingStatus], None]] = []
        self._monitoring = False
    
    def add_status_callback(self, callback: Callable[[TrainingStatus], None]):
        """Add a callback to be called when status updates"""
        self.status_callbacks.append(callback)
    
    async def get_training_status(self) -> TrainingStatus:
        """Get current training status from the UI"""
        status = TrainingStatus()
        
        # Check if training is running by looking for stop button
        stop_btn = await self.page.query_selector('button:has-text("Stop"), button:has-text("Abort")')
        status.is_running = stop_btn is not None and await stop_btn.is_visible()
        
        # Try to get progress info from the UI
        # Gradio progress bar
        progress_bar = await self.page.query_selector('.progress-bar, [role="progressbar"]')
        if progress_bar:
            progress_text = await progress_bar.get_attribute("aria-valuenow")
            if progress_text:
                try:
                    status.current_step = int(float(progress_text))
                except ValueError:
                    pass
        
        # Get log output
        log_area = await self.page.query_selector('textarea[readonly], .log-output, pre')
        if log_area:
            status.log_text = await log_area.inner_text()
            # Parse loss from log if available
            status.loss = self._parse_loss_from_log(status.log_text)
        
        return status
    
    def _parse_loss_from_log(self, log_text: str) -> Optional[float]:
        """Extract the latest loss value from training log"""
        import re
        # Look for patterns like "loss: 1.234" or "Loss: 1.234"
        matches = re.findall(r'loss[:\s]+([0-9]+\.?[0-9]*)', log_text, re.IGNORECASE)
        if matches:
            try:
                return float(matches[-1])
            except ValueError:
                pass
        return None
    
    async def monitor_training(self, interval: float = 5.0, max_duration: float = None):
        """
        Monitor training progress at regular intervals
        
        Args:
            interval: Seconds between status checks
            max_duration: Maximum monitoring duration in seconds (None for unlimited)
        """
        self._monitoring = True
        start_time = datetime.now()
        
        while self._monitoring:
            status = await self.get_training_status()
            
            # Notify callbacks
            for callback in self.status_callbacks:
                callback(status)
            
            # Check if training completed
            if not status.is_running:
                print("Training completed or stopped")
                break
            
            # Check max duration
            if max_duration:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= max_duration:
                    print(f"Max monitoring duration ({max_duration}s) reached")
                    break
            
            await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self._monitoring = False
    
    async def wait_for_training_complete(self, timeout: float = None) -> bool:
        """Wait for training to complete"""
        start_time = datetime.now()
        
        while True:
            status = await self.get_training_status()
            if not status.is_running:
                return True
            
            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout:
                    return False
            
            await asyncio.sleep(5)


async def run_automated_training(
    params: TrainingParams,
    webui_config: Optional[WebUIConfig] = None,
    monitor: bool = True,
    on_status: Optional[Callable[[TrainingStatus], None]] = None,
) -> bool:
    """
    Run a complete automated training job
    
    Args:
        params: Training parameters to use
        webui_config: Web UI configuration
        monitor: Whether to monitor training progress
        on_status: Callback for status updates
    
    Returns:
        True if training completed successfully
    """
    automation = LLaMABoardMonitor(webui_config)
    
    if on_status:
        automation.add_status_callback(on_status)
    
    try:
        # Navigate to UI
        print(f"Connecting to LLaMA Board at {automation.config.url}...")
        await automation.navigate_to_ui()
        
        # Configure training
        print("Configuring training parameters...")
        await automation.configure_training(params)
        
        # Start training
        print("Starting training...")
        success = await automation.start_training()
        if not success:
            print("Failed to start training")
            return False
        
        # Monitor if requested
        if monitor:
            print("Monitoring training progress...")
            await automation.wait_for_training_complete()
        
        print("Training automation completed!")
        return True
        
    except Exception as e:
        print(f"Error during automated training: {e}")
        return False
    finally:
        if automation.browser:
            await automation.browser.close()

