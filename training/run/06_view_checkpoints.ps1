# ============================================================
# STEP 6: View All Checkpoints
# ============================================================
# Lists all saved checkpoints from all training stages

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "CHECKPOINT SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

$stages = @(
    @{Name="SFT (Stage 1)"; Path="saves/vgpt2_v3/sft"},
    @{Name="DPO (Stage 2)"; Path="saves/vgpt2_v3/dpo"},
    @{Name="KTO (Stage 3)"; Path="saves/vgpt2_v3/kto"}
)

$totalSize = 0

foreach ($stage in $stages) {
    Write-Host "`n[$($stage.Name)]" -ForegroundColor Yellow
    Write-Host "  Path: $($stage.Path)" -ForegroundColor Gray
    
    if (Test-Path $stage.Path) {
        # Check for final adapter
        $finalAdapter = Join-Path $stage.Path "adapter_model.safetensors"
        if (Test-Path $finalAdapter) {
            $size = [math]::Round((Get-Item $finalAdapter).Length/1MB, 1)
            Write-Host "  FINAL MODEL: adapter_model.safetensors (${size} MB)" -ForegroundColor Green
            $totalSize += $size
        }
        
        # List checkpoints
        $checkpoints = Get-ChildItem -Path $stage.Path -Directory -Filter "checkpoint-*" | Sort-Object { [int]($_.Name -replace 'checkpoint-', '') }
        
        if ($checkpoints) {
            Write-Host "  Checkpoints: $($checkpoints.Count)" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "  Step`t`tSize (MB)`tTime" -ForegroundColor Gray
            Write-Host "  ----`t`t---------`t----" -ForegroundColor Gray
            
            foreach ($cp in $checkpoints) {
                $cpSize = [math]::Round((Get-ChildItem -Path $cp.FullName -Recurse | Measure-Object -Property Length -Sum).Sum/1MB, 0)
                $step = $cp.Name -replace 'checkpoint-', ''
                Write-Host "  $step`t`t$cpSize`t`t$($cp.LastWriteTime.ToString('MM/dd HH:mm'))"
                $totalSize += $cpSize
            }
        } else {
            Write-Host "  No checkpoints found" -ForegroundColor Gray
        }
    } else {
        Write-Host "  Not started yet" -ForegroundColor Gray
    }
}

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
$totalGB = [math]::Round($totalSize/1024, 2)
Write-Host "TOTAL CHECKPOINT SIZE: ${totalGB} GB" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan

# Disk space check
Write-Host "`n[DISK SPACE]" -ForegroundColor Yellow
Get-PSDrive C | Select-Object Name, @{N='Used(GB)';E={[math]::Round($_.Used/1GB,2)}}, @{N='Free(GB)';E={[math]::Round($_.Free/1GB,2)}} | Format-Table -AutoSize

