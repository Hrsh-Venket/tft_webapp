#!/usr/bin/env python3
"""
Create sample data in Supabase for testing
"""

import psycopg2
import json
from datetime import datetime
import sys

DATABASE_URL = "postgresql://postgres:TFT_webapp123@db.gnyvkxdwlcojkgsarksr.supabase.co:5432/postgres"

def create_sample_data():
    """Create some sample match data for testing"""
    
    print("Creating sample data in Supabase...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Sample match data
        sample_matches = [
            {
                'match_id': 'TEST_MATCH_001',
                'game_datetime': datetime.now(),
                'game_length': 1800.0,
                'game_version': 'Test Version',
                'set_core_name': 'TFTSet15',
                'queue_id': 1100,
                'tft_set_number': 15,
                'raw_data': json.dumps({'test': 'data'})
            },
            {
                'match_id': 'TEST_MATCH_002', 
                'game_datetime': datetime.now(),
                'game_length': 2100.0,
                'game_version': 'Test Version',
                'set_core_name': 'TFTSet15',
                'queue_id': 1100,
                'tft_set_number': 15,
                'raw_data': json.dumps({'test': 'data'})
            }
        ]
        
        # Insert sample matches
        for match in sample_matches:
            cursor.execute("""
                INSERT INTO matches (
                    match_id, game_datetime, game_length, game_version,
                    set_core_name, queue_id, tft_set_number, raw_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id) DO NOTHING
            """, (
                match['match_id'], match['game_datetime'], match['game_length'],
                match['game_version'], match['set_core_name'], match['queue_id'],
                match['tft_set_number'], match['raw_data']
            ))
        
        # Sample participant data
        sample_participants = [
            # Match 1 participants
            ('TEST_MATCH_001', 'player1', 1, 9, 35, 7, 150, 2100.0, '{}', '[]', '[{"character_id":"TFT14_Aphelios","tier":3}]', []),
            ('TEST_MATCH_001', 'player2', 2, 8, 33, 0, 120, 2050.0, '{}', '[]', '[{"character_id":"TFT14_Jinx","tier":2}]', []),
            ('TEST_MATCH_001', 'player3', 3, 8, 31, 0, 100, 1900.0, '{}', '[]', '[{"character_id":"TFT14_Vanguard","tier":2}]', []),
            ('TEST_MATCH_001', 'player4', 4, 7, 29, 0, 80, 1800.0, '{}', '[]', '[]', []),
            ('TEST_MATCH_001', 'player5', 5, 7, 27, 0, 60, 1700.0, '{}', '[]', '[]', []),
            ('TEST_MATCH_001', 'player6', 6, 6, 25, 0, 40, 1600.0, '{}', '[]', '[]', []),
            ('TEST_MATCH_001', 'player7', 7, 6, 23, 0, 20, 1500.0, '{}', '[]', '[]', []),
            ('TEST_MATCH_001', 'player8', 8, 5, 21, 0, 10, 1400.0, '{}', '[]', '[]', []),
            # Match 2 participants  
            ('TEST_MATCH_002', 'player9', 1, 9, 34, 6, 140, 2000.0, '{}', '[]', '[{"character_id":"TFT14_Aphelios","tier":2}]', []),
            ('TEST_MATCH_002', 'player10', 2, 8, 32, 1, 110, 1950.0, '{}', '[]', '[]', []),
        ]
        
        # Insert sample participants
        for participant in sample_participants:
            cursor.execute("""
                INSERT INTO participants (
                    match_id, puuid, placement, level, last_round,
                    players_eliminated, total_damage_to_players,
                    time_eliminated, companion, traits, units, augments
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id, puuid) DO NOTHING
            """, participant)
        
        conn.commit()
        
        # Test the data
        cursor.execute("SELECT COUNT(*) FROM matches")
        match_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM participants") 
        participant_count = cursor.fetchone()[0]
        
        print(f"Sample data created!")
        print(f"Matches: {match_count}")
        print(f"Participants: {participant_count}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if create_sample_data():
        print("Sample data created successfully!")
        print("Your Streamlit app should now work with basic queries.")
    else:
        print("Failed to create sample data.")
        sys.exit(1)