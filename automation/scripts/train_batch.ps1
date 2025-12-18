# LLaMA Factory - Batch Training Script
# Run multiple training jobs sequentially or in parallel
# Usage: .\train_batch.ps1 -ConfigDir "path/to/configs" [-Parallel] [-MaxJobs 2]

param(
    [Parameter(Mandatory=$true)]
    [string]$ConfigDir,
    
    [Parameter(Mandatory=$false)]
    [string]$Pattern = "*.yaml",
    
    [Parameter(Mandatory=$false)]
    [switch]$Parallel,
    
    [Parameter(Mandatory=$false)]
    [int]$MaxJobs = 1,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item $ScriptDir).Parent.Parent.FullName
$TrainScript = Join-Path $ScriptDir "train_single.ps1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LLaMA Factory Batch Training" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Find all config files
$ConfigFiles = Get-ChildItem -Path $ConfigDir -Filter $Pattern -File
$TotalJobs = $ConfigFiles.Count

if ($TotalJobs -eq 0) {
    Write-Host "No config files found matching pattern: $Pattern" -ForegroundColor Red
    exit 1
}

Write-Host "Found $TotalJobs configuration files" -ForegroundColor Yellow
Write-Host "Mode: $(if ($Parallel) { "Parallel (max $MaxJobs)" } else { "Sequential" })" -ForegroundColor Yellow
Write-Host ""

# Create results tracking
$Results = @()
$StartTime = Get-Date

if ($Parallel -and $MaxJobs -gt 1) {
    # Parallel execution using PowerShell jobs
    Write-Host "Starting parallel training jobs..." -ForegroundColor Green
    
    $Jobs = @()
    foreach ($ConfigFile in $ConfigFiles) {
        # Wait if we've hit max concurrent jobs
        while (($Jobs | Where-Object { $_.State -eq 'Running' }).Count -ge $MaxJobs) {
            Start-Sleep -Seconds 10
        }
        
        $JobName = $ConfigFile.BaseName
        Write-Host "  Starting job: $JobName" -ForegroundColor Cyan
        
        if (-not $DryRun) {
            $Job = Start-Job -Name $JobName -ScriptBlock {
                param($Script, $Config)
                & $Script -ConfigPath $Config
            } -ArgumentList $TrainScript, $ConfigFile.FullName
            $Jobs += $Job
        }
    }
    
    # Wait for all jobs to complete
    if (-not $DryRun) {
        Write-Host "Waiting for all jobs to complete..." -ForegroundColor Yellow
        $Jobs | Wait-Job | Out-Null
        
        foreach ($Job in $Jobs) {
            $Results += [PSCustomObject]@{
                Name = $Job.Name
                State = $Job.State
                Output = Receive-Job -Job $Job
            }
        }
        $Jobs | Remove-Job
    }
} else {
    # Sequential execution
    $CurrentJob = 0
    foreach ($ConfigFile in $ConfigFiles) {
        $CurrentJob++
        $JobName = $ConfigFile.BaseName
        
        Write-Host "[$CurrentJob/$TotalJobs] Training: $JobName" -ForegroundColor Cyan
        
        $JobStart = Get-Date
        $Success = $true
        
        if (-not $DryRun) {
            try {
                & $TrainScript -ConfigPath $ConfigFile.FullName
            } catch {
                $Success = $false
                Write-Host "  ERROR: $_" -ForegroundColor Red
            }
        }
        
        $JobDuration = (Get-Date) - $JobStart
        $Results += [PSCustomObject]@{
            Name = $JobName
            Success = $Success
            Duration = $JobDuration.ToString('hh\:mm\:ss')
        }
        
        Write-Host ""
    }
}

# Summary
$EndTime = Get-Date
$TotalDuration = $EndTime - $StartTime

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Batch Training Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total Jobs: $TotalJobs" -ForegroundColor White
Write-Host "Total Duration: $($TotalDuration.ToString('hh\:mm\:ss'))" -ForegroundColor White
Write-Host ""

if (-not $DryRun) {
    $Results | Format-Table -AutoSize
}

