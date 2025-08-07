#!/usr/bin/env python3
"""
Manual Data Upload Script for TFT Webapp
Clean version without Unicode characters
"""

import json
import psycopg2
from datetime import datetime
import sys
import os

DATABASE_URL = "postgresql://postgres:TFT_webapp123@db.gnyvkxdwlcojkgsarksr.supabase.co:5432/postgres"

def test_connection():
    print("Testing database connection...")
    try:
        # Test basic connectivity first
        import socket
        hostname = "db.gnyvkxdwlcojkgsarksr.supabase.co"
        port = 5432
        
        print(f"Testing DNS resolution for {hostname}...")
        try:
            socket.getaddrinfo(hostname, port)
            print("[OK] DNS resolution successful")
        except socket.gaierror as e:
            print(f"[ERROR] DNS resolution failed: {e}")
            print("Possible fixes:")
            print("1. Check internet connection")
            print("2. Try different DNS (8.8.8.8, 1.1.1.1)")
            print("3. Use mobile hotspot")
            print("4. Check firewall/antivirus")
            return False
        
        print("Testing database connection...")
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        print("[OK] Database connection successful!")
        return True
        
    except psycopg2.OperationalError as e:
        error_msg = str(e).lower()
        print(f"[ERROR] Connection failed: {e}")
        
        if "name or service not known" in error_msg or "nodename nor servname provided" in error_msg:
            print("\nDNS Resolution Issue:")
            print("1. Check internet connection")
            print("2. Try: ping db.gnyvkxdwlcojkgsarksr.supabase.co")
            print("3. Change DNS to 8.8.8.8 or 1.1.1.1")
            print("4. Try mobile hotspot")
        elif "timeout" in error_msg:
            print("\nConnection Timeout:")
            print("1. Check firewall settings")
            print("2. Try different network")
            print("3. Contact IT/network admin")
        elif "authentication failed" in error_msg:
            print("\nAuth Issue:")
            print("1. Check DATABASE_URL credentials")
            print("2. Verify Supabase project is active")
        else:
            print("\nGeneral troubleshooting:")
            print("1. Check Supabase project status")
            print("2. Verify DATABASE_URL is correct")
            print("3. Try from different location")
        
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

def upload_data(jsonl_file="matches_filtered.jsonl", batch_size=1000, skip_raw_data=True):
    if not os.path.exists(jsonl_file):
        print(f"[ERROR] File not found: {jsonl_file}")
        return False
    
    print(f"[OPTIMIZED] Uploading from {jsonl_file}...")
    print(f"Batch size: {batch_size}, Skip raw data: {skip_raw_data}")
    
    try:
        # Test connection first
        if not test_connection():
            print("[ERROR] Cannot connect to database. Upload aborted.")
            return False
        
        # Optimized connection
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
        line_num = 0
        
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
                    
                    # Add to batch
                    match_batch.append((
                        match_id, game_datetime, match_info.get('game_length'),
                        match_info.get('game_version'), match_info.get('tft_set_core_name'),
                        match_info.get('queue_id'), match_info.get('tft_set_number'),
                        None if skip_raw_data else json.dumps(match_data)
                    ))
                    
                    # Add participants to batch
                    for participant in match_info['participants']:
                        participant_batch.append((
                            match_id, participant['puuid'], participant.get('placement'),
                            participant.get('level'), participant.get('last_round'),
                            participant.get('players_eliminated'), 
                            participant.get('total_damage_to_players'),
                            participant.get('time_eliminated'),
                            json.dumps(participant.get('companion', {})),
                            json.dumps(participant.get('traits', [])),
                            json.dumps(participant.get('units', [])),
                            participant.get('augments', [])
                        ))
                    
                    # Process batch when full
                    if len(match_batch) >= batch_size:
                        matches_imported += execute_batch_clean(cursor, match_batch, participant_batch)
                        conn.commit()
                        print(f"[BATCH] Processed {line_num} lines... ({matches_imported} matches)")
                        match_batch = []
                        participant_batch = []
                        
                except Exception as e:
                    print(f"Error on line {line_num}: {e}")
                    continue
        
        # Process remaining batch
        if match_batch:
            matches_imported += execute_batch_clean(cursor, match_batch, participant_batch)
            conn.commit()
        
        # Final stats
        cursor.execute("SELECT COUNT(*) FROM matches")
        total_matches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM participants")
        total_participants = cursor.fetchone()[0]
        
        print(f"\n[SUCCESS] OPTIMIZED Upload Complete!")
        print(f"- Lines processed: {line_num}")
        print(f"- New matches: {matches_imported}")
        print(f"- Storage saved: {'~80%' if skip_raw_data else '0%'}")
        print(f"- Total in database: {total_matches} matches, {total_participants} participants")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        return False

