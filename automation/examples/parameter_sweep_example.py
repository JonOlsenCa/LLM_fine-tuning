"""
Parameter Sweep Example

Demonstrates how to run a hyperparameter sweep across:
- Learning rates
- LoRA ranks
- Batch sizes

Then compare and find the best configuration.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.orchestrator_extras import ExtendedOrchestrator


def main():
    print("=" * 60)
    print("  LLaMA Factory Parameter Sweep Example")
    print("=" * 60)
    print()
    
    orchestrator = ExtendedOrchestrator()
    
    # Define sweep parameters
    model = "llama3-8b"
    dataset = "alpaca_en_demo"
    
    learning_rates = [1e-4, 5e-5, 1e-5]
    lora_ranks = [8, 16]
    batch_sizes = [2]
    
    total_experiments = len(learning_rates) * len(lora_ranks) * len(batch_sizes)
    
    print(f"Model: {model}")
    print(f"Dataset: {dataset}")
    print()
    print("Sweep Configuration:")
    print(f"  Learning Rates: {learning_rates}")
    print(f"  LoRA Ranks: {lora_ranks}")
    print(f"  Batch Sizes: {batch_sizes}")
    print()
    print(f"Total experiments to run: {total_experiments}")
    print()
    
    response = input("Start sweep? [y/N]: ").strip().lower()
    if response != 'y':
        print("Sweep cancelled.")
        return
    
    print()
    print("Running parameter sweep...")
    print("-" * 60)
    
    exp_ids = orchestrator.run_parameter_sweep(
        model=model,
        dataset=dataset,
        learning_rates=learning_rates,
        lora_ranks=lora_ranks,
        batch_sizes=batch_sizes,
        sequential=True,  # Run one at a time
        tags=["sweep", "example"],
    )
    
    print("-" * 60)
    print()
    print(f"Sweep completed! {len(exp_ids)} experiments run.")
    print()
    
    # Compare results
    print("Comparing experiments...")
    comparison = orchestrator.experiment_manager.compare_experiments(exp_ids)
    
    if comparison['results_comparison'].get('ranking_by_loss'):
        print()
        print("Ranking by Final Loss:")
        print("-" * 40)
        for i, item in enumerate(comparison['results_comparison']['ranking_by_loss'], 1):
            print(f"  {i}. {item['name']}: {item['loss']:.4f}")
    
    # Get best experiment
    best = orchestrator.experiment_manager.get_best_experiment()
    if best:
        print()
        print("=" * 40)
        print(f"BEST CONFIGURATION: {best.name}")
        print("=" * 40)
        print(f"  Learning Rate: {best.config.learning_rate}")
        print(f"  LoRA Rank: {best.config.lora_rank}")
        print(f"  Batch Size: {best.config.batch_size}")
        print(f"  Final Loss: {best.result.final_loss:.4f}")
        print()
        print(f"Output directory: {best.output_dir}")
    
    # Export results
    export_path = orchestrator.experiment_manager.export_to_csv(
        Path("automation/experiments/sweep_results.csv")
    )
    print()
    print(f"Results exported to: {export_path}")


if __name__ == "__main__":
    main()

