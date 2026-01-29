#!/bin/bash
# Script to run E2E tests with Testcontainers

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Installing/upgrading required packages..."
pip install -q -r requirements-test.txt

echo ""
echo "Running E2E tests..."
pytest tests/test_e2e_docker.py -v