def execute_batch_clean(cursor, match_batch, participant_batch):
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
        print(f"Batch error: {e}")
        return 0

def show_stats():
    try:
        # Test connection first
        if not test_connection():
            print("[ERROR] Cannot connect to database. Stats unavailable.")
            return
        
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM matches")
        matches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM participants")
        participants = cursor.fetchone()[0]
        
        print(f"\nDatabase Stats:")
        print(f"- Matches: {matches:,}")
        print(f"- Participants: {participants:,}")
        
        if matches > 0:
            cursor.execute("SELECT AVG(placement::float) FROM participants")
            avg_placement = cursor.fetchone()[0]
            print(f"- Average placement: {avg_placement:.2f}")
            
            # Additional stats
            cursor.execute("SELECT MIN(game_datetime), MAX(game_datetime) FROM matches")
            min_date, max_date = cursor.fetchone()
            if min_date and max_date:
                print(f"- Date range: {min_date.date()} to {max_date.date()}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Stats failed: {e}")
        print("Connection or query issue. Try option 1 to test connection.")

def run_diagnostics():
    """Run comprehensive network diagnostics"""
    import subprocess
    import platform
    
    print("\n=== Network Diagnostics ===")
    hostname = "db.gnyvkxdwlcojkgsarksr.supabase.co"
    
    # Ping test
    print(f"1. Testing ping to {hostname}...")
    try:
        ping_cmd = ["ping", "-c", "4"] if platform.system() != "Windows" else ["ping", "-n", "4"]
        ping_cmd.append(hostname)
        result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("[OK] Ping successful")
        else:
            print(f"[ERROR] Ping failed: {result.stderr}")
    except Exception as e:
        print(f"[ERROR] Ping test failed: {e}")
    
    # DNS lookup test
    print(f"\n2. Testing DNS lookup...")
    try:
        import socket
        ip = socket.gethostbyname(hostname)
        print(f"[OK] DNS resolved to: {ip}")
    except Exception as e:
        print(f"[ERROR] DNS lookup failed: {e}")
    
    # Port connectivity test
    print(f"\n3. Testing port 5432 connectivity...")
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, 5432))
        if result == 0:
            print("[OK] Port 5432 is reachable")
        else:
            print(f"[ERROR] Cannot connect to port 5432")
        sock.close()
    except Exception as e:
        print(f"[ERROR] Port test failed: {e}")
    
    # Environment info
    print(f"\n4. Environment info:")
    print(f"   - Platform: {platform.system()} {platform.release()}")
    print(f"   - Python: {platform.python_version()}")
    try:
        import psycopg2
        print(f"   - psycopg2: {psycopg2.__version__}")
    except:
        print("   - psycopg2: Not installed")
    
    print("\n=== Troubleshooting Tips ===")
    print("If tests fail:")
    print("1. Check internet connection")
    print("2. Try mobile hotspot")
    print("3. Change DNS to 8.8.8.8 or 1.1.1.1")
    print("4. Check firewall/antivirus settings")
    print("5. Try from different location/network")

if __name__ == "__main__":
    print("=" * 40)
    print("TFT Database Upload Tool")
    print("=" * 40)
    
    while True:
        print("\n1. Test connection")
        print("2. Upload data")
        print("3. Show stats")
        print("4. Network diagnostics")
        print("5. Exit")
        
        choice = input("Choice (1-5): ").strip()
        
        if choice == '1':
            test_connection()
        elif choice == '2':
            # Get filename
            filename = input("JSONL file (default: matches_filtered.jsonl): ").strip()
            if not filename:
                filename = "matches_filtered.jsonl"
            
            # Get optimization settings
            batch_input = input("Batch size (default: 1000): ").strip()
            batch_size = int(batch_input) if batch_input.isdigit() else 1000
            
            skip_raw = input("Skip raw data? (y/N, saves ~80% space): ").strip().lower()
            skip_raw_data = skip_raw in ['y', 'yes']
            
            upload_data(filename, batch_size, skip_raw_data)
        elif choice == '3':
            show_stats()
        elif choice == '4':
            run_diagnostics()
        elif choice == '5':
            break
        else:
            print("Invalid choice")