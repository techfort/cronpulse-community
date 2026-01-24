# Script start
API_KEY="your-api-key"
MONITOR=$(curl -X POST https://cron-monitor.fly.dev/monitors \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Data Migration", "interval": 5, "webhook_url": "https://hooks.slack.com/services/.../migration", "expires_at": "2025-07-31T16:15:00Z"}')
MONITOR_ID=$(echo $MONITOR | jq -r '.id')

# During job execution
while job_running; do
  curl -X POST https://cron-monitor.fly.dev/ping/$MONITOR_ID -H "X-API-Key: $API_KEY"
  sleep 300  # Ping every 5 minutes
done

# Job complete
curl -X DELETE https://cron-monitor.fly.dev/monitors/$MONITOR_ID -H "X-API-Key: $API_KEY"