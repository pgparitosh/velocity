#!/bin/bash
# Velocity Platform - Linux/POSIX Development Setup Script
# Configures a local Python virtual environment and installs all dependencies.

set -e

echo "--- Velocity Platform: Setting up Local Development Environment ---"

# 1. Check Python version
if python3 --version | grep -q "Python 3\.\(12\|13\)"; then
    echo "Found compatible Python version: $(python3 --version)"
else
    echo "Error: Required Python 3.12+ (Found: $(python3 --version)). Please install via apt/brew."
    exit 1
fi

# 2. Create Virtual Environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# 3. Install Dependencies
echo "Installing dependencies in editable mode..."
./.venv/bin/pip install -e ".[dev,prod]"

# 4. Success
echo -e "\nSetup Complete!"
echo "To activate the environment, run: source .venv/bin/activate"
