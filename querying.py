"""
TFT Composition Querying Module

This module provides flexible querying capabilities for TFT match data with clustering integration.
Supports logical operations (AND, OR, XOR, NOT) and statistical analysis.

Updated to support both PostgreSQL database operations and legacy file-based operations.
"""

import json
import csv
import logging
from collections import defaultdict
from typing import Optional, List, Dict, Any, Callable, Union
from contextlib import contextmanager
import uuid

logger = logging.getLogger(__name__)

# Database imports
try:
    from database.connection import get_db_session, execute_query, DatabaseError
    from database.config import get_database_config
    import sqlalchemy as sa
    from sqlalchemy import text
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False

# Legacy file-based imports
try:
    from clustering import query_jsonl
    HAS_FILE_SUPPORT = True
except ImportError:
    # Create a minimal query_jsonl function if clustering module is not available
    def query_jsonl(filename, filter_func=None):
        """Minimal JSONL query function for when clustering module is unavailable."""
        import json
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        match = json.loads(line.strip())
                        if filter_func is None or filter_func(match):
                            yield match
        except FileNotFoundError:
            # Return empty generator if file not found
            return
            yield  # Make this a generator function
    
    HAS_FILE_SUPPORT = True  # We now have basic file support
    logger.info("Using minimal JSONL query functionality (clustering module unavailable)")


def load_clusters(csv_filename='hierarchical_clusters.csv'):
    """
    Load hierarchical cluster assignments from CSV file.
    
    :param csv_filename: Path to the hierarchical clusters CSV file
    :return: Dictionary mapping (match_id, puuid) to {'sub_cluster_id', 'main_cluster_id'}
    """
    clusters = {}
    try:
        with open(csv_filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row['match_id'], row['puuid'])
                clusters[key] = {
                    'sub_cluster_id': int(row['sub_cluster_id']) if row['sub_cluster_id'] != '-1' else -1,
                    'main_cluster_id': int(row['main_cluster_id']) if row['main_cluster_id'] != '-1' else -1
                }
    except FileNotFoundError:
        print(f"Warning: Cluster file {csv_filename} not found. Cluster functionality disabled.")
        # Try legacy format
        return load_legacy_clusters(csv_filename.replace('hierarchical_', ''))
    return clusters


def load_legacy_clusters(csv_filename='clusters.csv'):
    """Load legacy cluster format for backward compatibility."""
    clusters = {}
    try:
        with open(csv_filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row['match_id'], row['puuid'])
                clusters[key] = {
                    'sub_cluster_id': int(row['cluster_id']) if row['cluster_id'] != '-1' else -1,
                    'main_cluster_id': -1
                }
    except FileNotFoundError:
        print(f"Warning: Neither hierarchical nor legacy cluster file found.")
    return clusters

def query_participants(filter_func, jsonl_filename='matches_filtered.jsonl', csv_filename='hierarchical_clusters.csv'):
    """
    Query participants from match data with hierarchical cluster information.
    
    :param filter_func: Function that takes (participant, cluster_data, match) and returns bool
                       cluster_data is dict with 'sub_cluster_id', 'main_cluster_id'
    :param jsonl_filename: Path to the JSONL match data file
    :param csv_filename: Path to the hierarchical clusters CSV file (optional)
    :return: List of matching participants
    """
    clusters = load_clusters(csv_filename) if csv_filename else {}
    results = []
    for match in query_jsonl(jsonl_filename):
        match_id = match['metadata']['match_id']
        for participant in match['info']['participants']:
            puuid = participant['puuid']
            cluster_data = clusters.get((match_id, puuid), {
                'sub_cluster_id': -1, 
                'main_cluster_id': -1
            })
            if filter_func(participant, cluster_data, match):
                results.append(participant)
    return results

