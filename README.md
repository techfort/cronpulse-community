# CronPulse Community Edition 🔔

A lightweight, self-hosted cron job monitoring solution. Get instant alerts when your scheduled tasks fail to run.

## Features

- 🎯 **Simple Monitoring**: Create monitors for your cron jobs with customizable intervals
- 📧 **Multiple Alert Methods**: Email and webhook notifications when jobs miss their schedule
- 🔑 **API-First Design**: Full REST API with optional web UI
- 💾 **SQLite Database**: Zero-configuration embedded database
- 🐳 **Docker Ready**: Single-container deployment with persistent storage
- 🆓 **Open Source**: No subscriptions, no limits, fully self-hosted

## Quick Start with Docker

### Using Docker Compose (Recommended)

1. **Clone the repository:**
```bash
git clone <your-repo-url>
cd cronpulse-community
```

2. **Create environment file:**
```bash
cat > .env << EOF
JWT_SECRET=$(openssl rand -hex 32)
BREVO_API_KEY=your-brevo-api-key-here
EOF
```

3. **Start the service:**
```bash
docker-compose up -d
```

4. **Access the application:**
- Web UI: http://localhost:8000
- API: http://localhost:8000/api

### Using Docker directly

```bash
# Build the image
docker build -t cronpulse-community .

# Run the container
docker run -d \
  -p 8000:8000 \
  -v cronpulse-data:/app/data \
  -e JWT_SECRET=$(openssl rand -hex 32) \
  -e BREVO_API_KEY=your-api-key \
  --name cronpulse \
  cronpulse-community
```

## Local Development Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set environment variables:**
```bash
export JWT_SECRET=$(openssl rand -hex 32)
export BREVO_API_KEY=your-brevo-api-key-here
export DATABASE_URL=sqlite:///data/monitors.db
```

3. **Run the application:**
```bash
uvicorn main:app --reload
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database path | `sqlite:///data/monitors.db` |
| `JWT_SECRET` | Secret key for JWT tokens | Required |
| `BREVO_API_KEY` | API key for email alerts | Optional |

### Email Setup

CronPulse uses [Brevo](https://www.brevo.com/) (formerly Sendinblue) for sending email alerts:

1. Sign up for a free Brevo account
2. Get your API key from account settings
3. Set the `BREVO_API_KEY` environment variable

## Usage

### 1. Create an Account

Visit http://localhost:8000 and sign up with your email.

### 2. Create a Monitor

Via UI:
- Navigate to "Monitors" page
- Click "Create Monitor"
- Fill in job name, interval, and alert destinations

Via API:
```bash
curl -X POST http://localhost:8000/api/monitors \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Database Backup",
    "interval_minutes": 60,
    "alert_email": "you@example.com"
  }'
```

### 3. Ping Your Monitor

Add this to your cron job:
```bash
# Your actual job
0 * * * * /path/to/backup.sh && curl -X POST http://localhost:8000/api/monitors/{monitor_id}/ping
```

### 4. Get Alerts

If your job fails to ping within the expected interval, CronPulse will send an alert to your configured destinations.

## API Documentation

Full API documentation is available at http://localhost:8000/documentation after starting the application.

### Key Endpoints

- `POST /api/auth/signup` - Create new account
- `POST /api/auth/login` - Login
- `GET /api/monitors` - List monitors
- `POST /api/monitors` - Create monitor
- `POST /api/monitors/{id}/ping` - Record successful job execution
- `POST /api/api-keys` - Create API key

## Data Persistence

The SQLite database is stored in `/app/data/monitors.db` inside the container. Make sure to:

1. **Use a volume** to persist data between container restarts:
   ```bash
   docker volume create cronpulse-data
   ```

2. **Backup regularly**:
   ```bash
   docker cp cronpulse:/app/data/monitors.db ./backup.db
   ```

3. **Restore from backup**:
   ```bash
   docker cp ./backup.db cronpulse:/app/data/monitors.db
   docker restart cronpulse
   ```

## Architecture

```
cronpulse-community/
├── api/              # API endpoints and services
│   ├── auth.py       # Authentication endpoints
│   ├── monitors.py   # Monitor management
│   ├── api_keys.py   # API key management
│   └── services/     # Business logic
├── db/               # Database layer
│   ├── models/       # SQLAlchemy models
│   └── repositories/ # Data access layer
├── ui/               # Web interface
│   └── templates/    # HTML templates
├── main.py           # Application entry point
└── docker-compose.yml
```

## Troubleshooting

### Database locked errors

If you see "database is locked" errors, ensure:
- Only one instance is running
- No other processes are accessing the database file
- The volume has proper read/write permissions

### Alerts not sending

Check:
- `BREVO_API_KEY` is set correctly
- Email addresses are valid
- Check application logs: `docker logs cronpulse`

### Container won't start

```bash
# Check logs
docker logs cronpulse

# Verify environment variables
docker exec cronpulse env | grep -E 'JWT_SECRET|DATABASE_URL'

# Rebuild if needed
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Contributing

This is the community edition of CronPulse. Contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Your chosen license here]

## Support

- Report issues: [GitHub Issues]
- Documentation: See `/documentation` in the running application
- Example usage: See `example/` directory

---

Built with ❤️ using FastAPI, SQLAlchemy, and SQLite
