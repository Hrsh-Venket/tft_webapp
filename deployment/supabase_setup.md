---
noteId: "f6b5170072dc11f095e8a9866d35445a"
tags: []

---

# Complete Supabase Setup Guide for TFT Webapp

This guide covers the complete setup of Supabase as your PostgreSQL database for the TFT Match Analysis webapp, including connection pooling, security, and optimization for production use.

## Table of Contents

1. [Why Supabase?](#why-supabase)
2. [Account Setup](#account-setup)
3. [Project Creation](#project-creation)
4. [Database Configuration](#database-configuration)
5. [Security Setup](#security-setup)
6. [Connection Pooling](#connection-pooling)
7. [Environment Variables](#environment-variables)
8. [Schema Migration](#schema-migration)
9. [Performance Optimization](#performance-optimization)
10. [Monitoring and Maintenance](#monitoring-and-maintenance)
11. [Backup and Recovery](#backup-and-recovery)
12. [Cost Management](#cost-management)

## Why Supabase?

Supabase provides several advantages for this TFT webapp:

- **Free Tier**: 2 projects with 500MB database storage
- **Built-in Connection Pooling**: PgBouncer included
- **Real-time Capabilities**: For future live match tracking
- **Built-in Auth**: For user management (future feature)
- **REST API**: Auto-generated APIs for your database
- **Dashboard**: Easy database management interface
- **Automatic Backups**: Daily backups with point-in-time recovery
- **SSL by Default**: Secure connections out of the box

## Account Setup

### 1. Create Supabase Account
1. Go to [https://app.supabase.com/](https://app.supabase.com/)
2. Sign up with GitHub (recommended) or email
3. Verify your email address
4. Complete your profile setup

### 2. Understand Pricing
- **Free Tier**: Perfect for development and small applications
  - 2 projects
  - 500MB database storage
  - Up to 5GB egress per month
  - Community support
  
- **Pro Tier ($25/month)**: For production applications
  - Unlimited projects
  - 8GB database storage included
  - 250GB egress included
  - Email support
  - Daily backups

## Project Creation

### 1. Create New Project
1. Click "New Project" in the Supabase dashboard
2. Choose your organization (or create new one)
3. Fill in project details:
   - **Name**: `tft-match-analysis`
   - **Database Password**: Generate a strong password (save this!)
   - **Region**: Choose closest to your Heroku region (US East for us region)

### 2. Wait for Project Setup
- Project creation takes 2-3 minutes
- You'll see a progress indicator
- Don't navigate away during setup

### 3. Access Project Dashboard
Once ready, you'll have access to:
- Database schema editor
- API documentation
- Authentication settings
- Storage management
- Real-time logs

## Database Configuration

### 1. Get Connection Details
In your project dashboard, go to Settings → Database:

```
Host: db.your-project-ref.supabase.co
Database name: postgres
Port: 5432
User: postgres
Password: [your-generated-password]
```

### 2. Connection String
Supabase provides connection strings in multiple formats:

**PostgreSQL URL (for SQLAlchemy):**
```
postgresql://postgres:[YOUR-PASSWORD]@db.your-project-ref.supabase.co:5432/postgres
```

**Connection URI with SSL:**
```
postgresql://postgres:[YOUR-PASSWORD]@db.your-project-ref.supabase.co:5432/postgres?sslmode=require
```

### 3. API Keys
Go to Settings → API:
- **Public anon key**: For frontend operations
- **Secret service_role key**: For admin operations (keep secret!)

## Security Setup

### 1. Row Level Security (RLS)
For production applications, enable RLS:

```sql
-- Enable RLS on sensitive tables
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE participants ENABLE ROW LEVEL SECURITY;

-- Create policies (example - adjust based on your needs)
CREATE POLICY "Enable read access for all users" ON matches FOR SELECT USING (true);
CREATE POLICY "Enable insert for authenticated users" ON matches FOR INSERT WITH CHECK (auth.role() = 'authenticated');
```

### 2. Database Roles
Create specific roles for different access levels:

```sql
-- Create read-only role for application
CREATE ROLE tft_app_read;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tft_app_read;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO tft_app_read;

-- Create read-write role
CREATE ROLE tft_app_write;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO tft_app_write;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO tft_app_write;
```

### 3. Network Security
- SSL is enabled by default (good!)
- Consider IP allowlisting for extra security
- Use environment variables for credentials

## Connection Pooling

Supabase includes PgBouncer for connection pooling:

### 1. Pooler Configuration
Access pooler settings in Settings → Database:
- **Pool Mode**: Transaction (recommended for web apps)
- **Default Pool Size**: 15 (adjustable)
- **Max Client Connections**: 200

### 2. Connection Methods

**Direct Connection (Port 5432):**
- Direct to PostgreSQL
- Use for admin tasks and migrations
- Higher resource usage

**Pooled Connection (Port 6543):**
```
postgresql://postgres:[YOUR-PASSWORD]@db.your-project-ref.supabase.co:6543/postgres
```
- Through PgBouncer
- Use for application connections
- Better for concurrent users

### 3. Application Configuration
Configure your app to use pooled connections:

```python
# In your database config
SUPABASE_DB_HOST = "db.your-project-ref.supabase.co"
SUPABASE_DB_PORT = 6543  # Use pooler port
SUPABASE_DB_USE_POOLING = True
SUPABASE_DB_POOL_MODE = "transaction"
```

## Environment Variables

### 1. Required Variables for Your App
```env
# Supabase Project Settings
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Database Connection (use pooler)
SUPABASE_DB_HOST=db.your-project-ref.supabase.co
SUPABASE_DB_PORT=6543
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-database-password

# Connection Settings
DB_SSL_MODE=require
DB_USE_POOLING=true
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

### 2. Set in Heroku
```bash
# Set Supabase environment variables
heroku config:set SUPABASE_URL="https://your-project-ref.supabase.co" --app your-tft-app
heroku config:set SUPABASE_ANON_KEY="your-anon-key" --app your-tft-app
heroku config:set SUPABASE_DB_HOST="db.your-project-ref.supabase.co" --app your-tft-app
heroku config:set SUPABASE_DB_PORT="6543" --app your-tft-app
heroku config:set SUPABASE_DB_PASSWORD="your-database-password" --app your-tft-app
heroku config:set DB_SSL_MODE="require" --app your-tft-app
```

## Schema Migration

### 1. Using Supabase Dashboard
1. Go to Table Editor in your project
2. Click "New Table"
3. Use the SQL editor for complex operations

### 2. Run Your Existing Migrations
Execute your migration scripts in order:

```sql
-- In Supabase SQL Editor, run each migration file:
-- 1. 001_initial_schema.sql
-- 2. 002_indexes.sql  
-- 3. 003_functions_views.sql
-- 4. 004_insert_match_function.sql
-- 5. 005_clustering_enhancements.sql
```

### 3. Automated Migration Script
Use the migration script from your deployment:

```bash
# Local testing
python deployment/migrate_to_production.py --target=supabase --db-url="postgresql://postgres:password@db.your-project-ref.supabase.co:5432/postgres?sslmode=require"

# Or set environment variables and run
export DATABASE_URL="postgresql://postgres:password@db.your-project-ref.supabase.co:5432/postgres?sslmode=require"
python deployment/migrate_to_production.py
```

## Performance Optimization

### 1. Database Configuration
In Supabase Dashboard → Settings → Database, configure:

```sql
-- Optimize for your workload
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();
```

### 2. Index Strategy
Create indexes for your TFT queries:

```sql
-- Participant queries
CREATE INDEX idx_participants_match_id ON participants(match_id);
CREATE INDEX idx_participants_puuid ON participants(puuid);
CREATE INDEX idx_participants_placement ON participants(placement);

-- Trait queries
CREATE INDEX idx_participants_traits_gin ON participants USING GIN (traits);

-- Unit queries  
CREATE INDEX idx_participants_units_gin ON participants USING GIN (units);

-- Cluster queries
CREATE INDEX idx_participants_cluster ON participants(main_cluster_id, sub_cluster_id);

-- Composite indexes for common queries
CREATE INDEX idx_participants_composite ON participants(placement, level, main_cluster_id);
```

### 3. Query Optimization
Use EXPLAIN ANALYZE to optimize queries:

```sql
-- Check query performance
EXPLAIN ANALYZE SELECT * FROM participants WHERE placement <= 4;

-- Monitor slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

## Monitoring and Maintenance

### 1. Supabase Dashboard Monitoring
Monitor in your project dashboard:
- Database size and growth
- API requests and usage
- Active connections
- Query performance

### 2. Custom Monitoring
Set up monitoring queries:

```sql
-- Check database size
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check connection stats
SELECT 
    state,
    count(*) 
FROM pg_stat_activity 
GROUP BY state;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes;
```

### 3. Alerts and Notifications
Set up alerts for:
- Database storage usage (approaching limits)
- Connection pool exhaustion
- Query performance degradation
- Error rates

## Backup and Recovery

### 1. Automatic Backups
Supabase provides:
- **Daily backups** (retained for 7 days on free tier)
- **Point-in-time recovery** (Pro tier)
- **Backup downloads** for local storage

### 2. Manual Backups
Create manual backups before major changes:

```bash
# Using pg_dump (install PostgreSQL client tools)
pg_dump "postgresql://postgres:password@db.your-project-ref.supabase.co:5432/postgres?sslmode=require" > backup_$(date +%Y%m%d).sql

# Restore from backup
psql "postgresql://postgres:password@db.your-project-ref.supabase.co:5432/postgres?sslmode=require" < backup_20250806.sql
```

### 3. Application-Level Backups
Implement data export functionality:

```python
# Export critical data
python deployment/backup_data.py --output=data_backup_$(date +%Y%m%d).json
```

## Cost Management

### 1. Monitor Usage
Track usage in Supabase dashboard:
- Database storage
- Egress bandwidth
- API requests
- Compute time

### 2. Optimize Costs
- Use connection pooling to reduce connections
- Implement query caching
- Archive old data
- Optimize images and file storage

### 3. Upgrade Planning
Consider Pro tier when you need:
- More than 500MB storage
- More than 5GB monthly egress
- Multiple projects
- Priority support

## Migration from Local Development

### 1. Data Export from Local
```bash
# Export from local PostgreSQL
pg_dump "postgresql://tft_user:tft_password@localhost:6432/tft_matches" --data-only > local_data.sql

# Import to Supabase
psql "postgresql://postgres:password@db.your-project-ref.supabase.co:5432/postgres?sslmode=require" < local_data.sql
```

### 2. Configuration Update
Update your local development to use Supabase:

```env
# .env.development
DATABASE_URL=postgresql://postgres:password@db.your-project-ref.supabase.co:6543/postgres?sslmode=require
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

### 3. Test Migration
1. Run your application locally with Supabase
2. Test all functionality
3. Verify data integrity
4. Check performance

## Troubleshooting Common Issues

### 1. Connection Issues
```bash
# Test connection
psql "postgresql://postgres:password@db.your-project-ref.supabase.co:5432/postgres?sslmode=require" -c "SELECT version();"

# Check if pooler is working
psql "postgresql://postgres:password@db.your-project-ref.supabase.co:6543/postgres?sslmode=require" -c "SELECT version();"
```

### 2. SSL Certificate Issues
If you encounter SSL issues:
```python
# Disable SSL verification (NOT recommended for production)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```

### 3. Performance Issues
- Check connection pool settings
- Monitor slow queries
- Review index usage
- Consider upgrading to Pro tier

## Security Best Practices

### 1. Credential Management
- Never commit database passwords to git
- Use environment variables for all credentials
- Rotate passwords regularly
- Use read-only credentials where possible

### 2. Network Security
- Use SSL connections always
- Consider IP allowlisting
- Monitor connection attempts
- Set up proper firewall rules

### 3. Application Security
- Implement input validation
- Use parameterized queries
- Enable row-level security
- Regular security audits

## Integration Testing

### 1. Test Database Connection
```python
# Test script
import os
from database.connection import test_connection

# Set Supabase environment variables
os.environ['SUPABASE_DB_HOST'] = 'db.your-project-ref.supabase.co'
os.environ['SUPABASE_DB_PASSWORD'] = 'your-password'

# Test connection
result = test_connection()
print(f"Connection test: {'SUCCESS' if result['success'] else 'FAILED'}")
```

### 2. Performance Testing
```python
# Load testing
import time
from database.connection import get_db_session

def test_query_performance():
    start_time = time.time()
    with get_db_session() as session:
        result = session.execute("SELECT COUNT(*) FROM participants")
        count = result.fetchone()[0]
    
    end_time = time.time()
    print(f"Query returned {count} participants in {end_time - start_time:.2f} seconds")

test_query_performance()
```

## Next Steps

1. Complete project creation and configuration
2. Run database migrations
3. Test connection from your application
4. Set up monitoring and alerts
5. Configure backups and disaster recovery
6. Deploy to Heroku with Supabase configuration

## Resources

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PgBouncer Configuration](https://www.pgbouncer.org/config.html)
- [Heroku + Supabase Integration](https://supabase.com/partners/integrations/heroku)

---

**Important**: Keep your database password and API keys secure. Never share them publicly or commit them to version control.