# ============================================================
# STEP 1: Stop Resource Hogs
# ============================================================
# Stops common applications that consume memory/CPU during training

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "STOPPING RESOURCE HOGS" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

$processesToKill = @(
    "chrome",
    "msedge", 
    "firefox",
    "Teams",
    "slack",
    "Discord",
    "OneDrive",
    "Spotify",
    "Zoom",
    "WebexHost",
    "dropbox"
)

foreach ($proc in $processesToKill) {
    $running = Get-Process -Name $proc -ErrorAction SilentlyContinue
    if ($running) {
        Write-Host "Stopping $proc..." -ForegroundColor Yellow
        Stop-Process -Name $proc -Force -ErrorAction SilentlyContinue
        Write-Host "  Stopped $proc" -ForegroundColor Green
    } else {
        Write-Host "  $proc not running" -ForegroundColor Gray
    }
}

Write-Host "`n[POST-CLEANUP GPU STATUS]" -ForegroundColor Yellow
nvidia-smi

Write-Host "`n[POST-CLEANUP MEMORY]" -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
$freeRAM = [math]::Round($os.FreePhysicalMemory/1MB, 2)
Write-Host "Free RAM: ${freeRAM} GB" -ForegroundColor Green

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "Resource cleanup complete." -ForegroundColor Green
Write-Host "Run 02_start_monitor.ps1 to begin monitoring." -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan

