#!/bin/bash

# E2E test script for cron-monitor
# Assumes: Signed-up user with API key, app running at http://localhost:8000
# Dependencies: curl, jq
# Usage: bash e2e_test.sh <api_key> <webhook_url> [email_recipient]

# Exit on error
set -e

# Input validation
if [ $# -lt 2 ]; then
    echo "Usage: $0 <api_key> <webhook_url> [email_recipient]"
    echo "Example: $0 key-xxxx https://webhook.site/xxx test@example.com"
    exit 1
fi

API_KEY="$1"
WEBHOOK_URL="$2"
EMAIL_RECIPIENT="${3:-test@example.com}"
BASE_URL="http://localhost:8000"
TEST_NAME="e2e-test-$(date +%s)"
INTERVAL=5  # Monitor interval in minutes
TIMEOUT=360  # Timeout for alert check (seconds, slightly over 5 minutes)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "Starting E2E test for cron-monitor..."

# Step 1: Create a monitor
echo "Creating monitor: $TEST_NAME"
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/monitors" \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$TEST_NAME\",\"interval\":$INTERVAL,\"email_recipient\":\"$EMAIL_RECIPIENT\",\"webhook_url\":\"$WEBHOOK_URL\"}")

if ! echo "$CREATE_RESPONSE" | jq -e '.id' >/dev/null; then
    echo -e "${RED}Failed to create monitor: $CREATE_RESPONSE${NC}"
    exit 1
fi

MONITOR_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')
echo -e "${GREEN}Monitor created: ID=$MONITOR_ID${NC}"

# Step 2: Ping the monitor
echo "Pinging monitor: ID=$MONITOR_ID"
PING_RESPONSE=$(curl -s -X POST "$BASE_URL/ping/$MONITOR_ID" \
    -H "X-API-Key: $API_KEY")

if ! echo "$PING_RESPONSE" | jq -e '.message' >/dev/null; then
    echo -e "${RED}Failed to ping monitor: $PING_RESPONSE${NC}"
    exit 1
fi
echo -e "${GREEN}Ping successful${NC}"

# Step 3: Wait for missed ping alert (5-minute interval)
echo "Waiting for missed ping alert (up to $TIMEOUT seconds)..."
# Optional: Manually trigger check_missed_pings for faster testing
# Comment out if you want to wait for the scheduled 5-minute interval
MANUAL_CHECK_RESPONSE=$(curl -s -X POST "$BASE_URL/check_missed_pings" \
    -H "X-API-Key: $API_KEY" 2>/dev/null || echo "Manual trigger not supported")

# Sleep to ensure APScheduler detects missed ping
sleep $TIMEOUT

# Step 4: Verify alerts (manual check required for email/webhook)
echo "Please check the following for alerts:"
echo "- Email: $EMAIL_RECIPIENT (via Mailgun dashboard or inbox)"
echo "- Webhook: $WEBHOOK_URL (check webhook service logs)"
echo "Expected alert: 'Monitor $TEST_NAME has missed a ping!'"

# Optional: Add automated webhook verification if using webhook.site
if [[ "$WEBHOOK_URL" == https://webhook.site/* ]]; then
    WEBHOOK_TOKEN=$(echo "$WEBHOOK_URL" | cut -d'/' -f4)
    WEBHOOK_CHECK=$(curl -s "https://webhook.site/token/$WEBHOOK_TOKEN/requests" | jq -r '.data[] | select(.content | contains("missed a ping"))')
    if [ -n "$WEBHOOK_CHECK" ]; then
        echo -e "${GREEN}Webhook alert received${NC}"
    else
        echo -e "${RED}Webhook alert not found${NC}"
    fi
fi

# Step 5: Delete the monitor
echo "Deleting monitor: ID=$MONITOR_ID"
DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/monitors/$MONITOR_ID" \
    -H "X-API-Key: $API_KEY" -w "%{http_code}")

if [ "$DELETE_RESPONSE" != "204" ]; then
    echo -e "${RED}Failed to delete monitor: HTTP $DELETE_RESPONSE${NC}"
    exit 1
fi
echo -e "${GREEN}Monitor deleted${NC}"

# Step 6: Verify monitor is removed
echo "Listing monitors to confirm deletion"
LIST_RESPONSE=$(curl -s -X GET "$BASE_URL/monitors" \
    -H "X-API-Key: $API_KEY")

if echo "$LIST_RESPONSE" | jq -e ".[] | select(.id == $MONITOR_ID)" >/dev/null; then
    echo -e "${RED}Monitor ID=$MONITOR_ID still exists${NC}"
    exit 1
fi
echo -e "${GREEN}Monitor successfully removed${NC}"

echo -e "${GREEN}E2E test passed!${NC}"

# Cleanup
echo "Test complete. Check Mailgun dashboard and webhook logs for alerts."