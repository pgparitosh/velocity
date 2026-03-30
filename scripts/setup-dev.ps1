# Velocity Platform - Windows Development Setup Script
# Configures a local Python virtual environment and installs all dependencies.

Write-Host "--- Velocity Platform: Setting up Local Development Environment ---" -ForegroundColor Cyan

# 1. Check Python version
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.(12|13)") {
    Write-Host "Found compatible Python version: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "Required Python 3.12+ (Found: $pythonVersion). Please install from python.org" -ForegroundColor Red
    exit 1
}

# 2. Create Virtual Environment
if (!(Test-Path .venv)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

# 3. Install Dependencies
Write-Host "Installing dependencies in editable mode..." -ForegroundColor Cyan
& .\.venv\Scripts\pip install -e ".[dev,prod]"

# 4. Success
Write-Host "`nSetup Complete!" -ForegroundColor Green
Write-Host "To activate the environment, run: .\.venv\Scripts\activate"
Write-Host "To run tests, run: pytest"
