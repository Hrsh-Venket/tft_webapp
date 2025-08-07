"""
Database Clustering Operations for TFT Match Analysis

This module provides database-optimized clustering operations including:
- Efficient data extraction from PostgreSQL using JSON operations
- Batch processing for large datasets
- Memory-optimized carry unit extraction
- Cluster result storage and management
- Incremental clustering support
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set, FrozenSet
from contextlib import contextmanager
from dataclasses import dataclass
import json
from datetime import datetime

from sqlalchemy import text, func, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert

from .connection import get_db_session, get_database_manager, retry_on_database_error

logger = logging.getLogger(__name__)


@dataclass
class ClusteringConfig:
    """Configuration for clustering operations."""
    min_sub_cluster_size: int = 5
    min_main_cluster_size: int = 3
    batch_size: int = 1000
    memory_limit_mb: int = 500
    enable_incremental: bool = True
    similarity_threshold: float = 0.6  # For main cluster grouping
    carry_item_threshold: int = 2  # Minimum items to be considered a carry


@dataclass
class ClusteringStats:
    """Statistics for clustering operations."""
    participants_processed: int = 0
    participants_clustered: int = 0
    sub_clusters_created: int = 0
    main_clusters_created: int = 0
    processing_time_seconds: float = 0
    memory_peak_mb: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'participants_processed': self.participants_processed,
            'participants_clustered': self.participants_clustered,
            'sub_clusters_created': self.sub_clusters_created,
            'main_clusters_created': self.main_clusters_created,
            'processing_time_seconds': round(self.processing_time_seconds, 2),
            'memory_peak_mb': round(self.memory_peak_mb, 2)
        }


class DatabaseClusteringEngine:
    """
    Database-optimized clustering engine for TFT compositions.
    
    Provides efficient clustering operations using PostgreSQL's JSON capabilities
    and batch processing for handling large datasets.
    """
    
    def __init__(self, config: Optional[ClusteringConfig] = None):
        self.config = config or ClusteringConfig()
        self.stats = ClusteringStats()
        self.db_manager = get_database_manager()
    
    @retry_on_database_error(max_retries=3, delay=2.0)
    def extract_carry_compositions(self, 
                                 batch_size: Optional[int] = None,
                                 filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Extract compositions with carry units from database using efficient SQL.
        
        Args:
            batch_size: Number of participants to process at once
            filters: Additional SQL filters (e.g., date range, set version)
            
        Returns:
            List of composition dictionaries with carry information
        """
        batch_size = batch_size or self.config.batch_size
        filters = filters or {}
        
        logger.info("Extracting carry compositions from database...")
        
        # Build dynamic WHERE clause
        where_conditions = ["1=1"]  # Always true base condition
        query_params = {'min_items': self.config.carry_item_threshold}
        
        if filters.get('date_from'):
            where_conditions.append("m.game_datetime >= :date_from")
            query_params['date_from'] = filters['date_from']
        
        if filters.get('date_to'):
            where_conditions.append("m.game_datetime <= :date_to")
            query_params['date_to'] = filters['date_to']
        
        if filters.get('set_core_name'):
            where_conditions.append("m.set_core_name = :set_core_name")
            query_params['set_core_name'] = filters['set_core_name']
        
        if filters.get('queue_types'):
            queue_placeholders = ','.join([f':queue_{i}' for i in range(len(filters['queue_types']))])
            where_conditions.append(f"m.queue_type IN ({queue_placeholders})")
            for i, queue_type in enumerate(filters['queue_types']):
                query_params[f'queue_{i}'] = queue_type
        
        if filters.get('match_game_ids'):
            match_placeholders = ','.join([f':game_id_{i}' for i in range(len(filters['match_game_ids']))])
            where_conditions.append(f"m.game_id IN ({match_placeholders})")
            for i, game_id in enumerate(filters['match_game_ids']):
                query_params[f'game_id_{i}'] = game_id
        
        where_clause = " AND ".join(where_conditions)
        
        # Efficient query using PostgreSQL JSON operations
        query = text(f"""
        WITH carry_units AS (
            SELECT 
                p.participant_id,
                p.match_id,
                p.puuid,
                p.placement,
                p.last_round,
                p.summoner_name,
                m.game_id,
                -- Extract carry units (units with >= :min_items items)
                ARRAY(
                    SELECT DISTINCT unit->>'character_id'
                    FROM jsonb_array_elements(p.units_raw) AS unit
                    WHERE jsonb_array_length(unit->'itemNames') >= :min_items
                    AND unit->>'character_id' IS NOT NULL
                    AND unit->>'character_id' != ''
                    ORDER BY unit->>'character_id'
                ) AS carry_units,
                p.units_raw,
                p.traits_raw
            FROM participants p
            INNER JOIN matches m ON p.match_id = m.match_id
            WHERE {where_clause}
        )
        SELECT 
            participant_id,
            match_id,
            puuid,
            placement,
            last_round,
            summoner_name,
            game_id,
            carry_units,
            units_raw,
            traits_raw,
            CASE 
                WHEN array_length(carry_units, 1) IS NULL THEN 0
                ELSE array_length(carry_units, 1)
            END as carry_count
        FROM carry_units
        WHERE array_length(carry_units, 1) > 0  -- Only include compositions with carries
        ORDER BY participant_id
        LIMIT :batch_size
        """)
        
        query_params['batch_size'] = batch_size
        
        try:
            with self.db_manager.get_session() as session:
                result = session.execute(query, query_params)
                compositions = []
                
                for row in result:
                    # Convert to composition format compatible with existing clustering logic
                    composition = {
                        'participant_id': row.participant_id,
                        'match_id': str(row.match_id),
                        'puuid': row.puuid,
                        'game_id': row.game_id,
                        'summoner_name': row.summoner_name or '',
                        'carries': frozenset(row.carry_units),
                        'carry_count': row.carry_count,
                        'placement': row.placement,
                        'last_round': row.last_round,
                        'units_raw': row.units_raw,
                        'traits_raw': row.traits_raw,
                        'participant_data': {
                            'placement': row.placement,
                            'last_round': row.last_round,
                            'units': row.units_raw or [],
                            'traits': row.traits_raw or []
                        }
                    }
                    compositions.append(composition)
                
                logger.info(f"Extracted {len(compositions)} compositions with carries from database")
                return compositions
                
        except Exception as e:
            logger.error(f"Error extracting carry compositions: {e}")
            raise
    
    @retry_on_database_error()
    def get_existing_clusters(self) -> Dict[str, Dict[str, Any]]:
        """
        Get existing cluster assignments from database.
        
        Returns:
            Dictionary mapping participant_id to cluster information
        """
        try:
            with self.db_manager.get_session() as session:
                query = text("""
                SELECT 
                    participant_id,
                    sub_cluster_id,
                    main_cluster_id,
                    carry_units,
                    created_at
                FROM participant_clusters
                ORDER BY sub_cluster_id, main_cluster_id
                """)
                
                result = session.execute(query)
                existing_clusters = {}
                
                for row in result:
                    existing_clusters[str(row.participant_id)] = {
                        'sub_cluster_id': row.sub_cluster_id,
                        'main_cluster_id': row.main_cluster_id,
                        'carry_units': row.carry_units,
                        'created_at': row.created_at
                    }
                
                logger.info(f"Found {len(existing_clusters)} existing cluster assignments")
                return existing_clusters
                
        except Exception as e:
            logger.error(f"Error getting existing clusters: {e}")
            return {}
    
    @retry_on_database_error()
    def get_unclustered_matches(self, 
                               filters: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Get match IDs that don't have clustering results yet.
        
        Args:
            filters: Additional filters (date range, set version, etc.)
            
        Returns:
            List of unclustered match IDs (game_id format)
        """
        try:
            with self.db_manager.get_session() as session:
                # Build dynamic WHERE clause for match filters
                where_conditions = ["1=1"]  # Always true base condition
                query_params = {}
                
                if filters:
                    if filters.get('date_from'):
                        where_conditions.append("m.game_datetime >= :date_from")
                        query_params['date_from'] = filters['date_from']
                    
                    if filters.get('date_to'):
                        where_conditions.append("m.game_datetime <= :date_to")
                        query_params['date_to'] = filters['date_to']
                    
                    if filters.get('set_core_name'):
                        where_conditions.append("m.set_core_name = :set_core_name")
                        query_params['set_core_name'] = filters['set_core_name']
                    
                    if filters.get('queue_types'):
                        queue_placeholders = ','.join([f':queue_{i}' for i in range(len(filters['queue_types']))])
                        where_conditions.append(f"m.queue_type IN ({queue_placeholders})")
                        for i, queue_type in enumerate(filters['queue_types']):
                            query_params[f'queue_{i}'] = queue_type
                
                where_clause = " AND ".join(where_conditions)
                
                query = text(f"""
                SELECT DISTINCT m.game_id
                FROM matches m
                INNER JOIN participants p ON m.match_id = p.match_id
                LEFT JOIN participant_clusters pc ON p.participant_id = pc.participant_id 
                    AND pc.algorithm = 'hierarchical'
                WHERE {where_clause}
                    AND pc.participant_id IS NULL  -- No clustering results yet
                ORDER BY m.game_datetime DESC
                """)
                
                result = session.execute(query, query_params)
                unclustered_matches = [row.game_id for row in result]
                
                logger.info(f"Found {len(unclustered_matches)} unclustered matches")
                return unclustered_matches
                
        except Exception as e:
            logger.error(f"Error getting unclustered matches: {e}")
            return []
    
    @retry_on_database_error()
    def clear_existing_clusters(self, match_ids: Optional[List[str]] = None):
        """
        Clear existing cluster assignments, optionally filtered by match IDs.
        
        Args:
            match_ids: If provided, only clear clusters for these matches
        """
        try:
            with self.db_manager.get_session() as session:
                if match_ids:
                    # Convert string match_ids to UUIDs for the query
                    placeholders = ','.join([f':match_id_{i}' for i in range(len(match_ids))])
                    query = text(f"""
                    DELETE FROM participant_clusters 
                    WHERE match_id IN (
                        SELECT match_id FROM matches WHERE game_id IN ({placeholders})
                    )
                    """)
                    params = {f'match_id_{i}': match_id for i, match_id in enumerate(match_ids)}
                    result = session.execute(query, params)
                else:
                    query = text("DELETE FROM participant_clusters")
                    result = session.execute(query)
                
                deleted_count = result.rowcount
                logger.info(f"Cleared {deleted_count} existing cluster assignments")
                
        except Exception as e:
            logger.error(f"Error clearing existing clusters: {e}")
            raise
    
    @retry_on_database_error()
    def store_cluster_assignments(self, 
                                cluster_assignments: List[Dict[str, Any]],
                                batch_size: int = 100) -> int:
        """
        Store cluster assignments in database using individual inserts.
        
        Args:
            cluster_assignments: List of cluster assignment dictionaries
            batch_size: Number of records to process per transaction batch
            
        Returns:
            Number of assignments stored
        """
        logger.info(f"Storing {len(cluster_assignments)} cluster assignments in database...")
        
        total_inserted = 0
        
        try:
            with self.db_manager.get_session() as session:
                # Process in batches to manage memory and transactions
                for i in range(0, len(cluster_assignments), batch_size):
                    batch = cluster_assignments[i:i + batch_size]
                    batch_inserted = 0
                    
                    for assignment in batch:
                        try:
                            carry_units_array = list(assignment.get('carry_units', []))
                            metadata = {
                                'carry_count': len(carry_units_array),
                                'similarity_scores': assignment.get('similarity_scores', {}),
                                'clustering_version': '2.0',
                                'algorithm': 'hierarchical'
                            }
                            
                            # Check if this participant already has a cluster assignment
                            # Use participant_id as UUID, not string
                            participant_id = assignment['participant_id']
                            existing = session.execute(text("""
                                SELECT cluster_id FROM participant_clusters 
                                WHERE participant_id = :participant_id AND algorithm = 'hierarchical'
                                ORDER BY cluster_date DESC LIMIT 1
                            """), {'participant_id': participant_id}).fetchone()
                            
                            if existing:
                                # Update existing record
                                update_query = text("""
                                UPDATE participant_clusters 
                                SET main_cluster_id = :main_cluster_id,
                                    sub_cluster_id = :sub_cluster_id,
                                    carry_units = :carry_units,
                                    cluster_metadata = :cluster_metadata,
                                    parameters = :parameters,
                                    updated_at = NOW()
                                WHERE cluster_id = :cluster_id
                                """)
                                
                                session.execute(update_query, {
                                    'cluster_id': existing[0],
                                    'main_cluster_id': assignment.get('main_cluster_id', -1),
                                    'sub_cluster_id': assignment.get('sub_cluster_id', -1),
                                    'carry_units': carry_units_array,
                                    'cluster_metadata': json.dumps(metadata),
                                    'parameters': json.dumps({
                                        'min_sub_cluster_size': 5,
                                        'min_main_cluster_size': 3,
                                        'similarity_threshold': 0.6
                                    })
                                })
                            else:
                                # Insert new record
                                insert_query = text("""
                                INSERT INTO participant_clusters 
                                (participant_id, algorithm, main_cluster_id, sub_cluster_id, 
                                 carry_units, cluster_metadata, parameters, match_id, puuid, created_at)
                                VALUES 
                                (:participant_id, 'hierarchical', :main_cluster_id, :sub_cluster_id,
                                 :carry_units, :cluster_metadata, :parameters, :match_id, :puuid, NOW())
                                """)
                                
                                session.execute(insert_query, {
                                    'participant_id': participant_id,
                                    'main_cluster_id': assignment.get('main_cluster_id', -1),
                                    'sub_cluster_id': assignment.get('sub_cluster_id', -1),
                                    'carry_units': carry_units_array,
                                    'cluster_metadata': json.dumps(metadata),
                                    'parameters': json.dumps({
                                        'min_sub_cluster_size': self.config.min_sub_cluster_size,
                                        'min_main_cluster_size': self.config.min_main_cluster_size,
                                        'similarity_threshold': self.config.similarity_threshold
                                    }),
                                    'match_id': assignment.get('match_id'),
                                    'puuid': assignment.get('puuid', '')
                                })
                            
                            batch_inserted += 1
                            
                        except Exception as e:
                            logger.warning(f"Failed to store cluster assignment for participant {assignment.get('participant_id', 'unknown')}: {e}")
                            continue
                    
                    total_inserted += batch_inserted
                    logger.debug(f"Processed batch {i//batch_size + 1}: {batch_inserted}/{len(batch)} records")
                
                logger.info(f"Successfully stored {total_inserted} cluster assignments")
                return total_inserted
                
        except Exception as e:
            logger.error(f"Error storing cluster assignments: {e}")
            raise
    
    def calculate_cluster_statistics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive clustering statistics from database.
        
        Returns:
            Dictionary with clustering statistics
        """
        try:
            with self.db_manager.get_session() as session:
                # Basic counts
                stats_query = text("""
                SELECT 
                    COUNT(*) as total_participants,
                    COUNT(*) FILTER (WHERE sub_cluster_id != -1) as sub_clustered,
                    COUNT(*) FILTER (WHERE main_cluster_id != -1) as main_clustered,
                    COUNT(DISTINCT sub_cluster_id) FILTER (WHERE sub_cluster_id != -1) as unique_sub_clusters,
                    COUNT(DISTINCT main_cluster_id) FILTER (WHERE main_cluster_id != -1) as unique_main_clusters
                FROM participant_clusters
                """)
                
                basic_stats = session.execute(stats_query).fetchone()
                
                # Sub-cluster size distribution
                sub_cluster_sizes = session.execute(text("""
                SELECT 
                    sub_cluster_id,
                    COUNT(*) as size,
                    AVG(CAST(p.placement as FLOAT)) as avg_placement,
                    COUNT(*) FILTER (WHERE p.placement = 1) * 100.0 / COUNT(*) as winrate,
                    COUNT(*) FILTER (WHERE p.placement <= 4) * 100.0 / COUNT(*) as top4_rate
                FROM participant_clusters pc
                INNER JOIN participants p ON pc.participant_id = p.participant_id
                WHERE pc.sub_cluster_id != -1
                GROUP BY sub_cluster_id
                ORDER BY size DESC
                """)).fetchall()
                
                # Main cluster size distribution
                main_cluster_sizes = session.execute(text("""
                SELECT 
                    main_cluster_id,
                    COUNT(*) as size,
                    COUNT(DISTINCT sub_cluster_id) as sub_clusters,
                    AVG(CAST(p.placement as FLOAT)) as avg_placement,
                    COUNT(*) FILTER (WHERE p.placement = 1) * 100.0 / COUNT(*) as winrate,
                    COUNT(*) FILTER (WHERE p.placement <= 4) * 100.0 / COUNT(*) as top4_rate
                FROM participant_clusters pc
                INNER JOIN participants p ON pc.participant_id = p.participant_id
                WHERE pc.main_cluster_id != -1
                GROUP BY main_cluster_id
                ORDER BY size DESC
                """)).fetchall()
                
                # Carry unit frequency analysis
                carry_analysis = session.execute(text("""
                SELECT 
                    unit_name,
                    COUNT(*) as frequency,
                    AVG(CAST(p.placement as FLOAT)) as avg_placement,
                    COUNT(*) FILTER (WHERE p.placement = 1) * 100.0 / COUNT(*) as winrate
                FROM participant_clusters pc
                CROSS JOIN LATERAL unnest(pc.carry_units) AS unit_name
                INNER JOIN participants p ON pc.participant_id = p.participant_id
                WHERE array_length(pc.carry_units, 1) > 0
                GROUP BY unit_name
                HAVING COUNT(*) >= 10
                ORDER BY frequency DESC
                LIMIT 20
                """)).fetchall()
                
                return {
                    'basic_statistics': {
                        'total_participants': basic_stats.total_participants,
                        'participants_in_sub_clusters': basic_stats.sub_clustered,
                        'participants_in_main_clusters': basic_stats.main_clustered,
                        'unique_sub_clusters': basic_stats.unique_sub_clusters,
                        'unique_main_clusters': basic_stats.unique_main_clusters,
                        'sub_clustering_rate': round((basic_stats.sub_clustered / basic_stats.total_participants) * 100, 1) if basic_stats.total_participants > 0 else 0,
                        'main_clustering_rate': round((basic_stats.main_clustered / basic_stats.total_participants) * 100, 1) if basic_stats.total_participants > 0 else 0
                    },
                    'sub_cluster_analysis': [
                        {
                            'sub_cluster_id': row.sub_cluster_id,
                            'size': row.size,
                            'avg_placement': round(row.avg_placement, 2),
                            'winrate': round(row.winrate, 1),
                            'top4_rate': round(row.top4_rate, 1)
                        }
                        for row in sub_cluster_sizes[:10]  # Top 10 largest
                    ],
                    'main_cluster_analysis': [
                        {
                            'main_cluster_id': row.main_cluster_id,
                            'size': row.size,
                            'sub_clusters': row.sub_clusters,
                            'avg_placement': round(row.avg_placement, 2),
                            'winrate': round(row.winrate, 1),
                            'top4_rate': round(row.top4_rate, 1)
                        }
                        for row in main_cluster_sizes
                    ],
                    'popular_carries': [
                        {
                            'unit_name': row.unit_name,
                            'frequency': row.frequency,
                            'avg_placement': round(row.avg_placement, 2),
                            'winrate': round(row.winrate, 1)
                        }
                        for row in carry_analysis
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error calculating cluster statistics: {e}")
            return {'error': str(e)}
    
    @contextmanager
    def clustering_transaction(self):
        """
        Context manager for clustering operations with transaction rollback on failure.
        """
        start_time = time.time()
        try:
            logger.info("Starting clustering transaction")
            yield
            self.stats.processing_time_seconds = time.time() - start_time
            logger.info(f"Clustering transaction completed in {self.stats.processing_time_seconds:.2f} seconds")
        except Exception as e:
            logger.error(f"Clustering transaction failed: {e}")
            # Rollback handled by session context managers
            raise
    
    def optimize_database_for_clustering(self):
        """
        Optimize database settings and create temporary indexes for clustering operations.
        """
        try:
            with self.db_manager.get_session() as session:
                logger.info("Optimizing database for clustering operations...")
                
                # Create temporary indexes for clustering performance
                optimization_queries = [
                    # Index for carry unit extraction
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_units_gin ON participants USING gin (units_raw)",
                    
                    # Index for cluster lookups
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_lookup ON participant_clusters (sub_cluster_id, main_cluster_id)",
                    
                    # Index for match filtering
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_clustering ON matches (set_core_name, queue_type, game_datetime)",
                    
                    # Update statistics for query planner
                    "ANALYZE participants",
                    "ANALYZE matches",
                    "ANALYZE participant_clusters"
                ]
                
                for query in optimization_queries:
                    try:
                        session.execute(text(query))
                        logger.debug(f"Executed: {query[:50]}...")
                    except Exception as e:
                        logger.warning(f"Optimization query failed (continuing): {e}")
                
                logger.info("Database optimization completed")
                
        except Exception as e:
            logger.warning(f"Database optimization failed: {e}")
    
    def export_clusters_to_csv(self, output_file: str, include_details: bool = True) -> bool:
        """
        Export cluster assignments to CSV file for backward compatibility.
        
        Args:
            output_file: Path to output CSV file
            include_details: Whether to include detailed cluster information
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                logger.info(f"Exporting clusters to {output_file}...")
                
                if include_details:
                    query = text("""
                    SELECT 
                        m.game_id as match_id,
                        pc.puuid,
                        COALESCE(p.summoner_name, '') as riot_id,
                        pc.sub_cluster_id,
                        pc.main_cluster_id,
                        array_to_string(pc.carry_units, ',') as carries,
                        p.last_round,
                        p.placement,
                        pc.created_at
                    FROM participant_clusters pc
                    INNER JOIN participants p ON pc.participant_id = p.participant_id
                    INNER JOIN matches m ON p.match_id = m.match_id
                    ORDER BY pc.main_cluster_id, pc.sub_cluster_id, p.placement
                    """)
                else:
                    query = text("""
                    SELECT 
                        m.game_id as match_id,
                        pc.puuid,
                        COALESCE(p.summoner_name, '') as riot_id,
                        pc.sub_cluster_id,
                        pc.main_cluster_id,
                        array_to_string(pc.carry_units, ',') as carries,
                        p.last_round
                    FROM participant_clusters pc
                    INNER JOIN participants p ON pc.participant_id = p.participant_id
                    INNER JOIN matches m ON p.match_id = m.match_id
                    ORDER BY pc.main_cluster_id, pc.sub_cluster_id
                    """)
                
                result = session.execute(query)
                
                # Write to CSV
                import csv
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    if include_details:
                        writer = csv.writer(f)
                        writer.writerow([
                            'match_id', 'puuid', 'riot_id', 'sub_cluster_id', 'main_cluster_id',
                            'carries', 'last_round', 'placement', 'clustered_at'
                        ])
                        
                        for row in result:
                            writer.writerow([
                                row.match_id, row.puuid, row.riot_id, 
                                row.sub_cluster_id, row.main_cluster_id,
                                row.carries if row.carries else 'NO_CARRIES',
                                row.last_round, row.placement, row.created_at
                            ])
                    else:
                        writer = csv.writer(f)
                        writer.writerow([
                            'match_id', 'puuid', 'riot_id', 'sub_cluster_id', 'main_cluster_id',
                            'carries', 'last_round'
                        ])
                        
                        for row in result:
                            writer.writerow([
                                row.match_id, row.puuid, row.riot_id,
                                row.sub_cluster_id, row.main_cluster_id,
                                row.carries if row.carries else 'NO_CARRIES',
                                row.last_round
                            ])
                
                logger.info(f"Successfully exported clusters to {output_file}")
                return True
                
        except Exception as e:
            logger.error(f"Error exporting clusters to CSV: {e}")
            return False


# Utility functions for common operations
def create_clustering_engine(config: Optional[ClusteringConfig] = None) -> DatabaseClusteringEngine:
    """Create a new database clustering engine with configuration."""
    return DatabaseClusteringEngine(config)


def get_database_cluster_stats() -> Dict[str, Any]:
    """Get comprehensive clustering statistics from database."""
    engine = DatabaseClusteringEngine()
    return engine.calculate_cluster_statistics()


def export_database_clusters_to_csv(output_file: str, include_details: bool = True) -> bool:
    """Export database clusters to CSV file."""
    engine = DatabaseClusteringEngine()
    return engine.export_clusters_to_csv(output_file, include_details)


def get_cluster_performance_summary(main_cluster_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Get performance summary for main clusters from database views.
    
    Args:
        main_cluster_ids: Optional list of specific cluster IDs to analyze
        
    Returns:
        Dictionary with performance summary data
    """
    try:
        db_manager = get_database_manager()
        
        with db_manager.get_session() as session:
            if main_cluster_ids:
                placeholders = ','.join([f':cluster_{i}' for i in range(len(main_cluster_ids))])
                query = text(f"""
                SELECT 
                    main_cluster_id,
                    sub_cluster_count,
                    total_participants,
                    all_carries,
                    avg_placement,
                    winrate,
                    top4_rate,
                    avg_last_round,
                    carry_frequencies,
                    earliest_match,
                    latest_match,
                    avg_placement_recent
                FROM cluster_performance_stats
                WHERE main_cluster_id IN ({placeholders})
                ORDER BY avg_placement ASC, total_participants DESC
                """)
                params = {f'cluster_{i}': cluster_id for i, cluster_id in enumerate(main_cluster_ids)}
            else:
                query = text("""
                SELECT 
                    main_cluster_id,
                    sub_cluster_count,
                    total_participants,
                    all_carries,
                    avg_placement,
                    winrate,
                    top4_rate,
                    avg_last_round,
                    carry_frequencies,
                    earliest_match,
                    latest_match,
                    avg_placement_recent
                FROM cluster_performance_stats
                ORDER BY avg_placement ASC, total_participants DESC
                LIMIT 50
                """)
                params = {}
            
            result = session.execute(query, params)
            
            clusters = []
            for row in result:
                cluster_data = {
                    'main_cluster_id': row.main_cluster_id,
                    'sub_cluster_count': row.sub_cluster_count,
                    'total_participants': row.total_participants,
                    'common_carries': row.all_carries[:10] if row.all_carries else [],  # Top 10 carries
                    'avg_placement': round(row.avg_placement, 2),
                    'winrate': round(row.winrate, 1),
                    'top4_rate': round(row.top4_rate, 1),
                    'avg_last_round': round(row.avg_last_round, 1),
                    'carry_frequencies': row.carry_frequencies or {},
                    'date_range': {
                        'earliest': row.earliest_match.isoformat() if row.earliest_match else None,
                        'latest': row.latest_match.isoformat() if row.latest_match else None
                    },
                    'recent_performance': {
                        'avg_placement_7d': round(row.avg_placement_recent, 2) if row.avg_placement_recent else None,
                        'performance_trend': 'improving' if (row.avg_placement_recent and row.avg_placement_recent < row.avg_placement) else 'stable' if row.avg_placement_recent else 'unknown'
                    }
                }
                clusters.append(cluster_data)
            
            return {
                'clusters': clusters,
                'summary': {
                    'total_clusters': len(clusters),
                    'best_cluster': clusters[0] if clusters else None,
                    'avg_cluster_size': round(sum(c['total_participants'] for c in clusters) / len(clusters), 1) if clusters else 0
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting cluster performance summary: {e}")
        return {'error': str(e)}


def get_carry_unit_analysis() -> Dict[str, Any]:
    """
    Get comprehensive analysis of carry units across all clusters.
    
    Returns:
        Dictionary with carry unit frequency and performance data
    """
    try:
        db_manager = get_database_manager()
        
        with db_manager.get_session() as session:
            query = text("""
            WITH carry_analysis AS (
                SELECT 
                    unit_name,
                    COUNT(*) as total_appearances,
                    COUNT(DISTINCT pc.main_cluster_id) as cluster_appearances,
                    AVG(p.placement) as avg_placement,
                    COUNT(*) FILTER (WHERE p.placement = 1) * 100.0 / COUNT(*) as winrate,
                    COUNT(*) FILTER (WHERE p.placement <= 4) * 100.0 / COUNT(*) as top4_rate,
                    AVG(p.last_round) as avg_last_round,
                    
                    -- Performance by position in carry list
                    AVG(p.placement) FILTER (WHERE array_position(pc.carry_units, unit_name) = 1) as primary_carry_avg_placement,
                    COUNT(*) FILTER (WHERE array_position(pc.carry_units, unit_name) = 1) as primary_carry_count,
                    
                    -- Recent performance (last 7 days)
                    AVG(p.placement) FILTER (WHERE m.game_datetime >= NOW() - INTERVAL '7 days') as recent_avg_placement,
                    COUNT(*) FILTER (WHERE m.game_datetime >= NOW() - INTERVAL '7 days') as recent_appearances
                    
                FROM participant_clusters pc
                CROSS JOIN LATERAL unnest(pc.carry_units) AS unit_name
                INNER JOIN participants p ON pc.participant_id = p.participant_id
                INNER JOIN matches m ON p.match_id = m.match_id
                WHERE array_length(pc.carry_units, 1) > 0
                GROUP BY unit_name
                HAVING COUNT(*) >= 50  -- Minimum appearances for statistical significance
                ORDER BY total_appearances DESC
            )
            SELECT * FROM carry_analysis LIMIT 30
            """)
            
            result = session.execute(query)
            
            carries = []
            for row in result:
                carry_data = {
                    'unit_name': row.unit_name,
                    'total_appearances': row.total_appearances,
                    'cluster_appearances': row.cluster_appearances,
                    'avg_placement': round(row.avg_placement, 2),
                    'winrate': round(row.winrate, 1),
                    'top4_rate': round(row.top4_rate, 1),
                    'avg_last_round': round(row.avg_last_round, 1),
                    'primary_carry_stats': {
                        'avg_placement': round(row.primary_carry_avg_placement, 2) if row.primary_carry_avg_placement else None,
                        'count': row.primary_carry_count,
                        'primary_carry_rate': round((row.primary_carry_count / row.total_appearances) * 100, 1)
                    },
                    'recent_performance': {
                        'avg_placement': round(row.recent_avg_placement, 2) if row.recent_avg_placement else None,
                        'appearances': row.recent_appearances,
                        'trend': 'improving' if (row.recent_avg_placement and row.recent_avg_placement < row.avg_placement) else 'stable' if row.recent_avg_placement else 'unknown'
                    },
                    'versatility': round(row.cluster_appearances / row.total_appearances * 100, 1) if row.total_appearances > 0 else 0
                }
                carries.append(carry_data)
            
            return {
                'top_carries': carries,
                'summary': {
                    'total_carries_analyzed': len(carries),
                    'most_popular': carries[0]['unit_name'] if carries else None,
                    'best_performer': min(carries, key=lambda x: x['avg_placement'])['unit_name'] if carries else None,
                    'most_versatile': max(carries, key=lambda x: x['versatility'])['unit_name'] if carries else None
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting carry unit analysis: {e}")
        return {'error': str(e)}