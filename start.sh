#!/bin/bash

# CronPulse Community Edition - Quick Start Script

set -e

echo "🔔 CronPulse Community Edition - Quick Start"
echo "============================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    
    # Generate JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    
    # Update .env with generated secret
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" .env
    else
        # Linux
        sed -i "s/JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" .env
    fi
    
    echo "✅ Generated JWT secret"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your BREVO_API_KEY for email alerts"
    echo ""
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "🐳 Building Docker image..."
docker build -t cronpulse-community . || {
    echo "❌ Docker build failed"
    exit 1
}

echo ""
echo "🚀 Starting CronPulse..."
docker-compose up -d || {
    echo "❌ Failed to start containers"
    exit 1
}

echo ""
echo "✅ CronPulse is starting up!"
echo ""
echo "📍 Access points:"
echo "   - Web UI: http://localhost:8000"
echo "   - API: http://localhost:8000/api"
echo "   - Docs: http://localhost:8000/documentation"
echo ""
echo "📊 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop service:"
echo "   docker-compose down"
echo ""
echo "💾 Database location:"
echo "   Docker volume: cronpulse-data"
echo "   Path: /app/data/monitors.db"
echo ""
echo "🔧 Next steps:"
echo "   1. Visit http://localhost:8000 to create an account"
echo "   2. Configure BREVO_API_KEY in .env for email alerts"
echo "   3. Create your first monitor!"
echo ""
