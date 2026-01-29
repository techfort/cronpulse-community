#!/bin/bash
set -e

echo "🚀 Starting CronPulse Community Edition..."

# Run database migrations
echo "📦 Running database migrations..."
alembic upgrade head

# Start the application
echo "✅ Migrations complete. Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
