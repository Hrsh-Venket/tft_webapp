#!/usr/bin/env python3
"""
Simple Database Initialization for Supabase
Creates basic tables needed for TFT querying
"""

import psycopg2
import sys

# Supabase connection
DATABASE_URL = "postgresql://postgres:TFT_webapp123@db.gnyvkxdwlcojkgsarksr.supabase.co:5432/postgres"

def create_basic_tables():
    """Create basic tables for TFT match analysis"""
    
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Simple matches table (no partitioning)
    print("Creating matches table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            game_datetime TIMESTAMPTZ,
            game_length REAL,
            game_version TEXT,
            set_core_name TEXT,
            set_mutators TEXT[],
            queue_id INTEGER,
            tft_set_number INTEGER,
            raw_data JSONB
        );
    """)
    
    # Participants table
    print("Creating participants table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            match_id TEXT,
            puuid TEXT,
            placement INTEGER,
            level INTEGER,
            last_round INTEGER,
            players_eliminated INTEGER,
            total_damage_to_players INTEGER,
            time_eliminated REAL,
            companion JSONB,
            traits JSONB,
            units JSONB,
            augments TEXT[],
            PRIMARY KEY (match_id, puuid)
        );
    """)
    
    # Basic indexes
    print("Creating indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_datetime ON matches(game_datetime);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_participants_placement ON participants(placement);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_participants_puuid ON participants(puuid);")
    
    conn.commit()
    
    # Test the tables
    print("Testing tables...")
    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('matches', 'participants');")
    table_count = cursor.fetchone()[0]
    print(f"Created {table_count} tables successfully!")
    
    cursor.close()
    conn.close()
    print("Database initialization complete!")

if __name__ == "__main__":
    try:
        create_basic_tables()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)