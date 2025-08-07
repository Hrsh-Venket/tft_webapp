#!/usr/bin/env python3
"""
Manual Data Upload Script for TFT Webapp Owner
This script is for YOU to run locally to upload data to your Supabase database.
Users will only query the data, not upload it.
"""

import json
import psycopg2
from datetime import datetime
import sys
import os

# Your Supabase connection - you can also set this as environment variable
DATABASE_URL = "postgresql://postgres:TFT_webapp123@db.gnyvkxdwlcojkgsarksr.supabase.co:5432/postgres"

def test_connection():
    """Test database connection first"""
    print("Testing database connection...")
    try:
        # Try different connection approaches
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        print("✓ Database connection successful!")
        return True
    except psycopg2.OperationalError as e:
        print(f"✗ Connection failed: {e}")
        print("\nTroubleshooting suggestions:")
        print("1. Check your internet connection")
        print("2. Try from a different network (mobile hotspot)")
        print("3. Check if the Supabase URL is correct")
        print("4. Verify firewall/antivirus isn't blocking the connection")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def upload_matches_data(jsonl_file="matches_filtered.jsonl", batch_size=1000, skip_raw_data=True):
    """Upload your TFT match data to the database (OPTIMIZED)"""
    
    if not os.path.exists(jsonl_file):
        print(f"✗ File not found: {jsonl_file}")
        print("Make sure your JSONL file is in the same directory as this script.")
        return False
    
    print(f"🚀 Starting OPTIMIZED upload from {jsonl_file}...")
    print(f"File size: {os.path.getsize(jsonl_file):,} bytes")
    print(f"Batch size: {batch_size:,}, Skip raw data: {skip_raw_data}")
    
    try:
        # Optimized connection with performance settings
        conn = psycopg2.connect(
            DATABASE_URL, 
            connect_timeout=30,
            options='-c synchronous_commit=off'
        )
        cursor = conn.cursor()
        
        # Batch storage
        match_batch = []
        participant_batch = []
        matches_imported = 0
        participants_imported = 0
        matches_skipped = 0
        line_num = 0
        
        print("📊 Processing file...")
        
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_num += 1
                if not line.strip():
                    continue
                    
                try:
                    match_data = json.loads(line.strip())
                    match_info = match_data['info']
                    match_id = match_data['metadata']['match_id']
                    game_datetime = datetime.fromtimestamp(match_info['game_datetime'] / 1000)
                    
                    # Add to match batch
                    match_batch.append((
                        match_id,
                        game_datetime,
                        match_info.get('game_length'),
                        match_info.get('game_version'),
                        match_info.get('tft_set_core_name'),
                        match_info.get('queue_id'),
                        match_info.get('tft_set_number'),
                        None if skip_raw_data else json.dumps(match_data)
                    ))
                    
                    # Add participants to batch
                    for participant in match_info['participants']:
                        participant_batch.append((
                            match_id,
                            participant['puuid'],
                            participant.get('placement'),
                            participant.get('level'),
                            participant.get('last_round'),
                            participant.get('players_eliminated'),
                            participant.get('total_damage_to_players'),
                            participant.get('time_eliminated'),
                            json.dumps(participant.get('companion', {})),
                            json.dumps(participant.get('traits', [])),
                            json.dumps(participant.get('units', [])),
                            participant.get('augments', [])
                        ))
                    
                    # Execute batch when size is reached
                    if len(match_batch) >= batch_size:
                        matches_imported += execute_batch(cursor, match_batch, participant_batch)
                        conn.commit()
                        
                        print(f"⚡ Processed {line_num:,} lines... ({matches_imported:,} matches, {len(participant_batch):,} participants)")
                        match_batch = []
                        participant_batch = []
                        
                except json.JSONDecodeError as e:
                    print(f"JSON error on line {line_num}: {e}")
                    continue
                except Exception as e:
                    print(f"Error processing line {line_num}: {e}")
                    continue
        
        # Process remaining batch
        if match_batch:
            matches_imported += execute_batch(cursor, match_batch, participant_batch)
            conn.commit()
        
        # Get final database stats
        cursor.execute("SELECT COUNT(*) FROM matches")
        total_matches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM participants")
        total_participants = cursor.fetchone()[0]
        
        print(f"\n🎉 OPTIMIZED Upload Complete!")
        print(f"📊 Results:")
        print(f"   • Lines processed: {line_num:,}")
        print(f"   • New matches imported: {matches_imported:,}")
        print(f"   • Storage saved: {'~80%' if skip_raw_data else '0%'} (raw data)")
        print(f"   • Total matches in database: {total_matches:,}")
        print(f"   • Total participants in database: {total_participants:,}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Upload failed: {e}")
        return False