def get_compositions_in_cluster(cluster_id, jsonl_filename, csv_filename='hierarchical_clusters.csv', cluster_type='sub'):
    """
    Get all compositions in a specific cluster (sub-cluster or main cluster).
    
    :param cluster_id: ID of the cluster to retrieve
    :param jsonl_filename: Path to the JSONL match data file
    :param csv_filename: Path to the hierarchical clusters CSV file
    :param cluster_type: 'sub' for sub-clusters, 'main' for main clusters
    :return: List of participant data for the cluster
    """
    wanted = set()
    cluster_field = 'sub_cluster_id' if cluster_type == 'sub' else 'main_cluster_id'
    
    try:
        with open(csv_filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row[cluster_field]) == cluster_id:
                    wanted.add((row['match_id'], row['puuid']))
    except FileNotFoundError:
        # Try legacy format
        return get_compositions_in_legacy_cluster(cluster_id, jsonl_filename, csv_filename.replace('hierarchical_', ''))
    
    results = []
    with open(jsonl_filename, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            match = json.loads(line)
            match_id = match['metadata']['match_id']
            for participant in match['info']['participants']:
                puuid = participant['puuid']
                if (match_id, puuid) in wanted:
                    results.append(participant)
                    wanted.discard((match_id, puuid))
                    if not wanted:
                        return results
    return results


def get_compositions_in_legacy_cluster(cluster_id, jsonl_filename, csv_filename='clusters.csv'):
    """Legacy function for backward compatibility."""
    wanted = set()
    try:
        with open(csv_filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row['cluster_id']) == cluster_id:
                    wanted.add((row['match_id'], row['puuid']))
    except FileNotFoundError:
        return []
    
    results = []
    with open(jsonl_filename, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            match = json.loads(line)
            match_id = match['metadata']['match_id']
            for participant in match['info']['participants']:
                puuid = participant['puuid']
                if (match_id, puuid) in wanted:
                    results.append(participant)
                    wanted.discard((match_id, puuid))
                    if not wanted:
                        return results
    return results

class LogicalFilter:
    """Helper class for building logical operations with filters"""
    def __init__(self, filter_func):
        self.filter_func = filter_func
    
    def __call__(self, p, c, m):
        return self.filter_func(p, c, m)
    
    def __and__(self, other):
        return LogicalFilter(lambda p, c, m: self.filter_func(p, c, m) and other.filter_func(p, c, m))
    
    def __or__(self, other):
        return LogicalFilter(lambda p, c, m: self.filter_func(p, c, m) or other.filter_func(p, c, m))
    
    def __xor__(self, other):
        return LogicalFilter(lambda p, c, m: self.filter_func(p, c, m) ^ other.filter_func(p, c, m))
    
    def __invert__(self):
        return LogicalFilter(lambda p, c, m: not self.filter_func(p, c, m))


class TFTQueryLegacy:
    """
    Flexible query builder for TFT composition analysis with logical operations support.
    """
    
    def __init__(self, jsonl_filename='matches_filtered.jsonl', csv_filename='hierarchical_clusters.csv'):
        self.jsonl_filename = jsonl_filename
        self.csv_filename = csv_filename
        self._sub_cluster_id = None
        self._main_cluster_id = None
        self._filters = []

    def set_sub_cluster(self, cluster_id):
        """Filter results to specific sub-cluster only."""
        self._sub_cluster_id = cluster_id
        return self
    
    def set_main_cluster(self, cluster_id):
        """Filter results to specific main cluster only."""
        self._main_cluster_id = cluster_id  
        return self
    
    def set_cluster(self, cluster_id):
        """Legacy compatibility - defaults to sub-cluster."""
        return self.set_sub_cluster(cluster_id)

    def add_unit(self, unit_id, must_have=True):
        """Add filter for presence/absence of a specific unit."""
        def filter_func(p, c, m):
            units = [u['character_id'] for u in p['units']]
            return (unit_id in units) == must_have
        self._filters.append(LogicalFilter(filter_func))
        return self
    
    def add_unit_count(self, unit_id, count):
        """Add filter for exact unit count of a specific unit type."""
        def filter_func(p, c, m):
            unit_count = sum(1 for u in p['units'] if u['character_id'] == unit_id)
            return unit_count == count
        self._filters.append(LogicalFilter(filter_func))
        return self

    def add_item_on_unit(self, unit_id, item_id):
        """Add filter for specific item on specific unit."""
        def filter_func(p, c, m):
            return any(u['character_id'] == unit_id and item_id in u['itemNames'] for u in p['units'])
        self._filters.append(LogicalFilter(filter_func))
        return self
    
    def add_trait(self, trait_name, min_tier=1, max_tier=4):
        """Add filter for trait activation level."""
        def filter_func(p, c, m):
            return any(t['name'] == trait_name and min_tier <= t['tier_current'] <= max_tier for t in p['traits'])
        self._filters.append(LogicalFilter(filter_func))
        return self

    def add_player_level(self, min_level=1, max_level=10):
        """Add filter for player level range."""
        def filter_func(p, c, m):
            return min_level <= p['level'] <= max_level
        self._filters.append(LogicalFilter(filter_func))
        return self

    def add_last_round(self, min_round=1, max_round=50):
        """Add filter for last round survived range."""
        def filter_func(p, c, m):
            return min_round <= p['last_round'] <= max_round
        self._filters.append(LogicalFilter(filter_func))
        return self

    def add_unit_star_level(self, unit_id, min_star=1, max_star=3):
        """Add filter for unit star level range."""
        def filter_func(p, c, m):
            return any(u['character_id'] == unit_id and min_star <= u['tier'] <= max_star for u in p['units'])
        self._filters.append(LogicalFilter(filter_func))
        return self

    def add_unit_item_count(self, unit_id, min_count=0, max_count=3):
        """Add filter for number of items on a specific unit."""
        def filter_func(p, c, m):
            return any(u['character_id'] == unit_id and min_count <= len(u['itemNames']) <= max_count for u in p['units'])
        self._filters.append(LogicalFilter(filter_func))
        return self

    def add_augment(self, augment_id):
        """Add filter for specific augment."""
        def filter_func(p, c, m):
            return augment_id in p['augments']
        self._filters.append(LogicalFilter(filter_func))
        return self

    def set_patch(self, patch_version):
        """Add filter for specific patch version."""
        def filter_func(p, c, m):
            return m['info']['game_version'].startswith(f'Version {patch_version}')
        self._filters.append(LogicalFilter(filter_func))
        return self
    
    def add_custom_filter(self, filter_func):
        """Add a custom filter function that takes (participant, cluster_id, match) and returns bool."""
        self._filters.append(LogicalFilter(filter_func))
        return self
    
    def add_or_group(self, *conditions):
        """Add multiple conditions combined with OR logic."""
        if not conditions:
            return self
        
        def or_filter(p, c, m):
            return any(cond(p, c, m) for cond in conditions)
        
        self._filters.append(LogicalFilter(or_filter))
        return self
    
    def add_xor_group(self, *conditions):
        """Add multiple conditions combined with XOR logic."""
        if not conditions:
            return self
        
        def xor_filter(p, c, m):
            results = [cond(p, c, m) for cond in conditions]
            return sum(results) == 1  # XOR: exactly one should be true
        
        self._filters.append(LogicalFilter(xor_filter))
        return self
    
    def add_not_filter(self, condition):
        """Add a NOT condition."""
        def not_filter(p, c, m):
            return not condition(p, c, m)
        
        self._filters.append(LogicalFilter(not_filter))
        return self

    def _combined_filter(self, p, cluster_data, m):
        """Internal method to combine all filters."""
        # Check sub-cluster filter
        if self._sub_cluster_id is not None and cluster_data.get('sub_cluster_id', -1) != self._sub_cluster_id:
            return False
        
        # Check main cluster filter  
        if self._main_cluster_id is not None and cluster_data.get('main_cluster_id', -1) != self._main_cluster_id:
            return False
            
        # Apply all other filters
        return all(f(p, cluster_data, m) for f in self._filters)

    def execute(self):
        """Execute the query and return matching participants."""
        return query_participants(self._combined_filter, self.jsonl_filename, self.csv_filename)

    def get_stats(self):
        """Execute the query and return statistical summary."""
        participants = self.execute()
        if not participants:
            return None
        
        count = len(participants)
        avg_place = sum(p['placement'] for p in participants) / count
        winrate = (sum(1 for p in participants if p['placement'] == 1) / count) * 100
        top4_rate = (sum(1 for p in participants if p['placement'] <= 4) / count) * 100
        
        return {
            'play_count': count,
            'avg_placement': round(avg_place, 2),
            'winrate': round(winrate, 2),
            'top4_rate': round(top4_rate, 2)
        }

    @staticmethod
    def get_all_cluster_stats(jsonl_filename='matches.jsonl', csv_filename='hierarchical_clusters.csv', 
                             min_size=5, cluster_type='sub'):
        """
        Get statistical summary for all clusters (sub-clusters or main clusters).
        
        :param jsonl_filename: Path to match data
        :param csv_filename: Path to hierarchical cluster data
        :param min_size: Minimum cluster size to include
        :param cluster_type: 'sub' for sub-clusters, 'main' for main clusters
        :return: List of cluster statistics sorted by frequency
        """
        total_parts = 0
        cluster_data = defaultdict(list)
        clusters = load_clusters(csv_filename)
        cluster_field = 'sub_cluster_id' if cluster_type == 'sub' else 'main_cluster_id'
        
        for match in query_jsonl(jsonl_filename):
            total_parts += len(match['info']['participants'])
            for p in match['info']['participants']:
                cluster_info = clusters.get((match['metadata']['match_id'], p['puuid']), 
                                          {'sub_cluster_id': -1, 'main_cluster_id': -1})
                cluster_id = cluster_info.get(cluster_field, -1)
                if cluster_id != -1:
                    cluster_data[cluster_id].append(p)
        
        stats = []
        for cid, parts in cluster_data.items():
            if len(parts) < min_size:
                continue
            
            play_count = len(parts)
            avg_place = sum(p['placement'] for p in parts) / play_count
            winrate = sum(1 for p in parts if p['placement'] == 1) / play_count * 100
            top4 = sum(1 for p in parts if p['placement'] <= 4) / play_count * 100
            frequency = play_count / total_parts * 100 if total_parts else 0
            
            # Get carry units based on cluster type
            if cluster_type == 'main':
                # For main clusters, get common carries across all sub-clusters
                sub_cluster_ids = set()
                # Get all sub-cluster IDs that belong to this main cluster
                for match in query_jsonl(jsonl_filename):
                    for p in match['info']['participants']:
                        cluster_info = clusters.get((match['metadata']['match_id'], p['puuid']), 
                                                  {'sub_cluster_id': -1, 'main_cluster_id': -1})
                        if cluster_info.get('main_cluster_id') == cid:
                            sub_cluster_ids.add(cluster_info.get('sub_cluster_id'))
                
                # Get carry sets for each sub-cluster
                sub_cluster_carry_sets = []
                for sub_cid in sub_cluster_ids:
                    if sub_cid != -1:
                        sub_parts = []
                        for match in query_jsonl(jsonl_filename):
                            for p in match['info']['participants']:
                                cluster_info = clusters.get((match['metadata']['match_id'], p['puuid']), 
                                                          {'sub_cluster_id': -1, 'main_cluster_id': -1})
                                if cluster_info.get('sub_cluster_id') == sub_cid:
                                    sub_parts.append(p)
                        
                        if sub_parts:
                            # Get carries from first participant in sub-cluster
                            sub_carries = set()
                            for unit in sub_parts[0]['units']:
                                if len(unit.get('itemNames', [])) >= 2:
                                    sub_carries.add(unit['character_id'])
                            sub_cluster_carry_sets.append(sub_carries)
                
                # Find intersection (common carries)
                if sub_cluster_carry_sets:
                    common_carries = sub_cluster_carry_sets[0]
                    for carry_set in sub_cluster_carry_sets[1:]:
                        common_carries = common_carries.intersection(carry_set)
                    carry_units = sorted(list(common_carries))
                else:
                    carry_units = []
            else:
                # For sub-clusters, get carries from representative
                representative = parts[0]
                carry_units = [u['character_id'] for u in representative['units'] 
                              if len(u.get('itemNames', [])) >= 2]
            
            stats.append({
                'cluster_id': cid,
                'play_count': play_count,
                'avg_place': round(avg_place, 2),
                'winrate': round(winrate, 2),
                'top4': round(top4, 2),
                'frequency': round(frequency, 2),
                'carries': sorted(carry_units) if carry_units else ['NO_CARRIES'],
                'cluster_type': cluster_type
            })
        
        stats.sort(key=lambda x: x['frequency'], reverse=True)
        return stats


def print_cluster_compositions(cluster_id, jsonl_filename, csv_filename='hierarchical_clusters.csv', 
                              cluster_type='sub', max_samples=5):
    """
    Print detailed breakdown of compositions in a specific cluster.
    
    :param cluster_id: ID of the cluster to analyze
    :param jsonl_filename: Path to match data
    :param csv_filename: Path to hierarchical cluster data
    :param cluster_type: 'sub' for sub-clusters, 'main' for main clusters
    :param max_samples: Maximum number of sample compositions to show
    """
    comps = get_compositions_in_cluster(cluster_id, jsonl_filename, csv_filename, cluster_type)
    
    if not comps:
        print(f"No compositions found for {cluster_type}-cluster {cluster_id}")
        return
    
    cluster_label = f"{cluster_type.upper()}-CLUSTER {cluster_id}"
    print(f"=== {cluster_label} ANALYSIS ===")
    print(f"Total compositions: {len(comps)}")
    
    # Calculate cluster statistics
    avg_place = sum(c['placement'] for c in comps) / len(comps)
    winrate = sum(1 for c in comps if c['placement'] == 1) / len(comps) * 100
    top4_rate = sum(1 for c in comps if c['placement'] <= 4) / len(comps) * 100
    
    print(f"Performance: {avg_place:.2f} avg place, {winrate:.1f}% winrate, {top4_rate:.1f}% top4 rate")
    
    # Show sample compositions
    print(f"\nSample compositions (showing up to {max_samples}):")
    for i, comp in enumerate(comps[:max_samples], 1):
        # Units with 2+ items are carries
        carry_units = [(u['character_id'], len(u.get('itemNames', []))) for u in comp['units'] 
                      if len(u.get('itemNames', [])) >= 2]
        other_units = [u['character_id'] for u in comp['units'] 
                      if len(u.get('itemNames', [])) < 2]
        
        print(f"\n  Sample {i}: Placement {comp['placement']}, Level {comp['level']}, Round {comp.get('last_round', 50)}")
        if carry_units:
            carries_display = ', '.join([f"{unit}({items})" for unit, items in carry_units])
            print(f"    Carries: {carries_display}")
        else:
            print(f"    Carries: No carry units (no units with 2+ items)")
        print(f"    Other units: {', '.join(other_units[:8])}{'...' if len(other_units) > 8 else ''}")


def analyze_top_clusters(jsonl_filename='matches.jsonl', csv_filename='hierarchical_clusters.csv', 
                        top_n=10, cluster_type='sub'):
    """
    Analyze and display the top performing clusters.
    
    :param jsonl_filename: Path to match data
    :param csv_filename: Path to hierarchical cluster data  
    :param top_n: Number of top clusters to analyze
    :param cluster_type: 'sub' for sub-clusters, 'main' for main clusters
    """
    all_stats = TFTQueryLegacy.get_all_cluster_stats(jsonl_filename, csv_filename, cluster_type=cluster_type)
    
    if not all_stats:
        print(f"No valid {cluster_type}-clusters found!")
        return
    
    cluster_label = f"{cluster_type.upper()}-CLUSTERS"
    print(f"{'='*100}")
    print(f"{'TOP ' + str(top_n) + ' TFT COMPOSITION ' + cluster_label:^100}")
    print(f"{'='*100}")
    print(f"{'Rank':<4} {'Cluster':<8} {'Type':<5} {'Size':<6} {'Carries':<35} {'Avg Place':<10} {'Winrate':<9} {'Top4':<8} {'Freq':<6}")
    print(f"{'-'*100}")

    for i, s in enumerate(all_stats[:top_n]):
        carries_display = ', '.join(s['carries']) if isinstance(s['carries'], list) else str(s['carries'])
        if len(carries_display) > 33:
            carries_display = carries_display[:30] + "..."
        
        cluster_type_short = s.get('cluster_type', 'sub')[:3].upper()
        print(f"{i+1:<4} {s['cluster_id']:<8} {cluster_type_short:<5} {s['play_count']:<6} {carries_display:<35} {s['avg_place']:<10} {s['winrate']:<8.1f}% {s['top4']:<7.1f}% {s['frequency']:<5.1f}%")
    
    return all_stats[:top_n]


# ============================================================================
# POSTGRESQL-BASED QUERYING SYSTEM
# ============================================================================

class DatabaseQueryFilter:
    """Represents a SQL WHERE clause filter condition."""
    
    def __init__(self, condition: str, params: Optional[Dict[str, Any]] = None):
        """
        Initialize a database query filter.
        
        Args:
            condition: SQL condition string with placeholders
            params: Parameters for the SQL condition
        """
        self.condition = condition
        self.params = params or {}
    
    def __and__(self, other):
        """Combine with AND logic."""
        new_params = {**self.params}
        # Rename conflicting parameter names
        for key, value in other.params.items():
            if key in new_params:
                new_key = f"{key}_2"
                while new_key in new_params:
                    new_key = f"{new_key}_alt"
                new_params[new_key] = value
                other_condition = other.condition.replace(f":{key}", f":{new_key}")
            else:
                new_params[key] = value
                other_condition = other.condition
        
        return DatabaseQueryFilter(
            f"({self.condition}) AND ({other_condition})",
            new_params
        )
    
    def __or__(self, other):
        """Combine with OR logic."""
        new_params = {**self.params}
        # Rename conflicting parameter names
        for key, value in other.params.items():
            if key in new_params:
                new_key = f"{key}_2"
                while new_key in new_params:
                    new_key = f"{new_key}_alt"
                new_params[new_key] = value
                other_condition = other.condition.replace(f":{key}", f":{new_key}")
            else:
                new_params[key] = value
                other_condition = other.condition
        
        return DatabaseQueryFilter(
            f"({self.condition}) OR ({other_condition})",
            new_params
        )
    
    def __xor__(self, other):
        """Combine with XOR logic."""
        new_params = {**self.params}
        # Rename conflicting parameter names
        for key, value in other.params.items():
            if key in new_params:
                new_key = f"{key}_2"
                while new_key in new_params:
                    new_key = f"{new_key}_alt"
                new_params[new_key] = value
                other_condition = other.condition.replace(f":{key}", f":{new_key}")
            else:
                new_params[key] = value
                other_condition = other.condition
        
        return DatabaseQueryFilter(
            f"(({self.condition}) AND NOT ({other_condition})) OR (NOT ({self.condition}) AND ({other_condition}))",
            new_params
        )
    
    def __invert__(self):
        """Apply NOT logic."""
        return DatabaseQueryFilter(f"NOT ({self.condition})", self.params)


class TFTQueryDB:
    """
    PostgreSQL-based TFT composition query builder with same API as legacy TFTQuery.
    
    Provides flexible querying capabilities for TFT match data with clustering integration.
    Uses PostgreSQL for dramatically better performance with large datasets.
    """
    
    def __init__(self, use_database: bool = True):
        """
        Initialize the TFT query builder.
        
        Args:
            use_database: If True, use PostgreSQL; if False, fall back to legacy file-based
        """
        self.use_database = use_database and HAS_DATABASE
        
        # Legacy fallback support
        if not self.use_database:
            if not HAS_FILE_SUPPORT:
                raise ImportError("Neither database nor file-based support available")
            logger.warning("Database not available, falling back to file-based operations")
        
        # Query state
        self._sub_cluster_id = None
        self._main_cluster_id = None
        self._filters: List[DatabaseQueryFilter] = []
        
        # For legacy compatibility
        self.jsonl_filename = 'matches_filtered.jsonl'
        self.csv_filename = 'hierarchical_clusters.csv'
    
    def set_sub_cluster(self, cluster_id: int):
        """Filter results to specific sub-cluster only."""
        self._sub_cluster_id = cluster_id
        return self
    
    def set_main_cluster(self, cluster_id: int):
        """Filter results to specific main cluster only."""
        self._main_cluster_id = cluster_id
        return self
    
    def set_cluster(self, cluster_id: int):
        """Legacy compatibility - defaults to sub-cluster."""
        return self.set_sub_cluster(cluster_id)
    
    def add_unit(self, unit_id: str, must_have: bool = True):
        """Add filter for presence/absence of a specific unit."""
        if not self.use_database:
            # Delegate to legacy implementation
            return self._add_legacy_filter(lambda p, c, m: (unit_id in [u['character_id'] for u in p['units']]) == must_have)
        
        if must_have:
            condition = """
                EXISTS (
                    SELECT 1 FROM jsonb_array_elements(p.units_raw) AS unit_data
                    WHERE unit_data->>'character_id' = :unit_id
                )
            """
        else:
            condition = """
                NOT EXISTS (
                    SELECT 1 FROM jsonb_array_elements(p.units_raw) AS unit_data
                    WHERE unit_data->>'character_id' = :unit_id
                )
            """
        
        self._filters.append(DatabaseQueryFilter(condition, {"unit_id": unit_id}))
        return self
    
    def add_unit_count(self, unit_id: str, count: int):
        """Add filter for exact unit count of a specific unit type."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: sum(1 for u in p['units'] if u['character_id'] == unit_id) == count)
        
        condition = """
            (SELECT COUNT(*) 
             FROM jsonb_array_elements(p.units_raw) AS unit_data
             WHERE unit_data->>'character_id' = :unit_id) = :count
        """
        
        self._filters.append(DatabaseQueryFilter(condition, {"unit_id": unit_id, "count": count}))
        return self
    
    def add_item_on_unit(self, unit_id: str, item_id: str):
        """Add filter for specific item on specific unit."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: any(u['character_id'] == unit_id and item_id in u['itemNames'] for u in p['units']))
        
        condition = """
            EXISTS (
                SELECT 1 FROM jsonb_array_elements(p.units_raw) AS unit_data
                WHERE unit_data->>'character_id' = :unit_id
                AND jsonb_array_elements_text(unit_data->'itemNames') = :item_id
            )
        """
        
        self._filters.append(DatabaseQueryFilter(condition, {"unit_id": unit_id, "item_id": item_id}))
        return self
    
    def add_trait(self, trait_name: str, min_tier: int = 1, max_tier: int = 4):
        """Add filter for trait activation level."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: any(t['name'] == trait_name and min_tier <= t['tier_current'] <= max_tier for t in p['traits']))
        
        condition = """
            EXISTS (
                SELECT 1 FROM jsonb_array_elements(p.traits_raw) AS trait_data
                WHERE trait_data->>'name' = :trait_name
                AND (trait_data->>'tier_current')::INTEGER >= :min_tier
                AND (trait_data->>'tier_current')::INTEGER <= :max_tier
            )
        """
        
        self._filters.append(DatabaseQueryFilter(condition, {
            "trait_name": trait_name,
            "min_tier": min_tier,
            "max_tier": max_tier
        }))
        return self
    
    def add_player_level(self, min_level: int = 1, max_level: int = 10):
        """Add filter for player level range."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: min_level <= p['level'] <= max_level)
        
        condition = "p.level >= :min_level AND p.level <= :max_level"
        self._filters.append(DatabaseQueryFilter(condition, {"min_level": min_level, "max_level": max_level}))
        return self
    
    def add_last_round(self, min_round: int = 1, max_round: int = 50):
        """Add filter for last round survived range."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: min_round <= p['last_round'] <= max_round)
        
        condition = "p.last_round >= :min_round AND p.last_round <= :max_round"
        self._filters.append(DatabaseQueryFilter(condition, {"min_round": min_round, "max_round": max_round}))
        return self
    
    def add_unit_star_level(self, unit_id: str, min_star: int = 1, max_star: int = 3):
        """Add filter for unit star level range."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: any(u['character_id'] == unit_id and min_star <= u['tier'] <= max_star for u in p['units']))
        
        condition = """
            EXISTS (
                SELECT 1 FROM jsonb_array_elements(p.units_raw) AS unit_data
                WHERE unit_data->>'character_id' = :unit_id
                AND (unit_data->>'tier')::INTEGER >= :min_star
                AND (unit_data->>'tier')::INTEGER <= :max_star
            )
        """
        
        self._filters.append(DatabaseQueryFilter(condition, {
            "unit_id": unit_id,
            "min_star": min_star,
            "max_star": max_star
        }))
        return self
    
    def add_unit_item_count(self, unit_id: str, min_count: int = 0, max_count: int = 3):
        """Add filter for number of items on a specific unit."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: any(u['character_id'] == unit_id and min_count <= len(u['itemNames']) <= max_count for u in p['units']))
        
        condition = """
            EXISTS (
                SELECT 1 FROM jsonb_array_elements(p.units_raw) AS unit_data
                WHERE unit_data->>'character_id' = :unit_id
                AND jsonb_array_length(unit_data->'itemNames') >= :min_count
                AND jsonb_array_length(unit_data->'itemNames') <= :max_count
            )
        """
        
        self._filters.append(DatabaseQueryFilter(condition, {
            "unit_id": unit_id,
            "min_count": min_count,
            "max_count": max_count
        }))
        return self
    
    def add_augment(self, augment_id: str):
        """Add filter for specific augment."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: augment_id in p['augments'])
        
        condition = """
            EXISTS (
                SELECT 1 FROM jsonb_array_elements_text(p.augments) AS augment
                WHERE augment = :augment_id
            )
        """
        self._filters.append(DatabaseQueryFilter(condition, {"augment_id": augment_id}))
        return self
    
    def set_patch(self, patch_version: str):
        """Add filter for specific patch version."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: m['info']['game_version'].startswith(f'Version {patch_version}'))
        
        condition = "m.game_version LIKE :patch_pattern"
        self._filters.append(DatabaseQueryFilter(condition, {"patch_pattern": f"Version {patch_version}%"}))
        return self
    
    def add_custom_filter(self, condition: str, params: Optional[Dict[str, Any]] = None):
        """
        Add a custom SQL filter condition.
        
        Args:
            condition: SQL WHERE condition with parameter placeholders
            params: Parameters for the condition
        """
        if not self.use_database:
            raise NotImplementedError("Custom SQL filters only supported in database mode")
        
        self._filters.append(DatabaseQueryFilter(condition, params or {}))
        return self
    
    def add_or_group(self, *conditions):
        """Add multiple conditions combined with OR logic."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: any(cond(p, c, m) for cond in conditions))
        
        if not conditions:
            return self
        
        # For database mode, conditions should be DatabaseQueryFilter objects or SQL strings
        if all(isinstance(cond, str) for cond in conditions):
            or_condition = " OR ".join(f"({cond})" for cond in conditions)
            self._filters.append(DatabaseQueryFilter(or_condition))
        else:
            # Support for custom callable conditions (convert to legacy mode)
            return self._add_legacy_filter(lambda p, c, m: any(cond(p, c, m) for cond in conditions))
        
        return self
    
    def add_xor_group(self, *conditions):
        """Add multiple conditions combined with XOR logic."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: sum(cond(p, c, m) for cond in conditions) == 1)
        
        if not conditions:
            return self
            
        # XOR: exactly one condition should be true
        if len(conditions) == 2 and all(isinstance(cond, str) for cond in conditions):
            xor_condition = f"(({conditions[0]}) AND NOT ({conditions[1]})) OR (NOT ({conditions[0]}) AND ({conditions[1]}))"
            self._filters.append(DatabaseQueryFilter(xor_condition))
        else:
            # Fallback to legacy mode for complex XOR
            return self._add_legacy_filter(lambda p, c, m: sum(cond(p, c, m) for cond in conditions) == 1)
        
        return self
    
    def add_not_filter(self, condition):
        """Add a NOT condition."""
        if not self.use_database:
            return self._add_legacy_filter(lambda p, c, m: not condition(p, c, m))
        
        if isinstance(condition, str):
            not_condition = f"NOT ({condition})"
            self._filters.append(DatabaseQueryFilter(not_condition))
        else:
            # Fallback to legacy mode
            return self._add_legacy_filter(lambda p, c, m: not condition(p, c, m))
        
        return self
    
    def _add_legacy_filter(self, filter_func: Callable):
        """Add a legacy Python filter function (for backward compatibility)."""
        # This would require switching to legacy mode
        if self.use_database:
            logger.warning("Switching to legacy mode due to complex filter. Consider using SQL-based filters.")
            self.use_database = False
        
        # Convert to legacy TFTQueryLegacy and delegate
        legacy_query = TFTQueryLegacy(self.jsonl_filename, self.csv_filename)
        if self._sub_cluster_id is not None:
            legacy_query.set_sub_cluster(self._sub_cluster_id)
        if self._main_cluster_id is not None:
            legacy_query.set_main_cluster(self._main_cluster_id)
        legacy_query.add_custom_filter(filter_func)
        return legacy_query
    
    def _build_sql_query(self) -> tuple[str, Dict[str, Any]]:
        """Build the complete SQL query with all filters."""
        base_query = """
            SELECT 
                p.participant_id,
                p.match_id,
                p.puuid,
                p.summoner_name,
                p.placement,
                p.level,
                p.last_round,
                p.players_eliminated,
                p.total_damage_to_players,
                p.gold_left,
                p.augments,
                p.traits_raw,
                p.units_raw,
                m.game_datetime,
                m.game_version,
                m.queue_type,
                COALESCE(pc.main_cluster_id, -1) as main_cluster_id,
                COALESCE(pc.sub_cluster_id, -1) as sub_cluster_id
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            LEFT JOIN participant_clusters pc ON p.participant_id = pc.participant_id
            WHERE 1=1
        """
        
        all_params = {}
        
        # Add cluster filters
        if self._sub_cluster_id is not None:
            base_query += " AND COALESCE(pc.sub_cluster_id, -1) = :sub_cluster_id"
            all_params["sub_cluster_id"] = self._sub_cluster_id
        
        if self._main_cluster_id is not None:
            base_query += " AND COALESCE(pc.main_cluster_id, -1) = :main_cluster_id"
            all_params["main_cluster_id"] = self._main_cluster_id
        
        # Add all other filters
        for filter_obj in self._filters:
            base_query += f" AND ({filter_obj.condition})"
            all_params.update(filter_obj.params)
        
        base_query += " ORDER BY p.placement ASC"
        
        return base_query, all_params
    
    def execute(self) -> List[Dict[str, Any]]:
        """Execute the query and return matching participants."""
        if not self.use_database:
            # Delegate to legacy implementation
            return self._execute_legacy()
        
        try:
            query, params = self._build_sql_query()
            
            with get_db_session() as session:
                result = session.execute(text(query), params)
                rows = result.fetchall()
                
                # Convert to list of dictionaries (matching legacy format)
                participants = []
                for row in rows:
                    participant = {
                        'participant_id': str(row.participant_id),
                        'match_id': str(row.match_id),
                        'puuid': row.puuid,
                        'summoner_name': row.summoner_name,
                        'placement': row.placement,
                        'level': row.level,
                        'last_round': row.last_round,
                        'players_eliminated': row.players_eliminated,
                        'total_damage_to_players': row.total_damage_to_players,
                        'gold_left': row.gold_left,
                        'augments': row.augments,
                        'traits': row.traits_raw,  # For legacy compatibility
                        'units': row.units_raw,    # For legacy compatibility
                        'game_datetime': row.game_datetime,
                        'game_version': row.game_version,
                        'queue_type': row.queue_type,
                        'main_cluster_id': row.main_cluster_id,
                        'sub_cluster_id': row.sub_cluster_id
                    }
                    participants.append(participant)
                
                return participants
                
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            # Fall back to legacy mode if database fails
            logger.warning("Falling back to legacy file-based mode")
            self.use_database = False
            return self._execute_legacy()
    
    def _execute_legacy(self) -> List[Dict[str, Any]]:
        """Execute query using legacy file-based method."""
        # This is a fallback - in practice, would need to implement
        # conversion of current state to legacy TFTQuery
        if not HAS_FILE_SUPPORT:
            raise RuntimeError("Legacy file support not available")
        
        # For now, return empty list as placeholder
        logger.warning("Legacy execution not fully implemented")
        return []
    
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Execute the query and return statistical summary."""
        participants = self.execute()
        if not participants:
            return None
        
        count = len(participants)
        avg_place = sum(p['placement'] for p in participants) / count
        winrate = (sum(1 for p in participants if p['placement'] == 1) / count) * 100
        top4_rate = (sum(1 for p in participants if p['placement'] <= 4) / count) * 100
        
        return {
            'play_count': count,
            'avg_placement': round(avg_place, 2),
            'winrate': round(winrate, 2),
            'top4_rate': round(top4_rate, 2)
        }
    
    @staticmethod
    def get_all_cluster_stats(min_size: int = 5, cluster_type: str = 'sub', use_database: bool = True) -> List[Dict[str, Any]]:
        """
        Get statistical summary for all clusters using PostgreSQL.
        
        Args:
            min_size: Minimum cluster size to include
            cluster_type: 'sub' for sub-clusters, 'main' for main clusters
            use_database: Whether to use database queries
            
        Returns:
            List of cluster statistics sorted by frequency
        """
        if not use_database or not HAS_DATABASE:
            # Fallback to legacy implementation
            return TFTQueryLegacy.get_all_cluster_stats(min_size=min_size, cluster_type=cluster_type)
        
        try:
            cluster_id_field = 'sub_cluster_id' if cluster_type == 'sub' else 'main_cluster_id'
            
            query = f"""
                WITH cluster_stats AS (
                    SELECT 
                        pc.{cluster_id_field} as cluster_id,
                        COUNT(*) as play_count,
                        AVG(p.placement) as avg_place,
                        COUNT(*) FILTER (WHERE p.placement = 1) * 100.0 / COUNT(*) as winrate,
                        COUNT(*) FILTER (WHERE p.placement <= 4) * 100.0 / COUNT(*) as top4,
                        array_agg(DISTINCT carry_unit ORDER BY carry_unit) as carries
                    FROM participant_clusters pc
                    INNER JOIN participants p ON pc.participant_id = p.participant_id
                    CROSS JOIN LATERAL unnest(pc.carry_units) AS carry_unit
                    WHERE pc.{cluster_id_field} != -1
                    GROUP BY pc.{cluster_id_field}
                    HAVING COUNT(*) >= :min_size
                ),
                total_participants AS (
                    SELECT COUNT(*) as total_count 
                    FROM participant_clusters pc
                    INNER JOIN participants p ON pc.participant_id = p.participant_id
                    WHERE pc.{cluster_id_field} != -1
                )
                SELECT 
                    cs.cluster_id,
                    cs.play_count,
                    ROUND(cs.avg_place, 2) as avg_place,
                    ROUND(cs.winrate, 2) as winrate,
                    ROUND(cs.top4, 2) as top4,
                    ROUND(cs.play_count::DECIMAL / tp.total_count * 100, 2) as frequency,
                    COALESCE(cs.carries, ARRAY['NO_CARRIES']) as carries,
                    :cluster_type as cluster_type
                FROM cluster_stats cs
                CROSS JOIN total_participants tp
                ORDER BY frequency DESC, avg_place ASC
            """
            
            with get_db_session() as session:
                result = session.execute(text(query), {
                    "min_size": min_size,
                    "cluster_type": cluster_type
                })
                
                stats = []
                for row in result:
                    stats.append({
                        'cluster_id': row.cluster_id,
                        'play_count': row.play_count,
                        'avg_place': row.avg_place,
                        'winrate': row.winrate,
                        'top4': row.top4,
                        'frequency': row.frequency,
                        'carries': list(row.carries) if row.carries else ['NO_CARRIES'],
                        'cluster_type': row.cluster_type
                    })
                
                return stats
                
        except Exception as e:
            logger.error(f"Database cluster stats query failed: {e}")
            # Fallback to legacy implementation
            return TFTQueryLegacy.get_all_cluster_stats(min_size=min_size, cluster_type=cluster_type)


# ============================================================================
# DATABASE-BASED HELPER FUNCTIONS
# ============================================================================

def get_compositions_in_cluster_db(cluster_id: int, cluster_type: str = 'sub', limit: int = None) -> List[Dict[str, Any]]:
    """
    Get all compositions in a specific cluster using database queries.
    
    Args:
        cluster_id: ID of the cluster to retrieve
        cluster_type: 'sub' for sub-clusters, 'main' for main clusters
        limit: Maximum number of compositions to return
        
    Returns:
        List of participant data for the cluster
    """
    if not HAS_DATABASE:
        return []
    
    try:
        cluster_id_field = 'sub_cluster_id' if cluster_type == 'sub' else 'main_cluster_id'
        
        query = f"""
            SELECT 
                p.participant_id,
                p.match_id,
                p.puuid,
                p.summoner_name,
                p.placement,
                p.level,
                p.last_round,
                p.players_eliminated,
                p.total_damage_to_players,
                p.gold_left,
                p.augments,
                p.traits_raw,
                p.units_raw,
                pc.carry_units,
                m.game_datetime,
                m.game_version
            FROM participants p
            JOIN participant_clusters pc ON p.participant_id = pc.participant_id
            JOIN matches m ON p.match_id = m.match_id
            WHERE pc.{cluster_id_field} = :cluster_id
            AND pc.{cluster_id_field} != -1
            ORDER BY p.placement ASC
            {f'LIMIT {limit}' if limit else ''}
        """
        
        with get_db_session() as session:
            result = session.execute(text(query), {"cluster_id": cluster_id})
            rows = result.fetchall()
            
            compositions = []
            for row in rows:
                comp = {
                    'participant_id': str(row.participant_id),
                    'match_id': str(row.match_id),
                    'puuid': row.puuid,
                    'summoner_name': row.summoner_name,
                    'placement': row.placement,
                    'level': row.level,
                    'last_round': row.last_round,
                    'players_eliminated': row.players_eliminated,
                    'total_damage_to_players': row.total_damage_to_players,
                    'gold_left': row.gold_left,
                    'augments': row.augments,
                    'traits': row.traits_raw,  # For legacy compatibility
                    'units': row.units_raw,    # For legacy compatibility
                    'carry_units': list(row.carry_units) if row.carry_units else [],
                    'game_datetime': row.game_datetime,
                    'game_version': row.game_version
                }
                compositions.append(comp)
            
            return compositions
            
    except Exception as e:
        logger.error(f"Database cluster composition query failed: {e}")
        return []


def print_cluster_compositions_db(cluster_id: int, cluster_type: str = 'sub', max_samples: int = 5):
    """
    Print detailed breakdown of compositions in a specific cluster using database queries.
    
    Args:
        cluster_id: ID of the cluster to analyze
        cluster_type: 'sub' for sub-clusters, 'main' for main clusters
        max_samples: Maximum number of sample compositions to show
    """
    comps = get_compositions_in_cluster_db(cluster_id, cluster_type, limit=max_samples * 2)
    
    if not comps:
        print(f"No compositions found for {cluster_type}-cluster {cluster_id}")
        return
    
    cluster_label = f"{cluster_type.upper()}-CLUSTER {cluster_id}"
    print(f"=== {cluster_label} ANALYSIS ===")
    print(f"Total compositions: {len(comps)}")
    
    # Calculate cluster statistics
    avg_place = sum(c['placement'] for c in comps) / len(comps)
    winrate = sum(1 for c in comps if c['placement'] == 1) / len(comps) * 100
    top4_rate = sum(1 for c in comps if c['placement'] <= 4) / len(comps) * 100
    
    print(f"Performance: {avg_place:.2f} avg place, {winrate:.1f}% winrate, {top4_rate:.1f}% top4 rate")
    
    # Show sample compositions
    print(f"\nSample compositions (showing up to {max_samples}):")
    for i, comp in enumerate(comps[:max_samples], 1):
        # Extract carry information
        carry_units = comp.get('carry_units', [])
        if not carry_units and 'units' in comp:
            # Fallback: identify carries as units with 2+ items
            carry_units = []
            for unit in comp['units']:
                if isinstance(unit, dict) and len(unit.get('itemNames', [])) >= 2:
                    carry_units.append(unit['character_id'])
        
        # Other units (non-carries)
        other_units = []
        if 'units' in comp:
            for unit in comp['units']:
                if isinstance(unit, dict):
                    unit_id = unit['character_id']
                    if unit_id not in carry_units:
                        other_units.append(unit_id)
        
        print(f"\n  Sample {i}: Placement {comp['placement']}, Level {comp['level']}, Round {comp.get('last_round', 'N/A')}")
        if carry_units:
            print(f"    Carries: {', '.join(carry_units)}")
        else:
            print(f"    Carries: No identified carry units")
        print(f"    Other units: {', '.join(other_units[:8])}{'...' if len(other_units) > 8 else ''}")


# For backward compatibility, create an alias that automatically selects the best available implementation
if HAS_DATABASE:
    TFTQuery = TFTQueryDB
    logger.info("Using database-backed TFT querying")
elif HAS_FILE_SUPPORT:
    TFTQuery = TFTQueryLegacy
    logger.info("Using legacy file-based TFT querying")
else:
    # Create a minimal fallback class for when neither database nor file support is available
    class TFTQueryFallback:
        def __init__(self, *args, **kwargs):
            logger.warning("Neither database nor file support available - using fallback mode")
        
        def add_unit(self, *args, **kwargs):
            return self
        
        def add_trait(self, *args, **kwargs):
            return self
            
        def add_player_level(self, *args, **kwargs):
            return self
            
        def set_sub_cluster(self, *args, **kwargs):
            return self
            
        def set_main_cluster(self, *args, **kwargs):
            return self
            
        def set_cluster(self, *args, **kwargs):
            return self
            
        def add_unit_count(self, *args, **kwargs):
            return self
            
        def add_item_on_unit(self, *args, **kwargs):
            return self
            
        def add_last_round(self, *args, **kwargs):
            return self
            
        def add_unit_star_level(self, *args, **kwargs):
            return self
            
        def add_unit_item_count(self, *args, **kwargs):
            return self
            
        def add_augment(self, *args, **kwargs):
            return self
            
        def set_patch(self, *args, **kwargs):
            return self
            
        def add_custom_filter(self, *args, **kwargs):
            return self
            
        def get_stats(self):
            return {
                "error": "Neither database nor file support available",
                "play_count": 0,
                "avg_placement": 0,
                "winrate": 0,
                "top4_rate": 0
            }
        
        def execute(self):
            return []
    
    TFTQuery = TFTQueryFallback
    logger.warning("Using fallback TFT querying - limited functionality available")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="TFT Querying - Analyze and query TFT composition data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python querying.py                                          # Use default files
  python querying.py --input matches_filtered.jsonl          # Specify input file
  python querying.py --clusters hierarchical_clusters.csv    # Specify cluster file
  python querying.py --top-n 5                              # Show top 5 clusters
        """
    )
    
    parser.add_argument('--input', type=str, default='matches_filtered.jsonl',
                       help='Input JSONL file with match data (default: matches_filtered.jsonl)')
    parser.add_argument('--clusters', type=str, default='hierarchical_clusters.csv',
                       help='Cluster assignments CSV file (default: hierarchical_clusters.csv)')
    parser.add_argument('--top-n', type=int, default=10,
                       help='Number of top clusters to analyze (default: 10)')
    parser.add_argument('--use-database', action='store_true',
                       help='Use PostgreSQL database instead of files (default: auto-detect)')
    parser.add_argument('--force-legacy', action='store_true',
                       help='Force use of legacy file-based mode')
    
    args = parser.parse_args()
    
    # Determine which mode to use
    use_database_mode = args.use_database or (HAS_DATABASE and not args.force_legacy)
    
    if use_database_mode and HAS_DATABASE:
        # Set global filenames for the TFTQuery class for backward compatibility
        try:
            TFTQueryLegacy._default_jsonl_filename = args.input
            TFTQueryLegacy._default_csv_filename = args.clusters
        except AttributeError:
            pass  # Class might not have these attributes
    else:
        use_database_mode = False
    
    print("TFT Querying System")
    print("=" * 50)
    print(f"Mode: {'PostgreSQL Database' if use_database_mode else 'Legacy File-based'}")
    if not use_database_mode:
        print(f"Input: {args.input}")
        print(f"Clusters: {args.clusters}")
    print(f"Top N: {args.top_n}")
    print()
    
    # Show top sub-clusters and main clusters
    print(f"\n1. Top {args.top_n} Sub-Clusters Analysis:")
    if use_database_mode:
        # Use database-based cluster stats
        try:
            sub_cluster_stats = TFTQuery.get_all_cluster_stats(min_size=5, cluster_type='sub', use_database=True)
            top_sub_clusters = sub_cluster_stats[:args.top_n]
            
            if top_sub_clusters:
                print(f"{'='*100}")
                print(f"{'TOP ' + str(args.top_n) + ' TFT COMPOSITION SUB-CLUSTERS':^100}")
                print(f"{'='*100}")
                print(f"{'Rank':<4} {'Cluster':<8} {'Type':<5} {'Size':<6} {'Carries':<35} {'Avg Place':<10} {'Winrate':<9} {'Top4':<8} {'Freq':<6}")
                print(f"{'-'*100}")
                
                for i, s in enumerate(top_sub_clusters):
                    carries_display = ', '.join(s['carries']) if isinstance(s['carries'], list) else str(s['carries'])
                    if len(carries_display) > 33:
                        carries_display = carries_display[:30] + "..."
                    print(f"{i+1:<4} {s['cluster_id']:<8} {'SUB':<5} {s['play_count']:<6} {carries_display:<35} {s['avg_place']:<10} {s['winrate']:<8.1f}% {s['top4']:<7.1f}% {s['frequency']:<5.1f}%")
            else:
                print("No sub-clusters found in database.")
        except Exception as e:
            print(f"Database query failed: {e}")
            top_sub_clusters = []
    else:
        # Use legacy file-based analysis
        top_sub_clusters = analyze_top_clusters(
            jsonl_filename=args.input, 
            csv_filename=args.clusters, 
            top_n=args.top_n, 
            cluster_type='sub'
        )
    
    print(f"\n2. Top {args.top_n} Main Clusters Analysis:")
    if use_database_mode:
        # Use database-based cluster stats
        try:
            main_cluster_stats = TFTQuery.get_all_cluster_stats(min_size=5, cluster_type='main', use_database=True)
            top_main_clusters = main_cluster_stats[:args.top_n]
            
            if top_main_clusters:
                print(f"{'='*100}")
                print(f"{'TOP ' + str(args.top_n) + ' TFT COMPOSITION MAIN-CLUSTERS':^100}")
                print(f"{'='*100}")
                print(f"{'Rank':<4} {'Cluster':<8} {'Type':<5} {'Size':<6} {'Carries':<35} {'Avg Place':<10} {'Winrate':<9} {'Top4':<8} {'Freq':<6}")
                print(f"{'-'*100}")
                
                for i, s in enumerate(top_main_clusters):
                    carries_display = ', '.join(s['carries']) if isinstance(s['carries'], list) else str(s['carries'])
                    if len(carries_display) > 33:
                        carries_display = carries_display[:30] + "..."
                    print(f"{i+1:<4} {s['cluster_id']:<8} {'MAIN':<5} {s['play_count']:<6} {carries_display:<35} {s['avg_place']:<10} {s['winrate']:<8.1f}% {s['top4']:<7.1f}% {s['frequency']:<5.1f}%")
            else:
                print("No main clusters found in database.")
        except Exception as e:
            print(f"Database query failed: {e}")
            top_main_clusters = []
    else:
        # Use legacy file-based analysis
        top_main_clusters = analyze_top_clusters(
            jsonl_filename=args.input, 
            csv_filename=args.clusters, 
            top_n=args.top_n, 
            cluster_type='main'
        )
    
    # Example queries
    print("\n3. Example Queries:")
    
    try:
        if use_database_mode:
            # Database-based examples
            print("Using PostgreSQL database queries...")
            
            # Basic unit query
            aphelios_stats = TFTQuery(use_database=True).add_unit('TFT14_Aphelios').get_stats()
            print(f"Compositions with Aphelios: {aphelios_stats}")
            
            # Trait query
            vanguard_stats = TFTQuery(use_database=True).add_trait('TFT14_Vanguard', min_tier=2).get_stats()
            print(f"Vanguard tier 2+ compositions: {vanguard_stats}")
            
            # Level-based query
            high_level_stats = TFTQuery(use_database=True).add_player_level(min_level=9).get_stats()
            print(f"Level 9+ compositions: {high_level_stats}")
            
        else:
            # Legacy file-based examples
            print("Using legacy file-based queries...")
            
            # Basic unit query
            aphelios_stats = TFTQueryLegacy(args.input, args.clusters).add_unit('TFT14_Aphelios').get_stats()
            print(f"Compositions with Aphelios: {aphelios_stats}")
            
            # Complex logical query
            complex_stats = TFTQueryLegacy(args.input, args.clusters).add_or_group(
                lambda p, c, m: p['level'] >= 9,
                lambda p, c, m: any(t['name'] == 'TFT14_Vanguard' and t['tier_current'] > 0 for t in p['traits'])
            ).get_stats()
            print(f"Level 9+ OR Vanguard trait: {complex_stats}")
            
    except Exception as e:
        print(f"Query examples failed: {e}")
    
    if top_sub_clusters:
        # Detailed analysis of top sub-cluster
        print(f"\n4. Detailed Analysis of Top Sub-Cluster:")
        if use_database_mode:
            print_cluster_compositions_db(
                top_sub_clusters[0]['cluster_id'], 
                cluster_type='sub', 
                max_samples=3
            )
        else:
            print_cluster_compositions(
                top_sub_clusters[0]['cluster_id'], 
                args.input, 
                args.clusters, 
                cluster_type='sub', 
                max_samples=3
            )
    
    if top_main_clusters:
        # Detailed analysis of top main cluster  
        print(f"\n5. Detailed Analysis of Top Main Cluster:")
        if use_database_mode:
            print_cluster_compositions_db(
                top_main_clusters[0]['cluster_id'], 
                cluster_type='main', 
                max_samples=3
            )
        else:
            print_cluster_compositions(
                top_main_clusters[0]['cluster_id'], 
                args.input, 
                args.clusters, 
                cluster_type='main', 
                max_samples=3
            )
    
    print(f"\n{'='*60}")
    print("QUERYING COMPLETE")
    print(f"{'='*60}")
    print("Interactive usage:")
    print(f"  from querying import TFTQuery")
    print(f"  query = TFTQuery('{args.input}', '{args.clusters}')")
    print(f"  results = query.add_unit('TFT14_Aphelios').get_stats()")