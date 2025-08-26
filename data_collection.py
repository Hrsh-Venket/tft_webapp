"""
TFT Data Collection Module

This module handles all Riot Games API interactions for collecting TFT match data.
Includes rate limiting, player lookup, match history, and bulk data collection.
"""

# ===============================
# CONFIGURATION - EDIT THESE VALUES
# ===============================

API_KEY = "RGAPI-8ba24f5f-3ff3-4c08-bb6d-68d46b6cf7ee"  # Replace with your actual Riot API key
days = 0
START_TIMESTAMP = (130032000 + (days * 86400))   # Epoch timestamp for period-based collection
INIT_TRACKER_ONLY = False      # Set to True to only initialize tracker

# Collection settings
TIER = 'PLATINUM'            # Minimum tier for data collection
REGION_MATCHES = 'sea'         # Region for match data
REGION_PLAYERS = 'sg2'         # Region for player rankings
OUTPUT_FILE = 'matches.jsonl'  # Output file (for backward compatibility)
BATCH_SIZE = 50                # Batch size for processing
MAX_WORKERS = 5                # Maximum concurrent workers

# Database settings
USE_DATABASE = True            # Use PostgreSQL instead of JSONL
ENABLE_JSONL_BACKUP = False    # Also save to JSONL file as backup
DB_BATCH_SIZE = 25             # Database batch size (smaller for stability)
ENABLE_DB_VALIDATION = True    # Validate data before database insertion

# ===============================
# END CONFIGURATION
# ===============================

import requests
import time
import json
import threading
import os
from datetime import datetime
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

# Database imports
try:
    from database.data_import import MatchDataImporter, batch_insert_matches, check_match_exists
    from database.connection import get_database_manager, test_connection
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Database functionality not available: {e}")
    DATABASE_AVAILABLE = False


class RateLimiter:
    """
    Thread-safe rate limiter for Riot Games API.
    Handles both per-second and per-window rate limits.
    """
    
    def __init__(self, max_per_second=20, max_per_window=100, window_seconds=120):
        self.max_per_second = max_per_second
        self.max_per_window = max_per_window
        self.window_seconds = window_seconds
        self.second_requests = deque()
        self.window_requests = deque()
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        with self.lock:
            while True:
                now = time.time()
                # Clean window
                while self.window_requests and self.window_requests[0] < now - self.window_seconds:
                    self.window_requests.popleft()
                # Check window
                if len(self.window_requests) >= self.max_per_window:
                    sleep_time = self.window_requests[0] + self.window_seconds - now + 0.01
                    time.sleep(sleep_time)
                    continue
                # Clean second
                while self.second_requests and self.second_requests[0] < now - 1:
                    self.second_requests.popleft()
                # Check second
                if len(self.second_requests) >= self.max_per_second:
                    sleep_time = self.second_requests[0] + 1 - now + 0.01
                    time.sleep(sleep_time)
                    continue
                break

    def record_request(self):
        """Record that a request was made."""
        with self.lock:
            now = time.time()
            self.window_requests.append(now)
            self.second_requests.append(now)


