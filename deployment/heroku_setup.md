---
noteId: "c5bf854072dc11f095e8a9866d35445a"
tags: []

---

# Complete Heroku Deployment Guide for TFT Webapp

This guide provides step-by-step instructions for deploying your TFT Match Analysis webapp to Heroku with Supabase database integration.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Heroku Setup](#initial-heroku-setup)
3. [Application Configuration](#application-configuration)
4. [Database Setup](#database-setup)
5. [Environment Variables](#environment-variables)
6. [Deployment Process](#deployment-process)
7. [Post-Deployment Setup](#post-deployment-setup)
8. [Scaling and Performance](#scaling-and-performance)
9. [Monitoring and Logging](#monitoring-and-logging)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

### 1. Account Setup
- [Heroku account](https://signup.heroku.com/) (free tier available)
- [Supabase account](https://app.supabase.com/) (free tier includes 2 projects)
- [GitHub account](https://github.com/) for code repository

### 2. Local Development Tools
```bash
# Install Heroku CLI
# Windows (using Chocolatey)
choco install heroku-cli

# macOS (using Homebrew)
brew install heroku/brew/heroku

# Ubuntu/Debian
curl https://cli-assets.heroku.com/install.sh | sh

# Verify installation
heroku --version
```

### 3. Git Repository Setup
```bash
# Initialize git repository (if not already done)
git init
git add .
git commit -m "Initial commit for TFT webapp"

# Create GitHub repository and push
git remote add origin https://github.com/yourusername/tft_webapp.git
git branch -M main
git push -u origin main
```

## Initial Heroku Setup

### 1. Login to Heroku
```bash
heroku login
```

### 2. Create Heroku Application
```bash
# Create new app (replace 'your-tft-app' with your desired name)
heroku create your-tft-app --region us

# Or create with specific settings
heroku create your-tft-app \
  --region us \
  --stack heroku-22 \
  --buildpack heroku/python
```

### 3. Verify App Creation
```bash
# Check app info
heroku info --app your-tft-app

# List all apps
heroku apps
```

## Application Configuration

### 1. Configure Python Runtime
Ensure your `runtime.txt` is properly set:
```
python-3.11.8
```

### 2. Update Requirements File
Use the production-optimized requirements:
```bash
# Copy production requirements
cp deployment/production_requirements.txt requirements.txt

# Or if you want to keep both files
# Heroku will use requirements.txt by default
```

### 3. Configure Procfile
Your `Procfile` should contain:
```
web: streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false
release: python deployment/migrate_to_production.py
```

## Database Setup

### Option A: Heroku Postgres (Simpler)
```bash
# Add Heroku Postgres addon
heroku addons:create heroku-postgresql:essential-0 --app your-tft-app

# Get database URL
heroku config:get DATABASE_URL --app your-tft-app
```

### Option B: Supabase (Recommended for this app)
1. Follow the [Supabase Setup Guide](supabase_setup.md)
2. Get your Supabase connection details
3. Configure environment variables (see below)

## Environment Variables

### 1. Core Application Settings
```bash
# Set environment type
heroku config:set ENVIRONMENT=production --app your-tft-app
heroku config:set DEBUG=false --app your-tft-app

# Streamlit configuration
heroku config:set STREAMLIT_THEME_BASE=dark --app your-tft-app
heroku config:set STREAMLIT_THEME_PRIMARY_COLOR="#FF6B6B" --app your-tft-app
```

### 2. Database Configuration (Supabase)
```bash
# Replace with your actual Supabase details
heroku config:set SUPABASE_URL="https://your-project.supabase.co" --app your-tft-app
heroku config:set SUPABASE_ANON_KEY="your-anon-key" --app your-tft-app
heroku config:set SUPABASE_DB_HOST="db.your-project.supabase.co" --app your-tft-app
heroku config:set SUPABASE_DB_PASSWORD="your-db-password" --app your-tft-app
heroku config:set SUPABASE_DB_USER="postgres" --app your-tft-app
heroku config:set SUPABASE_DB_NAME="postgres" --app your-tft-app
heroku config:set SUPABASE_DB_PORT="5432" --app your-tft-app
```

### 3. Database Performance Settings
```bash
# Connection pooling settings
heroku config:set DB_POOL_SIZE=10 --app your-tft-app
heroku config:set DB_MAX_OVERFLOW=20 --app your-tft-app
heroku config:set DB_POOL_TIMEOUT=30 --app your-tft-app
heroku config:set DB_STATEMENT_TIMEOUT=300000 --app your-tft-app

# SSL settings
heroku config:set DB_SSL_MODE=require --app your-tft-app
```

### 4. Optional External Services
```bash
# TFT API key (for data collection)
heroku config:set TFT_API_KEY="your-riot-api-key" --app your-tft-app

# Error tracking (optional)
heroku config:set SENTRY_DSN="your-sentry-dsn" --app your-tft-app
```

### 5. Bulk Configuration from File
Create a `.env.production` file:
```env
ENVIRONMENT=production
DEBUG=false
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_DB_HOST=db.your-project.supabase.co
SUPABASE_DB_PASSWORD=your-db-password
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_SSL_MODE=require
```

Then set all variables at once:
```bash
# Set config from file
heroku config:set $(cat .env.production | xargs) --app your-tft-app
```

## Deployment Process

### 1. Connect GitHub Repository (Recommended)
```bash
# Connect app to GitHub repo
heroku git:remote -a your-tft-app

# Or set up automatic deploys from GitHub UI
# Go to: https://dashboard.heroku.com/apps/your-tft-app/deploy/github
```

### 2. Deploy via Git
```bash
# Add Heroku remote (if not using GitHub integration)
heroku git:remote -a your-tft-app

# Deploy to Heroku
git push heroku main

# Or deploy specific branch
git push heroku feature-branch:main
```

### 3. Deploy via GitHub Integration
1. Go to Heroku Dashboard → Your App → Deploy
2. Connect to GitHub repository
3. Enable automatic deploys (optional)
4. Click "Deploy Branch"

### 4. Monitor Deployment
```bash
# View deployment logs
heroku logs --tail --app your-tft-app

# Check app status
heroku ps --app your-tft-app
```

## Post-Deployment Setup

### 1. Run Database Migrations
```bash
# Trigger release phase (runs automatically on deploy)
heroku releases --app your-tft-app

# Or run manually
heroku run python deployment/migrate_to_production.py --initial-setup --app your-tft-app
```

### 2. Verify Application Health
```bash
# Open app in browser
heroku open --app your-tft-app

# Check health endpoint
curl https://your-tft-app.herokuapp.com/health

# View app info
heroku info --app your-tft-app
```

### 3. Set Up Data Import (if needed)
```bash
# Run one-time data import
heroku run python deployment/migrate_to_production.py --import-data --app your-tft-app
```

## Scaling and Performance

### 1. Dyno Management
```bash
# Scale web dynos
heroku ps:scale web=1 --app your-tft-app

# For higher traffic
heroku ps:scale web=2 --app your-tft-app

# Check current scaling
heroku ps --app your-tft-app
```

### 2. Dyno Types and Pricing
```bash
# Upgrade to faster dyno (better for CPU-intensive tasks)
heroku ps:resize web=basic --app your-tft-app

# Professional dynos (no sleep, better performance)
heroku ps:resize web=standard-1x --app your-tft-app

# For high-performance needs
heroku ps:resize web=standard-2x --app your-tft-app
```

### 3. Add-ons for Performance
```bash
# Redis for caching
heroku addons:create heroku-redis:mini --app your-tft-app

# Advanced monitoring
heroku addons:create newrelic:wayne --app your-tft-app

# Error tracking
heroku addons:create sentry:f1 --app your-tft-app
```

## Monitoring and Logging

### 1. View Logs
```bash
# Real-time logs
heroku logs --tail --app your-tft-app

# Logs with source
heroku logs --tail --source app --app your-tft-app

# Historical logs
heroku logs --num 500 --app your-tft-app
```

### 2. Application Metrics
```bash
# View metrics in dashboard
heroku open --app your-tft-app --path=/metrics

# Or access via CLI
heroku ps:exec --app your-tft-app
```

### 3. Health Monitoring
```bash
# Check app health
heroku run python deployment/health_check.py --app your-tft-app

# Set up uptime monitoring (external service recommended)
# Use services like UptimeRobot, Pingdom, or StatusCake
```

### 4. Database Monitoring
```bash
# Database metrics (if using Heroku Postgres)
heroku pg:info --app your-tft-app

# For Supabase, use their dashboard
# https://app.supabase.com/project/your-project/reports
```

## Custom Domain Setup (Optional)

### 1. Add Custom Domain
```bash
# Add domain
heroku domains:add www.yourdomain.com --app your-tft-app

# Get DNS target
heroku domains --app your-tft-app
```

### 2. SSL Certificate
```bash
# Add SSL certificate (automatic with custom domains)
heroku certs:auto:enable --app your-tft-app

# Check SSL status
heroku certs --app your-tft-app
```

## Backup and Recovery

### 1. Database Backups (Supabase)
- Supabase automatically handles backups
- Access via: Settings → Database → Backups

### 2. Application Backup
```bash
# Download app code
heroku git:clone -a your-tft-app

# Export config
heroku config --app your-tft-app > config-backup.txt
```

### 3. Scheduled Backups
Consider setting up automated backups:
- Database: Use Supabase backup policies
- Files: Use GitHub for code versioning

## CI/CD Pipeline (Recommended)

### 1. GitHub Actions Setup
Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Heroku

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: akhileshns/heroku-deploy@v3.12.12
      with:
        heroku_api_key: ${{secrets.HEROKU_API_KEY}}
        heroku_app_name: "your-tft-app"
        heroku_email: "your-email@example.com"
```

### 2. Review Apps (for testing)
Enable review apps in Heroku Dashboard:
- Go to Deploy tab
- Enable review apps
- Configure `app.json` settings

## Security Best Practices

### 1. Environment Variables
- Never commit sensitive data to git
- Use Heroku config vars for all secrets
- Rotate API keys regularly

### 2. Database Security
- Use SSL connections (already configured)
- Implement connection pooling
- Regular security updates

### 3. Application Security
- Keep dependencies updated
- Use security scanning tools
- Implement proper error handling

## Cost Optimization

### 1. Dyno Management
- Use eco dynos for development
- Scale down during low usage
- Consider dyno cycling for cost savings

### 2. Database Optimization
- Optimize queries for performance
- Use connection pooling
- Monitor database usage

### 3. Add-on Management
- Review add-on usage monthly
- Choose appropriate tiers
- Remove unused add-ons

## Maintenance

### 1. Regular Updates
```bash
# Update dependencies
pip list --outdated
pip install --upgrade package-name

# Update Heroku stack
heroku stack:set heroku-22 --app your-tft-app
```

### 2. Health Checks
- Monitor application performance
- Review logs regularly
- Check database health

### 3. Backup Verification
- Test backup restore procedures
- Verify data integrity
- Document recovery processes

## Next Steps

1. Complete the [Supabase Setup Guide](supabase_setup.md)
2. Set up monitoring and alerting
3. Configure automated backups
4. Implement CI/CD pipeline
5. Set up custom domain (if needed)

## Support and Resources

- [Heroku Documentation](https://devcenter.heroku.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Supabase Documentation](https://supabase.com/docs)
- [Troubleshooting Guide](troubleshooting.md)

---

**Note**: Replace all placeholder values (your-tft-app, your-project, etc.) with your actual application names and credentials.