---
noteId: "0603368072e011f095e8a9866d35445a"
tags: []

---

# TFT Webapp - Complete Troubleshooting Guide

This comprehensive guide covers common issues and solutions for deploying and running the TFT webapp on Heroku with Supabase.

## Table of Contents

1. [Pre-Deployment Issues](#pre-deployment-issues)
2. [Deployment Issues](#deployment-issues)
3. [Database Connection Issues](#database-connection-issues)
4. [Application Runtime Issues](#application-runtime-issues)
5. [Performance Issues](#performance-issues)
6. [Monitoring and Debugging](#monitoring-and-debugging)
7. [Common Error Messages](#common-error-messages)
8. [Recovery Procedures](#recovery-procedures)

## Pre-Deployment Issues

### Missing Dependencies

**Problem**: Build fails with missing package errors
```
ERROR: Could not find a version that satisfies the requirement package-name
```

**Solutions**:
```bash
# Update requirements.txt with correct versions
pip freeze > requirements_exact.txt

# Check for conflicting dependencies
pip-compile --verbose requirements.txt

# Use exact versions from deployment/production_requirements.txt
cp deployment/production_requirements.txt requirements.txt
```

### Python Version Issues

**Problem**: Heroku uses wrong Python version
```
remote: -----> Python app detected
remote: -----> Using Python version specified in runtime.txt
remote: !     Requested runtime (python-3.9.0) is not available for this stack (heroku-22).
```

**Solutions**:
```bash
# Update runtime.txt to supported version
echo "python-3.11.8" > runtime.txt

# Check supported versions
heroku stack --app your-app-name

# List available Python runtimes
curl -s https://api.heroku.com/buildpacks/heroku/python | jq -r '.supported_python_versions[]'
```

### Git Repository Issues

**Problem**: Heroku can't access repository
```
fatal: 'heroku' does not appear to be a git repository
```

**Solutions**:
```bash
# Add Heroku remote
heroku git:remote -a your-app-name

# Verify remotes
git remote -v

# Reset if needed
git remote rm heroku
heroku git:remote -a your-app-name
```

## Deployment Issues

### Build Timeout

**Problem**: Build takes too long and times out
```
Build timed out (exceeded 15 minutes)
```

**Solutions**:
```bash
# Use cached builds
heroku config:set DISABLE_COLLECTSTATIC=1 --app your-app-name

# Optimize requirements.txt (remove dev dependencies)
# Use wheels for faster installation
heroku config:set PIP_USE_WHEEL=true --app your-app-name

# Split large dependencies across multiple deployments
```

### Procfile Issues

**Problem**: Web process doesn't start correctly
```
Process exited with status 127
```

**Solutions**:
```bash
# Check Procfile syntax (no tabs, correct spacing)
web: streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true

# Test locally
foreman start web

# Verify process types
heroku ps --app your-app-name
```

### Release Phase Failures

**Problem**: Migration fails during release phase
```
release: python deployment/migrate_to_production.py
remote: Released v3
remote: https://your-app.herokuapp.com/ deployed to Heroku
remote: 
remote: ERROR: Release command failed
```

**Solutions**:
```bash
# Check release logs
heroku releases --app your-app-name
heroku releases:output v3 --app your-app-name

# Test migration locally
python deployment/migrate_to_production.py --dry-run

# Skip release phase if needed
# Comment out release line in Procfile temporarily
```

## Database Connection Issues

### Connection Refused

**Problem**: Can't connect to Supabase database
```
psycopg2.OperationalError: connection to server at "db.xxxxx.supabase.co" (xxx.xxx.xxx.xxx), port 5432 failed
```

**Solutions**:
```bash
# Check environment variables
heroku config --app your-app-name | grep -E "(SUPABASE|DB_)"

# Test connection manually
psql "postgresql://postgres:password@db.your-project.supabase.co:5432/postgres?sslmode=require"

# Verify Supabase project status
# Go to https://app.supabase.com/projects

# Check SSL mode
heroku config:set DB_SSL_MODE=require --app your-app-name

# Use pooler connection
heroku config:set SUPABASE_DB_PORT=6543 --app your-app-name
```

### SSL Certificate Issues

**Problem**: SSL verification fails
```
sslmode value "require" invalid when SSL support is not compiled in
```

**Solutions**:
```bash
# Use binary package instead
pip uninstall psycopg2
pip install psycopg2-binary

# Set SSL mode in connection string
export DATABASE_URL="postgresql://user:pass@host:5432/db?sslmode=require"

# Disable SSL for testing (NOT for production)
heroku config:set DB_SSL_MODE=disable --app your-app-name
```

### Connection Pool Exhausted

**Problem**: Too many database connections
```
remaining connection slots are reserved for non-replication superuser connections
```

**Solutions**:
```bash
# Reduce pool size
heroku config:set DB_POOL_SIZE=5 --app your-app-name
heroku config:set DB_MAX_OVERFLOW=10 --app your-app-name

# Use connection pooling (Supabase PgBouncer)
heroku config:set SUPABASE_DB_PORT=6543 --app your-app-name

# Enable connection recycling
heroku config:set DB_POOL_RECYCLE=3600 --app your-app-name

# Monitor connections
# In Supabase dashboard: Settings -> Database -> Connection pooling
```

## Application Runtime Issues

### Streamlit Import Errors

**Problem**: Application can't import required modules
```
ModuleNotFoundError: No module named 'querying'
ImportError: cannot import name 'TFTQuery' from 'querying'
```

**Solutions**:
```bash
# Verify file structure
heroku run ls -la --app your-app-name

# Check Python path
heroku run python -c "import sys; print(sys.path)" --app your-app-name

# Add project root to path in streamlit_app.py
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Verify imports locally
python -c "from querying import TFTQuery"
```

### Port Binding Issues

**Problem**: Streamlit can't bind to Heroku's assigned port
```
OSError: [Errno 98] Address already in use
```

**Solutions**:
```bash
# Ensure Procfile uses $PORT variable
web: streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0

# Check if port is being used
heroku run netstat -tulpn --app your-app-name

# Restart dynos
heroku ps:restart --app your-app-name
```

### Memory Issues

**Problem**: Application runs out of memory
```
Process exceeded memory quota (512 MB) with 1024 MB
```

**Solutions**:
```bash
# Upgrade dyno type
heroku ps:resize web=basic --app your-app-name

# Optimize memory usage
# Use @st.cache_data for data loading
# Process data in chunks
# Clear unused variables

# Monitor memory usage
heroku run python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')" --app your-app-name

# Check logs for memory warnings
heroku logs --tail --app your-app-name | grep -i memory
```

### File Not Found Issues

**Problem**: Application can't find CSV or data files
```
FileNotFoundError: [Errno 2] No such file or directory: 'hierarchical_clusters.csv'
```

**Solutions**:
```bash
# Check if files are in git repository
git ls-files | grep -E "\.(csv|json)$"

# Verify files in deployed app
heroku run ls -la *.csv --app your-app-name

# Use absolute paths
import os
from pathlib import Path

base_dir = Path(__file__).parent
csv_path = base_dir / "hierarchical_clusters.csv"

# Check .gitignore doesn't exclude data files
grep -E "\.(csv|json)" .gitignore
```

## Performance Issues

### Slow Database Queries

**Problem**: Queries take too long to execute
```
Query timeout exceeded (300000ms)
```

**Solutions**:
```bash
# Check query performance in Supabase dashboard
# Settings -> Database -> Query performance

# Add database indexes
# Run in Supabase SQL editor:
CREATE INDEX idx_participants_placement ON participants(placement);
CREATE INDEX idx_participants_cluster ON participants(main_cluster_id);

# Increase timeout
heroku config:set DB_STATEMENT_TIMEOUT=600000 --app your-app-name

# Optimize queries
# Use LIMIT clauses
# Add WHERE conditions to filter data
# Use connection pooling
```

### Slow Application Loading

**Problem**: Streamlit app takes too long to load
```
H12 Request timeout error
```

**Solutions**:
```bash
# Use caching for expensive operations
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data():
    return pd.read_csv('data.csv')

# Optimize data loading
# Load data in chunks
# Use lazy loading
# Precompute expensive calculations

# Check dyno performance
heroku logs --tail --app your-app-name | grep -E "(H12|timeout)"
```

### High Memory Usage

**Problem**: Application uses too much memory
```
dyno=web.1 sample#memory_total=512.00MB sample#memory_rss=510.23MB
```

**Solutions**:
```bash
# Profile memory usage
heroku run python -m memory_profiler streamlit_app.py --app your-app-name

# Optimize pandas operations
# Use categorical data types
# Process data in chunks
# Clear dataframes when not needed

# Monitor memory over time
heroku addons:create newrelic:wayne --app your-app-name
```

## Monitoring and Debugging

### Accessing Logs

```bash
# Real-time logs
heroku logs --tail --app your-app-name

# Application logs only
heroku logs --tail --source app --app your-app-name

# Error logs only
heroku logs --tail --app your-app-name | grep -i error

# Specific number of log lines
heroku logs --num 500 --app your-app-name

# Save logs to file
heroku logs --num 1000 --app your-app-name > heroku_logs.txt
```

### Health Monitoring

```bash
# Check app status
heroku ps --app your-app-name

# Check dyno performance
heroku ps:exec --dyno=web.1 --app your-app-name

# Monitor response times
curl -w "@curl-format.txt" -s -o /dev/null https://your-app.herokuapp.com/

# Set up uptime monitoring
# Use external services like UptimeRobot or Pingdom
```

### Database Monitoring

```bash
# Supabase dashboard monitoring
# Go to: https://app.supabase.com/project/your-project/reports

# Check connection stats
heroku run python -c "
from database.connection import get_database_manager
db = get_database_manager()
print(db.get_connection_info())
" --app your-app-name

# Monitor query performance
# In Supabase SQL editor:
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

## Common Error Messages

### "No web processes running"

```
Error R10 (Boot timeout) -> Web process failed to bind to $PORT within 60 seconds of launch
```

**Fix**:
```bash
# Check Procfile configuration
web: streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true

# Restart the app
heroku ps:restart --app your-app-name
```

### "Application Error"

```
An error occurred in the application and your page could not be served.
```

**Fix**:
```bash
# Check logs for specific error
heroku logs --tail --app your-app-name

# Common causes:
# - Missing environment variables
# - Database connection issues
# - Import errors
# - Port binding issues
```

### "Module Not Found"

```
ModuleNotFoundError: No module named 'module_name'
```

**Fix**:
```bash
# Add to requirements.txt
echo "module_name==x.x.x" >> requirements.txt

# Redeploy
git add requirements.txt
git commit -m "Add missing dependency"
git push heroku main
```

### "Connection Pool Exhausted"

```
QueuePool limit of size 20 overflow 30 reached, connection timed out
```

**Fix**:
```bash
# Reduce pool sizes
heroku config:set DB_POOL_SIZE=10 --app your-app-name
heroku config:set DB_MAX_OVERFLOW=15 --app your-app-name

# Enable connection recycling
heroku config:set DB_POOL_RECYCLE=1800 --app your-app-name
```

## Recovery Procedures

### Complete Application Reset

```bash
# Reset to last known good version
heroku releases --app your-app-name
heroku rollback v42 --app your-app-name  # Replace with good version

# Clear all config vars and reset
heroku config --app your-app-name  # List current config
heroku config:unset VAR_NAME --app your-app-name  # Remove problematic vars

# Restart application
heroku ps:restart --app your-app-name
```

### Database Recovery

```bash
# Restore from Supabase backup
# Go to: https://app.supabase.com/project/your-project/database/backups
# Select backup and restore

# Reset database migrations
heroku run python deployment/migrate_to_production.py --force --app your-app-name

# Test database connectivity
heroku run python -c "
from database.connection import test_connection
result = test_connection()
print('Connection:', 'OK' if result['success'] else 'FAILED')
" --app your-app-name
```

### Emergency Maintenance Mode

```bash
# Enable maintenance mode
heroku maintenance:on --app your-app-name

# Show maintenance page to users
# Fix issues...

# Disable maintenance mode
heroku maintenance:off --app your-app-name
```

### Complete Redeploy

```bash
# Create new Heroku app
heroku create new-app-name

# Set up all environment variables
heroku config:set $(cat .env.production | xargs) --app new-app-name

# Deploy to new app
git push heroku main

# Update DNS (if using custom domain)
heroku domains:add yourdomain.com --app new-app-name

# Delete old app after verification
heroku apps:destroy old-app-name --confirm old-app-name
```

## Getting Help

### Heroku Support

```bash
# Check Heroku status
curl -s https://status.heroku.com/api/v4/current-status.json | jq

# Open support ticket (paid plans)
heroku help

# Community support
# Stack Overflow: tag [heroku]
# Heroku Dev Center: https://devcenter.heroku.com/
```

### Supabase Support

```bash
# Check Supabase status
# https://status.supabase.com/

# Community support
# Discord: https://discord.supabase.com/
# GitHub Discussions: https://github.com/supabase/supabase/discussions
```

### Application-Specific Issues

```bash
# Enable debug mode (development only)
heroku config:set DEBUG=true --app your-app-name

# Run interactive shell
heroku run python --app your-app-name

# Execute specific debugging commands
heroku run python -c "
import sys
print('Python version:', sys.version)
print('Path:', sys.path)
try:
    from streamlit_app import main
    print('App import: OK')
except Exception as e:
    print('App import error:', e)
" --app your-app-name
```

---

## Quick Reference Commands

### Most Common Debugging Commands

```bash
# Check logs
heroku logs --tail --app your-app-name

# Check app status
heroku ps --app your-app-name

# Restart app
heroku ps:restart --app your-app-name

# Check config
heroku config --app your-app-name

# Test database connection
heroku run python -c "from database.connection import test_connection; print(test_connection())" --app your-app-name

# Check file structure
heroku run ls -la --app your-app-name

# Open app in browser
heroku open --app your-app-name
```

### Emergency Recovery

```bash
# If app is completely broken:
heroku maintenance:on --app your-app-name
heroku rollback --app your-app-name
heroku ps:restart --app your-app-name  
heroku maintenance:off --app your-app-name
```

This guide covers the most common issues encountered when deploying TFT webapp. For specific errors not covered here, check the logs and search for the exact error message in Heroku documentation or Stack Overflow.