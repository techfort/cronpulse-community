#!/bin/bash

# CronPulse Community Edition - Restart Script
# Usage: ./restart.sh [--wipe]

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
WIPE_DATA=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --wipe|-w)
            WIPE_DATA=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --wipe, -w    Wipe the SQLite database before starting"
            echo "  --help, -h    Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0              # Normal restart"
            echo "  $0 --wipe       # Restart with fresh database"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🔔 CronPulse Community Edition - Restart${NC}"
echo "=========================================="
echo ""

# Stop the container
echo -e "${YELLOW}Stopping container...${NC}"
docker compose down

# Wipe data if requested
if [ "$WIPE_DATA" = true ]; then
    echo ""
    echo -e "${RED}⚠️  WARNING: About to delete ALL data!${NC}"
    echo -e "${YELLOW}This will remove:${NC}"
    echo "  - All monitors"
    echo "  - All users"
    echo "  - All API keys"
    echo "  - All historical data"
    echo ""
    read -p "Are you sure you want to continue? Type 'yes' to confirm: " -r
    echo
    
    if [[ $REPLY == "yes" ]]; then
        echo -e "${YELLOW}Removing Docker volume...${NC}"
        docker volume rm cronpulse-community_cronpulse-data 2>/dev/null || echo "Volume not found or already removed"
        echo -e "${GREEN}✓ Database wiped${NC}"
    else
        echo -e "${YELLOW}Wipe cancelled. Starting with existing data...${NC}"
    fi
fi

# Start the container
echo ""
echo -e "${YELLOW}Starting container...${NC}"
docker compose up -d

# Wait for the container to be ready
echo ""
echo -e "${YELLOW}Waiting for container to be ready...${NC}"
sleep 3

# Check if container is running
if docker compose ps | grep -q "Up"; then
    echo ""
    echo -e "${GREEN}✅ CronPulse is running!${NC}"
    echo ""
    echo -e "${BLUE}Access your application at:${NC}"
    echo "  http://localhost:8000"
    echo ""
    
    if [ "$WIPE_DATA" = true ] && [[ $REPLY == "yes" ]]; then
        echo -e "${YELLOW}ℹ️  Fresh database created${NC}"
        echo "You'll need to create a new admin user or use the setup wizard"
    fi
    
    echo ""
    echo -e "${BLUE}View logs:${NC}"
    echo "  docker compose logs -f"
else
    echo ""
    echo -e "${RED}❌ Failed to start container${NC}"
    echo "Check logs with: docker compose logs"
    exit 1
fi
