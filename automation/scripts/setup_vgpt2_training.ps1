# VGPT2 Training Setup Script
# Sets up LLaMA Factory environment for VGPT2 fine-tuning
#
# Usage: .\automation\scripts\setup_vgpt2_training.ps1

param(
    [string]$LlamaFactoryPath = "C:\Github\LLaMA-Factory",
    [string]$DatasetPath = "data\vgpt2_training.json"
)

Write-Host "=============================================="
Write-Host "VGPT2 Training Environment Setup"
Write-Host "=============================================="

# Check if LLaMA Factory exists
if (-not (Test-Path $LlamaFactoryPath)) {
    Write-Host "LLaMA Factory not found. Cloning repository..."
    git clone https://github.com/hiyouga/LLaMA-Factory.git $LlamaFactoryPath
}

# Create data directory in LLaMA Factory if needed
$DataDir = Join-Path $LlamaFactoryPath "data"
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir | Out-Null
}

# Copy dataset info file
$DatasetInfoSrc = "automation\configs\vgpt2_dataset_info.json"
$DatasetInfoDst = Join-Path $DataDir "dataset_info.json"

Write-Host "`n📋 Setting up dataset configuration..."
if (Test-Path $DatasetInfoDst) {
    # Merge with existing dataset_info.json
    Write-Host "  Merging with existing dataset_info.json"
    $existing = Get-Content $DatasetInfoDst | ConvertFrom-Json -AsHashtable
    $vgpt2 = Get-Content $DatasetInfoSrc | ConvertFrom-Json -AsHashtable
    
    foreach ($key in $vgpt2.Keys) {
        $existing[$key] = $vgpt2[$key]
    }
    
    $existing | ConvertTo-Json -Depth 10 | Set-Content $DatasetInfoDst
} else {
    Copy-Item $DatasetInfoSrc $DatasetInfoDst
}
Write-Host "  ✓ Dataset info configured"

# Copy training data
Write-Host "`n📁 Copying training data..."
$TrainFile = "data\vgpt2_train_sharegpt.json"
$EvalFile = "data\vgpt2_eval_sharegpt.json"

if ((Test-Path $TrainFile) -and (Test-Path $EvalFile)) {
    Copy-Item $TrainFile (Join-Path $DataDir "vgpt2_train_sharegpt.json") -Force
    Copy-Item $EvalFile (Join-Path $DataDir "vgpt2_eval_sharegpt.json") -Force
    $TrainCount = (Get-Content $TrainFile | ConvertFrom-Json).Count
    $EvalCount = (Get-Content $EvalFile | ConvertFrom-Json).Count
    Write-Host "  ✓ Copied $TrainCount training records"
    Write-Host "  ✓ Copied $EvalCount eval records"
} else {
    Write-Host "  ⚠ Training data not found. Run these commands first:"
    Write-Host "     python scripts\generate_vgpt2_training_data.py --generate --format full --output data\vgpt2_training_full.json"
    Write-Host "     python scripts\prepare_training_data.py data\vgpt2_training_full.json --balance --format sharegpt"
}

# Verify setup
Write-Host "`n✅ Setup complete!"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Activate LLaMA Factory environment:"
Write-Host "     cd $LlamaFactoryPath"
Write-Host "     conda activate llamafactory"
Write-Host ""
Write-Host "  2. Start training:"
Write-Host "     llamafactory-cli train ..\LLM_fine-tuning\automation\configs\vgpt2_lora_sft.yaml"
Write-Host ""
Write-Host "  Or use QLoRA for limited VRAM:"
Write-Host "     llamafactory-cli train ..\LLM_fine-tuning\automation\configs\vgpt2_qlora_sft.yaml"

