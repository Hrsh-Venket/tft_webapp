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
                    connect_timeout=10,
                    options='-c default_transaction_isolation=read_committed'
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
                connect_timeout=15,
                options='-c default_transaction_isolation=read_committed'
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
    """Simplified TFT Query class for Streamlit Cloud"""
    
    def __init__(self):
        self.filters = []
        self.unit_filters = []
        self.trait_filters = []
        self.level_filters = []
    
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for filtered matches"""
        try:
            # Build WHERE clause
            where_conditions = []
            params = []
            param_counter = 1
            
            # Unit filters
            if self.unit_filters:
                unit_conditions = []
                for unit in self.unit_filters:
                    unit_conditions.append(f"units::text LIKE ${param_counter}")
                    params.append(f'%{unit}%')
                    param_counter += 1
                
                if unit_conditions:
                    where_conditions.append(f"({' OR '.join(unit_conditions)})")
            
            # Level filters
            if self.level_filters:
                for level_filter in self.level_filters:
                    where_conditions.append(f"level >= ${param_counter} AND level <= ${param_counter + 1}")
                    params.extend([level_filter['min'], level_filter['max']])
                    param_counter += 2
            
            # Trait filters
            if self.trait_filters:
                trait_conditions = []
                for trait in self.trait_filters:
                    trait_conditions.append(f"traits::text LIKE ${param_counter}")
                    params.append(f'%{trait["name"]}%')
                    param_counter += 1
                
                if trait_conditions:
                    where_conditions.append(f"({' OR '.join(trait_conditions)})")
            
            # Build final query
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            query = f"""
            SELECT 
                COUNT(*) as play_count,
                AVG(placement::float) as avg_placement,
                COUNT(*) FILTER (WHERE placement = 1) * 100.0 / COUNT(*) as winrate,
                COUNT(*) FILTER (WHERE placement <= 4) * 100.0 / COUNT(*) as top4_rate
            FROM participants 
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