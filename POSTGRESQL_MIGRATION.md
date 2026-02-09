# PostgreSQL Migration Guide

## Overview

XTS Allocator Server supports both SQLite (development) and PostgreSQL (production). This guide covers migrating from SQLite to PostgreSQL.

## Prerequisites

1. **PostgreSQL 12+** installed and running
2. **psycopg2-binary** Python package (included in requirements.txt)
3. Database credentials with CREATE DATABASE permissions

## Quick Start

### 1. Install PostgreSQL Driver

```bash
source venv/bin/activate
pip install psycopg2-binary==2.9.9
```

### 2. Create PostgreSQL Database

```sql
CREATE DATABASE xts_allocator;
CREATE USER xts_allocator WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE xts_allocator TO xts_allocator;
```

### 3. Configure Environment Variables

Create `.env` file or export environment variables:

```bash
export DB_TYPE=postgresql
export POSTGRES_USER=xts_allocator
export POSTGRES_PASSWORD=your_secure_password
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=xts_allocator
export JWT_SECRET_KEY=your_random_secret_key_here
export CORS_ORIGINS=https://your-frontend-domain.com
export XTS_ENV=production
```

### 4. Run Database Migrations

```bash
# Initialize database schema
python database_setup.py

# Or use Alembic migrations
alembic upgrade head
```

### 5. Verify Configuration

```python
from config import config
config.print_config()
```

## Environment Variables Reference

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_TYPE` | `sqlite` | Database type: `sqlite` or `postgresql` |
| `SQLITE_DB_PATH` | `xts_allocator.db` | SQLite database file path |
| `POSTGRES_USER` | `xts_allocator` | PostgreSQL username |
| `POSTGRES_PASSWORD` | *(empty)* | PostgreSQL password |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `xts_allocator` | PostgreSQL database name |

### Application Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `XTS_ENV` | `development` | Environment: `development`, `production`, `testing` |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `5000` | Server port |
| `DEBUG` | `false` | Enable debug mode |
| `SQL_ECHO` | `true` | Log all SQL queries |

### Security Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | *(dev default)* | **MUST CHANGE IN PRODUCTION** |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Access token lifetime (8 hours) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime |
| `CORS_ENABLED` | `true` | Enable CORS |
| `CORS_ORIGINS` | `*` | Allowed origins (comma-separated) |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |

## Migration Scenarios

### Scenario 1: Fresh PostgreSQL Installation

```bash
# Set environment
export DB_TYPE=postgresql
export POSTGRES_PASSWORD=your_password

# Create database
createdb xts_allocator

# Initialize schema
python database_setup.py

# Start server
python app.py
```

### Scenario 2: Migrate Data from SQLite to PostgreSQL

```bash
# 1. Export SQLite data
sqlite3 xts_allocator.db .dump > sqlite_dump.sql

# 2. Create PostgreSQL database
createdb xts_allocator

# 3. Import data (requires manual conversion of SQLite SQL to PostgreSQL)
# Note: SQLite and PostgreSQL have different SQL dialects
# You may need to use a migration tool like pgloader

# 4. Alternative: Use Python script to copy data
python migrate_sqlite_to_postgres.py
```

### Scenario 3: Using Docker PostgreSQL

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: xts_allocator
      POSTGRES_USER: xts_allocator
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  xts_allocator:
    build: .
    environment:
      DB_TYPE: postgresql
      POSTGRES_HOST: postgres
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5000:5000"
    depends_on:
      - postgres

volumes:
  postgres_data:
```

```bash
# Start services
docker-compose up -d

# Run migrations
docker-compose exec xts_allocator python database_setup.py
```

## PostgreSQL-Specific Features

### Connection Pooling

PostgreSQL connections use connection pooling:

- **pool_size**: 10 connections
- **max_overflow**: 20 additional connections
- **pool_pre_ping**: Verify connections before use
- **pool_recycle**: Recycle connections after 1 hour

### Performance Tuning

```sql
-- Recommended PostgreSQL settings for production
ALTER DATABASE xts_allocator SET shared_buffers TO '256MB';
ALTER DATABASE xts_allocator SET effective_cache_size TO '1GB';
ALTER DATABASE xts_allocator SET maintenance_work_mem TO '128MB';
ALTER DATABASE xts_allocator SET checkpoint_completion_target TO '0.9';
ALTER DATABASE xts_allocator SET wal_buffers TO '16MB';
ALTER DATABASE xts_allocator SET default_statistics_target TO '100';
```

### Indexes

The schema includes indexes on:
- `devices.state` - Fast state-based queries
- `devices.owner_email` - Fast owner lookups
- `devices.rack_id` - Rack-based filtering
- Unique constraints on `(rack_id, slot_name)`

## Alembic Migrations

### Generate New Migration

```bash
# After modifying models.py
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1
```

### View Migration History

```bash
alembic history
alembic current
```

## Troubleshooting

### Connection Refused

```bash
# Check PostgreSQL is running
systemctl status postgresql

# Check connection
psql -U xts_allocator -d xts_allocator -h localhost

# Check logs
tail -f /var/log/postgresql/postgresql-*.log
```

### Authentication Failed

```bash
# Verify pg_hba.conf allows password authentication
sudo nano /etc/postgresql/15/main/pg_hba.conf

# Should contain:
# local   all             all                                     md5
# host    all             all             127.0.0.1/32            md5
```

### Schema Differences

SQLite and PostgreSQL have different type mappings:
- SQLite `INTEGER` → PostgreSQL `INTEGER`
- SQLite `TEXT` → PostgreSQL `TEXT` or `VARCHAR`
- SQLite `JSON` → PostgreSQL `JSONB` (better performance)

### Performance Issues

```sql
-- Analyze tables after bulk operations
ANALYZE devices;
ANALYZE allocation_history;

-- Vacuum regularly
VACUUM ANALYZE;

-- Check slow queries
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

## Production Checklist

- [ ] PostgreSQL 12+ installed
- [ ] Strong JWT_SECRET_KEY set
- [ ] POSTGRES_PASSWORD is secure
- [ ] CORS_ORIGINS restricted to your domain
- [ ] SQL_ECHO=false (disable SQL logging)
- [ ] DEBUG=false
- [ ] Database backups configured
- [ ] Connection pooling tuned for your load
- [ ] PostgreSQL performance settings applied
- [ ] Monitoring and logging configured
- [ ] SSL/TLS certificates installed
- [ ] Firewall rules configured

## Backup and Restore

### Backup

```bash
# Full database dump
pg_dump -U xts_allocator -d xts_allocator -F c -f xts_backup_$(date +%Y%m%d).dump

# SQL format
pg_dump -U xts_allocator -d xts_allocator > xts_backup_$(date +%Y%m%d).sql
```

### Restore

```bash
# From custom format dump
pg_restore -U xts_allocator -d xts_allocator xts_backup_20260207.dump

# From SQL file
psql -U xts_allocator -d xts_allocator < xts_backup_20260207.sql
```

### Automated Backups

```bash
# Add to crontab
0 2 * * * /usr/bin/pg_dump -U xts_allocator -d xts_allocator -F c -f /backups/xts_$(date +\%Y\%m\%d).dump
```

## Support

For issues or questions:
- Check logs: `tail -f logs/xts_allocator.log`
- Validate config: `python -c "from config import config; config.print_config()"`
- GitHub Issues: https://github.com/rdkcentral/xts_allocator_server/issues
