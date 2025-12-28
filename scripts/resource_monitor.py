#!/usr/bin/env python3
"""
Resource Monitor for LLM Training
Shows: Available vs Required vs Used resources (GPU, RAM, CPU)
Run in separate terminal: python scripts/resource_monitor.py
"""

import subprocess
import psutil
import time
import os
from datetime import datetime

def get_gpu_info():
    """Get NVIDIA GPU stats via nvidia-smi"""
    try:
        result = subprocess.run([
            'nvidia-smi', 
            '--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw,power.limit',
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            parts = [p.strip() for p in result.stdout.strip().split(',')]
            # nvidia-smi returns MiB, convert to GB
            return {
                'name': parts[0],
                'vram_total': float(parts[1]) / 1024,  # MiB to GB
                'vram_used': float(parts[2]) / 1024,   # MiB to GB
                'vram_free': float(parts[3]) / 1024,   # MiB to GB
                'gpu_util': float(parts[4]),
                'temp': float(parts[5]),
                'power_draw': float(parts[6]) if parts[6] != '[N/A]' else 0,
                'power_limit': float(parts[7]) if parts[7] != '[N/A]' else 0,
            }
    except Exception as e:
        return None

def get_system_info():
    """Get CPU and RAM stats"""
    mem = psutil.virtual_memory()
    return {
        'cpu_percent': psutil.cpu_percent(interval=0.1),
        'cpu_count': psutil.cpu_count(),
        'ram_total': mem.total / (1024**3),
        'ram_used': mem.used / (1024**3),
        'ram_free': mem.available / (1024**3),
        'ram_percent': mem.percent,
    }

def bar(used, total, width=30):
    """Create a progress bar"""
    pct = min(used / total, 1.0) if total > 0 else 0
    filled = int(width * pct)
    return f"[{'█' * filled}{'░' * (width - filled)}]"

def color(pct):
    """Return color indicator based on usage percentage"""
    if pct >= 90: return "🔴"
    if pct >= 70: return "🟡"
    return "🟢"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    print("Starting Resource Monitor... (Ctrl+C to stop)\n")
    
    # Expected requirements for training
    REQUIRED = {
        'vram': 35,      # GB - estimated for Qwen 2.5 7B with LoRA
        'ram': 32,       # GB - for data loading
        'cpu': 30,       # % - for preprocessing
    }
    
    try:
        while True:
            clear_screen()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{'='*70}")
            print(f"  RESOURCE MONITOR - LLM Training    {now}")
            print(f"{'='*70}\n")
            
            # GPU Info
            gpu = get_gpu_info()
            if gpu:
                vram_pct = (gpu['vram_used'] / gpu['vram_total']) * 100
                gpu_pct = gpu['gpu_util']
                
                print(f"  🖥️  GPU: {gpu['name']}")
                print(f"  {'─'*66}")
                print(f"  VRAM Usage:    {bar(gpu['vram_used'], gpu['vram_total'])} {gpu['vram_used']:.1f} / {gpu['vram_total']:.1f} GB ({vram_pct:.1f}%) {color(vram_pct)}")
                print(f"  GPU Compute:   {bar(gpu_pct, 100)} {gpu_pct:.1f}% {color(100-gpu_pct)}")  # Invert - want HIGH usage
                print(f"  Temperature:   {gpu['temp']:.0f}°C")
                if gpu['power_limit'] > 0:
                    print(f"  Power:         {gpu['power_draw']:.0f}W / {gpu['power_limit']:.0f}W")
                print()
                
                # Analysis
                print(f"  📊 VRAM Analysis:")
                print(f"     Required (est): ~{REQUIRED['vram']} GB")
                print(f"     Available:      {gpu['vram_total']:.1f} GB")
                print(f"     Currently Used: {gpu['vram_used']:.1f} GB")
                print(f"     Headroom:       {gpu['vram_free']:.1f} GB")
                
                if gpu_pct < 50:
                    print(f"\n  ⚠️  GPU Utilization LOW ({gpu_pct:.0f}%) - may be CPU/IO bottlenecked")
                elif gpu_pct > 90:
                    print(f"\n  ✅ GPU Utilization GOOD ({gpu_pct:.0f}%) - training efficiently")
            else:
                print("  ❌ No NVIDIA GPU detected\n")
            
            # System Info  
            sys_info = get_system_info()
            ram_pct = sys_info['ram_percent']
            cpu_pct = sys_info['cpu_percent']
            
            print(f"\n  💾 System RAM:")
            print(f"  {'─'*66}")
            print(f"  RAM Usage:     {bar(sys_info['ram_used'], sys_info['ram_total'])} {sys_info['ram_used']:.1f} / {sys_info['ram_total']:.1f} GB ({ram_pct:.1f}%) {color(ram_pct)}")
            print(f"  CPU Usage:     {bar(cpu_pct, 100)} {cpu_pct:.1f}% ({sys_info['cpu_count']} cores)")
            
            print(f"\n{'='*70}")
            print(f"  Refreshing every 2 seconds... Press Ctrl+C to stop")
            print(f"{'='*70}")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")

if __name__ == "__main__":
    main()