def execute_batch(cursor, match_batch, participant_batch):
    """Execute batch inserts efficiently"""
    try:
        # Batch insert matches
        cursor.executemany("""
            INSERT INTO matches (
                match_id, game_datetime, game_length, game_version,
                set_core_name, queue_id, tft_set_number, raw_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (match_id) DO NOTHING
        """, match_batch)
        matches_added = cursor.rowcount
        
        # Batch insert participants  
        cursor.executemany("""
            INSERT INTO participants (
                match_id, puuid, placement, level, last_round,
                players_eliminated, total_damage_to_players,
                time_eliminated, companion, traits, units, augments
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (match_id, puuid) DO NOTHING
        """, participant_batch)
        
        return matches_added
        
    except Exception as e:
        print(f"Batch execution error: {e}")
        return 0

def clear_database():
    """Clear all match data (use with caution!)"""
    response = input("⚠️  Are you sure you want to CLEAR ALL DATA? Type 'YES' to confirm: ")
    if response != 'YES':
        print("Operation cancelled.")
        return
        
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM participants")
        participants_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM matches")  
        matches_deleted = cursor.rowcount
        
        conn.commit()
        
        print(f"✓ Cleared {matches_deleted:,} matches and {participants_deleted:,} participants")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Clear failed: {e}")

def show_database_stats():
    """Show current database statistics"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Basic counts
        cursor.execute("SELECT COUNT(*) FROM matches")
        match_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM participants")
        participant_count = cursor.fetchone()[0]
        
        print(f"\n📊 Database Statistics:")
        print(f"   • Total matches: {match_count:,}")
        print(f"   • Total participants: {participant_count:,}")
        
        if match_count > 0:
            # Date range
            cursor.execute("SELECT MIN(game_datetime), MAX(game_datetime) FROM matches")
            min_date, max_date = cursor.fetchone()
            print(f"   • Date range: {min_date.date()} to {max_date.date()}")
            
            # Average placement
            cursor.execute("SELECT AVG(placement::float) FROM participants")
            avg_placement = cursor.fetchone()[0]
            print(f"   • Average placement: {avg_placement:.2f}")
            
            # Win rate
            cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE placement = 1) * 100.0 / COUNT(*) as winrate
                FROM participants
            """)
            winrate = cursor.fetchone()[0]
            print(f"   • Win rate: {winrate:.1f}%")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Stats failed: {e}")

def main():
    """Main menu for database management"""
    print("=" * 50)
    print("TFT Webapp - Database Management")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. Test database connection")
        print("2. Upload match data")
        print("3. Show database statistics") 
        print("4. Clear all data (DANGER!)")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            test_connection()
        elif choice == '2':
            jsonl_file = input("Enter JSONL filename (default: matches_filtered.jsonl): ").strip()
            if not jsonl_file:
                jsonl_file = "matches_filtered.jsonl"
            
            # Get optimization settings
            print("\n🚀 Optimization Settings:")
            batch_input = input("Batch size (default: 1000, higher = faster): ").strip()
            batch_size = int(batch_input) if batch_input.isdigit() else 1000
            
            skip_raw = input("Skip raw data storage? (y/N, saves ~80% space): ").strip().lower()
            skip_raw_data = skip_raw in ['y', 'yes']
            
            upload_matches_data(jsonl_file, batch_size, skip_raw_data)
        elif choice == '3':
            show_database_stats()
        elif choice == '4':
            clear_database()
        elif choice == '5':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()