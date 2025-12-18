"""
LLaMA Factory Automation CLI

Command-line interface for the automation system.
Usage: python -m automation.cli <command> [options]
"""

import argparse
import sys
from pathlib import Path


def cmd_train(args):
    """Run a training job"""
    from .orchestrator_extras import ExtendedOrchestrator
    
    orchestrator = ExtendedOrchestrator()
    
    config_path, config = orchestrator.create_training_config(
        model=args.model,
        dataset=args.dataset,
        output_name=args.output_name,
        learning_rate=args.learning_rate,
        epochs=args.epochs,
        lora_rank=args.lora_rank,
        batch_size=args.batch_size,
        max_samples=args.max_samples,
    )
    
    print(f"Created config: {config_path}")
    
    if not args.config_only:
        exp_id = orchestrator.run_training_cli(
            config_path=config_path,
            experiment_name=args.name,
            monitor=not args.no_monitor,
            tags=args.tags.split(",") if args.tags else None,
        )
        print(f"Experiment completed: {exp_id}")


def cmd_sweep(args):
    """Run a hyperparameter sweep"""
    from .orchestrator_extras import ExtendedOrchestrator
    
    orchestrator = ExtendedOrchestrator()
    
    learning_rates = [float(x) for x in args.learning_rates.split(",")]
    lora_ranks = [int(x) for x in args.lora_ranks.split(",")]
    batch_sizes = [int(x) for x in args.batch_sizes.split(",")]
    
    exp_ids = orchestrator.run_parameter_sweep(
        model=args.model,
        dataset=args.dataset,
        learning_rates=learning_rates,
        lora_ranks=lora_ranks,
        batch_sizes=batch_sizes,
        sequential=not args.parallel,
        tags=args.tags.split(",") if args.tags else None,
    )
    
    print(f"Sweep completed. Experiments: {len(exp_ids)}")
    for exp_id in exp_ids:
        print(f"  - {exp_id}")


def cmd_webui(args):
    """Launch the Web UI"""
    from .orchestrator_extras import ExtendedOrchestrator
    
    orchestrator = ExtendedOrchestrator()
    process = orchestrator.launch_webui(open_browser=not args.no_browser)
    
    print("Press Ctrl+C to stop the server")
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()


def cmd_experiments(args):
    """Manage experiments"""
    from .experiment_manager_extras import ExperimentManagerExtended
    
    manager = ExperimentManagerExtended()
    
    if args.action == "list":
        experiments = manager.list_experiments(status=args.status)
        print(f"\nExperiments ({len(experiments)}):")
        print("-" * 80)
        for exp in experiments:
            loss_str = f"Loss: {exp.result.final_loss:.4f}" if exp.result else "No results"
            print(f"[{exp.status:10}] {exp.id} | {exp.name} | {loss_str}")
        print("-" * 80)
    
    elif args.action == "compare":
        if not args.ids:
            print("Error: --ids required for compare")
            return
        
        comparison = manager.compare_experiments(args.ids.split(","))
        print("\nExperiment Comparison:")
        print("-" * 80)
        
        if comparison['config_diff']:
            print("\nConfig Differences:")
            for key, values in comparison['config_diff'].items():
                print(f"  {key}:")
                for exp_id, value in values.items():
                    print(f"    {exp_id}: {value}")
        
        if comparison['results_comparison'].get('ranking_by_loss'):
            print("\nRanking by Loss:")
            for i, item in enumerate(comparison['results_comparison']['ranking_by_loss'], 1):
                print(f"  {i}. {item['name']}: {item['loss']:.4f}")
    
    elif args.action == "export":
        output_path = Path(args.output or "experiments.csv")
        manager.export_to_csv(output_path)
        print(f"Exported to: {output_path}")
    
    elif args.action == "best":
        best = manager.get_best_experiment()
        if best:
            print(f"\nBest Experiment: {best.name}")
            print(f"  ID: {best.id}")
            print(f"  Model: {best.config.model_name}")
            print(f"  Final Loss: {best.result.final_loss:.4f}")
        else:
            print("No completed experiments found")


def cmd_monitor(args):
    """Monitor a training job"""
    from .monitor_extras import monitor_training_job
    
    monitor = monitor_training_job(
        output_dir=args.output_dir,
        job_id=args.job_id,
        show_console=True,
        notifications=args.notify,
        notify_every=args.notify_every,
    )
    
    print(f"Monitoring: {args.output_dir}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()


def main():
    parser = argparse.ArgumentParser(
        description="LLaMA Factory Automation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Train command
    train_parser = subparsers.add_parser("train", help="Run training job")
    train_parser.add_argument("--model", required=True, help="Model name or preset")
    train_parser.add_argument("--dataset", required=True, help="Dataset name")
    train_parser.add_argument("--name", help="Experiment name")
    train_parser.add_argument("--output-name", help="Output directory name")
    train_parser.add_argument("--learning-rate", type=float, default=1e-4)
    train_parser.add_argument("--epochs", type=float, default=3.0)
    train_parser.add_argument("--lora-rank", type=int, default=8)
    train_parser.add_argument("--batch-size", type=int, default=2)
    train_parser.add_argument("--max-samples", type=int)
    train_parser.add_argument("--tags", help="Comma-separated tags")
    train_parser.add_argument("--config-only", action="store_true")
    train_parser.add_argument("--no-monitor", action="store_true")
    train_parser.set_defaults(func=cmd_train)
    
    # Sweep command
    sweep_parser = subparsers.add_parser("sweep", help="Run hyperparameter sweep")
    sweep_parser.add_argument("--model", required=True)
    sweep_parser.add_argument("--dataset", required=True)
    sweep_parser.add_argument("--learning-rates", default="1e-4,5e-5")
    sweep_parser.add_argument("--lora-ranks", default="8,16")
    sweep_parser.add_argument("--batch-sizes", default="2")
    sweep_parser.add_argument("--parallel", action="store_true")
    sweep_parser.add_argument("--tags")
    sweep_parser.set_defaults(func=cmd_sweep)
    
    # WebUI command
    webui_parser = subparsers.add_parser("webui", help="Launch Web UI")
    webui_parser.add_argument("--no-browser", action="store_true")
    webui_parser.set_defaults(func=cmd_webui)
    
    # Experiments command
    exp_parser = subparsers.add_parser("experiments", help="Manage experiments")
    exp_parser.add_argument("action", choices=["list", "compare", "export", "best"])
    exp_parser.add_argument("--status", help="Filter by status")
    exp_parser.add_argument("--ids", help="Comma-separated experiment IDs")
    exp_parser.add_argument("--output", help="Export output path")
    exp_parser.set_defaults(func=cmd_experiments)
    
    # Monitor command
    mon_parser = subparsers.add_parser("monitor", help="Monitor training")
    mon_parser.add_argument("output_dir", help="Output directory to monitor")
    mon_parser.add_argument("--job-id", help="Job identifier")
    mon_parser.add_argument("--notify", action="store_true")
    mon_parser.add_argument("--notify-every", type=int, default=100)
    mon_parser.set_defaults(func=cmd_monitor)
    
    args = parser.parse_args()
    
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

