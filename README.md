---
noteId: "b2dd5830734a11f095e8a9866d35445a"
tags: []

---

# TFT Composition Analysis App

A Streamlit web application for analyzing TFT (Teamfight Tactics) match data and composition clustering.

## Features

- **Cluster Analysis**: View hierarchical clusters of TFT compositions
- **Interactive Querying**: Query match data by units, traits, player levels
- **Statistical Analysis**: Get win rates, placement averages, and play counts
- **Real-time Database Integration**: Connect to PostgreSQL/Supabase for live data

## Local Development

### Prerequisites
- Python 3.8+
- PostgreSQL database (optional - app works without database)

### Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the app:
   ```bash
   streamlit run streamlit_app.py
   ```

3. Test the app:
   ```bash
   python test_app_locally.py
   ```

## Deployment to Streamlit Cloud

1. Push code to GitHub repository

2. Go to [share.streamlit.io](https://share.streamlit.io) and sign up with GitHub

3. Create new app:
   - Repository: Your GitHub repo
   - Main file: `streamlit_app.py`

4. Configure secrets (if using database):
   ```toml
   [database]
   DATABASE_URL = "postgresql://username:password@host:port/database"
   
   [app]
   ENVIRONMENT = "production"
   ```

5. App will auto-deploy at: `https://your-username-app-name.streamlit.app`

## Files Structure

- `streamlit_app.py` - Main Streamlit application
- `querying.py` - TFT data querying functionality
- `database/` - Database connection and operations
- `test_app_locally.py` - Local testing script
- `requirements.txt` - Python dependencies

## Usage

### Query Examples
```python
# Basic unit query
TFTQuery().add_unit('TFT14_Aphelios').get_stats()

# Trait query  
TFTQuery().add_trait('TFT14_Vanguard', min_tier=2).get_stats()

# Combined query
TFTQuery().add_unit('TFT14_Jinx').add_trait('TFT14_Rebel', min_tier=3).get_stats()
```

## Data

The app works with:
- Hierarchical cluster analysis CSV files
- JSONL match data files  
- PostgreSQL/Supabase database (optional)

## Support

For deployment guides and troubleshooting, see the `deployment/` folder.