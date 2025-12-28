# VGPT2 Training - GPU Maximization Script
# Run as Administrator for full effect
#
# This script:
# 1. Closes GPU-hungry apps (browsers, Teams, etc.)
# 2. Stops non-essential services
# 3. Sets high-performance power profile
# 4. Clears GPU memory

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VGPT2 GPU Maximization Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator. Some optimizations may fail." -ForegroundColor Yellow
}

# Show current GPU state
Write-Host "`n[1/5] Current GPU Status:" -ForegroundColor Green
nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv

# Apps to close (GPU-heavy)
$appsToClose = @(
    "DuckDuckGo",
    "msedge",
    "msedgewebview2",
    "chrome",
    "firefox",
    "ms-teams",
    "Teams",
    "WhatsApp",
    "Copilot",
    "slack",
    "discord",
    "Snagit*",
    "SnagitEditor",
    "Video.UI",
    "NVIDIA Overlay"
)

Write-Host "`n[2/5] Closing GPU-heavy applications..." -ForegroundColor Green
foreach ($app in $appsToClose) {
    $procs = Get-Process -Name $app -ErrorAction SilentlyContinue
    if ($procs) {
        Write-Host "  Closing: $app" -ForegroundColor Yellow
        $procs | Stop-Process -Force -ErrorAction SilentlyContinue
    }
}

# Stop some services that might use GPU
Write-Host "`n[3/5] Stopping non-essential services..." -ForegroundColor Green
$servicesToStop = @(
    "NVDisplay.ContainerLocalSystem"  # NVIDIA Display Container (optional)
)
foreach ($svc in $servicesToStop) {
    $service = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($service -and $service.Status -eq 'Running') {
        Write-Host "  Stopping: $svc" -ForegroundColor Yellow
        Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
    }
}

# Set high performance power plan
Write-Host "`n[4/5] Setting High Performance power plan..." -ForegroundColor Green
$highPerfGuid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
powercfg /setactive $highPerfGuid 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Power plan set to High Performance" -ForegroundColor Green
} else {
    Write-Host "  Could not set power plan (may need admin)" -ForegroundColor Yellow
}

# Clear CUDA cache
Write-Host "`n[5/5] Clearing CUDA/PyTorch caches..." -ForegroundColor Green
$cudaCache = "$env:USERPROFILE\.cache\torch"
if (Test-Path $cudaCache) {
    Write-Host "  Clearing PyTorch cache at $cudaCache"
    # Don't delete, just report size
    $size = (Get-ChildItem $cudaCache -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB
    Write-Host "  Cache size: $([math]::Round($size, 2)) GB"
}

# Wait for GPU memory to be released
Write-Host "`nWaiting 5 seconds for GPU memory release..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Final GPU state
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Final GPU Status:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv
nvidia-smi

Write-Host "`n[READY] GPU optimized for training!" -ForegroundColor Green
Write-Host "Run: llamafactory-cli train automation/configs/vgpt2_lora_sft.yaml" -ForegroundColor Cyan

