"""
TFT Two-Level Composition Clustering Module

This module implements a hierarchical clustering system:
1. Sub-compositions: Exact carry matching for precise compositions
2. Overarching clusters: Groups of sub-compositions with 2-3 common carry units

Carry unit detection: Units with 2 or more items are considered carries.
"""

# ===============================
# CONFIGURATION - EDIT THESE VALUES
# ===============================

CARRY_FREQUENCY_THRESHOLD = 0.75  # Minimum frequency for carries to be shown in main cluster names
CARRY_THRESHOLD = 0.75             # Minimum frequency for a unit to be considered a carry (50%)
GOLD_3STAR_THRESHOLD = 0.9        # Minimum frequency for g3star_ prefix (90%)
SILVER_3STAR_THRESHOLD = 0.5      # Minimum frequency for s3star_ prefix (50%)
TOP_UNITS_COUNT = 8               # Number of top units to display

# ===============================
# END CONFIGURATION
# ===============================

import json
import csv
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List, Dict, Set, FrozenSet, Tuple, Optional, Any
from pathlib import Path
import sys
import os

# Add database imports (imported only when needed to avoid circular dependencies)
import importlib


@dataclass
class Composition:
    """Represents a TFT composition with metadata and carry information."""
    match_id: str
    puuid: str
    riot_id: str
    carries: FrozenSet[str]
    last_round: int
    participant_data: dict
    sub_cluster_id: Optional[int] = None
    main_cluster_id: Optional[int] = None


@dataclass
class SubCluster:
    """Represents a sub-cluster of compositions with identical carry sets."""
    id: int
    carry_set: FrozenSet[str]
    compositions: List[Composition]
    size: int
    avg_placement: float
    winrate: float
    top4_rate: float


