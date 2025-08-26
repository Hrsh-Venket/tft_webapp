"""
Simple test to verify Streamlit can connect to Supabase
"""

def test_database_connection():
    """Test database connection from Streamlit"""
    try:
        # Try Streamlit secrets first
        import streamlit as st
        database_url = st.secrets["database"]["DATABASE_URL"]
        print(f"Got database URL from secrets: {database_url[:20]}...")
        
    except Exception as e:
        print(f"Could not get secrets: {e}")
        # Fallback to environment
        import os
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:TFT_webapp123@db.gnyvkxdwlcojkgsarksr.supabase.co:5432/postgres")
        print(f"Using environment/hardcoded URL: {database_url[:20]}...")
    
    # Test connection
    import psycopg2
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    # Test query
    cursor.execute("SELECT COUNT(*) FROM matches")
    match_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM participants") 
    participant_count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return {
        "matches": match_count,
        "participants": participant_count,
        "connection": "success"
    }

if __name__ == "__main__":
    result = test_database_connection()
    print("Database test result:", result)