class RiotAPIClient:
    """
    Client for interacting with Riot Games TFT API.
    Handles rate limiting and retries automatically.
    """
    
    def __init__(self, api_key, max_per_second=20, max_per_window=100, window_seconds=120):
        self.api_key = api_key
        self.limiter = RateLimiter(max_per_second, max_per_window, window_seconds)
    
    def _api_get(self, url):
        """Make a rate-limited API request with retry logic."""
        while True:
            self.limiter.wait_if_needed()
            resp = requests.get(url)
            if resp.status_code != 429:
                self.limiter.record_request()
                return resp
            retry_after = int(resp.headers.get('Retry-After', '10'))
            time.sleep(retry_after)
    
    def get_puuid(self, summoner_name, tag_line, region):
        """
        Get the PUUID of a player using their Riot ID and tag line.
        
        :param summoner_name: The player's Riot ID
        :param tag_line: The player's tag line
        :param region: The region of the player
        :return: The PUUID of the player
        """
        api_url = (
            f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/"
            f"{summoner_name}/{tag_line}?api_key={self.api_key}"
        )
        
        resp = self._api_get(api_url)
        if resp.status_code == 200:
            player_info = resp.json()
            return player_info['puuid']
        else:
            raise Exception(f"Failed to get PUUID: {resp.status_code} - {resp.text}")

    def get_last_match_ids(self, puuid, region, start='0', count='20'):
        """
        Get the last matches played by a player.
        
        :param puuid: Player's PUUID
        :param region: Region of the player
        :param start: Starting index for match history (default is 0)
        :param count: Number of matches to retrieve (default is 20)
        :return: List of match IDs
        """
        api_url = (
            f"https://{region}.api.riotgames.com/tft/match/v1/matches/by-puuid/"
            f"{puuid}/ids?start={start}&count={count}&api_key={self.api_key}"
        )
        
        resp = self._api_get(api_url)
        if resp.status_code == 200:
            return resp.json()
        else:
            raise Exception(f"Failed to get match IDs: {resp.status_code} - {resp.text}")

    def get_period_match_ids(self, puuid, region, start_time, end_time):
        """
        Get matches played by a player in a specific time period.
        
        :param puuid: Player's PUUID
        :param region: Region of the player
        :param start_time: Epoch timestamp in seconds
        :param end_time: Epoch timestamp in seconds
        :return: List of match IDs
        """
        api_url = (
            f"https://{region}.api.riotgames.com/tft/match/v1/matches/by-puuid/"
            f"{puuid}/ids?endTime={end_time}&startTime={start_time}&api_key={self.api_key}"
        )
        
        resp = self._api_get(api_url)
        if resp.status_code == 200:
            return resp.json()
        else:
            raise Exception(f"Failed to get period match IDs: {resp.status_code} - {resp.text}")

    def get_match_details(self, match_id, region):
        """
        Get the details of a specific match.
        
        :param match_id: ID of the match
        :param region: Region of the player
        :return: Match details as a JSON object
        """
        api_url = (
            f"https://{region}.api.riotgames.com/tft/match/v1/matches/"
            f"{match_id}?api_key={self.api_key}"
        )
        
        resp = self._api_get(api_url)
        if resp.status_code == 200:
            return resp.json()
        else:
            raise Exception(f"Failed to get match details: {resp.status_code} - {resp.text}")

    def get_league_by_puuid(self, puuid, region):
        """
        Get the league information of a player using their PUUID.
        
        :param puuid: Player's PUUID
        :param region: Region of the player
        :return: League information as a JSON object
        """
        api_url = (
            f"https://{region}.api.riotgames.com/tft/league/v1/by-puuid/"
            f"{puuid}?api_key={self.api_key}"
        )
        
        resp = self._api_get(api_url)
        if resp.status_code == 200:
            return resp.json()
        else:
            raise Exception(f"Failed to get league info: {resp.status_code} - {resp.text}")

    def get_players_list(self, region, tier, division='I', queue='RANKED_TFT'):
        """
        Get a list of players in a specific league tier and division.
        
        :param region: Region of the players
        :param tier: League tier in lowercase (e.g., diamond)
        :param division: League division (e.g., III). Default 'I' if Master, Grandmaster, or Challenger
        :param queue: Queue type (default is 'RANKED_TFT')
        :return: List of players in the specified league
        """
        if tier not in ['master', 'grandmaster', 'challenger']:
            return self._get_low_tier_players_list(region, tier.upper(), division, queue)
        else:
            return self._get_high_tier_players_list(region, tier, queue)

    def _get_low_tier_players_list(self, region, tier, division, queue):
        """Helper function to get players list for low tiers with pagination."""
        players_list = []
        page = 1
        
        while True:
            api_url = (
                f"https://{region}.api.riotgames.com/tft/league/v1/entries/"
                f"{tier}/{division}?queue={queue}&page={page}&api_key={self.api_key}"
            )
            
            resp = self._api_get(api_url)
            if resp.status_code != 200:
                break
                
            resp_list = resp.json()
            if not resp_list:
                break
                
            players_list.extend(resp_list)
            page += 1
            
        return players_list

    def _get_high_tier_players_list(self, region, tier, queue):
        """Helper function to get players list for high tiers (no pagination needed)."""
        api_url = (
            f"https://{region}.api.riotgames.com/tft/league/v1/"
            f"{tier}?queue={queue}&api_key={self.api_key}"
        )
        
        resp = self._api_get(api_url)
        if resp.status_code == 200:
            return resp.json()
        else:
            raise Exception(f"Failed to get high tier players: {resp.status_code} - {resp.text}")

    def get_players_tier_and_above(self, tier, region='sg2', division='I', queue='RANKED_TFT'):
        """
        Get all players in a specific tier and above.
        
        :param tier: Starting tier (e.g., 'EMERALD')
        :param region: Region of the players
        :param division: Division of the players (default is 'I')
        :param queue: Queue type (default is 'RANKED_TFT')
        :return: List of all players in the tier and above
        """
        tier = tier.upper()
        tiers = ['BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER']
        divisions = ['I', 'II', 'III', 'IV']
        
        if tier not in tiers:
            raise ValueError(f"Invalid tier. Must be one of: {', '.join(tiers)}")
        if division not in divisions:
            raise ValueError(f"Invalid division. Must be one of: {', '.join(divisions)}")
        
        tier_index = tiers.index(tier)
        div_index = divisions.index(division) if tier not in ['MASTER', 'GRANDMASTER', 'CHALLENGER'] else 0
        
        players_list = []
        
        for t in tiers[tier_index:]:
            if t in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
                high_tier_data = self.get_players_list(region=region, tier=t.lower(), queue=queue)
                players_list.extend(high_tier_data['entries'])
                print(f"Retrieved players for tier: {t.lower()}")
            else:
                # For lower tiers, get all divisions from current up to I
                start_div = div_index if t == tier else 3  # Start from IV for subsequent tiers
                for div_idx in range(start_div, -1, -1):
                    players_list.extend(self.get_players_list(
                        region=region, tier=t.lower(), division=divisions[div_idx], queue=queue
                    ))
                    print(f"Retrieved players for tier: {t} division: {divisions[div_idx]}")
                
        return players_list

    def get_matches_tier_and_above(self, tier, region_matches='sea', region_players='sg2', division='I', queue='RANKED_TFT'):
        """
        Get match IDs for all players in a specific tier and above.
        
        :param tier: Starting tier (e.g., 'EMERALD')
        :param region_matches: Region for match data (e.g., 'sea')
        :param region_players: Region for player rankings (e.g., 'sg2')
        :param division: Division of the players (default is 'I')
        :param queue: Queue type (default is 'RANKED_TFT')
        :return: List of unique match IDs
        """
        players_list = self.get_players_tier_and_above(
            tier=tier, region=region_players, division=division, queue=queue
        )
        
        match_ids = []
        for player in players_list:
            puuid = player['puuid']
            try:
                player_match_ids = self.get_last_match_ids(puuid=puuid, region=region_matches)
                match_ids.extend(player_match_ids)
            except Exception as e:
                print(f"Error getting matches for player {puuid}: {e}")
                continue
        
        # Remove duplicates
        return list(set(match_ids))


