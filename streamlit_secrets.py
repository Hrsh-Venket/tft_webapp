"""
Streamlit Cloud Secrets Integration
Helper functions to access secrets in Streamlit Cloud deployment
"""

import os

def get_database_url():
    """Get database URL from Streamlit secrets or environment variables"""
    try:
        import streamlit as st
        # Try Streamlit Cloud secrets first
        return st.secrets["database"]["DATABASE_URL"]
    except:
        # Fallback to environment variables (for local development)
        return os.getenv("DATABASE_URL")

def get_config_value(category, key, default=None):
    """Get any configuration value from secrets or environment"""
    try:
        import streamlit as st
        return st.secrets[category][key]
    except:
        return os.getenv(key, default)

def is_streamlit_cloud():
    """Check if running on Streamlit Cloud"""
    try:
        import streamlit as st
        # Check if we can access secrets (only available in Streamlit Cloud)
        _ = st.secrets
        return True
    except:
        return False