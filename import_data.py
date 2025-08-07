#!/usr/bin/env python3
"""
Import TFT Match Data to Supabase
Parses matches_filtered.jsonl and uploads to database
"""

import json
import psycopg2
from datetime import datetime
import sys

# Supabase connection
DATABASE_URL = "postgresql://postgres:TFT_webapp123@db.gnyvkxdwlcojkgsarksr.supabase.co:5432/postgres"

def parse_and_import_matches(jsonl_file="matches_filtered.jsonl"):
    """Parse JSONL file and import matches to database"""
    
    print("Connecting to Supabase database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    matches_imported = 0
    participants_imported = 0
    
    print(f"Reading {jsonl_file}...")
    
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    match_data = json.loads(line.strip())
                    
                    # Extract match info
                    match_info = match_data['info']
                    match_id = match_data['metadata']['match_id']
                    
                    # Convert game_datetime from milliseconds to timestamp
                    game_datetime = datetime.fromtimestamp(match_info['game_datetime'] / 1000)
                    
                    # Insert match
                    cursor.execute("""
                        INSERT INTO matches (
                            match_id, game_datetime, game_length, game_version,
                            set_core_name, queue_id, tft_set_number, raw_data
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (match_id) DO NOTHING
                    """, (
                        match_id,
                        game_datetime,
                        match_info.get('game_length'),
                        match_info.get('game_version'),
                        match_info.get('tft_set_core_name'),
                        match_info.get('queue_id'),
                        match_info.get('tft_set_number'),
                        json.dumps(match_data)
                    ))
                    
                    if cursor.rowcount > 0:
                        matches_imported += 1
                    
                    # Insert participants
                    for participant in match_info['participants']:
                        cursor.execute("""
                            INSERT INTO participants (
                                match_id, puuid, placement, level, last_round,
                                players_eliminated, total_damage_to_players,
                                time_eliminated, companion, traits, units, augments
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (match_id, puuid) DO NOTHING
                        """, (
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
                        
                        if cursor.rowcount > 0:
                            participants_imported += 1
                    
                    # Commit every 100 matches
                    if line_num % 100 == 0:
                        conn.commit()
                        print(f"Processed {line_num} matches... ({matches_imported} new matches, {participants_imported} new participants)")
                        
                except Exception as e:
                    print(f"Error processing line {line_num}: {e}")
                    continue
    
    # Final commit
    conn.commit()
    
    # Get final counts
    cursor.execute("SELECT COUNT(*) FROM matches")
    total_matches = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM participants")
    total_participants = cursor.fetchone()[0]
    
    print(f"\nImport complete!")
    print(f"New matches imported: {matches_imported}")
    print(f"New participants imported: {participants_imported}")
    print(f"Total matches in database: {total_matches}")
    print(f"Total participants in database: {total_participants}")
    
    cursor.close()
    conn.close()

def test_data_query():
    """Test querying the imported data"""
    print("\nTesting data queries...")
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Test basic stats
    cursor.execute("SELECT COUNT(*) FROM matches")
    match_count = cursor.fetchone()[0]
    print(f"Matches: {match_count}")
    
    cursor.execute("SELECT COUNT(*) FROM participants")
    participant_count = cursor.fetchone()[0]
    print(f"Participants: {participant_count}")
    
    # Test average placement
    cursor.execute("SELECT AVG(placement::float) FROM participants")
    avg_placement = cursor.fetchone()[0]
    print(f"Average placement: {avg_placement:.2f}")
    
    # Test win rate (1st place)
    cursor.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE placement = 1) as wins,
            COUNT(*) as total,
            (COUNT(*) FILTER (WHERE placement = 1) * 100.0 / COUNT(*)) as winrate
        FROM participants
    """)
    wins, total, winrate = cursor.fetchone()
    print(f"Win rate: {winrate:.2f}% ({wins}/{total})")
    
    # Test top 4 rate
    cursor.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE placement <= 4) as top4,
            COUNT(*) as total,
            (COUNT(*) FILTER (WHERE placement <= 4) * 100.0 / COUNT(*)) as top4_rate
        FROM participants
    """)
    top4, total, top4_rate = cursor.fetchone()
    print(f"Top 4 rate: {top4_rate:.2f}% ({top4}/{total})")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        print("Starting TFT data import to Supabase...")
        parse_and_import_matches()
        test_data_query()
        print("\nData import successful! Your Streamlit app queries should now work.")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)