class TFTClusteringEngine:
    """
    Two-level clustering engine for TFT compositions.
    
    Level 1: Sub-clusters based on exact carry matching
    Level 2: Main clusters grouping sub-clusters with 2-3 common carries
    """
    
    def __init__(self, min_sub_cluster_size: int = 5, min_main_cluster_size: int = 3):
        self.min_sub_cluster_size = min_sub_cluster_size
        self.min_main_cluster_size = min_main_cluster_size
        self.compositions: List[Composition] = []
        self.sub_clusters: List[SubCluster] = []
        self.main_cluster_assignments: Dict[int, int] = {}
    
    def extract_carry_units(self, participant: dict) -> FrozenSet[str]:
        """
        Extract carry units from a participant based on item count.
        
        Units with 2 or more items are considered carries.
        
        :param participant: Participant data from match
        :return: Set of carry unit IDs
        """
        carry_units = frozenset(
            unit['character_id'] for unit in participant.get('units', [])
            if len(unit.get('itemNames', [])) >= 2
        )
        
        return carry_units
    
    def load_compositions_from_database(self, 
                                        filters: Optional[Dict[str, Any]] = None,
                                        batch_size: int = 10000) -> None:
        """Load and process compositions from PostgreSQL database."""
        print("1. Loading compositions from database...")
        
        try:
            # Dynamic import to avoid circular dependencies
            clustering_ops = importlib.import_module('database.clustering_operations')
            DatabaseClusteringEngine = clustering_ops.DatabaseClusteringEngine
            
            # Initialize database clustering engine
            db_engine = DatabaseClusteringEngine()
            
            # Extract compositions with carries from database
            db_compositions = db_engine.extract_carry_compositions(
                batch_size=batch_size,
                filters=filters or {}
            )
            
            # Convert to legacy Composition format for compatibility
            compositions = []
            for db_comp in db_compositions:
                comp = Composition(
                    match_id=db_comp['game_id'],  # Use game_id for compatibility
                    puuid=db_comp['puuid'],
                    riot_id=db_comp['summoner_name'] or '',
                    carries=db_comp['carries'],
                    last_round=db_comp['last_round'],
                    participant_data=db_comp['participant_data']
                )
                # Store additional database info for later use
                comp.participant_id = db_comp['participant_id']
                comp.db_match_id = db_comp['match_id']  # Store UUID match_id
                compositions.append(comp)
            
            self.compositions = compositions
            print(f"   Loaded {len(self.compositions)} compositions from database")
            
        except ImportError as e:
            print(f"   Error: Database modules not available: {e}")
            print("   Please ensure database modules are installed and accessible.")
            raise
        except Exception as e:
            print(f"   Error loading compositions from database: {e}")
            raise
    
    def load_compositions(self, jsonl_filename: str) -> None:
        """Load and process compositions from JSONL file (legacy method)."""
        print("1. Loading compositions from match data...")
        print("   Note: Consider using load_compositions_from_database() for better performance")
        
        compositions = []
        for match in self._query_jsonl(jsonl_filename):
            match_id = match['metadata']['match_id']
            
            for participant in match['info']['participants']:
                puuid = participant['puuid']
                riot_id = f"{participant.get('riotIdGameName', '')}#{participant.get('riotIdTagline', '')}"
                carries = self.extract_carry_units(participant)
                last_round = participant.get('last_round', 50)
                
                comp = Composition(
                    match_id=match_id,
                    puuid=puuid,
                    riot_id=riot_id,
                    carries=carries,
                    last_round=last_round,
                    participant_data=participant
                )
                compositions.append(comp)
        
        self.compositions = compositions
        print(f"   Loaded {len(self.compositions)} compositions")
    
    def create_sub_clusters(self) -> None:
        """Create sub-clusters based on exact carry matching."""
        print("\n2. Creating sub-clusters (exact carry matching)...")
        
        # Group compositions by identical carry sets
        carry_groups = defaultdict(list)
        for comp in self.compositions:
            carry_groups[comp.carries].append(comp)
        
        # Create sub-clusters from groups meeting minimum size
        sub_clusters = []
        sub_cluster_id = 0
        
        for carry_set, comps in carry_groups.items():
            if len(comps) >= self.min_sub_cluster_size:
                # Calculate statistics
                avg_placement = sum(c.participant_data['placement'] for c in comps) / len(comps)
                winrate = sum(1 for c in comps if c.participant_data['placement'] == 1) / len(comps) * 100
                top4_rate = sum(1 for c in comps if c.participant_data['placement'] <= 4) / len(comps) * 100
                
                # Create sub-cluster
                sub_cluster = SubCluster(
                    id=sub_cluster_id,
                    carry_set=carry_set,
                    compositions=comps,
                    size=len(comps),
                    avg_placement=round(avg_placement, 2),
                    winrate=round(winrate, 2),
                    top4_rate=round(top4_rate, 2)
                )
                
                # Assign sub-cluster ID to compositions
                for comp in comps:
                    comp.sub_cluster_id = sub_cluster_id
                
                sub_clusters.append(sub_cluster)
                sub_cluster_id += 1
        
        self.sub_clusters = sub_clusters
        print(f"   Created {len(self.sub_clusters)} valid sub-clusters")
        print(f"   Sub-clustered {sum(sc.size for sc in self.sub_clusters)} compositions")
    
    def create_main_clusters(self) -> None:
        """Create main clusters by grouping sub-clusters with 2-3 common carries."""
        print("\n3. Creating main clusters (2-3 common carries)...")
        
        if len(self.sub_clusters) < 2:
            print("   Not enough sub-clusters for main clustering")
            return
        
        # Build similarity matrix between sub-clusters
        n = len(self.sub_clusters)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                similarity = self._calculate_carry_similarity(
                    self.sub_clusters[i].carry_set,
                    self.sub_clusters[j].carry_set
                )
                similarity_matrix[i, j] = similarity
                similarity_matrix[j, i] = similarity
        
        # Convert similarity to distance matrix
        distance_matrix = 1.0 - similarity_matrix
        
        # Perform agglomerative clustering
        # Use distance threshold to ensure clusters have meaningful commonality
        clustering = AgglomerativeClustering(
            n_clusters=None,
            linkage='average',
            metric='precomputed',
            distance_threshold=0.4  # Requires at least 60% similarity
        )
        
        main_labels = clustering.fit_predict(distance_matrix)
        
        # Process main cluster assignments
        main_cluster_sizes = Counter(main_labels)
        valid_main_clusters = {
            label for label, size in main_cluster_sizes.items() 
            if size >= self.min_main_cluster_size
        }
        
        # Assign main cluster IDs to sub-clusters and compositions
        for i, sub_cluster in enumerate(self.sub_clusters):
            if main_labels[i] in valid_main_clusters:
                main_cluster_id = main_labels[i]
                self.main_cluster_assignments[sub_cluster.id] = main_cluster_id
                
                # Propagate to compositions
                for comp in sub_cluster.compositions:
                    comp.main_cluster_id = main_cluster_id
        
        print(f"   Created {len(valid_main_clusters)} main clusters")
        print(f"   Grouped {len([sc for sc in self.sub_clusters if sc.id in self.main_cluster_assignments])} sub-clusters")
    
    def _calculate_carry_similarity(self, carries1: FrozenSet[str], carries2: FrozenSet[str]) -> float:
        """
        Calculate similarity between two carry sets based on common units.
        
        Returns similarity score between 0.0 and 1.0 based on:
        - Common carries / max(len(carries1), len(carries2))
        - Bonus for having 2-3 common carries (ideal range)
        """
        if not carries1 or not carries2:
            return 0.0
        
        common_carries = carries1.intersection(carries2)
        common_count = len(common_carries)
        
        if common_count == 0:
            return 0.0
        
        # Base similarity: Jaccard coefficient
        union_size = len(carries1.union(carries2))
        jaccard = common_count / union_size if union_size > 0 else 0.0
        
        # Bonus for having 2-3 common carries (sweet spot for clustering)
        if 2 <= common_count <= 3:
            bonus = 0.3
        elif common_count == 1:
            bonus = 0.1
        else:
            bonus = -0.1  # Penalize too many or too few common carries
        
        return min(1.0, jaccard + bonus)
    
    def save_results_to_database(self) -> None:
        """Save clustering results to PostgreSQL database."""
        print("\n4. Saving results to database...")
        
        try:
            # Dynamic import to avoid circular dependencies
            clustering_ops = importlib.import_module('database.clustering_operations')
            DatabaseClusteringEngine = clustering_ops.DatabaseClusteringEngine
            
            # Initialize database clustering engine
            db_engine = DatabaseClusteringEngine()
            
            # Prepare cluster assignments for database storage
            cluster_assignments = []
            missing_ids_count = 0
            
            for comp in self.compositions:
                participant_id = getattr(comp, 'participant_id', None)
                db_match_id = getattr(comp, 'db_match_id', None)
                
                # Skip if we don't have required database IDs
                if not participant_id or not db_match_id:
                    missing_ids_count += 1
                    continue
                
                assignment = {
                    'match_id': db_match_id,  # Use UUID match_id
                    'puuid': comp.puuid,
                    'participant_id': participant_id,
                    'sub_cluster_id': comp.sub_cluster_id if comp.sub_cluster_id is not None else -1,
                    'main_cluster_id': comp.main_cluster_id if comp.main_cluster_id is not None else -1,
                    'carry_units': list(comp.carries) if comp.carries else [],
                    'similarity_scores': getattr(comp, 'similarity_scores', {})
                }
                cluster_assignments.append(assignment)
            
            if missing_ids_count > 0:
                print(f"   Warning: Skipped {missing_ids_count} compositions due to missing database IDs")
            
            if cluster_assignments:
                # Store in database
                stored_count = db_engine.store_cluster_assignments(cluster_assignments)
                print(f"   Saved {stored_count} cluster assignments to database")
            else:
                print("   Warning: No valid cluster assignments to save")
                
        except ImportError as e:
            print(f"   Error: Database modules not available: {e}")
            print("   Please ensure database modules are installed and accessible.")
            raise
        except Exception as e:
            print(f"   Error saving results to database: {e}")
            raise
    
    def save_results(self, csv_filename: str = 'hierarchical_clusters.csv') -> None:
        """Save clustering results to CSV with both sub-cluster and main cluster information."""
        print(f"\n4. Saving results to {csv_filename}...")
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'match_id', 'puuid', 'riot_id', 'sub_cluster_id', 'main_cluster_id',
                'carries', 'last_round'
            ])
            
            for comp in self.compositions:
                carries_str = ','.join(sorted(comp.carries)) if comp.carries else 'NO_CARRIES'
                
                writer.writerow([
                    comp.match_id,
                    comp.puuid,
                    comp.riot_id,
                    comp.sub_cluster_id if comp.sub_cluster_id is not None else -1,
                    comp.main_cluster_id if comp.main_cluster_id is not None else -1,
                    carries_str,
                    comp.last_round
                ])
        
        print(f"   Saved {len(self.compositions)} compositions with clustering data")
    
    def get_frequent_carries_in_main_cluster(self, main_cluster_id: int, frequency_threshold: float = 0.9) -> List[str]:
        """
        Get carries that appear in at least X% of matches within a main cluster.
        
        :param main_cluster_id: ID of the main cluster
        :param frequency_threshold: Minimum frequency (0.9 = 90%)
        :return: List of carry units that meet the frequency threshold
        """
        # Get all compositions in this main cluster
        main_cluster_compositions = [
            comp for comp in self.compositions 
            if comp.main_cluster_id == main_cluster_id
        ]
        
        if not main_cluster_compositions:
            return []
        
        # Count how many times each carry appears
        carry_counts = defaultdict(int)
        total_matches = len(main_cluster_compositions)
        
        for comp in main_cluster_compositions:
            for carry in comp.carries:
                carry_counts[carry] += 1
        
        # Filter carries that meet frequency threshold
        frequent_carries = []
        for carry, count in carry_counts.items():
            frequency = count / total_matches
            if frequency >= frequency_threshold:
                frequent_carries.append(carry)
        
        return sorted(frequent_carries)

    def analyze_unit_properties_in_cluster(self, compositions: List[Composition]) -> str:
        """
        Analyze unit frequencies and properties within a cluster and return formatted display string.
        
        :param compositions: List of compositions in the cluster
        :return: Formatted string showing top units with prefixes
        """
        if not compositions:
            return ""
        
        total_matches = len(compositions)
        unit_stats = defaultdict(lambda: {
            'frequency': 0,
            'carry_count': 0,
            'star_counts': defaultdict(int)
        })
        
        # Analyze each composition
        for comp in compositions:
            units_in_comp = set()
            
            for unit in comp.participant_data.get('units', []):
                char_id = unit.get('character_id', '')
                if not char_id:
                    continue
                    
                units_in_comp.add(char_id)
                
                # Count star level
                tier = unit.get('tier', 1)
                unit_stats[char_id]['star_counts'][tier] += 1
                
                # Count if it's a carry (2+ items)
                item_count = len(unit.get('itemNames', []))
                if item_count >= 2:
                    unit_stats[char_id]['carry_count'] += 1
            
            # Count frequency (presence in match, not duplicates)
            for unit_name in units_in_comp:
                unit_stats[unit_name]['frequency'] += 1
        
        # Calculate percentages and create display names
        unit_display_list = []
        
        for unit_name, stats in unit_stats.items():
            frequency = stats['frequency'] / total_matches
            carry_frequency = stats['carry_count'] / total_matches if stats['frequency'] > 0 else 0
            
            # Calculate 3-star frequency
            star3_count = stats['star_counts'][3]
            star3_frequency = star3_count / stats['frequency'] if stats['frequency'] > 0 else 0
            
            # Build display name with prefixes
            display_name = unit_name
            
            # Add star prefixes (gold takes priority over silver)
            if star3_frequency >= GOLD_3STAR_THRESHOLD:
                display_name = f"g3star_{display_name}"
            elif star3_frequency >= SILVER_3STAR_THRESHOLD:
                display_name = f"s3star_{display_name}"
            
            # Add carry prefix
            if carry_frequency >= CARRY_THRESHOLD:
                display_name = f"Carry_{display_name}"
            
            unit_display_list.append((display_name, frequency))
        
        # Sort by frequency and take top N
        unit_display_list.sort(key=lambda x: x[1], reverse=True)
        top_units = unit_display_list[:TOP_UNITS_COUNT]
        
        return ', '.join([unit[0] for unit in top_units])

    def get_enhanced_main_cluster_display(self, main_cluster_id: int) -> str:
        """Get enhanced display string for main cluster showing top units with prefixes."""
        main_cluster_compositions = [
            comp for comp in self.compositions 
            if comp.main_cluster_id == main_cluster_id
        ]
        return self.analyze_unit_properties_in_cluster(main_cluster_compositions)

    def get_enhanced_sub_cluster_display(self, sub_cluster_id: int) -> str:
        """Get enhanced display string for sub-cluster showing top units with prefixes."""
        # Find the sub-cluster
        sub_cluster = None
        for sc in self.sub_clusters:
            if sc.id == sub_cluster_id:
                sub_cluster = sc
                break
        
        if not sub_cluster:
            return ""
        
        return self.analyze_unit_properties_in_cluster(sub_cluster.compositions)

    def get_clustering_statistics(self) -> Dict:
        """Generate comprehensive clustering statistics."""
        total_compositions = len(self.compositions)
        sub_clustered = len([c for c in self.compositions if c.sub_cluster_id is not None])
        main_clustered = len([c for c in self.compositions if c.main_cluster_id is not None])
        
        # Sub-cluster statistics
        sub_cluster_sizes = [sc.size for sc in self.sub_clusters]
        
        # Main cluster statistics  
        main_cluster_compositions = defaultdict(int)
        for comp in self.compositions:
            if comp.main_cluster_id is not None:
                main_cluster_compositions[comp.main_cluster_id] += 1
        
        return {
            'total_compositions': total_compositions,
            'sub_clusters': {
                'count': len(self.sub_clusters),
                'compositions_clustered': sub_clustered,
                'avg_size': round(np.mean(sub_cluster_sizes), 1) if sub_cluster_sizes else 0,
                'largest_size': max(sub_cluster_sizes) if sub_cluster_sizes else 0
            },
            'main_clusters': {
                'count': len(set(self.main_cluster_assignments.values())),
                'sub_clusters_grouped': len(self.main_cluster_assignments),
                'compositions_clustered': main_clustered,
                'sizes': dict(main_cluster_compositions)
            }
        }
    
    def _query_jsonl(self, filename: str, filter_func=None):
        """Query JSONL file with optional filtering."""
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    match = json.loads(line.strip())
                    if filter_func is None or filter_func(match):
                        yield match


