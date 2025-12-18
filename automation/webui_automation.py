"""
LLaMA Board Web UI Automation using Playwright

Provides automated interaction with the LLaMA Factory web interface:
- Model selection and configuration
- Dataset management
- Training parameter configuration  
- Training job launch and monitoring
- Model export and merge operations
"""

import asyncio
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime


@dataclass
class WebUIConfig:
    """Configuration for Web UI automation"""
    host: str = "127.0.0.1"
    port: int = 7860
    headless: bool = False
    timeout: int = 60000  # 60 seconds
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class TrainingParams:
    """Training parameters to configure in the Web UI"""
    # Model
    model_name: str
    model_path: Optional[str] = None
    
    # Method  
    finetuning_type: Literal["lora", "full", "freeze"] = "lora"
    lora_rank: int = 8
    lora_alpha: int = 16
    lora_target: str = "all"
    
    # Dataset
    dataset: str = "alpaca_en_demo"
    template: str = "llama3"
    cutoff_len: int = 2048
    max_samples: Optional[int] = None
    
    # Training
    learning_rate: float = 1e-4
    num_epochs: float = 3.0
    batch_size: int = 2
    gradient_accumulation: int = 4
    
    # Output
    output_dir: str = "saves/webui_train"
    logging_steps: int = 10
    save_steps: int = 500


class LLaMABoardAutomation:
    """
    Automation controller for LLaMA Board Web UI
    
    This class provides methods to interact with the Gradio-based
    LLaMA Board interface programmatically.
    """
    
    def __init__(self, config: Optional[WebUIConfig] = None):
        self.config = config or WebUIConfig()
        self.page = None
        self.browser = None
        
    async def _ensure_browser(self):
        """Ensure browser is launched (for direct Playwright usage)"""
        if self.browser is None:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.config.headless
            )
            self.page = await self.browser.new_page()
    
    async def navigate_to_ui(self) -> bool:
        """Navigate to the LLaMA Board UI"""
        await self._ensure_browser()
        await self.page.goto(self.config.url, timeout=self.config.timeout)
        # Wait for Gradio to fully load
        await self.page.wait_for_selector("gradio-app", timeout=self.config.timeout)
        return True
    
    async def select_language(self, language: str = "en"):
        """Select UI language"""
        lang_dropdown = await self.page.query_selector('[data-testid="lang-dropdown"]')
        if lang_dropdown:
            await lang_dropdown.click()
            await self.page.click(f'text="{language}"')
    
    async def configure_model(self, model_path: str, template: str = "llama3"):
        """Configure the model settings"""
        # Find and fill model path input
        model_input = await self.page.query_selector('input[placeholder*="model"]')
        if model_input:
            await model_input.fill(model_path)
        
        # Select template
        template_dropdown = await self.page.query_selector('[data-testid="template-dropdown"]')
        if template_dropdown:
            await template_dropdown.click()
            await self.page.click(f'text="{template}"')
    
    async def configure_training(self, params: TrainingParams):
        """Configure all training parameters"""
        # This interacts with Gradio components
        # Model configuration
        await self.configure_model(
            params.model_path or params.model_name,
            params.template
        )
        
        # Set finetuning type
        await self._set_dropdown("finetuning_type", params.finetuning_type)
        
        # Set LoRA parameters if applicable
        if params.finetuning_type == "lora":
            await self._set_slider("lora_rank", params.lora_rank)
            await self._set_slider("lora_alpha", params.lora_alpha)
        
        # Set training parameters
        await self._set_number("learning_rate", params.learning_rate)
        await self._set_number("num_epochs", params.num_epochs)
        await self._set_number("batch_size", params.batch_size)
        
        # Set output directory
        await self._set_textbox("output_dir", params.output_dir)
    
    async def _set_dropdown(self, name: str, value: str):
        """Set a dropdown value"""
        dropdown = await self.page.query_selector(f'[data-testid="{name}"]')
        if dropdown:
            await dropdown.click()
            await self.page.click(f'text="{value}"')
    
    async def _set_slider(self, name: str, value: int):
        """Set a slider value"""
        # Gradio sliders have associated number inputs
        slider_input = await self.page.query_selector(f'[data-testid="{name}"] input')
        if slider_input:
            await slider_input.fill(str(value))
    
    async def _set_number(self, name: str, value: float):
        """Set a number input"""
        num_input = await self.page.query_selector(f'[data-testid="{name}"] input')
        if num_input:
            await num_input.fill(str(value))
    
    async def _set_textbox(self, name: str, value: str):
        """Set a textbox value"""
        textbox = await self.page.query_selector(f'[data-testid="{name}"] input, [data-testid="{name}"] textarea')
        if textbox:
            await textbox.fill(value)
    
    async def start_training(self) -> bool:
        """Click the Start Training button"""
        start_btn = await self.page.query_selector('button:has-text("Start")')
        if start_btn:
            await start_btn.click()
            return True
        return False
    
    async def stop_training(self) -> bool:
        """Click the Stop Training button"""
        stop_btn = await self.page.query_selector('button:has-text("Stop"), button:has-text("Abort")')
        if stop_btn:
            await stop_btn.click()
            return True
        return False

