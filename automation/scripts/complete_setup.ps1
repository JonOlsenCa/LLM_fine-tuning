# Complete VGPT2 Setup - Fix dataset_info.json
# Run after install_llamafactory.ps1

$LFPath = "C:\Github\LLaMA-Factory"
$DataPath = "C:\Github\LLM_fine-tuning"
$DataDir = "$LFPath\data"

Write-Host "Completing VGPT2 setup..."
Write-Host ""

# Check torch installation
Write-Host "[1/3] Verifying PyTorch installation..."
& "$LFPath\venv\Scripts\python.exe" -c "import torch; print(f'PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}')"

# Copy data files
Write-Host ""
Write-Host "[2/3] Copying VGPT2 data files..."
Copy-Item "$DataPath\data\vgpt2_train_test.json" $DataDir -Force
Copy-Item "$DataPath\data\vgpt2_eval_test.json" $DataDir -Force
Copy-Item "$DataPath\data\vgpt2_train_sharegpt.json" $DataDir -Force -ErrorAction SilentlyContinue
Copy-Item "$DataPath\data\vgpt2_eval_sharegpt.json" $DataDir -Force -ErrorAction SilentlyContinue
Write-Host "  Copied data files"

# Update dataset_info.json using Python (PowerShell JSON handling is problematic)
Write-Host ""
Write-Host "[3/3] Updating dataset_info.json..."
& "$LFPath\venv\Scripts\python.exe" -c @"
import json

# Load existing dataset_info
with open('$DataDir/dataset_info.json', 'r') as f:
    existing = json.load(f)

# Load VGPT2 dataset info
with open('$DataPath/automation/configs/vgpt2_dataset_info.json', 'r') as f:
    vgpt2 = json.load(f)

# Merge
existing.update(vgpt2)

# Save
with open('$DataDir/dataset_info.json', 'w') as f:
    json.dump(existing, f, indent=2)

print('  Updated dataset_info.json with VGPT2 datasets')
"@

# Test llamafactory-cli
Write-Host ""
Write-Host "[4/4] Testing LLaMA Factory CLI..."
& "$LFPath\venv\Scripts\llamafactory-cli.exe" version

Write-Host ""
Write-Host "=============================================="
Write-Host "Setup Complete!"
Write-Host "=============================================="
Write-Host ""
Write-Host "To run test training, execute:"
Write-Host ""
Write-Host "  cd $LFPath"
Write-Host "  .\venv\Scripts\activate"
Write-Host "  llamafactory-cli train $DataPath\automation\configs\vgpt2_test_train.yaml"
Write-Host ""

