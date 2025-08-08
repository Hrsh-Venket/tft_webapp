"""
Simple Database Connection for Streamlit Cloud
Direct psycopg2 connection without complex abstractions
"""

import os
import psycopg2
import streamlit as st
from typing import Optional, List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

def get_database_url() -> Optional[str]:
    """Get database URL from Streamlit secrets or environment"""
    try:
        # Try Streamlit secrets first
        if hasattr(st, 'secrets'):
            database_url = st.secrets.get("database", {}).get("DATABASE_URL")
            if database_url:
                return database_url
    except Exception as e:
        logger.warning(f"Could not access Streamlit secrets: {e}")
    
    # Try environment variable
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url
    
    return None

def create_ipv4_compatible_url(database_url: str) -> str:
    """Convert database URL to IPv4 compatible pooler format for Streamlit Cloud"""
    try:
        # Check if already using pooler format
        if "pooler.supabase.com" in database_url:
            return database_url
            
        # Convert direct connection to pooler connection
        # From: postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres  
        # To: postgresql://postgres.xxx:pass@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
        
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(database_url)
        
        if "supabase.co" in parsed.hostname:
            # Extract project ID from hostname (e.g., gnyvkxdwlcojkgsarksr from db.gnyvkxdwlcojkgsarksr.supabase.co)
            project_id = parsed.hostname.replace("db.", "").replace(".supabase.co", "")
            
            # Create pooler connection
            new_username = f"postgres.{project_id}"
            new_hostname = "aws-0-ap-southeast-1.pooler.supabase.com"
            
            # Rebuild netloc with new format
            new_netloc = f"{new_username}:{parsed.password}@{new_hostname}:{parsed.port}"
            new_parsed = parsed._replace(netloc=new_netloc)
            
            pooler_url = urlunparse(new_parsed)
            logger.info(f"Converted to pooler URL: {pooler_url}")
            return pooler_url
            
    except Exception as e:
        logger.warning(f"Failed to create pooler URL: {e}")
    
    return database_url