# Set detection logic removed - use manual timestamp instead


# Set detection data loading removed - use manual timestamp instead


def initialize_global_tracker_from_existing_data(jsonl_files=None):
    """
    Initialize the global match tracker from existing JSONL files.
    Useful for first-time setup to avoid re-downloading existing matches.
    
    :param jsonl_files: List of JSONL files to scan, or None for auto-detection
    :return: Number of matches added to tracker
    """
    if jsonl_files is None:
        # Auto-detect common JSONL files
        jsonl_files = []
        for filename in ['matches.jsonl', 'matches_set15.jsonl', 'matches_set14.jsonl']:
            if os.path.exists(filename):
                jsonl_files.append(filename)
    
    if not jsonl_files:
        print("No existing JSONL files found to initialize tracker from.")
        return 0
    
    print(f"Initializing global match tracker from existing data...")
    global_tracker = GlobalMatchTracker()
    initial_count = len(global_tracker.downloaded_matches)
    
    total_scanned = 0
    for jsonl_file in jsonl_files:
        print(f"   Scanning {jsonl_file}...")
        file_matches = set()
        
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            match = json.loads(line.strip())
                            match_id = match['metadata']['match_id']
                            file_matches.add(match_id)
                        except (KeyError, json.JSONDecodeError) as e:
                            print(f"     Warning: Invalid match data at line {line_num}: {e}")
                            continue
            
            print(f"     Found {len(file_matches)} matches in {jsonl_file}")
            global_tracker.mark_downloaded(list(file_matches))
            total_scanned += len(file_matches)
            
        except Exception as e:
            print(f"     Error reading {jsonl_file}: {e}")
            continue
    
    # Save the updated tracker
    global_tracker.save_tracker()
    
    new_matches_added = len(global_tracker.downloaded_matches) - initial_count
    print(f"\nGlobal tracker initialization complete:")
    print(f"   Files scanned: {len(jsonl_files)}")
    print(f"   Total matches scanned: {total_scanned}")
    print(f"   New matches added to tracker: {new_matches_added}")
    print(f"   Total matches in tracker: {len(global_tracker.downloaded_matches)}")
    
    return new_matches_added


