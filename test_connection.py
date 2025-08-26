#!/usr/bin/env python3
"""
Test the new IPv4-compatible database connection
"""

import os
from simple_database import test_connection, get_match_stats, create_ipv4_compatible_url

# Set the database URL for testing
os.environ["DATABASE_URL"] = "postgresql://postgres:TFT_webapp123@db.gnyvkxdwlcojkgsarksr.supabase.co:5432/postgres"

def main():
    print("Testing IPv4-compatible database connection...")
    
    # Show URL conversion
    original_url = os.environ["DATABASE_URL"]
    pooler_url = create_ipv4_compatible_url(original_url)
    
    print(f"\nOriginal URL: {original_url}")
    print(f"Pooler URL: {pooler_url}")
    
    # Test connection
    print("\nTesting connection...")
    if test_connection():
        print("[OK] Connection successful!")
        
        # Get stats
        print("\nGetting database stats...")
        stats = get_match_stats()
        print(f"Matches: {stats['matches']:,}")
        print(f"Participants: {stats['participants']:,}")
        
    else:
        print("[ERROR] Connection failed")

if __name__ == "__main__":
    main()