# LLaMA Factory - Launch Web UI Script
# Starts the LLaMA Board web interface
# Usage: .\launch_webui.ps1 [-Port 7860] [-Host "127.0.0.1"]

param(
    [Parameter(Mandatory=$false)]
    [int]$Port = 7860,
    
    [Parameter(Mandatory=$false)]
    [string]$Host = "127.0.0.1",
    
    [Parameter(Mandatory=$false)]
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item $ScriptDir).Parent.Parent.FullName

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LLaMA Factory Web UI Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Host: $Host" -ForegroundColor Yellow
Write-Host "Port: $Port" -ForegroundColor Yellow
Write-Host "URL: http://${Host}:${Port}" -ForegroundColor Green
Write-Host ""

Push-Location $ProjectRoot

try {
    # Activate venv
    $VenvPath = Join-Path $ProjectRoot "venv\Scripts\activate.ps1"
    if (Test-Path $VenvPath) {
        Write-Host "Activating virtual environment..." -ForegroundColor Green
        & $VenvPath
    }
    
    # Set environment variables for Windows
    $env:GRADIO_SERVER_NAME = $Host
    $env:GRADIO_SERVER_PORT = $Port
    
    Write-Host "Starting LLaMA Board..." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
    Write-Host ""
    
    # Open browser if requested
    if ($OpenBrowser) {
        Start-Sleep -Seconds 3
        Start-Process "http://${Host}:${Port}"
    }
    
    # Launch the web UI
    python -m llamafactory.cli webui
    
} finally {
    Pop-Location
}