class GlobalMatchTracker:
    """Global tracker for all downloaded matches to prevent duplicates across all sessions."""
    
    def __init__(self, tracker_file='global_matches_downloaded.json', use_database=USE_DATABASE):
        self.tracker_file = tracker_file
        self.use_database = use_database and DATABASE_AVAILABLE
        self.downloaded_matches = set()
        self.db_importer = None
        
        if self.use_database:
            try:
                self.db_importer = MatchDataImporter()
                print("   Using database for match tracking")
            except Exception as e:
                print(f"   Warning: Could not initialize database tracker, falling back to file: {e}")
                self.use_database = False
        
        if not self.use_database:
            self.load_tracker()
    
    def load_tracker(self):
        """Load the global match tracker from file."""
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.downloaded_matches = set(data.get('downloaded_matches', []))
                print(f"   Loaded global match tracker: {len(self.downloaded_matches)} matches already downloaded")
            except Exception as e:
                print(f"   Warning: Could not load global match tracker: {e}")
                self.downloaded_matches = set()
    
    def save_tracker(self):
        """Save the global match tracker to file (if not using database)."""
        if not self.use_database:
            try:
                data = {
                    'downloaded_matches': list(self.downloaded_matches),
                    'last_updated': time.time(),
                    'total_matches': len(self.downloaded_matches)
                }
                with open(self.tracker_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"   Warning: Could not save global match tracker: {e}")
    
    def is_downloaded(self, match_id):
        """Check if a match has already been downloaded."""
        if self.use_database:
            try:
                return self.db_importer.check_match_exists(match_id)
            except Exception as e:
                print(f"   Warning: Database check failed, using local cache: {e}")
                return match_id in self.downloaded_matches
        else:
            return match_id in self.downloaded_matches
    
    def mark_downloaded(self, match_ids):
        """Mark matches as downloaded."""
        if isinstance(match_ids, str):
            match_ids = [match_ids]
        
        if self.use_database:
            # For database mode, matches are marked downloaded when inserted
            # This method is mainly for compatibility
            new_matches = [mid for mid in match_ids if mid not in self.downloaded_matches]
            self.downloaded_matches.update(new_matches)  # Keep local cache for session
            return len(new_matches)
        else:
            new_matches = [mid for mid in match_ids if mid not in self.downloaded_matches]
            self.downloaded_matches.update(new_matches)
            return len(new_matches)
    
    def get_stats(self):
        """Get statistics about downloaded matches."""
        if self.use_database:
            try:
                db_stats = self.db_importer.get_match_count()
                return {
                    'total_downloaded': db_stats,
                    'tracker_type': 'database',
                    'session_cache': len(self.downloaded_matches)
                }
            except Exception as e:
                print(f"   Warning: Could not get database stats: {e}")
                return {
                    'total_downloaded': len(self.downloaded_matches),
                    'tracker_type': 'file_fallback',
                    'error': str(e)
                }
        else:
            return {
                'total_downloaded': len(self.downloaded_matches),
                'tracker_type': 'file',
                'tracker_file': self.tracker_file
            }


