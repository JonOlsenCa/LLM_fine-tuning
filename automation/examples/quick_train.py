"""
Quick Training Example

Demonstrates how to use the automation system to:
1. Generate a training configuration
2. Run training with monitoring
3. Track the experiment
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.orchestrator_extras import ExtendedOrchestrator
from automation.config_generator_extras import MODEL_PRESETS


def main():
    print("=" * 60)
    print("  LLaMA Factory Quick Training Example")
    print("=" * 60)
    print()
    
    # Show available model presets
    print("Available model presets:")
    for name in MODEL_PRESETS:
        print(f"  - {name}")
    print()
    
    # Initialize orchestrator
    orchestrator = ExtendedOrchestrator()
    
    # Configuration
    model = "llama3-8b"  # Change to your preferred model
    dataset = "alpaca_en_demo"  # Change to your dataset
    
    print(f"Model: {model}")
    print(f"Dataset: {dataset}")
    print()
    
    # Create training configuration
    print("Creating training configuration...")
    config_path, config = orchestrator.create_training_config(
        model=model,
        dataset=dataset,
        learning_rate=1e-4,
        epochs=3.0,
        lora_rank=8,
        batch_size=2,
        max_samples=1000,  # Limit samples for quick demo
    )
    
    print(f"Config saved to: {config_path}")
    print()
    
    # Show config summary
    print("Configuration Summary:")
    print(f"  Output: {config.output.output_dir}")
    print(f"  Learning Rate: {config.training.learning_rate}")
    print(f"  Epochs: {config.training.num_train_epochs}")
    print(f"  LoRA Rank: {config.lora.lora_rank}")
    print(f"  Batch Size: {config.training.per_device_train_batch_size}")
    print()
    
    # Ask user to confirm
    response = input("Start training? [y/N]: ").strip().lower()
    if response != 'y':
        print("Training cancelled. Config saved for later use.")
        return
    
    # Run training
    print()
    print("Starting training...")
    print("-" * 60)
    
    exp_id = orchestrator.run_training_cli(
        config_path=config_path,
        experiment_name="quick_train_demo",
        monitor=True,
        tags=["demo", "quick-start"],
    )
    
    print("-" * 60)
    print()
    print(f"Training completed!")
    print(f"Experiment ID: {exp_id}")
    
    # Show results
    exp = orchestrator.experiment_manager.get_experiment(exp_id)
    if exp and exp.result:
        print()
        print("Results:")
        print(f"  Final Loss: {exp.result.final_loss:.4f}")
        print(f"  Best Loss: {exp.result.best_loss:.4f}")
        print(f"  Total Steps: {exp.result.total_steps}")


if __name__ == "__main__":
    main()

