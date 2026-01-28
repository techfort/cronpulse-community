#!/bin/bash

# CronPulse Database Backup Script
# Usage: ./backup.sh [backup_directory]

set -e

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/monitors_${TIMESTAMP}.db"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔄 CronPulse Database Backup${NC}"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if running in Docker
if [ -f "docker-compose.yml" ]; then
    echo -e "${BLUE}Backing up from Docker volume...${NC}"
    
    # Get container name
    CONTAINER=$(docker compose ps -q cronpulse 2>/dev/null)
    
    if [ -z "$CONTAINER" ]; then
        echo -e "${RED}❌ Container not running. Start it first with: docker compose up -d${NC}"
        exit 1
    fi
    
    # Copy database from container
    docker cp ${CONTAINER}:/app/data/monitors.db "$BACKUP_FILE"
    
else
    # Local backup
    if [ ! -f "data/monitors.db" ]; then
        echo -e "${RED}❌ Database not found at data/monitors.db${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Backing up local database...${NC}"
    cp data/monitors.db "$BACKUP_FILE"
fi

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✅ Backup created successfully!${NC}"
    echo -e "   File: $BACKUP_FILE"
    echo -e "   Size: $SIZE"
    echo ""
    
    # Show recent backups
    echo -e "${BLUE}Recent backups:${NC}"
    ls -lht "$BACKUP_DIR" | head -6
    echo ""
    
    # Cleanup old backups (keep last 30)
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/monitors_*.db 2>/dev/null | wc -l)
    if [ "$BACKUP_COUNT" -gt 30 ]; then
        echo -e "${BLUE}Cleaning up old backups (keeping last 30)...${NC}"
        ls -t "$BACKUP_DIR"/monitors_*.db | tail -n +31 | xargs rm -f
        echo -e "${GREEN}✅ Cleanup complete${NC}"
    fi
    
else
    echo -e "${RED}❌ Backup failed${NC}"
    exit 1
fi

echo -e "${GREEN}💾 Backup complete!${NC}"
echo ""
echo "To restore this backup:"
echo "  1. Stop the application: docker compose down"
echo "  2. Restore: docker cp $BACKUP_FILE cronpulse:/app/data/monitors.db"
echo "  3. Start: docker compose up -d"
