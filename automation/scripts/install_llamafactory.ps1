# LLaMA Factory Installation Script for VGPT2 Training
# Run this in PowerShell as Administrator (recommended)
#
# Usage: .\automation\scripts\install_llamafactory.ps1

$ErrorActionPreference = "Stop"
$LFPath = "C:\Github\LLaMA-Factory"
$VenvPath = "$LFPath\venv"
$DataPath = "C:\Github\LLM_fine-tuning"

Write-Host "=============================================="
Write-Host "LLaMA Factory Installation for VGPT2"
Write-Host "=============================================="
Write-Host ""

# Step 1: Check if LLaMA Factory is cloned
if (-not (Test-Path $LFPath)) {
    Write-Host "[1/6] Cloning LLaMA Factory..."
    git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git $LFPath
} else {
    Write-Host "[1/6] LLaMA Factory already exists at $LFPath"
}

# Step 2: Create virtual environment with Python 3.12
Write-Host ""
if (-not (Test-Path $VenvPath)) {
    Write-Host "[2/6] Creating Python 3.12 virtual environment..."
    py -3.12 -m venv $VenvPath
} else {
    Write-Host "[2/6] Virtual environment already exists"
}

# Step 3: Activate and install PyTorch with CUDA
Write-Host ""
Write-Host "[3/6] Installing PyTorch with CUDA 12.6..."
Write-Host "      This may take several minutes..."
& "$VenvPath\Scripts\pip.exe" install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# Step 4: Install LLaMA Factory
Write-Host ""
Write-Host "[4/6] Installing LLaMA Factory..."
Set-Location $LFPath
& "$VenvPath\Scripts\pip.exe" install -e ".[torch,metrics]"

# Step 5: Copy VGPT2 data files
Write-Host ""
Write-Host "[5/6] Setting up VGPT2 training data..."
$DataDir = "$LFPath\data"

# Copy test data files
Copy-Item "$DataPath\data\vgpt2_train_test.json" $DataDir -Force
Copy-Item "$DataPath\data\vgpt2_eval_test.json" $DataDir -Force
Copy-Item "$DataPath\data\vgpt2_train_sharegpt.json" $DataDir -Force -ErrorAction SilentlyContinue
Copy-Item "$DataPath\data\vgpt2_eval_sharegpt.json" $DataDir -Force -ErrorAction SilentlyContinue

# Update dataset_info.json
$existingInfo = Get-Content "$DataDir\dataset_info.json" | ConvertFrom-Json -AsHashtable
$vgpt2Info = Get-Content "$DataPath\automation\configs\vgpt2_dataset_info.json" | ConvertFrom-Json -AsHashtable
foreach ($key in $vgpt2Info.Keys) {
    $existingInfo[$key] = $vgpt2Info[$key]
}
$existingInfo | ConvertTo-Json -Depth 10 | Set-Content "$DataDir\dataset_info.json"

Write-Host "      Copied training data files"
Write-Host "      Updated dataset_info.json"

# Step 6: Verify installation
Write-Host ""
Write-Host "[6/6] Verifying installation..."
& "$VenvPath\Scripts\python.exe" -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
& "$VenvPath\Scripts\llamafactory-cli.exe" version

Write-Host ""
Write-Host "=============================================="
Write-Host "Installation Complete!"
Write-Host "=============================================="
Write-Host ""
Write-Host "To run test training:"
Write-Host ""
Write-Host "  cd $LFPath"
Write-Host "  .\venv\Scripts\activate"
Write-Host "  llamafactory-cli train $DataPath\automation\configs\vgpt2_test_train.yaml"
Write-Host ""
Write-Host "Or run full training:"
Write-Host "  llamafactory-cli train $DataPath\automation\configs\vgpt2_lora_sft.yaml"
Write-Host ""

