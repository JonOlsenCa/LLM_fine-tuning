# ============================================================
# STEP 0: Review System Resources
# ============================================================
# Run this FIRST to see what's consuming resources before training

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "SYSTEM RESOURCE REVIEW" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

Write-Host "`n[GPU STATUS]" -ForegroundColor Yellow
nvidia-smi

Write-Host "`n[TOP 20 MEMORY CONSUMERS]" -ForegroundColor Yellow
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 20 Name, @{N='Memory(MB)';E={[math]::Round($_.WorkingSet64/1MB,0)}}, CPU | Format-Table -AutoSize

Write-Host "`n[SYSTEM MEMORY]" -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
$totalRAM = [math]::Round($os.TotalVisibleMemorySize/1MB, 2)
$freeRAM = [math]::Round($os.FreePhysicalMemory/1MB, 2)
$usedRAM = $totalRAM - $freeRAM
Write-Host "Total RAM: ${totalRAM} GB"
Write-Host "Used RAM:  ${usedRAM} GB"
Write-Host "Free RAM:  ${freeRAM} GB"

Write-Host "`n[CPU INFO]" -ForegroundColor Yellow
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | Format-Table -AutoSize

Write-Host "`n[DISK SPACE - Training Output Drive]" -ForegroundColor Yellow
Get-PSDrive C | Select-Object Name, @{N='Used(GB)';E={[math]::Round($_.Used/1GB,2)}}, @{N='Free(GB)';E={[math]::Round($_.Free/1GB,2)}} | Format-Table -AutoSize

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "Review complete. Run 01_stop_resource_hogs.ps1 to free resources." -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan

