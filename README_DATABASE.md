---
noteId: "6666f35072b711f095e8a9866d35445a"
tags: []

---

# TFT Match Analysis Database Setup

This document provides instructions for setting up and managing the database for the TFT Match Analysis application.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements_db.txt
```

### 2. Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your database settings
```

### 3. Start Local Development Environment
```bash
# Start PostgreSQL and PgBouncer with Docker
docker-compose up -d

# Initialize the database
python setup_database.py init

# Test the setup
python setup_database.py test
```

## Environment Configuration

### Development (Local PostgreSQL)
```env
ENVIRONMENT=development
DB_HOST=localhost
DB_PORT=6432
DB_NAME=tft_matches
DB_USER=tft_user
DB_PASSWORD=tft_password
```

### Production (Heroku with Postgres)
```env
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@host:5432/database?sslmode=require
```

### Supabase
```env
SUPABASE_DB_HOST=db.your-project.supabase.co
SUPABASE_DB_PASSWORD=your-db-password
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

## Database Setup Commands

### Initialize Database
```bash
python setup_database.py init
```

### Run Migrations Only
```bash
python setup_database.py migrate
```

### Reset Database (Development Only)
```bash
python setup_database.py reset
```

### Test Database Connection
```bash
python setup_database.py test
```

### Check Database Status
```bash
python setup_database.py status
```

## Using the Database in Code

### Basic Usage
```python
from database import get_db_session

# Synchronous usage
with get_db_session() as session:
    result = session.execute("SELECT * FROM matches LIMIT 10")
    matches = result.fetchall()

# Using the database manager
from database import DatabaseManager

db = DatabaseManager()
with db.get_session() as session:
    # Your database operations
    pass
```

### Async Usage
```python
from database import get_async_db_session

async def get_matches():
    async with get_async_db_session() as session:
        result = await session.execute("SELECT * FROM matches LIMIT 10")
        return result.fetchall()
```

### Health Check
```python
from database import health_check

status = health_check()
print(f"Database status: {status['overall_status']}")
```

## Database Schema

The database includes the following main tables:

- **matches**: Core match data (partitioned by date)
- **participants**: Player participation data
- **participant_clusters**: Clustering analysis results
- **participant_units**: Normalized unit composition data
- **participant_traits**: Normalized trait composition data
- **match_statistics**: Pre-calculated match statistics
- **audit_log**: Change tracking

## Key Features

### 1. Connection Pooling
- PgBouncer for connection pooling in development
- SQLAlchemy connection pooling for production
- Configurable pool sizes and timeouts

### 2. Partitioning
- Matches table partitioned by month
- Automatic partition creation
- Improved query performance for time-based queries

### 3. Indexing
- Comprehensive indexing strategy
- GIN indexes for JSONB columns
- Partial indexes for specific use cases

### 4. Functions and Views
- Helper functions for data extraction
- Analytical views for common queries
- Materialized views for performance

### 5. Migration System
- SQL-based migrations
- Automatic migration tracking
- Safe migration rollback support

## Docker Development

### Start Services
```bash
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- PgBouncer connection pooler (port 6432)
- Redis for caching (port 6379)
- pgAdmin for database management (port 8080) - optional

### Access pgAdmin
- URL: http://localhost:8080
- Email: admin@tft.local
- Password: admin

## Production Deployment

### Heroku
1. Set the `DATABASE_URL` environment variable
2. Run migrations: `python setup_database.py migrate`
3. The application will automatically detect Heroku environment

### Supabase
1. Configure Supabase environment variables
2. Run migrations: `python setup_database.py migrate`
3. SSL is automatically enabled for Supabase connections

## Monitoring and Maintenance

### Connection Pool Monitoring
```python
from database import get_connection_info

info = get_connection_info()
print(f"Pool size: {info['pool_size']}")
print(f"Checked out: {info['checked_out']}")
```

### Index Usage Analysis
```sql
SELECT * FROM analyze_index_usage();
SELECT * FROM find_unused_indexes();
```

### Refresh Materialized Views
```sql
SELECT refresh_materialized_views();
```

## Troubleshooting

### Connection Issues
1. Check if PostgreSQL is running: `docker-compose ps`
2. Test connection: `python setup_database.py test`
3. Check logs: `docker-compose logs postgres`

### Performance Issues
1. Analyze slow queries in the application logs
2. Check index usage: `SELECT * FROM analyze_index_usage()`
3. Monitor connection pool: Use `get_connection_info()`

### Migration Issues
1. Check migration status: `python setup_database.py status`
2. Review migration logs in `database_setup.log`
3. For development, reset: `python setup_database.py reset`

## Security Considerations

1. Use strong passwords for database users
2. Enable SSL in production environments
3. Restrict database access to application servers only
4. Regularly update database and driver versions
5. Monitor for suspicious activity in audit logs

## Backup and Recovery

### Local Development
Data is stored in Docker volumes. To backup:
```bash
docker exec tft_postgres pg_dump -U tft_user tft_matches > backup.sql
```

### Production
- Heroku: Use Heroku Postgres backups
- Supabase: Use Supabase's backup features
- Custom: Implement automated backup scripts

## Performance Tuning

1. Adjust connection pool settings based on load
2. Monitor and optimize slow queries
3. Use appropriate indexes for your query patterns
4. Consider read replicas for heavy read workloads
5. Implement caching for frequently accessed data