"""
Database Data Import Utilities

Provides utilities for importing TFT match data into PostgreSQL database,
including batch operations, validation, and transaction management.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
import json
from datetime import datetime

from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.dialects.postgresql import insert

from .connection import get_db_session, get_database_manager, retry_on_database_error

logger = logging.getLogger(__name__)


@dataclass
class ImportStats:
    """Statistics tracking for import operations."""
    matches_processed: int = 0
    matches_inserted: int = 0
    matches_duplicate: int = 0
    participants_inserted: int = 0
    participants_duplicate: int = 0
    units_inserted: int = 0
    traits_inserted: int = 0
    errors: int = 0
    start_time: float = 0
    end_time: float = 0
    
    @property
    def duration_seconds(self) -> float:
        """Get import duration in seconds."""
        return self.end_time - self.start_time if self.end_time > 0 else 0
    
    @property
    def matches_per_second(self) -> float:
        """Get matches processed per second."""
        duration = self.duration_seconds
        return self.matches_processed / duration if duration > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'matches_processed': self.matches_processed,
            'matches_inserted': self.matches_inserted,
            'matches_duplicate': self.matches_duplicate,
            'participants_inserted': self.participants_inserted,
            'participants_duplicate': self.participants_duplicate,
            'units_inserted': self.units_inserted,
            'traits_inserted': self.traits_inserted,
            'errors': self.errors,
            'duration_seconds': self.duration_seconds,
            'matches_per_second': round(self.matches_per_second, 2)
        }


class MatchDataImporter:
    """Handles importing TFT match data into PostgreSQL database."""
    
    def __init__(self):
        self.stats = ImportStats()
    
    def reset_stats(self):
        """Reset import statistics."""
        self.stats = ImportStats()
    
    @retry_on_database_error(max_retries=3, delay=2.0)
    def insert_match_data(self, match_json: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Insert a complete match record with all participants.
        
        Args:
            match_json: Complete match data from Riot API
            
        Returns:
            Tuple of (success, message)
        """
        try:
            with get_db_session() as session:
                # Extract match metadata
                metadata = match_json.get('metadata', {})
                info = match_json.get('info', {})
                
                match_id = metadata.get('match_id')
                if not match_id:
                    return False, "Missing match_id in metadata"
                
                # Check if match already exists
                existing_match = session.execute(
                    text("SELECT game_id FROM matches WHERE game_id = :match_id"),
                    {'match_id': match_id}
                ).fetchone()
                
                if existing_match:
                    return False, f"Match {match_id} already exists (duplicate)"
                
                # Parse match data
                match_data = self._parse_match_data(match_json)
                if not match_data:
                    return False, "Failed to parse match data"
                
                # Insert match record
                match_insert = text("""
                    INSERT INTO matches (game_id, game_datetime, game_length, game_version, 
                                       queue_id, queue_type, game_mode, set_core_name, set_mutator, region)
                    VALUES (:game_id, :game_datetime, :game_length, :game_version,
                           :queue_id, :queue_type, :game_mode, :set_core_name, :set_mutator, :region)
                    RETURNING match_id
                """)
                
                result = session.execute(match_insert, match_data).fetchone()
                db_match_id = result[0]
                
                # Insert participants
                participants_data = self._parse_participants_data(match_json, db_match_id)
                participants_inserted = 0
                units_inserted = 0
                traits_inserted = 0
                
                for participant_data in participants_data:
                    # Insert participant
                    participant_insert = text("""
                        INSERT INTO participants (match_id, puuid, summoner_name, summoner_level, profile_icon_id,
                                                placement, placement_type, level, last_round, players_eliminated,
                                                time_eliminated, total_damage_to_players, gold_left, augments,
                                                companion, traits_raw, units_raw)
                        VALUES (:match_id, :puuid, :summoner_name, :summoner_level, :profile_icon_id,
                               :placement, :placement_type, :level, :last_round, :players_eliminated,
                               :time_eliminated, :total_damage_to_players, :gold_left, :augments,
                               :companion, :traits_raw, :units_raw)
                        RETURNING participant_id
                    """)
                    
                    participant_result = session.execute(participant_insert, participant_data).fetchone()
                    participant_id = participant_result[0]
                    participants_inserted += 1
                    
                    # Insert normalized units
                    if participant_data.get('units_normalized'):
                        for unit_data in participant_data['units_normalized']:
                            unit_data['participant_id'] = participant_id
                            unit_insert = text("""
                                INSERT INTO participant_units (participant_id, character_id, unit_name, tier, rarity,
                                                             chosen, items, item_names, unit_traits)
                                VALUES (:participant_id, :character_id, :unit_name, :tier, :rarity,
                                       :chosen, :items, :item_names, :unit_traits)
                            """)
                            session.execute(unit_insert, unit_data)
                            units_inserted += 1
                    
                    # Insert normalized traits
                    if participant_data.get('traits_normalized'):
                        for trait_data in participant_data['traits_normalized']:
                            trait_data['participant_id'] = participant_id
                            trait_insert = text("""
                                INSERT INTO participant_traits (participant_id, trait_name, current_tier, num_units,
                                                              style, tier_current, tier_total)
                                VALUES (:participant_id, :trait_name, :current_tier, :num_units,
                                       :style, :tier_current, :tier_total)
                            """)
                            session.execute(trait_insert, trait_data)
                            traits_inserted += 1
                
                # Update statistics
                self.stats.matches_inserted += 1
                self.stats.participants_inserted += participants_inserted
                self.stats.units_inserted += units_inserted
                self.stats.traits_inserted += traits_inserted
                
                logger.debug(f"Successfully inserted match {match_id} with {participants_inserted} participants")
                return True, f"Match {match_id} inserted successfully"
                
        except IntegrityError as e:
            logger.warning(f"Duplicate or constraint violation for match {match_id}: {e}")
            self.stats.matches_duplicate += 1
            return False, f"Duplicate or constraint violation: {str(e)}"
        except Exception as e:
            logger.error(f"Error inserting match {match_id}: {e}")
            self.stats.errors += 1
            return False, f"Error inserting match: {str(e)}"
    
    def _parse_match_data(self, match_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse match data from API response."""
        try:
            metadata = match_json.get('metadata', {})
            info = match_json.get('info', {})
            
            # Map queue type names to enum values
            queue_type_map = {
                'Ranked TFT': 'ranked',
                'Normal TFT': 'normal',
                'Tutorial TFT': 'tutorial',
                'Double Up': 'double_up',
                'Hyper Roll': 'hyper_roll'
            }
            
            # Map game mode names
            game_mode_map = {
                'TFT': 'classic',
                'DoubleUp': 'double_up',
                'TFT_Tutorial': 'tutorial',
                'Hyper_Roll': 'hyper_roll'
            }
            
            queue_type = queue_type_map.get(info.get('queue_type', ''), 'normal')
            game_mode = game_mode_map.get(info.get('game_mode', ''), 'classic')
            
            # Parse datetime
            game_datetime = datetime.fromtimestamp(info.get('game_datetime', 0) / 1000)
            
            # Parse game length (convert from seconds to interval)
            game_length_seconds = info.get('game_length', 0)
            game_length = f"{game_length_seconds} seconds"
            
            # Extract TFT set information
            tft_set_data = info.get('tft_set_data', {})
            set_core_name = tft_set_data.get('set_core_name', 'Unknown')
            set_mutator = tft_set_data.get('mutator', '')
            
            return {
                'game_id': metadata.get('match_id'),
                'game_datetime': game_datetime,
                'game_length': game_length,
                'game_version': info.get('game_version', ''),
                'queue_id': info.get('queue_id', 0),
                'queue_type': queue_type,
                'game_mode': game_mode,
                'set_core_name': set_core_name,
                'set_mutator': set_mutator if set_mutator else None,
                'region': metadata.get('data_version', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Error parsing match data: {e}")
            return None
    
    def _parse_participants_data(self, match_json: Dict[str, Any], match_id: str) -> List[Dict[str, Any]]:
        """Parse participants data from API response."""
        participants = []
        
        try:
            participants_data = match_json.get('info', {}).get('participants', [])
            
            for participant in participants_data:
                # Map placement to enum type
                placement_map = {
                    1: 'first', 2: 'second', 3: 'third', 4: 'fourth',
                    5: 'fifth', 6: 'sixth', 7: 'seventh', 8: 'eighth'
                }
                
                placement = participant.get('placement', 8)
                placement_type = placement_map.get(placement, 'eighth')
                
                # Parse time eliminated (convert to interval)
                time_eliminated_seconds = participant.get('time_eliminated', 0)
                time_eliminated = f"{time_eliminated_seconds} seconds" if time_eliminated_seconds > 0 else None
                
                participant_data = {
                    'match_id': match_id,
                    'puuid': participant.get('puuid', ''),
                    'summoner_name': participant.get('summoner_name', ''),
                    'summoner_level': participant.get('summoner_level', 0),
                    'profile_icon_id': participant.get('profile_icon_id', 0),
                    'placement': placement,
                    'placement_type': placement_type,
                    'level': participant.get('level', 1),
                    'last_round': participant.get('last_round', 1),
                    'players_eliminated': participant.get('players_eliminated', 0),
                    'time_eliminated': time_eliminated,
                    'total_damage_to_players': participant.get('total_damage_to_players', 0),
                    'gold_left': participant.get('gold_left', 0),
                    'augments': json.dumps(participant.get('augments', [])),
                    'companion': json.dumps(participant.get('companion', {})),
                    'traits_raw': json.dumps(participant.get('traits', [])),
                    'units_raw': json.dumps(participant.get('units', []))
                }
                
                # Parse normalized units and traits
                participant_data['units_normalized'] = self._parse_units(participant.get('units', []))
                participant_data['traits_normalized'] = self._parse_traits(participant.get('traits', []))
                
                participants.append(participant_data)
                
        except Exception as e:
            logger.error(f"Error parsing participants data: {e}")
        
        return participants
    
    def _parse_units(self, units_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse and normalize units data."""
        normalized_units = []
        
        for unit in units_data:
            try:
                unit_data = {
                    'character_id': unit.get('character_id', ''),
                    'unit_name': unit.get('name', unit.get('character_id', '')),
                    'tier': unit.get('tier', 1),
                    'rarity': unit.get('rarity', 1),
                    'chosen': unit.get('chosen', False),
                    'items': json.dumps(unit.get('itemNames', [])),
                    'item_names': json.dumps(unit.get('itemNames', [])),
                    'unit_traits': json.dumps(unit.get('character_traits', []))
                }
                normalized_units.append(unit_data)
            except Exception as e:
                logger.warning(f"Error parsing unit data: {e}")
                continue
        
        return normalized_units
    
    def _parse_traits(self, traits_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse and normalize traits data."""
        normalized_traits = []
        
        for trait in traits_data:
            try:
                # Only include active traits
                if trait.get('tier_current', 0) > 0:
                    trait_data = {
                        'trait_name': trait.get('name', ''),
                        'current_tier': trait.get('tier_current', 0),
                        'num_units': trait.get('num_units', 0),
                        'style': trait.get('style', 0),
                        'tier_current': trait.get('tier_current', 0),
                        'tier_total': trait.get('tier_total', 0)
                    }
                    normalized_traits.append(trait_data)
            except Exception as e:
                logger.warning(f"Error parsing trait data: {e}")
                continue
        
        return normalized_traits
    
    def batch_insert_matches(self, matches_data: List[Dict[str, Any]], 
                           batch_size: int = 50) -> ImportStats:
        """
        Insert multiple matches in batches with transaction management.
        
        Args:
            matches_data: List of match data dictionaries
            batch_size: Number of matches to process per batch
            
        Returns:
            ImportStats with operation results
        """
        self.reset_stats()
        self.stats.start_time = time.time()
        
        logger.info(f"Starting batch import of {len(matches_data)} matches (batch size: {batch_size})")
        
        for i in range(0, len(matches_data), batch_size):
            batch = matches_data[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(matches_data) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} matches)")
            
            # Process batch with transaction management
            with self._batch_transaction_context():
                for match_data in batch:
                    self.stats.matches_processed += 1
                    success, message = self.insert_match_data(match_data)
                    
                    if success:
                        logger.debug(f"Match imported: {message}")
                    else:
                        logger.warning(f"Match import failed: {message}")
        
        self.stats.end_time = time.time()
        
        # Log final statistics
        logger.info("Batch import completed:")
        logger.info(f"  Matches processed: {self.stats.matches_processed}")
        logger.info(f"  Matches inserted: {self.stats.matches_inserted}")
        logger.info(f"  Duplicates skipped: {self.stats.matches_duplicate}")
        logger.info(f"  Errors: {self.stats.errors}")
        logger.info(f"  Duration: {self.stats.duration_seconds:.2f}s")
        logger.info(f"  Rate: {self.stats.matches_per_second:.2f} matches/sec")
        
        return self.stats
    
    @contextmanager
    def _batch_transaction_context(self):
        """Context manager for batch transaction handling."""
        try:
            yield
        except Exception as e:
            logger.error(f"Batch transaction failed: {e}")
            raise
    
    @retry_on_database_error()
    def check_match_exists(self, match_id: str) -> bool:
        """
        Check if a match already exists in the database.
        
        Args:
            match_id: Game ID to check
            
        Returns:
            True if match exists, False otherwise
        """
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("SELECT 1 FROM matches WHERE game_id = :match_id LIMIT 1"),
                    {'match_id': match_id}
                ).fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking match existence: {e}")
            return False
    
    @retry_on_database_error()
    def get_match_count(self) -> int:
        """Get total number of matches in database."""
        try:
            with get_db_session() as session:
                result = session.execute(text("SELECT COUNT(*) FROM matches")).fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting match count: {e}")
            return 0
    
    @retry_on_database_error()
    def get_recent_matches(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recently imported matches.
        
        Args:
            days: Number of days back to look
            limit: Maximum number of matches to return
            
        Returns:
            List of match information
        """
        try:
            with get_db_session() as session:
                query = text("""
                    SELECT game_id, game_datetime, set_core_name, queue_type,
                           (SELECT COUNT(*) FROM participants p WHERE p.match_id = m.match_id) as participant_count
                    FROM matches m
                    WHERE game_datetime >= NOW() - INTERVAL ':days days'
                    ORDER BY game_datetime DESC
                    LIMIT :limit
                """)
                
                results = session.execute(query, {'days': days, 'limit': limit}).fetchall()
                
                matches = []
                for row in results:
                    matches.append({
                        'game_id': row[0],
                        'game_datetime': row[1],
                        'set_core_name': row[2],
                        'queue_type': row[3],
                        'participant_count': row[4]
                    })
                
                return matches
                
        except Exception as e:
            logger.error(f"Error getting recent matches: {e}")
            return []
    
    def validate_match_data(self, match_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate match data before insertion.
        
        Args:
            match_json: Match data to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        if not match_json.get('metadata', {}).get('match_id'):
            errors.append("Missing match_id in metadata")
        
        info = match_json.get('info', {})
        if not info:
            errors.append("Missing info section")
            return False, errors
        
        # Check participants
        participants = info.get('participants', [])
        if not participants:
            errors.append("No participants found")
        elif len(participants) != 8:
            errors.append(f"Expected 8 participants, found {len(participants)}")
        
        # Validate each participant has required fields
        for i, participant in enumerate(participants):
            if not participant.get('puuid'):
                errors.append(f"Participant {i} missing puuid")
            
            placement = participant.get('placement')
            if placement is None or not (1 <= placement <= 8):
                errors.append(f"Participant {i} has invalid placement: {placement}")
        
        # Check for duplicate placements
        placements = [p.get('placement') for p in participants if p.get('placement')]
        if len(set(placements)) != len(placements):
            errors.append("Duplicate placements found")
        
        return len(errors) == 0, errors


# Convenience functions for common operations
def insert_match_data(match_json: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Insert a single match into the database.
    
    Args:
        match_json: Complete match data from Riot API
        
    Returns:
        Tuple of (success, message)
    """
    importer = MatchDataImporter()
    return importer.insert_match_data(match_json)


def batch_insert_matches(matches_data: List[Dict[str, Any]], 
                        batch_size: int = 50) -> ImportStats:
    """
    Insert multiple matches in batches.
    
    Args:
        matches_data: List of match data dictionaries
        batch_size: Number of matches to process per batch
        
    Returns:
        ImportStats with operation results
    """
    importer = MatchDataImporter()
    return importer.batch_insert_matches(matches_data, batch_size)


def check_match_exists(match_id: str) -> bool:
    """Check if a match exists in the database."""
    importer = MatchDataImporter()
    return importer.check_match_exists(match_id)


def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    importer = MatchDataImporter()
    
    try:
        with get_db_session() as session:
            # Get table counts
            matches_count = session.execute(text("SELECT COUNT(*) FROM matches")).scalar()
            participants_count = session.execute(text("SELECT COUNT(*) FROM participants")).scalar()
            units_count = session.execute(text("SELECT COUNT(*) FROM participant_units")).scalar()
            traits_count = session.execute(text("SELECT COUNT(*) FROM participant_traits")).scalar()
            
            # Get date range
            date_range = session.execute(text("""
                SELECT MIN(game_datetime) as earliest, MAX(game_datetime) as latest
                FROM matches
            """)).fetchone()
            
            # Get recent activity
            recent_matches = session.execute(text("""
                SELECT COUNT(*) FROM matches 
                WHERE game_datetime >= NOW() - INTERVAL '24 hours'
            """)).scalar()
            
            return {
                'matches': matches_count,
                'participants': participants_count,
                'units': units_count,
                'traits': traits_count,
                'date_range': {
                    'earliest': date_range[0] if date_range else None,
                    'latest': date_range[1] if date_range else None
                },
                'recent_matches_24h': recent_matches,
                'last_updated': datetime.now()
            }
            
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {'error': str(e)}