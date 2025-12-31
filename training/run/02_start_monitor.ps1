# ============================================================
# STEP 2: Start Resource Monitor
# ============================================================
# Opens a separate window to monitor GPU/CPU/Memory during training
# Run this BEFORE starting training, keep it open in a separate terminal

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "RESOURCE MONITOR" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop monitoring" -ForegroundColor Yellow
Write-Host ""

$refreshSeconds = 5

while ($true) {
    Clear-Host
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host "TRAINING RESOURCE MONITOR (refreshes every ${refreshSeconds}s)" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
    Write-Host "=" * 60 -ForegroundColor Cyan
    
    Write-Host "`n[GPU STATUS]" -ForegroundColor Yellow
    nvidia-smi --query-gpu=timestamp,name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits | ForEach-Object {
        $parts = $_ -split ','
        Write-Host "  GPU Util: $($parts[2].Trim())%  |  VRAM: $($parts[4].Trim())/$($parts[5].Trim()) MB  |  Temp: $($parts[6].Trim())°C"
    }
    
    Write-Host "`n[SYSTEM MEMORY]" -ForegroundColor Yellow
    $os = Get-CimInstance Win32_OperatingSystem
    $totalRAM = [math]::Round($os.TotalVisibleMemorySize/1MB, 2)
    $freeRAM = [math]::Round($os.FreePhysicalMemory/1MB, 2)
    $usedRAM = $totalRAM - $freeRAM
    $pctUsed = [math]::Round(($usedRAM / $totalRAM) * 100, 1)
    Write-Host "  RAM: ${usedRAM}/${totalRAM} GB (${pctUsed}% used)"
    
    Write-Host "`n[CHECKPOINT STATUS]" -ForegroundColor Yellow
    $checkpointDir = "saves/vgpt2_v3/sft"
    if (Test-Path $checkpointDir) {
        $checkpoints = Get-ChildItem -Path $checkpointDir -Directory -Filter "checkpoint-*" | Sort-Object Name -Descending | Select-Object -First 3
        if ($checkpoints) {
            Write-Host "  Latest checkpoints:"
            foreach ($cp in $checkpoints) {
                $size = [math]::Round((Get-ChildItem -Path $cp.FullName -Recurse | Measure-Object -Property Length -Sum).Sum/1MB, 0)
                Write-Host "    $($cp.Name) - ${size} MB - $($cp.LastWriteTime)"
            }
        } else {
            Write-Host "  No checkpoints yet"
        }
    } else {
        Write-Host "  Checkpoint directory not created yet"
    }
    
    Write-Host "`n[TRAINING PROCESS]" -ForegroundColor Yellow
    $pythonProcs = Get-Process -Name "python" -ErrorAction SilentlyContinue
    if ($pythonProcs) {
        foreach ($p in $pythonProcs) {
            $mem = [math]::Round($p.WorkingSet64/1MB, 0)
            Write-Host "  PID: $($p.Id) | Memory: ${mem} MB | CPU: $([math]::Round($p.CPU, 1))s"
        }
    } else {
        Write-Host "  No Python process running"
    }
    
    Start-Sleep -Seconds $refreshSeconds
}