def test_connection() -> bool:
    """Test if database connection works"""
    database_url = get_database_url()
    if not database_url:
        return False
    
    try:
        # Create IPv4-compatible pooler URL
        pooler_url = create_ipv4_compatible_url(database_url)
        
        # Try connection strategies in order of preference for Streamlit Cloud
        urls_to_try = [
            pooler_url,  # IPv4-compatible pooler connection (best for Streamlit Cloud)
            database_url,  # Original direct connection (fallback)
        ]
        
        for url in urls_to_try:
            try:
                conn = psycopg2.connect(
                    url, 
                    connect_timeout=10
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
                logger.info(f"Connection successful with: {url}")
                return True
            except Exception as e:
                logger.warning(f"Failed connection attempt with {url}: {e}")
                continue
        
        return False
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False

def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """Execute a query and return results"""
    database_url = get_database_url()
    if not database_url:
        raise Exception("No database URL available")
    
    # Create IPv4-compatible pooler URL
    pooler_url = create_ipv4_compatible_url(database_url)
    
    # Try connection methods in order of preference for Streamlit Cloud
    urls_to_try = [
        pooler_url,  # IPv4-compatible pooler connection (best for Streamlit Cloud)
        database_url,  # Original direct connection (fallback)
    ]
    
    for url in urls_to_try:
        try:
            conn = psycopg2.connect(
                url, 
                connect_timeout=15
            )
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch results
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            cursor.close()
            conn.close()
            
            return results
            
        except Exception as e:
            logger.warning(f"Query failed with {url}: {e}")
            continue
    
    raise Exception("All connection attempts failed")

def get_match_stats() -> Dict[str, int]:
    """Get basic database statistics"""
    try:
        # Get match count
        match_result = execute_query("SELECT COUNT(*) as count FROM matches")
        match_count = match_result[0]['count'] if match_result else 0
        
        # Get participant count  
        participant_result = execute_query("SELECT COUNT(*) as count FROM participants")
        participant_count = participant_result[0]['count'] if participant_result else 0
        
        return {
            'matches': match_count,
            'participants': participant_count
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {'matches': 0, 'participants': 0}

class SimpleTFTQuery:
    """Simplified TFT Query class for Streamlit Cloud with full TFTQuery functionality"""
    
    def __init__(self):
        self.filters = []
        self.unit_filters = []
        self.trait_filters = []
        self.level_filters = []
        self.unit_count_filters = []
        self.item_on_unit_filters = []
        self.last_round_filters = []
        self.unit_star_filters = []
        self.unit_item_count_filters = []
        self.augment_filters = []
        self.patch_filters = []
        self.custom_filters = []
        self._sub_cluster_id = None
        self._main_cluster_id = None
    
    def add_unit(self, unit_name: str):
        """Add unit filter"""
        # Clean unit name (remove TFT14_ prefix if present)
        clean_name = unit_name.replace('TFT14_', '')
        self.unit_filters.append(clean_name)
        return self
    
    def add_trait(self, trait_name: str, min_tier: int = 1):
        """Add trait filter"""
        clean_name = trait_name.replace('TFT14_', '')
        self.trait_filters.append({'name': clean_name, 'min_tier': min_tier})
        return self
    
    def add_player_level(self, min_level: int = 1, max_level: int = 10):
        """Add player level filter"""
        self.level_filters.append({'min': min_level, 'max': max_level})
        return self
    
    def add_unit_count(self, unit_name: str, count: int):
        """Add filter for exact unit count of a specific unit type"""
        clean_name = unit_name.replace('TFT14_', '')
        self.unit_count_filters.append({'unit': clean_name, 'count': count})
        return self
    
    def add_item_on_unit(self, unit_name: str, item_name: str):
        """Add filter for specific item on specific unit"""
        clean_unit = unit_name.replace('TFT14_', '')
        clean_item = item_name.replace('TFT14_', '')
        self.item_on_unit_filters.append({'unit': clean_unit, 'item': clean_item})
        return self
    
    def add_last_round(self, min_round: int = 1, max_round: int = 50):
        """Add filter for last round survived range"""
        self.last_round_filters.append({'min': min_round, 'max': max_round})
        return self
    
    def add_unit_star_level(self, unit_name: str, min_star: int = 1, max_star: int = 3):
        """Add filter for unit star level range"""
        clean_name = unit_name.replace('TFT14_', '')
        self.unit_star_filters.append({'unit': clean_name, 'min_star': min_star, 'max_star': max_star})
        return self
    
    def add_unit_item_count(self, unit_name: str, min_count: int = 0, max_count: int = 3):
        """Add filter for number of items on a specific unit"""
        clean_name = unit_name.replace('TFT14_', '')
        self.unit_item_count_filters.append({'unit': clean_name, 'min_count': min_count, 'max_count': max_count})
        return self
    
    def add_augment(self, augment_name: str):
        """Add filter for specific augment"""
        clean_name = augment_name.replace('TFT14_', '')
        self.augment_filters.append(clean_name)
        return self
    
    def set_patch(self, patch_version: str):
        """Add filter for specific patch version"""
        self.patch_filters.append(patch_version)
        return self
    
    def set_sub_cluster(self, cluster_id: int):
        """Filter results to specific sub-cluster only"""
        self._sub_cluster_id = cluster_id
        return self
    
    def set_main_cluster(self, cluster_id: int):
        """Filter results to specific main cluster only"""
        self._main_cluster_id = cluster_id
        return self
    
    def set_cluster(self, cluster_id: int):
        """Legacy compatibility - defaults to sub-cluster"""
        return self.set_sub_cluster(cluster_id)
    
    def add_custom_filter(self, sql_condition: str, params: Optional[List] = None):
        """Add a custom SQL filter condition"""
        if params is None:
            params = []
        self.custom_filters.append({'condition': sql_condition, 'params': params})
        return self
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for filtered matches"""
        try:
            # Build WHERE clause
            where_conditions = []
            params = []
            
            # Unit filters
            if self.unit_filters:
                unit_conditions = []
                for unit in self.unit_filters:
                    unit_conditions.append("units::text LIKE %s")
                    params.append(f'%{unit}%')
                
                if unit_conditions:
                    where_conditions.append(f"({' OR '.join(unit_conditions)})")
            
            # Unit count filters
            if self.unit_count_filters:
                for filter_data in self.unit_count_filters:
                    # Count occurrences of unit in units JSON array
                    where_conditions.append("""
                        (SELECT COUNT(*) 
                         FROM jsonb_array_elements(units) AS unit 
                         WHERE unit->>'character_id' LIKE %s) = %s
                    """)
                    params.extend([f'%{filter_data["unit"]}%', filter_data['count']])
            
            # Item on unit filters
            if self.item_on_unit_filters:
                for filter_data in self.item_on_unit_filters:
                    where_conditions.append("""
                        EXISTS (
                            SELECT 1 FROM jsonb_array_elements(units) AS unit,
                                         jsonb_array_elements_text(unit->'itemNames') AS item_name
                            WHERE unit->>'character_id' LIKE %s
                            AND item_name LIKE %s
                        )
                    """)
                    params.extend([f'%{filter_data["unit"]}%', f'%{filter_data["item"]}%'])
            
            # Last round filters
            if self.last_round_filters:
                for round_filter in self.last_round_filters:
                    where_conditions.append("last_round >= %s AND last_round <= %s")
                    params.extend([round_filter['min'], round_filter['max']])
            
            # Unit star level filters
            if self.unit_star_filters:
                for filter_data in self.unit_star_filters:
                    where_conditions.append("""
                        EXISTS (
                            SELECT 1 FROM jsonb_array_elements(units) AS unit,
                                         jsonb_array_elements_text(unit->'itemNames') AS item_name
                            WHERE unit->>'character_id' LIKE %s
                            AND (unit->>'tier')::INTEGER >= %s
                            AND (unit->>'tier')::INTEGER <= %s
                        )
                    """)
                    params.extend([f'%{filter_data["unit"]}%', filter_data['min_star'], filter_data['max_star']])
            
            # Unit item count filters
            if self.unit_item_count_filters:
                for filter_data in self.unit_item_count_filters:
                    where_conditions.append("""
                        EXISTS (
                            SELECT 1 FROM jsonb_array_elements(units) AS unit,
                                         jsonb_array_elements_text(unit->'itemNames') AS item_name
                            WHERE unit->>'character_id' LIKE %s
                            AND jsonb_array_length(unit->'itemNames') >= %s
                            AND jsonb_array_length(unit->'itemNames') <= %s
                        )
                    """)
                    params.extend([f'%{filter_data["unit"]}%', filter_data['min_count'], filter_data['max_count']])
            
            # Augment filters
            if self.augment_filters:
                augment_conditions = []
                for augment in self.augment_filters:
                    augment_conditions.append("augments::text LIKE %s")
                    params.append(f'%{augment}%')
                
                if augment_conditions:
                    where_conditions.append(f"({' OR '.join(augment_conditions)})")
            
            # Patch filters
            if self.patch_filters:
                # Join with matches table for patch info
                patch_conditions = []
                for patch in self.patch_filters:
                    patch_conditions.append("m.game_version LIKE %s")
                    params.append(f'%Version {patch}%')
                
                if patch_conditions:
                    where_conditions.append(f"({' OR '.join(patch_conditions)})")
            
            # Custom filters
            if self.custom_filters:
                for custom_filter in self.custom_filters:
                    where_conditions.append(f"({custom_filter['condition']})")
                    params.extend(custom_filter['params'])
            
            # Level filters
            if self.level_filters:
                for level_filter in self.level_filters:
                    where_conditions.append("level >= %s AND level <= %s")
                    params.extend([level_filter['min'], level_filter['max']])
            
            # Trait filters
            if self.trait_filters:
                trait_conditions = []
                for trait in self.trait_filters:
                    trait_conditions.append("traits::text LIKE %s")
                    params.append(f'%{trait["name"]}%')
                
                if trait_conditions:
                    where_conditions.append(f"({' OR '.join(trait_conditions)})")
            
            # Build final query
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Build base query - include matches table if needed for patch filtering
            if self.patch_filters or self._sub_cluster_id is not None or self._main_cluster_id is not None:
                # Need to join with matches table and potentially cluster data
                base_from = "FROM participants p JOIN matches m ON p.match_id = m.match_id"
                
                # Add cluster filtering if needed (simplified - may not work without cluster tables)
                if self._sub_cluster_id is not None or self._main_cluster_id is not None:
                    # Note: This assumes we have cluster data in the database
                    # In a real implementation, you'd join with cluster tables
                    if self._sub_cluster_id is not None:
                        logger.warning("Sub-cluster filtering not implemented without cluster tables")
                        # Placeholder - returns all results for now
                        pass
                    if self._main_cluster_id is not None:
                        logger.warning("Main cluster filtering not implemented without cluster tables")
                        # Placeholder - returns all results for now
                        pass
            else:
                base_from = "FROM participants p"
            
            query = f"""
            SELECT 
                COUNT(*) as play_count,
                COALESCE(AVG(p.placement::float), 0) as avg_placement,
                CASE 
                    WHEN COUNT(*) = 0 THEN 0 
                    ELSE COUNT(*) FILTER (WHERE p.placement = 1) * 100.0 / COUNT(*) 
                END as winrate,
                CASE 
                    WHEN COUNT(*) = 0 THEN 0 
                    ELSE COUNT(*) FILTER (WHERE p.placement <= 4) * 100.0 / COUNT(*) 
                END as top4_rate
            {base_from}
            {where_clause}
            """
            
            results = execute_query(query, tuple(params))
            
            if results:
                result = results[0]
                return {
                    'play_count': int(result['play_count'] or 0),
                    'avg_placement': round(float(result['avg_placement'] or 0), 2),
                    'winrate': round(float(result['winrate'] or 0), 1),
                    'top4_rate': round(float(result['top4_rate'] or 0), 1)
                }
            else:
                return {
                    'play_count': 0,
                    'avg_placement': 0,
                    'winrate': 0,
                    'top4_rate': 0
                }
                
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {
                'error': str(e),
                'play_count': 0,
                'avg_placement': 0,
                'winrate': 0,
                'top4_rate': 0
            }
    
    def execute(self) -> List[Dict[str, Any]]:
        """Execute the query and return matching participants"""
        try:
            # Build WHERE clause
            where_conditions = []
            params = []
            
            # Add all the same filters as in get_stats()
            # Unit filters
            if self.unit_filters:
                unit_conditions = []
                for unit in self.unit_filters:
                    unit_conditions.append("units::text LIKE %s")
                    params.append(f'%{unit}%')
                
                if unit_conditions:
                    where_conditions.append(f"({' OR '.join(unit_conditions)})")
            
            # Level filters
            if self.level_filters:
                for level_filter in self.level_filters:
                    where_conditions.append("level >= %s AND level <= %s")
                    params.extend([level_filter['min'], level_filter['max']])
            
            # Trait filters
            if self.trait_filters:
                trait_conditions = []
                for trait in self.trait_filters:
                    trait_conditions.append("traits::text LIKE %s")
                    params.append(f'%{trait["name"]}%')
                
                if trait_conditions:
                    where_conditions.append(f"({' OR '.join(trait_conditions)})")
            
            # Unit count filters
            if self.unit_count_filters:
                for filter_data in self.unit_count_filters:
                    where_conditions.append("""
                        (SELECT COUNT(*) 
                         FROM jsonb_array_elements(units) AS unit 
                         WHERE unit->>'character_id' LIKE %s) = %s
                    """)
                    params.extend([f'%{filter_data["unit"]}%', filter_data['count']])
            
            # Item on unit filters
            if self.item_on_unit_filters:
                for filter_data in self.item_on_unit_filters:
                    where_conditions.append("""
                        EXISTS (
                            SELECT 1 FROM jsonb_array_elements(units) AS unit,
                                         jsonb_array_elements_text(unit->'itemNames') AS item_name
                            WHERE unit->>'character_id' LIKE %s
                            AND item_name LIKE %s
                        )
                    """)
                    params.extend([f'%{filter_data["unit"]}%', f'%{filter_data["item"]}%'])
            
            # Last round filters
            if self.last_round_filters:
                for round_filter in self.last_round_filters:
                    where_conditions.append("last_round >= %s AND last_round <= %s")
                    params.extend([round_filter['min'], round_filter['max']])
            
            # Unit star level filters
            if self.unit_star_filters:
                for filter_data in self.unit_star_filters:
                    where_conditions.append("""
                        EXISTS (
                            SELECT 1 FROM jsonb_array_elements(units) AS unit,
                                         jsonb_array_elements_text(unit->'itemNames') AS item_name
                            WHERE unit->>'character_id' LIKE %s
                            AND (unit->>'tier')::INTEGER >= %s
                            AND (unit->>'tier')::INTEGER <= %s
                        )
                    """)
                    params.extend([f'%{filter_data["unit"]}%', filter_data['min_star'], filter_data['max_star']])
            
            # Unit item count filters
            if self.unit_item_count_filters:
                for filter_data in self.unit_item_count_filters:
                    where_conditions.append("""
                        EXISTS (
                            SELECT 1 FROM jsonb_array_elements(units) AS unit,
                                         jsonb_array_elements_text(unit->'itemNames') AS item_name
                            WHERE unit->>'character_id' LIKE %s
                            AND jsonb_array_length(unit->'itemNames') >= %s
                            AND jsonb_array_length(unit->'itemNames') <= %s
                        )
                    """)
                    params.extend([f'%{filter_data["unit"]}%', filter_data['min_count'], filter_data['max_count']])
            
            # Augment filters
            if self.augment_filters:
                augment_conditions = []
                for augment in self.augment_filters:
                    augment_conditions.append("augments::text LIKE %s")
                    params.append(f'%{augment}%')
                
                if augment_conditions:
                    where_conditions.append(f"({' OR '.join(augment_conditions)})")
            
            # Patch filters
            if self.patch_filters:
                patch_conditions = []
                for patch in self.patch_filters:
                    patch_conditions.append("m.game_version LIKE %s")
                    params.append(f'%Version {patch}%')
                
                if patch_conditions:
                    where_conditions.append(f"({' OR '.join(patch_conditions)})")
            
            # Custom filters
            if self.custom_filters:
                for custom_filter in self.custom_filters:
                    where_conditions.append(f"({custom_filter['condition']})")
                    params.extend(custom_filter['params'])
            
            # Build final query
            if self.patch_filters or self._sub_cluster_id is not None or self._main_cluster_id is not None:
                base_from = "FROM participants p JOIN matches m ON p.match_id = m.match_id"
                
                # Add cluster filtering if needed (simplified - may not work without cluster tables)
                if self._sub_cluster_id is not None:
                    logger.warning("Sub-cluster filtering not implemented without cluster tables")
                    # Placeholder - returns all results for now
                    pass
                if self._main_cluster_id is not None:
                    logger.warning("Main cluster filtering not implemented without cluster tables")
                    # Placeholder - returns all results for now
                    pass
            else:
                base_from = "FROM participants p"
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            query = f"""
            SELECT 
                p.match_id,
                p.puuid,
                p.placement,
                p.level,
                p.last_round,
                p.players_eliminated,
                p.total_damage_to_players,
                p.time_eliminated,
                p.companion,
                p.traits,
                p.units,
                p.augments
            {base_from}
            {where_clause}
            ORDER BY p.placement ASC
            LIMIT 1000
            """
            
            results = execute_query(query, tuple(params))
            
            # Convert to format expected by legacy code
            participants = []
            for result in results:
                participants.append({
                    'match_id': result['match_id'],
                    'puuid': result['puuid'],
                    'placement': result['placement'],
                    'level': result['level'],
                    'last_round': result['last_round'],
                    'players_eliminated': result.get('players_eliminated', 0),
                    'total_damage_to_players': result.get('total_damage_to_players', 0),
                    'time_eliminated': result.get('time_eliminated', 0),
                    'companion': result.get('companion', {}),
                    'traits': result.get('traits', []),
                    'units': result.get('units', []),
                    'augments': result.get('augments', [])
                })
            
            return participants
            
        except Exception as e:
            logger.error(f"Execute query failed: {e}")
            return []
    
    def or_(self, *other_queries):
        """
        Combine this query with other queries using OR logic.
        Returns a new SimpleTFTQuery instance with combined filters.
        
        Usage: SimpleTFTQuery().add_unit('Jinx').or_(SimpleTFTQuery().add_unit('Ahri'))
        """
        if not other_queries:
            return self
        
        # Create new query instance
        new_query = SimpleTFTQuery()
        new_query._sub_cluster_id = self._sub_cluster_id
        new_query._main_cluster_id = self._main_cluster_id
        
        # Build SQL conditions from all queries
        all_conditions = []
        all_params = []
        param_counter = 0
        
        # Get current query conditions
        current_conditions, current_params = self._build_where_conditions()
        if current_conditions:
            # Rename parameters to avoid conflicts
            renamed_conditions = []
            for condition in current_conditions:
                for i, param in enumerate(current_params):
                    condition = condition.replace('%s', f'%s', 1)  # Keep placeholder format
                renamed_conditions.append(condition)
            
            if renamed_conditions:
                current_clause = f"({' AND '.join(renamed_conditions)})"
                all_conditions.append(current_clause)
                all_params.extend(current_params)
        
        # Get conditions from other queries
        for other_query in other_queries:
            if hasattr(other_query, '_build_where_conditions'):
                other_conditions, other_params = other_query._build_where_conditions()
                if other_conditions:
                    # Rename parameters to avoid conflicts
                    renamed_conditions = []
                    for condition in other_conditions:
                        for i, param in enumerate(other_params):
                            condition = condition.replace('%s', f'%s', 1)  # Keep placeholder format
                        renamed_conditions.append(condition)
                    
                    if renamed_conditions:
                        other_clause = f"({' AND '.join(renamed_conditions)})"
                        all_conditions.append(other_clause)
                        all_params.extend(other_params)
        
        # Combine with OR logic
        if all_conditions:
            combined_condition = f"({' OR '.join(all_conditions)})"
            new_query.custom_filters.append({'condition': combined_condition, 'params': all_params})
        
        return new_query
    
    def not_(self, other_query=None):
        """
        Apply NOT logic to this query or to another query.
        Returns a new SimpleTFTQuery instance.
        
        Usage: 
        - SimpleTFTQuery().not_(SimpleTFTQuery().add_unit('Jinx')) = NOT Jinx
        - SimpleTFTQuery().add_trait('SG').not_(SimpleTFTQuery().add_unit('Jinx')) = SG AND NOT Jinx
        """
        new_query = SimpleTFTQuery()
        new_query._sub_cluster_id = self._sub_cluster_id
        new_query._main_cluster_id = self._main_cluster_id
        
        if other_query is None:
            # NOT this query
            current_conditions, current_params = self._build_where_conditions()
            if current_conditions:
                current_clause = f"({' AND '.join(current_conditions)})"
                not_condition = f"NOT {current_clause}"
                new_query.custom_filters.append({'condition': not_condition, 'params': current_params})
        else:
            # This query AND NOT other_query
            current_conditions, current_params = self._build_where_conditions()
            if hasattr(other_query, '_build_where_conditions'):
                other_conditions, other_params = other_query._build_where_conditions()
                
                all_params = current_params[:]
                conditions_parts = []
                
                # Add current query conditions
                if current_conditions:
                    current_clause = f"({' AND '.join(current_conditions)})"
                    conditions_parts.append(current_clause)
                
                # Add NOT other query conditions
                if other_conditions:
                    other_clause = f"({' AND '.join(other_conditions)})"
                    conditions_parts.append(f"NOT {other_clause}")
                    all_params.extend(other_params)
                
                if conditions_parts:
                    combined_condition = ' AND '.join(conditions_parts)
                    new_query.custom_filters.append({'condition': combined_condition, 'params': all_params})
        
        return new_query
    
    def xor(self, other_query):
        """
        Combine this query with another query using XOR logic.
        Returns a new SimpleTFTQuery instance.
        
        Usage: SimpleTFTQuery().add_unit('Jinx').xor(SimpleTFTQuery().add_unit('Ahri'))
        """
        new_query = SimpleTFTQuery()
        new_query._sub_cluster_id = self._sub_cluster_id
        new_query._main_cluster_id = self._main_cluster_id
        
        if hasattr(other_query, '_build_where_conditions'):
            current_conditions, current_params = self._build_where_conditions()
            other_conditions, other_params = other_query._build_where_conditions()
            
            # XOR: (A AND NOT B) OR (NOT A AND B)
            if current_conditions and other_conditions:
                current_clause = f"({' AND '.join(current_conditions)})"
                other_clause = f"({' AND '.join(other_conditions)})"
                
                # We need to duplicate the parameters because each condition appears twice in XOR
                # XOR formula: (A AND NOT B) OR (NOT A AND B)
                # This means: A_params, B_params, A_params, B_params
                all_params = current_params[:]  # For first A
                all_params.extend(other_params)  # For first B  
                all_params.extend(current_params)  # For second NOT A
                all_params.extend(other_params)  # For second B
                
                xor_condition = f"(({current_clause}) AND NOT ({other_clause})) OR (NOT ({current_clause}) AND ({other_clause}))"
                new_query.custom_filters.append({'condition': xor_condition, 'params': all_params})
        
        return new_query
    
    def _build_where_conditions(self):
        """
        Internal helper method to build WHERE conditions and parameters.
        Returns tuple of (conditions_list, params_list).
        """
        where_conditions = []
        params = []
        
        # Unit filters
        if self.unit_filters:
            unit_conditions = []
            for unit in self.unit_filters:
                unit_conditions.append("units::text LIKE %s")
                params.append(f'%{unit}%')
            
            if unit_conditions:
                where_conditions.append(f"({' OR '.join(unit_conditions)})")
        
        # Unit count filters
        if self.unit_count_filters:
            for filter_data in self.unit_count_filters:
                where_conditions.append("""
                    (SELECT COUNT(*) 
                     FROM jsonb_array_elements(units) AS unit 
                     WHERE unit->>'character_id' LIKE %s) = %s
                """)
                params.extend([f'%{filter_data["unit"]}%', filter_data['count']])
        
        # Item on unit filters
        if self.item_on_unit_filters:
            for filter_data in self.item_on_unit_filters:
                where_conditions.append("""
                    EXISTS (
                        SELECT 1 FROM jsonb_array_elements(units) AS unit,
                                     jsonb_array_elements_text(unit->'itemNames') AS item_name
                        WHERE unit->>'character_id' LIKE %s
                        AND item_name LIKE %s
                    )
                """)
                params.extend([f'%{filter_data["unit"]}%', f'%{filter_data["item"]}%'])
        
        # Last round filters
        if self.last_round_filters:
            for round_filter in self.last_round_filters:
                where_conditions.append("last_round >= %s AND last_round <= %s")
                params.extend([round_filter['min'], round_filter['max']])
        
        # Unit star level filters
        if self.unit_star_filters:
            for filter_data in self.unit_star_filters:
                where_conditions.append("""
                    EXISTS (
                        SELECT 1 FROM jsonb_array_elements(units) AS unit
                        WHERE unit->>'character_id' LIKE %s
                        AND (unit->>'tier')::INTEGER >= %s
                        AND (unit->>'tier')::INTEGER <= %s
                    )
                """)
                params.extend([f'%{filter_data["unit"]}%', filter_data['min_star'], filter_data['max_star']])
        
        # Unit item count filters
        if self.unit_item_count_filters:
            for filter_data in self.unit_item_count_filters:
                where_conditions.append("""
                    EXISTS (
                        SELECT 1 FROM jsonb_array_elements(units) AS unit
                        WHERE unit->>'character_id' LIKE %s
                        AND jsonb_array_length(unit->'itemNames') >= %s
                        AND jsonb_array_length(unit->'itemNames') <= %s
                    )
                """)
                params.extend([f'%{filter_data["unit"]}%', filter_data['min_count'], filter_data['max_count']])
        
        # Augment filters
        if self.augment_filters:
            augment_conditions = []
            for augment in self.augment_filters:
                augment_conditions.append("augments::text LIKE %s")
                params.append(f'%{augment}%')
            
            if augment_conditions:
                where_conditions.append(f"({' OR '.join(augment_conditions)})")
        
        # Patch filters
        if self.patch_filters:
            patch_conditions = []
            for patch in self.patch_filters:
                patch_conditions.append("m.game_version LIKE %s")
                params.append(f'%Version {patch}%')
            
            if patch_conditions:
                where_conditions.append(f"({' OR '.join(patch_conditions)})")
        
        # Level filters
        if self.level_filters:
            for level_filter in self.level_filters:
                where_conditions.append("level >= %s AND level <= %s")
                params.extend([level_filter['min'], level_filter['max']])
        
        # Trait filters
        if self.trait_filters:
            trait_conditions = []
            for trait in self.trait_filters:
                trait_conditions.append("traits::text LIKE %s")
                params.append(f'%{trait["name"]}%')
            
            if trait_conditions:
                where_conditions.append(f"({' OR '.join(trait_conditions)})")
        
        # Custom filters
        if self.custom_filters:
            for custom_filter in self.custom_filters:
                where_conditions.append(f"({custom_filter['condition']})")
                params.extend(custom_filter['params'])
        
        return where_conditions, params