---
noteId: "2a1b3c4d734211f095e8a9866d35445a"
tags: []
---

# Streamlit Community Cloud Deployment Guide

## Why Streamlit Community Cloud?
- **Completely FREE** - No payment information required
- **Perfect for database apps** - Better than HF Spaces for full applications
- **No cold starts** - Better performance and uptime
- **Private repo support** - Can deploy from private GitHub repos
- **Built-in secrets management** - Secure environment variables
- **Custom domains** - Professional URLs available

## Prerequisites
- GitHub account (free)
- Your TFT webapp code in a GitHub repository
- Supabase database (you already have this)

## Step-by-Step Deployment

### 1. Prepare Your GitHub Repository

#### Option A: Create New Repository
1. Go to [github.com](https://github.com)
2. Click "New repository"
3. Name: `tft-match-analysis`
4. Set as Public or Private (both work with Streamlit Cloud)
5. Initialize with README

#### Option B: Use Existing Repository
If you already have your code in GitHub, skip to step 2.

### 2. Upload Your Code to GitHub

**Essential files to include:**
- `streamlit_app.py` (your main app)
- `requirements.txt` 
- `database/` folder (entire folder)
- `querying.py`
- `clustering.py` (if using clustering features)
- `README.md` (optional but recommended)

**Files to exclude (.gitignore):**
```
.env
__pycache__/
*.pyc
.DS_Store
matches.jsonl
matches_filtered.jsonl
hierarchical_clusters_detailed_analysis/
*.csv
docker-compose.yml
Procfile
runtime.txt
```

### 3. Create Streamlit Community Cloud Account

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "Sign up" 
3. **Sign up with GitHub** (this links your accounts automatically)
4. Authorize Streamlit to access your GitHub repos

### 4. Deploy Your App

1. **Click "New app"** on your Streamlit Cloud dashboard
2. **Select repository**: Choose your `tft-match-analysis` repo
3. **Select branch**: Usually `main` or `master`
4. **Main file path**: `streamlit_app.py`
5. **Advanced settings** (optional):
   - Custom URL: `your-username-tft-analysis.streamlit.app`

### 5. Configure Environment Variables (Secrets)

1. **In your app dashboard**, click "⚙️ Settings"
2. **Click "Secrets"** tab
3. **Add your environment variables** in TOML format:

```toml
# Streamlit secrets format (TOML)
[database]
DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@db.gnyvkxdwlcojkgsarksr.supabase.co:5432/postgres"

[app]
ENVIRONMENT = "production"
USE_DATABASE = "true"
DEBUG = "false"

# Optional: Add other settings
[performance]
DB_POOL_SIZE = "5"
DB_MAX_OVERFLOW = "10"
```

### 6. Update Your Code for Streamlit Cloud

Create this file in your repo root: `secrets_template.py`

```python
# Access secrets in Streamlit Cloud
import streamlit as st
import os

def get_database_url():
    """Get database URL from Streamlit secrets or environment variables"""
    try:
        # Try Streamlit Cloud secrets first
        return st.secrets["database"]["DATABASE_URL"]
    except:
        # Fallback to environment variables (for local development)
        return os.getenv("DATABASE_URL")

def get_setting(category, key, default=None):
    """Get any setting from secrets or environment"""
    try:
        return st.secrets[category][key]
    except:
        return os.getenv(key, default)
```

Update your `database/config.py` to use this:

```python
# Add to your database/config.py
try:
    import streamlit as st
    # Try to get from Streamlit secrets
    DATABASE_URL = st.secrets.get("database", {}).get("DATABASE_URL") or os.getenv("DATABASE_URL")
except:
    # Fallback for local development
    DATABASE_URL = os.getenv("DATABASE_URL")
```

### 7. Deploy and Test

1. **Push your code** to GitHub:
```bash
git add .
git commit -m "Deploy to Streamlit Cloud"
git push origin main
```

2. **Streamlit Cloud will automatically deploy** (usually takes 2-3 minutes)

3. **Your app will be available at**: 
   `https://your-username-tft-analysis.streamlit.app`

### 8. Monitor and Manage

**App Management:**
- **View logs**: Click "Manage app" > "Logs" 
- **Reboot app**: If something goes wrong, click "Reboot app"
- **Update secrets**: Change environment variables anytime
- **Custom domain**: Available in settings (free!)

**Performance Monitoring:**
- Built-in analytics and usage stats
- Error tracking and logging
- Resource usage monitoring

## Troubleshooting

### Common Issues:

1. **Import errors**: Make sure all dependencies are in `requirements.txt`
2. **Database connection fails**: Check your secrets configuration
3. **App won't start**: Check the logs for detailed error messages
4. **Slow loading**: May need to optimize database queries for cloud environment

### Debug Steps:
```python
# Add this to your streamlit_app.py for debugging
import streamlit as st

# Debug secrets (remove after testing)
if st.checkbox("Show debug info"):
    st.write("Secrets available:", list(st.secrets.keys()) if hasattr(st, 'secrets') else "No secrets")
    st.write("Database URL configured:", bool(get_database_url()))
```

### Performance Tips:
- Use `@st.cache_data` for expensive operations
- Optimize database queries with proper indexes
- Consider connection pooling for high traffic

## Advantages Summary

✅ **Perfect for your TFT app** - Designed for data applications  
✅ **Excellent database support** - Much better than HF Spaces  
✅ **Professional URLs** - Custom domains available  
✅ **Real-time updates** - Push to GitHub = automatic deployment  
✅ **Better performance** - No arbitrary compute limits  
✅ **Built-in monitoring** - Logs, analytics, error tracking  

## Next Steps After Deployment

1. **Test all functionality** - Database queries, clustering, analysis
2. **Set up monitoring** - Check logs regularly
3. **Optimize performance** - Add caching where beneficial
4. **Share your work** - Get feedback from the TFT community!

Your app will be live at a professional URL and ready to handle serious traffic with your Supabase database integration!