def run_incremental_clustering_pipeline(
    filters: Optional[Dict[str, Any]] = None,
    csv_filename: Optional[str] = None,
    min_sub_cluster_size: int = 5,
    min_main_cluster_size: int = 3,
    save_to_csv: bool = False,
    force_recluster: bool = False
) -> Dict:
    """
    Run incremental clustering pipeline - only cluster new/unclustered matches.
    
    :param filters: Database filters (date range, set version, queue types)
    :param csv_filename: Optional CSV file for backward compatibility
    :param min_sub_cluster_size: Minimum size for valid sub-clusters
    :param min_main_cluster_size: Minimum size for valid main clusters
    :param save_to_csv: Whether to also export results to CSV
    :param force_recluster: If True, reclusters all matches regardless of existing data
    :return: Dictionary with clustering statistics
    """
    print("=== TFT Incremental Database-Backed Clustering Pipeline ===\n")
    
    try:
        # Dynamic import to avoid circular dependencies
        clustering_ops = importlib.import_module('database.clustering_operations')
        DatabaseClusteringEngine = clustering_ops.DatabaseClusteringEngine
        
        # Initialize clustering engine
        db_engine = DatabaseClusteringEngine()
        
        if not force_recluster:
            # Find unclustered matches
            unclustered_matches = db_engine.get_unclustered_matches(filters)
            
            if not unclustered_matches:
                print("No unclustered matches found. All matches have been clustered.")
                
                # Return existing statistics
                try:
                    get_database_cluster_stats = clustering_ops.get_database_cluster_stats
                    db_stats = get_database_cluster_stats()
                    return {
                        'pipeline_stats': {'total_compositions': 0},
                        'database_stats': db_stats,
                        'message': 'No new matches to cluster'
                    }
                except Exception:
                    return {'message': 'No new matches to cluster'}
            
            print(f"Found {len(unclustered_matches)} unclustered matches")
            
            # Add filter to only process unclustered matches
            if filters is None:
                filters = {}
            filters['match_game_ids'] = unclustered_matches
        else:
            print("Force reclustering all matches...")
            # Clear existing clusters if force reclustering
            db_engine.clear_existing_clusters()
        
        # Run regular clustering pipeline with filtered data
        return run_database_clustering_pipeline(
            filters=filters,
            csv_filename=csv_filename,
            min_sub_cluster_size=min_sub_cluster_size,
            min_main_cluster_size=min_main_cluster_size,
            save_to_csv=save_to_csv
        )
        
    except ImportError as e:
        print(f"Error: Database modules not available: {e}")
        return {'error': 'Database modules not available'}
    except Exception as e:
        print(f"Error in incremental clustering pipeline: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


def run_database_clustering_pipeline(
    filters: Optional[Dict[str, Any]] = None,
    csv_filename: Optional[str] = None,
    min_sub_cluster_size: int = 5,
    min_main_cluster_size: int = 3,
    save_to_csv: bool = False
) -> Dict:
    """
    Run the complete two-level clustering pipeline using PostgreSQL database.
    
    :param filters: Database filters (date range, set version, queue types)
    :param csv_filename: Optional CSV file for backward compatibility
    :param min_sub_cluster_size: Minimum size for valid sub-clusters
    :param min_main_cluster_size: Minimum size for valid main clusters
    :param save_to_csv: Whether to also export results to CSV
    :return: Dictionary with clustering statistics
    """
    print("=== TFT Database-Backed Two-Level Clustering Pipeline ===\n")
    
    # Initialize clustering engine
    engine = TFTClusteringEngine(
        min_sub_cluster_size=min_sub_cluster_size,
        min_main_cluster_size=min_main_cluster_size
    )
    
    try:
        # Execute clustering pipeline with database backend
        engine.load_compositions_from_database(filters=filters)
        engine.create_sub_clusters()
        engine.create_main_clusters()
        
        # Save to database (primary storage)
        engine.save_results_to_database()
        
        # Optional CSV export for backward compatibility
        if save_to_csv and csv_filename:
            engine.save_results(csv_filename)
        
        # Generate statistics from database
        try:
            clustering_ops = importlib.import_module('database.clustering_operations')
            get_database_cluster_stats = clustering_ops.get_database_cluster_stats
            db_stats = get_database_cluster_stats()
        except ImportError:
            print("   Warning: Database statistics not available")
            db_stats = {'error': 'Database modules not available'}
        
        # Get legacy-compatible stats for consistency
        legacy_stats = engine.get_clustering_statistics()
        
        # Combine statistics
        combined_stats = {
            'pipeline_stats': legacy_stats,
            'database_stats': db_stats,
            'total_compositions': legacy_stats['total_compositions'],
            'sub_clusters': legacy_stats['sub_clusters'],
            'main_clusters': legacy_stats['main_clusters']
        }
        
        # Print results summary
        print(f"\n5. Clustering Results Summary:")
        print(f"   Total compositions: {combined_stats['total_compositions']}")
        print(f"   Sub-clusters: {combined_stats['sub_clusters']['count']} (avg size: {combined_stats['sub_clusters']['avg_size']})")
        print(f"   Main clusters: {combined_stats['main_clusters']['count']}")
        print(f"   Compositions in sub-clusters: {combined_stats['sub_clusters']['compositions_clustered']}")
        print(f"   Compositions in main clusters: {combined_stats['main_clusters']['compositions_clustered']}")
        
        print(f"\n{'='*70}")
        print("DATABASE-BACKED HIERARCHICAL CLUSTERING COMPLETE")
        print(f"{'='*70}")
        print("Results stored in PostgreSQL database (participant_clusters table)")
        if csv_filename and save_to_csv:
            print(f"CSV export: {csv_filename}")
        print("Sub-clusters: Exact carry matching for precise compositions")
        print("Main clusters: Groups of sub-clusters with 2-3 common carries")
        print("Carry detection: Units with 2 or more items are considered carries")
        
        return combined_stats
        
    except Exception as e:
        print(f"Error in database clustering pipeline: {e}")
        import traceback
        traceback.print_exc()
        return {}


def run_hierarchical_clustering_pipeline(
    jsonl_filename: str = 'matches_filtered.jsonl',
    csv_filename: str = 'hierarchical_clusters.csv',
    min_sub_cluster_size: int = 5,
    min_main_cluster_size: int = 3
) -> Dict:
    """
    Run the complete two-level clustering pipeline.
    
    :param jsonl_filename: Input JSONL file with match data
    :param csv_filename: Output CSV file for clustering results
    :param min_sub_cluster_size: Minimum size for valid sub-clusters
    :param min_main_cluster_size: Minimum size for valid main clusters
    :return: Dictionary with clustering statistics
    """
    print("=== TFT Two-Level Clustering Pipeline ===\n")
    
    # Initialize clustering engine
    engine = TFTClusteringEngine(
        min_sub_cluster_size=min_sub_cluster_size,
        min_main_cluster_size=min_main_cluster_size
    )
    
    try:
        # Execute clustering pipeline
        engine.load_compositions(jsonl_filename)
        engine.create_sub_clusters()
        engine.create_main_clusters()
        engine.save_results(csv_filename)
        
        # Generate statistics
        stats = engine.get_clustering_statistics()
        
        # Print results summary
        print(f"\n5. Clustering Results Summary:")
        print(f"   Total compositions: {stats['total_compositions']}")
        print(f"   Sub-clusters: {stats['sub_clusters']['count']} (avg size: {stats['sub_clusters']['avg_size']})")
        print(f"   Main clusters: {stats['main_clusters']['count']}")
        print(f"   Compositions in sub-clusters: {stats['sub_clusters']['compositions_clustered']}")
        print(f"   Compositions in main clusters: {stats['main_clusters']['compositions_clustered']}")
        
        print(f"\n{'='*70}")
        print("HIERARCHICAL CLUSTERING COMPLETE")
        print(f"{'='*70}")
        print(f"Output file: {csv_filename}")
        print("Sub-clusters: Exact carry matching for precise compositions")
        print("Main clusters: Groups of sub-clusters with 2-3 common carries")
        print("Carry detection: Units with 2 or more items are considered carries")
        print(f"Display format: Top {TOP_UNITS_COUNT} units with prefixes:")
        print(f"  - Carry_ prefix for units that are carries ≥{int(CARRY_THRESHOLD*100)}% of the time")
        print(f"  - g3star_ prefix for units that are 3-star ≥{int(GOLD_3STAR_THRESHOLD*100)}% of the time")
        print(f"  - s3star_ prefix for units that are 3-star ≥{int(SILVER_3STAR_THRESHOLD*100)}% of the time")
        
        return stats
        
    except Exception as e:
        print(f"Error in clustering pipeline: {e}")
        return {}


# Legacy compatibility functions
def query_jsonl(filename, filter_func=None):
    """Legacy compatibility function."""
    engine = TFTClusteringEngine()
    return engine._query_jsonl(filename, filter_func)


def extract_compositions(jsonl_filename):
    """Legacy compatibility function for basic composition extraction."""
    engine = TFTClusteringEngine()
    engine.load_compositions(jsonl_filename)
    
    # Convert to legacy format
    legacy_compositions = []
    for comp in engine.compositions:
        legacy_compositions.append({
            'match_id': comp.match_id,
            'puuid': comp.puuid,
            'riot_id': comp.riot_id,
            'carries': comp.carries,
            'participant_data': comp.participant_data
        })
    
    return legacy_compositions


def run_clustering_pipeline(jsonl_filename='matches_filtered.jsonl', csv_filename='clusters.csv', min_cluster_size=5):
    """Legacy compatibility function that runs new hierarchical clustering."""
    print("Note: Using new hierarchical clustering system")
    return run_hierarchical_clustering_pipeline(
        jsonl_filename=jsonl_filename,
        csv_filename=csv_filename,
        min_sub_cluster_size=min_cluster_size
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="TFT Clustering - Analyze and cluster TFT compositions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Database-backed clustering (recommended):
  python clustering.py --use-database                            # Full database clustering
  python clustering.py --use-database --incremental             # Only cluster new matches
  python clustering.py --use-database --incremental --force-recluster  # Recluster everything
  python clustering.py --use-database --csv-export clusters.csv  # Export to CSV too
  python clustering.py --use-database --set-filter TFTSet14      # Filter by TFT set
  python clustering.py --use-database --date-from 2024-08-01     # Filter by date
  
  # Legacy file-based clustering:
  python clustering.py                                    # Use default files
  python clustering.py --input matches.jsonl            # Specify input file
  python clustering.py --output my_clusters.csv         # Specify output file
  python clustering.py --min-sub-cluster-size 3         # Set minimum sub-cluster size
        """
    )
    
    # Database options
    parser.add_argument('--use-database', action='store_true',
                       help='Use PostgreSQL database instead of JSONL files (recommended)')
    parser.add_argument('--incremental', action='store_true',
                       help='Run incremental clustering (only process new/unclustered matches)')
    parser.add_argument('--force-recluster', action='store_true',
                       help='Force reclustering of all matches (clears existing clusters)')
    parser.add_argument('--csv-export', type=str,
                       help='Export clustering results to CSV file (for database mode)')
    
    # Database filters
    parser.add_argument('--set-filter', type=str,
                       help='Filter by TFT set (e.g., TFTSet14)')
    parser.add_argument('--date-from', type=str,
                       help='Filter matches from date (YYYY-MM-DD)')
    parser.add_argument('--date-to', type=str,
                       help='Filter matches to date (YYYY-MM-DD)')
    parser.add_argument('--queue-types', nargs='+', 
                       choices=['ranked', 'normal', 'hyper_roll', 'double_up'],
                       help='Filter by queue types')
    
    # Legacy file-based options
    parser.add_argument('--input', type=str, default='matches_filtered.jsonl',
                       help='Input JSONL file with match data (default: matches_filtered.jsonl)')
    parser.add_argument('--output', type=str, default='hierarchical_clusters.csv',
                       help='Output CSV file for cluster assignments (default: hierarchical_clusters.csv)')
    
    # Clustering parameters
    parser.add_argument('--min-sub-cluster-size', type=int, default=5,
                       help='Minimum size for sub-clusters (default: 5)')
    parser.add_argument('--min-main-cluster-size', type=int, default=3,
                       help='Minimum size for main clusters (default: 3)')
    parser.add_argument('--batch-size', type=int, default=10000,
                       help='Batch size for database processing (default: 10000)')
    
    args = parser.parse_args()
    
    print("TFT Clustering System")
    print("=" * 50)
    
    if args.use_database:
        # Database-backed clustering
        if args.incremental:
            print("Mode: Incremental database-backed clustering (PostgreSQL)")
        else:
            print("Mode: Full database-backed clustering (PostgreSQL)")
        
        # Build database filters
        filters = {}
        if args.set_filter:
            filters['set_core_name'] = args.set_filter
        if args.date_from:
            from datetime import datetime
            filters['date_from'] = datetime.strptime(args.date_from, '%Y-%m-%d')
        if args.date_to:
            from datetime import datetime
            filters['date_to'] = datetime.strptime(args.date_to, '%Y-%m-%d')
        if args.queue_types:
            filters['queue_types'] = args.queue_types
        
        print(f"Database filters: {filters}")
        print(f"Min sub-cluster size: {args.min_sub_cluster_size}")
        print(f"Min main cluster size: {args.min_main_cluster_size}")
        print(f"Batch size: {args.batch_size}")
        if args.incremental:
            print(f"Incremental mode: {'enabled' if not args.force_recluster else 'disabled (force recluster)'}")
        if args.csv_export:
            print(f"CSV export: {args.csv_export}")
        print()
        
        # Run appropriate clustering pipeline
        if args.incremental:
            stats = run_incremental_clustering_pipeline(
                filters=filters,
                csv_filename=args.csv_export,
                min_sub_cluster_size=args.min_sub_cluster_size,
                min_main_cluster_size=args.min_main_cluster_size,
                save_to_csv=bool(args.csv_export),
                force_recluster=args.force_recluster
            )
        else:
            stats = run_database_clustering_pipeline(
                filters=filters,
                csv_filename=args.csv_export,
                min_sub_cluster_size=args.min_sub_cluster_size,
                min_main_cluster_size=args.min_main_cluster_size,
                save_to_csv=bool(args.csv_export)
            )
        
    else:
        # Legacy file-based clustering
        print("Mode: File-based clustering (legacy)")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Min sub-cluster size: {args.min_sub_cluster_size}")
        print(f"Min main cluster size: {args.min_main_cluster_size}")
        print()
        
        # Run the hierarchical clustering pipeline
        stats = run_hierarchical_clustering_pipeline(
            jsonl_filename=args.input,
            csv_filename=args.output,
            min_sub_cluster_size=args.min_sub_cluster_size,
            min_main_cluster_size=args.min_main_cluster_size
        )
    
    if stats:
        print(f"\n{'='*60}")
        print("CLUSTERING COMPLETE")
        print(f"{'='*60}")
        sub_count = stats['sub_clusters']['count']
        main_count = stats['main_clusters']['count']
        total_comps = stats['total_compositions']
        print(f"Generated {sub_count} sub-clusters and {main_count} main clusters from {total_comps} compositions")
        
        # Export all main clusters to CSV
        print(f"\n{'='*60}")
        print("EXPORTING MAIN CLUSTERS TO CSV")
        print(f"{'='*60}")
        
        try:
            # Get cluster statistics without printing
            from querying import TFTQuery, load_clusters
            import csv
            
            # Load cluster data
            clusters = load_clusters(args.output)
            if not clusters:
                print("No cluster data found")
            else:
                # Get all main cluster IDs
                main_cluster_ids = set()
                for cluster_info in clusters.values():
                    if cluster_info['main_cluster_id'] != -1:
                        main_cluster_ids.add(cluster_info['main_cluster_id'])
                
                main_cluster_stats = []
                
                # Create clustering engine to access sub-cluster data
                engine = TFTClusteringEngine()
                engine.load_compositions(args.input)
                engine.create_sub_clusters()
                engine.create_main_clusters()
                
                # Calculate stats for each main cluster
                for cluster_id in sorted(main_cluster_ids):
                    query = TFTQuery(args.input, args.output)
                    query.set_main_cluster(cluster_id)
                    stats = query.get_stats()
                    
                    if stats['play_count'] > 0:
                        # Get enhanced display with top units and prefixes
                        enhanced_display = engine.get_enhanced_main_cluster_display(cluster_id)
                        
                        main_cluster_stats.append({
                            'cluster_id': cluster_id,
                            'size': stats['play_count'],
                            'top_units': enhanced_display,
                            'avg_place': stats['avg_placement'],
                            'winrate': stats['winrate'],
                            'top4_rate': stats['top4_rate'],
                            'frequency': (stats['play_count'] / total_comps) * 100
                        })
                
                # Sort by avg_place ascending (best placement first)
                main_cluster_stats.sort(key=lambda x: x['avg_place'])
                
                # Export to CSV
                csv_filename = args.output.replace('.csv', '_main_clusters_analysis.csv')
                with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['rank', 'cluster_id', 'size', f'top_{TOP_UNITS_COUNT}_units', 'avg_place', 'winrate', 'top4_rate', 'frequency']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for i, cluster in enumerate(main_cluster_stats, 1):
                        writer.writerow({
                            'rank': i,
                            'cluster_id': cluster['cluster_id'],
                            'size': cluster['size'],
                            f'top_{TOP_UNITS_COUNT}_units': cluster['top_units'],
                            'avg_place': f"{cluster['avg_place']:.2f}",
                            'winrate': f"{cluster['winrate']:.1f}%",
                            'top4_rate': f"{cluster['top4_rate']:.1f}%",
                            'frequency': f"{cluster['frequency']:.1f}%"
                        })
                
                print(f"Exported {len(main_cluster_stats)} main clusters to: {csv_filename}")
                
                # Create folder for individual main cluster CSV files
                import os
                detailed_folder = args.output.replace('.csv', '_detailed_analysis')
                os.makedirs(detailed_folder, exist_ok=True)
                print(f"\nCreating detailed analysis in folder: {detailed_folder}")
                
                # Export sub-cluster details for each main cluster
                for cluster in main_cluster_stats:
                    cluster_id = cluster['cluster_id']
                    cluster_filename = os.path.join(detailed_folder, f"main_cluster_{cluster_id:02d}_subclusters.csv")
                    
                    # Get sub-clusters that belong to this main cluster
                    main_cluster_sub_clusters = []
                    for sub_cluster in engine.sub_clusters:
                        if engine.main_cluster_assignments.get(sub_cluster.id) == cluster_id:
                            main_cluster_sub_clusters.append(sub_cluster)
                    
                    # Write sub-cluster details to CSV
                    with open(cluster_filename, 'w', newline='', encoding='utf-8') as subfile:
                        subwriter = csv.DictWriter(subfile, fieldnames=[
                            'sub_cluster_id', 'size', f'top_{TOP_UNITS_COUNT}_units', 'avg_place', 'winrate', 'top4_rate'
                        ])
                        subwriter.writeheader()
                        
                        # Sort sub-clusters by avg_place
                        main_cluster_sub_clusters.sort(key=lambda x: x.avg_placement)
                        
                        for sub_cluster in main_cluster_sub_clusters:
                            # Get enhanced display for sub-cluster
                            enhanced_sub_display = engine.get_enhanced_sub_cluster_display(sub_cluster.id)
                            
                            subwriter.writerow({
                                'sub_cluster_id': sub_cluster.id,
                                'size': sub_cluster.size,
                                f'top_{TOP_UNITS_COUNT}_units': enhanced_sub_display,
                                'avg_place': f"{sub_cluster.avg_placement:.2f}",
                                'winrate': f"{sub_cluster.winrate:.1f}%",
                                'top4_rate': f"{sub_cluster.top4_rate:.1f}%"
                            })
                
                print(f"\nTop 5 Main Clusters (by avg placement):")
                print(f"Top {TOP_UNITS_COUNT} units by frequency - Carry ≥{int(CARRY_THRESHOLD*100)}%, g3star ≥{int(GOLD_3STAR_THRESHOLD*100)}%, s3star ≥{int(SILVER_3STAR_THRESHOLD*100)}%:")
                print(f"{'Rank':<4} {'ID':<4} {'Size':<6} {'Avg Place':<10} {'Winrate':<9} {'Top4':<8} {'Top Units'}")
                print(f"{'-'*120}")
                for i, cluster in enumerate(main_cluster_stats[:5], 1):
                    units_short = cluster['top_units'][:80] + "..." if len(cluster['top_units']) > 80 else cluster['top_units']
                    avg_place_display = f"{cluster['avg_place']:.2f}"
                    winrate_display = f"{cluster['winrate']:.1f}%"
                    top4_display = f"{cluster['top4_rate']:.1f}%"
                    print(f"{i:<4} {cluster['cluster_id']:<4} {cluster['size']:<6} {avg_place_display:<10} {winrate_display:<9} {top4_display:<8} {units_short}")
                
        except Exception as e:
            print(f"Error creating main clusters analysis: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\nFiles generated:")
        print(f"  - {args.output}: Cluster assignments")
        csv_analysis_file = args.output.replace('.csv', '_main_clusters_analysis.csv')
        print(f"  - {csv_analysis_file}: Main clusters analysis (CSV)")
        detailed_folder = args.output.replace('.csv', '_detailed_analysis')
        print(f"  - {detailed_folder}/: Individual CSV files for each main cluster's sub-clusters")
        print(f"\nNext steps:")
        print(f"  - Run querying: python querying.py --input {args.input} --clusters {args.output}")
        print(f"  - Open {csv_analysis_file} in Excel/spreadsheet for detailed analysis")
        print(f"  - Explore individual main cluster details in {detailed_folder}/ folder")
    else:
        print("\nClustering failed!")