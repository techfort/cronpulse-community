# Database Migrations Guide

CronPulse Community Edition uses Alembic for database migrations.

## Quick Start

### Run Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Check current migration version
alembic current

# View migration history
alembic history --verbose
```

## Creating New Migrations

When you modify database models (files in `db/models/`), create a new migration:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration file in alembic/versions/
# Edit if needed, then apply it:
alembic upgrade head
```

## Migration Commands

```bash
# Upgrade to specific version
alembic upgrade <revision>

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision>

# Show SQL without running it
alembic upgrade head --sql
```

## Docker Usage

In Docker, migrations run automatically on startup (see `start.sh`):

```bash
# Manual migration in running container
docker exec cronpulse-1 alembic upgrade head
```

## Initial Setup

The initial migration (`1289f3062858_initial_migration.py`) creates all tables:
- `users` - User accounts
- `monitors` - Monitor configurations
- `api_keys` - API key management
- `settings` - Application settings

## Environment Variables

Alembic uses the `DATABASE_URL` environment variable:

```bash
# SQLite (default)
DATABASE_URL=sqlite:///data/monitors.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

## Best Practices

1. **Always review auto-generated migrations** before applying
2. **Test migrations** on a copy of production data
3. **Backup database** before running migrations in production
4. **Never edit applied migrations** - create a new one instead
5. **Use descriptive migration messages** for better history

## Troubleshooting

### "Table already exists" error

If you have an existing database without migrations:

```bash
# Mark current state as migrated without running migrations
alembic stamp head
```

### Reset database (development only)

```bash
# Delete database file
rm data/monitors.db

# Run migrations to recreate
alembic upgrade head
```

### Check migration status

```bash
# See which migrations have been applied
alembic current

# See pending migrations
alembic history
```

## Migration File Structure

Migrations are stored in `alembic/versions/`. Each file contains:

- `upgrade()` - Steps to apply the migration
- `downgrade()` - Steps to reverse the migration (rollback)

## Production Deployment

1. Backup database before deploying
2. Run migrations: `alembic upgrade head`
3. Verify application starts successfully
4. If issues occur, rollback: `alembic downgrade -1`

## Further Reading

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