class SetBasedCollectionProgress:
    """Tracks progress for set-based data collection with resume capability."""
    
    def __init__(self, progress_file, global_tracker=None, use_database=USE_DATABASE):
        self.progress_file = progress_file
        self.processed_players = set()
        self.processed_matches = set()  # Keep for session tracking
        self.total_players = 0
        self.start_time = time.time()
        self.matches_collected = 0
        self.matches_inserted = 0  # New: track successful database insertions
        self.matches_duplicate = 0  # New: track duplicates
        self.matches_errors = 0  # New: track errors
        self.use_database = use_database and DATABASE_AVAILABLE
        self.global_tracker = global_tracker or GlobalMatchTracker(use_database=use_database)
        
        # Database-specific tracking
        if self.use_database:
            self.db_importer = MatchDataImporter()
        
        self.load_progress()
    
    def load_progress(self):
        """Load existing progress if available."""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    self.processed_players = set(data.get('processed_players', []))
                    self.processed_matches = set(data.get('processed_matches', []))
                    self.matches_collected = data.get('matches_collected', 0)
                    print(f"   Resumed: {len(self.processed_players)} players processed, {self.matches_collected} matches collected")
            except Exception as e:
                print(f"   Warning: Could not load progress file: {e}")
    
    
    def add_processed_player(self, puuid):
        """Mark a player as processed."""
        self.processed_players.add(puuid)
    
    def add_processed_matches(self, match_ids):
        """Mark matches as processed and update global tracker."""
        # Update session tracking
        new_matches = [mid for mid in match_ids if mid not in self.processed_matches]
        self.processed_matches.update(new_matches)
        
        # Update global tracking
        global_new = self.global_tracker.mark_downloaded(match_ids)
        self.matches_collected += len(new_matches)
        
        return len(new_matches)
    
    def is_player_processed(self, puuid):
        """Check if player has been processed."""
        return puuid in self.processed_players
    
    def is_match_processed(self, match_id):
        """Check if match has been processed (checks both session and global)."""
        return match_id in self.processed_matches or self.global_tracker.is_downloaded(match_id)
    
    def is_match_downloaded_globally(self, match_id):
        """Check if match has been downloaded in any previous session."""
        return self.global_tracker.is_downloaded(match_id)
    
    def save_progress(self):
        """Save current progress to file and update global tracker."""
        try:
            data = {
                'processed_players': list(self.processed_players),
                'processed_matches': list(self.processed_matches),
                'matches_collected': self.matches_collected,
                'timestamp': time.time()
            }
            with open(self.progress_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Save global tracker
            self.global_tracker.save_tracker()
        except Exception as e:
            print(f"   Warning: Could not save progress: {e}")
    
    def store_matches_database(self, matches_data):
        """Store matches in database and return statistics."""
        if not self.use_database or not matches_data:
            return 0, 0, 0
        
        inserted = 0
        duplicates = 0
        errors = 0
        
        for match_data in matches_data:
            try:
                # Validate data before insertion if enabled
                if ENABLE_DB_VALIDATION:
                    is_valid, validation_errors = self.db_importer.validate_match_data(match_data)
                    if not is_valid:
                        print(f"     Validation failed: {', '.join(validation_errors)}")
                        errors += 1
                        continue
                
                # Insert match data
                success, message = self.db_importer.insert_match_data(match_data)
                
                if success:
                    inserted += 1
                elif "duplicate" in message.lower() or "already exists" in message.lower():
                    duplicates += 1
                else:
                    errors += 1
                    print(f"     Database error: {message}")
                    
            except Exception as e:
                errors += 1
                print(f"     Unexpected error storing match: {e}")
        
        # Update tracking statistics
        self.matches_inserted += inserted
        self.matches_duplicate += duplicates
        self.matches_errors += errors
        
        return inserted, duplicates, errors
    
    def print_progress(self):
        """Print current progress statistics."""
        elapsed = time.time() - self.start_time
        processed_count = len(self.processed_players)
        remaining = self.total_players - processed_count
        
        if processed_count > 0:
            rate = processed_count / elapsed * 60  # players per minute
            eta_minutes = remaining / rate if rate > 0 else 0
        else:
            rate = 0
            eta_minutes = 0
        
        if self.use_database:
            print(f"   Progress: {processed_count}/{self.total_players} players "
                  f"({processed_count/self.total_players*100:.1f}%) | "
                  f"DB: {self.matches_inserted} inserted, {self.matches_duplicate} duplicates, {self.matches_errors} errors | "
                  f"{rate:.1f} players/min | ETA: {eta_minutes:.0f}min")
        else:
            print(f"   Progress: {processed_count}/{self.total_players} players "
                  f"({processed_count/self.total_players*100:.1f}%) | "
                  f"{self.matches_collected} matches | "
                  f"{rate:.1f} players/min | "
                  f"ETA: {eta_minutes:.0f}min")


def collect_period_match_data(api_key, start_timestamp, tier='CHALLENGER', 
                                region_matches='sea', region_players='sg2',
                                output_file=None, batch_size=50, max_workers=5,
                                progress_file=None):
    """
    Collect all TFT match data from a specific timestamp from high-tier players.
    
    :param api_key: Riot Games API key
    :param start_timestamp: Start timestamp (epoch seconds)
    :param tier: Minimum tier to collect data from
    :param region_matches: Region for match data
    :param region_players: Region for player rankings
    :param output_file: Output JSONL file (auto-generated if None)
    :param batch_size: Number of matches to process in each batch
    :param max_workers: Number of concurrent workers
    :param progress_file: Progress tracking file (auto-generated if None)
    """
    if output_file is None:
        output_file = 'matches.jsonl'
    
    if progress_file is None:
        progress_file = 'progress_period.json'
    
    start_date = datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d')
    print(f"=== TFT PERIOD DATA COLLECTION ===")
    print(f"Target: {tier}+ players from {region_players}")
    print(f"Start date: {start_date}")
    print(f"Output: {output_file}")
    print(f"Progress: {progress_file}")
    
    client = RiotAPIClient(api_key)
    global_tracker = GlobalMatchTracker()
    progress = SetBasedCollectionProgress(progress_file, global_tracker)
    
    # Use the provided start timestamp
    period_start_timestamp = start_timestamp
    print(f"Using start timestamp: {start_timestamp} ({datetime.fromtimestamp(start_timestamp)})")
    
    # Step 2: Get player list
    print(f"\n=== COLLECTING PLAYER LIST ===")
    players_list = client.get_players_tier_and_above(
        tier=tier, region=region_players
    )
    progress.total_players = len(players_list)
    
    # Filter out already processed players
    remaining_players = [p for p in players_list if not progress.is_player_processed(p['puuid'])]
    
    print(f"Total players: {len(players_list)}")
    print(f"Remaining players: {len(remaining_players)}")
    
    if not remaining_players:
        print("All players already processed!")
        return True
    
    # Step 3: Collect matches for each player
    print(f"\n=== COLLECTING PERIOD MATCHES ===")
    current_time = int(time.time())
    
    for i, player in enumerate(remaining_players, 1):
        puuid = player['puuid']
        player_name = player.get('summonerName', f'Player_{i}')
        
        print(f"\nPlayer {i}/{len(remaining_players)}: {player_name}")
        
        try:
            # Get all matches for this player within the period timeframe
            player_match_ids = client.get_period_match_ids(
                puuid, region_matches, period_start_timestamp, current_time
            )
            
            print(f"   Found {len(player_match_ids)} matches in period timeframe")
            
            # Filter out already processed matches (including globally downloaded ones)
            session_new = [mid for mid in player_match_ids if not progress.is_match_processed(mid)]
            globally_downloaded = [mid for mid in player_match_ids if progress.is_match_downloaded_globally(mid)]
            
            print(f"   Already downloaded globally: {len(globally_downloaded)}")
            print(f"   New matches to collect: {len(session_new)}")
            
            new_match_ids = session_new
            
            if new_match_ids:
                # Process matches in batches
                for batch_start in range(0, len(new_match_ids), batch_size):
                    batch_ids = new_match_ids[batch_start:batch_start + batch_size]
                    
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_match = {
                            executor.submit(client.get_match_details, match_id, region_matches): match_id 
                            for match_id in batch_ids
                        }
                        
                        batch_details = []
                        valid_matches = []
                        
                        for future in as_completed(future_to_match):
                            try:
                                match_details = future.result()
                                match_id = future_to_match[future]
                                
                                # Add collection metadata
                                match_details['collection_info'] = {
                                    'start_timestamp': period_start_timestamp,
                                    'collection_timestamp': current_time
                                }
                                batch_details.append(match_details)
                                valid_matches.append(match_id)
                                    
                            except Exception as e:
                                match_id = future_to_match[future]
                                print(f"     Error fetching {match_id}: {e}")
                        
                        # Store batch data (database and/or file)
                        if batch_details:
                            inserted, duplicates, errors = store_matches_data(
                                batch_details, progress, output_file, USE_DATABASE
                            )
                            new_count = progress.add_processed_matches(valid_matches)
                            
                            if USE_DATABASE and DATABASE_AVAILABLE:
                                print(f"     Stored {len(batch_details)} matches: {inserted} inserted, {duplicates} duplicates, {errors} errors ({new_count} session new)")
                            else:
                                print(f"     Saved {len(batch_details)} valid matches ({new_count} new)")
            
            # Mark player as processed
            progress.add_processed_player(puuid)
            progress.save_progress()
            progress.print_progress()
            
        except Exception as e:
            print(f"   Error processing player {puuid}: {e}")
            continue
    
    # Final summary
    print(f"\n{'='*60}")
    print("PERIOD-BASED DATA COLLECTION COMPLETE")
    print(f"{'='*60}")
    print(f"Output file: {output_file}")
    print(f"Players processed: {len(progress.processed_players)}")
    print(f"Matches collected: {progress.matches_collected}")
    print(f"Collection timeframe: {datetime.fromtimestamp(period_start_timestamp)} to {datetime.now()}")
    
    # Clean up progress file on successful completion
    try:
        os.remove(progress_file)
        print(f"Progress file {progress_file} removed (collection complete)")
    except:
        pass
    
    return True


def append_to_jsonl(filename, matches):
    """
    Append matches to a JSONL file.
    
    :param filename: Path to the JSONL file
    :param matches: List of match dictionaries to append
    """
    with open(filename, 'a') as f:
        for match in matches:
            json.dump(match, f)
            f.write('\n')


def store_matches_data(matches, progress=None, output_file=None, use_database=USE_DATABASE):
    """
    Store matches data to database and/or JSONL file based on configuration.
    
    :param matches: List of match data dictionaries
    :param progress: SetBasedCollectionProgress instance for tracking
    :param output_file: JSONL output file (for backup/compatibility)
    :param use_database: Whether to use database storage
    :return: Tuple of (inserted, duplicates, errors)
    """
    inserted, duplicates, errors = 0, 0, 0
    
    if not matches:
        return inserted, duplicates, errors
    
    # Store in database if enabled
    if use_database and DATABASE_AVAILABLE:
        if progress and hasattr(progress, 'store_matches_database'):
            db_inserted, db_duplicates, db_errors = progress.store_matches_database(matches)
            inserted += db_inserted
            duplicates += db_duplicates
            errors += db_errors
        else:
            # Fallback: use direct database insertion
            try:
                importer = MatchDataImporter()
                for match_data in matches:
                    success, message = importer.insert_match_data(match_data)
                    if success:
                        inserted += 1
                    elif "duplicate" in message.lower() or "already exists" in message.lower():
                        duplicates += 1
                    else:
                        errors += 1
                        print(f"Database error: {message}")
            except Exception as e:
                print(f"Error in database storage: {e}")
                errors += len(matches)
    
    # Store in JSONL file if enabled (backup or fallback)
    if ENABLE_JSONL_BACKUP and output_file:
        try:
            append_to_jsonl(output_file, matches)
            print(f"     Also saved {len(matches)} matches to {output_file} as backup")
        except Exception as e:
            print(f"Warning: Could not save to JSONL backup: {e}")
    elif not use_database and output_file:
        # Fallback to JSONL if database is not available
        try:
            append_to_jsonl(output_file, matches)
            inserted = len(matches)  # Count as inserted for progress tracking
        except Exception as e:
            print(f"Error saving to JSONL: {e}")
            errors = len(matches)
    
    return inserted, duplicates, errors


def collect_match_data(api_key, tier='CHALLENGER', region_matches='sea', region_players='sg2', 
                      output_file='matches.jsonl', batch_size=50, max_workers=5):
    """
    Complete pipeline for collecting TFT match data from high-tier players.
    
    :param api_key: Riot Games API key
    :param tier: Minimum tier to collect data from
    :param region_matches: Region for match data
    :param region_players: Region for player rankings  
    :param output_file: Output JSONL file
    :param batch_size: Number of matches to process in each batch
    :param max_workers: Number of concurrent workers for match detail fetching
    """
    print(f"Starting TFT data collection for {tier}+ players...")
    
    # Initialize API client and global tracker
    client = RiotAPIClient(api_key)
    global_tracker = GlobalMatchTracker()
    
    # Get match IDs
    print("1. Collecting match IDs from high-tier players...")
    all_match_ids = client.get_matches_tier_and_above(
        tier=tier, 
        region_matches=region_matches, 
        region_players=region_players
    )
    print(f"   Found {len(all_match_ids)} unique matches")
    
    # Filter out already downloaded matches
    new_match_ids = [mid for mid in all_match_ids if not global_tracker.is_downloaded(mid)]
    already_downloaded = len(all_match_ids) - len(new_match_ids)
    
    print(f"   Already downloaded: {already_downloaded} matches")
    print(f"   New matches to collect: {len(new_match_ids)}")
    
    if not new_match_ids:
        print("   All matches already downloaded!")
        return
    
    match_ids = new_match_ids
    
    # Process matches in batches
    print(f"2. Fetching match details (batch size: {batch_size}, workers: {max_workers})...")
    total_batches = (len(match_ids) + batch_size - 1) // batch_size
    
    for batch_num, i in enumerate(range(0, len(match_ids), batch_size), 1):
        batch_ids = match_ids[i:i + batch_size]
        print(f"   Processing batch {batch_num}/{total_batches} ({len(batch_ids)} matches)")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_match = {
                executor.submit(client.get_match_details, match_id, region_matches): match_id 
                for match_id in batch_ids
            }
            
            batch_details = []
            for future in as_completed(future_to_match):
                try:
                    match_details = future.result()
                    batch_details.append(match_details)
                except Exception as e:
                    match_id = future_to_match[future]
                    print(f"     Error fetching details for match {match_id}: {e}")
        
        # Store batch data (database and/or file)
        if batch_details:
            inserted, duplicates, errors = store_matches_data(
                batch_details, None, output_file, USE_DATABASE
            )
            
            # Mark matches as downloaded
            successful_match_ids = [match['metadata']['match_id'] for match in batch_details]
            global_tracker.mark_downloaded(successful_match_ids)
            global_tracker.save_tracker()
            
            if USE_DATABASE and DATABASE_AVAILABLE:
                print(f"     Stored {len(batch_details)} matches: {inserted} inserted, {duplicates} duplicates, {errors} errors")
            else:
                print(f"     Saved {len(batch_details)} matches to {output_file}")
    
    print(f"\n{'='*60}")
    print("DATA COLLECTION COMPLETE")
    print(f"{'='*60}")
    print(f"Output file: {output_file}")
    print(f"Total matches collected: {len(match_ids)}")
    print("Ready for clustering and analysis!")


if __name__ == "__main__":
    print("TFT Data Collection System")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check API key
    if API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: Please set your API key in the API_KEY variable at the top of this file")
        exit(1)
    
    # Test database connection if enabled
    if USE_DATABASE and DATABASE_AVAILABLE:
        print("Testing database connection...")
        try:
            db_test = test_connection()
            if db_test['success']:
                print(f"  ✓ Database connected: {db_test['database_version']}")
                print(f"  ✓ Response time: {db_test['response_time_ms']}ms")
                
                # Get current database statistics
                from database.data_import import get_database_stats
                db_stats = get_database_stats()
                print(f"  ✓ Current database: {db_stats.get('matches', 0)} matches, {db_stats.get('participants', 0)} participants")
            else:
                print(f"  ✗ Database connection failed: {db_test.get('error', 'Unknown error')}")
                print("  ✗ Falling back to JSONL mode")
                USE_DATABASE = False
        except Exception as e:
            print(f"  ✗ Database test failed: {e}")
            print("  ✗ Falling back to JSONL mode")
            USE_DATABASE = False
        print()

    # Display current configuration
    print("Current Configuration:")
    print(f"  API Key: {'*' * (len(API_KEY) - 4) + API_KEY[-4:]}")
    print(f"  Tier: {TIER}")
    print(f"  Regions: {REGION_PLAYERS} (players), {REGION_MATCHES} (matches)")
    print(f"  Storage: {'PostgreSQL' if USE_DATABASE and DATABASE_AVAILABLE else 'JSONL'}")
    if USE_DATABASE and DATABASE_AVAILABLE:
        print(f"  Database batch size: {DB_BATCH_SIZE}")
        print(f"  Validation: {'Enabled' if ENABLE_DB_VALIDATION else 'Disabled'}")
        print(f"  JSONL backup: {'Enabled' if ENABLE_JSONL_BACKUP else 'Disabled'}")
    else:
        print(f"  Output file: {OUTPUT_FILE}")
    print(f"  API batch size: {BATCH_SIZE}, Workers: {MAX_WORKERS}")
    if INIT_TRACKER_ONLY:
        print(f"  Mode: Initialize tracker only")
    else:
        readable_time = datetime.fromtimestamp(START_TIMESTAMP).strftime('%Y-%m-%d %H:%M:%S')
        print(f"  Mode: Period-based collection from {readable_time}")
    print()
    
    # Special mode: Initialize global tracker
    if INIT_TRACKER_ONLY:
        print("Initializing global match tracker from existing data...")
        matches_added = initialize_global_tracker_from_existing_data()
        if matches_added > 0:
            print(f"\nSuccessfully initialized global tracker with {matches_added} matches")
        else:
            print("\nNo new matches added to tracker")
        exit(0)
    
    # Run period-based collection
    print(f"Starting period-based collection from timestamp {START_TIMESTAMP}")
    readable_time = datetime.fromtimestamp(START_TIMESTAMP).strftime('%Y-%m-%d %H:%M:%S')
    print(f"Start time: {readable_time}")
    
    # Use appropriate batch size for storage method
    effective_batch_size = DB_BATCH_SIZE if USE_DATABASE and DATABASE_AVAILABLE else BATCH_SIZE
    
    success = collect_period_match_data(
        api_key=API_KEY,
        start_timestamp=START_TIMESTAMP,
        tier=TIER,
        region_matches=REGION_MATCHES,
        region_players=REGION_PLAYERS,
        output_file=OUTPUT_FILE,
        batch_size=effective_batch_size,
        max_workers=MAX_WORKERS
    )
    
    print("\n" + "="*60)
    if success:
        print("DATA COLLECTION COMPLETE")
    else:
        print("DATA COLLECTION FAILED")
    print("="*60)
    # Display final statistics
    if USE_DATABASE and DATABASE_AVAILABLE:
        try:
            from database.data_import import get_database_stats
            final_stats = get_database_stats()
            print("Database statistics:")
            print(f"  - Total matches: {final_stats.get('matches', 0)}")
            print(f"  - Total participants: {final_stats.get('participants', 0)}")
            print(f"  - Total units: {final_stats.get('units', 0)}")
            print(f"  - Total traits: {final_stats.get('traits', 0)}")
            if final_stats.get('date_range', {}).get('latest'):
                print(f"  - Latest match: {final_stats['date_range']['latest']}")
        except Exception as e:
            print(f"Could not retrieve database statistics: {e}")
    
    print("Files generated:")
    if USE_DATABASE and DATABASE_AVAILABLE:
        print("  - PostgreSQL database: Match data stored in database")
    if ENABLE_JSONL_BACKUP and os.path.exists(OUTPUT_FILE):
        print(f"  - {OUTPUT_FILE}: JSONL backup")
    elif not USE_DATABASE and os.path.exists(OUTPUT_FILE):
        print(f"  - {OUTPUT_FILE}: Match data")
    if os.path.exists('global_matches_downloaded.json'):
        print("  - global_matches_downloaded.json: Global match tracking (fallback)")
    
    print("\nNext steps:")
    if USE_DATABASE and DATABASE_AVAILABLE:
        print("  - Explore data: Use Streamlit app or database queries")
        print("  - Run clustering: python clustering.py (may need database integration)")
        print("  - Analyze data: Connect to PostgreSQL with your favorite tools")
    else:
        print("  - Run clustering: python clustering.py")
        print("  - Run querying: python querying.py")
    print("\nTo change settings, edit the configuration variables at the top of this file.")