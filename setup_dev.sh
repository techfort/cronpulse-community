#!/bin/bash

# Setup virtual environment for CronPulse Community Edition

set -e

VENV_DIR="venv"

echo "🔧 Setting up CronPulse Community Edition Development Environment"
echo "=================================================================="
echo ""

# Check if venv already exists
if [ -d "$VENV_DIR" ]; then
    echo "✓ Virtual environment already exists at $VENV_DIR"
else
    echo "Creating virtual environment..."
    python3 -m venv $VENV_DIR
    echo "✓ Virtual environment created"
fi

echo ""
echo "Activating virtual environment..."
source $VENV_DIR/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Installing development dependencies..."
pip install pytest pytest-cov httpx

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run tests:"
echo "  source venv/bin/activate && pytest tests/ -v"
echo ""
echo "Or use the test runner:"
echo "  ./run_tests.sh"
