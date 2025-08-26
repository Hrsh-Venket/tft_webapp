#!/usr/bin/env python3
"""
Simple Supabase Database Initialization Script
Runs all SQL migration files in order
"""

import os
import psycopg2
from pathlib import Path

# Set your Supabase connection string
DATABASE_URL = "postgresql://postgres:TFT_webapp123@db.gnyvkxdwlcojkgsarksr.supabase.co:5432/postgres"

def run_migrations():
    """Run all SQL migration files in order"""
    
    # Connect to database
    print("Connecting to Supabase database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Get migration files in order
    migrations_dir = Path("database/migrations")
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    print(f"Found {len(migration_files)} migration files")
    
    for migration_file in migration_files:
        print(f"Running migration: {migration_file.name}")
        
        try:
            # Read and execute SQL file
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            cursor.execute(sql)
            conn.commit()
            print(f"  ✓ {migration_file.name} completed successfully")
            
        except Exception as e:
            print(f"  ✗ Error in {migration_file.name}: {e}")
            conn.rollback()
    
    # Test the connection
    print("\nTesting database connection...")
    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
    table_count = cursor.fetchone()[0]
    print(f"Database initialized with {table_count} tables")
    
    cursor.close()
    conn.close()
    print("Database initialization complete!")

if __name__ == "__main__":
    run_migrations()