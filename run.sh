#!/bin/bash

# Load environment variables from .env
source .env


# Check for -d flag to run in Docker
if [ "$1" = "-d" ]; then
    # Build and run in Docker
    docker build -t cron-monitor .
    docker run -p 8000:8000 \
      -e MAILGUN_API_KEY="$MAILGUN_API_KEY" \
      -e MAILGUN_DOMAIN="$MAILGUN_DOMAIN" \
      -e SECRET_KEY="$SECRET_KEY" \
      cron-monitor
else
    # Run locally with uvicorn and --reload
    source .venv/bin/activate
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload --app-dir .
fi