#!/bin/bash

# Run tests for CronPulse Community Edition

set -e

echo "🧪 Running CronPulse Community Edition Tests"
echo "============================================"
echo ""

# Check if venv exists, create if not
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Running setup..."
    ./setup_dev.sh
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if pytest is installed
if ! python -m pytest --version &>/dev/null; then
    echo "Installing test dependencies..."
    pip install pytest pytest-cov httpx
fi

# Run tests
echo ""
echo "Running unit tests..."
python -m pytest tests/ -v

echo ""
echo "✅ All tests passed!"
echo ""
echo "Summary:"
python -m pytest tests/ --tb=no -q
