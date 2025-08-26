#!/usr/bin/env python3
"""
Example usage of the updated TFT querying system.
Demonstrates both database and legacy modes with various query types.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Demonstrate TFT querying system usage."""
    
    print("TFT Querying System - Example Usage")
    print("=" * 50)
    
    # Import the new TFT querying system
    from querying import TFTQuery
    
    print("\n1. Basic Unit Query")
    print("-" * 30)
    
    # Create a query for compositions with Aphelios
    query = TFTQuery()  # Auto-detects database vs legacy mode
    stats = query.add_unit('TFT14_Aphelios').get_stats()
    
    if stats:
        print(f"Aphelios compositions:")
        print(f"  Matches: {stats['play_count']}")
        print(f"  Average Placement: {stats['avg_placement']}")
        print(f"  Win Rate: {stats['winrate']}%")
        print(f"  Top 4 Rate: {stats['top4_rate']}%")
    else:
        print("No Aphelios compositions found")
    
    print("\n2. Complex Multi-Filter Query")
    print("-" * 30)
    
    # Create a complex query with multiple filters
    complex_query = (TFTQuery()
                    .add_unit('TFT14_Aphelios')
                    .add_trait('TFT14_Vanguard', min_tier=2)
                    .add_player_level(min_level=8))
    
    complex_stats = complex_query.get_stats()
    
    if complex_stats:
        print(f"Aphelios + Vanguard 2+ + Level 8+ compositions:")
        print(f"  Matches: {complex_stats['play_count']}")
        print(f"  Average Placement: {complex_stats['avg_placement']}")
        print(f"  Win Rate: {complex_stats['winrate']}%")
        print(f"  Top 4 Rate: {complex_stats['top4_rate']}%")
    else:
        print("No matching complex compositions found")
    
    print("\n3. Cluster-Based Query")
    print("-" * 30)
    
    # Query a specific cluster
    cluster_query = TFTQuery().set_sub_cluster(1)  # Get cluster 1 compositions
    cluster_stats = cluster_query.get_stats()
    
    if cluster_stats:
        print(f"Sub-cluster 1 compositions:")
        print(f"  Matches: {cluster_stats['play_count']}")
        print(f"  Average Placement: {cluster_stats['avg_placement']}")
        print(f"  Win Rate: {cluster_stats['winrate']}%")
        print(f"  Top 4 Rate: {cluster_stats['top4_rate']}%")
    else:
        print("No compositions found in sub-cluster 1")
    
    print("\n4. Cluster Statistics Overview")
    print("-" * 30)
    
    # Get top performing clusters
    try:
        cluster_stats = TFTQuery.get_all_cluster_stats(min_size=5, cluster_type='sub')
        
        if cluster_stats:
            print(f"Top 5 Sub-Clusters:")
            print(f"{'ID':<4} {'Plays':<6} {'Avg Place':<10} {'Win%':<8} {'Top4%':<8} {'Carries'}")
            print("-" * 50)
            
            for i, stats in enumerate(cluster_stats[:5]):
                carries = ', '.join(stats['carries'][:3])  # Show first 3 carries
                if len(stats['carries']) > 3:
                    carries += "..."
                    
                print(f"{stats['cluster_id']:<4} {stats['play_count']:<6} {stats['avg_place']:<10} {stats['winrate']:<7.1f}% {stats['top4']:<7.1f}% {carries}")
        else:
            print("No cluster statistics available")
            
    except Exception as e:
        print(f"Error getting cluster stats: {e}")
    
    print("\n5. Advanced Filtering Examples")
    print("-" * 30)
    
    # High-level compositions
    high_level = TFTQuery().add_player_level(min_level=9).get_stats()
    if high_level:
        print(f"Level 9+ compositions: {high_level['play_count']} matches, {high_level['avg_placement']:.2f} avg place")
    
    # Specific trait tier
    vanguard_3 = TFTQuery().add_trait('TFT14_Vanguard', min_tier=3, max_tier=3).get_stats()
    if vanguard_3:
        print(f"Vanguard 3 compositions: {vanguard_3['play_count']} matches, {vanguard_3['avg_placement']:.2f} avg place")
    
    # Unit with items
    aphelios_items = TFTQuery().add_unit_item_count('TFT14_Aphelios', min_count=2).get_stats()
    if aphelios_items:
        print(f"Aphelios with 2+ items: {aphelios_items['play_count']} matches, {aphelios_items['avg_placement']:.2f} avg place")
    
    print("\n6. Database vs Legacy Mode")
    print("-" * 30)
    
    # Show which mode is being used
    test_query = TFTQuery()
    mode = "Database" if test_query.use_database else "Legacy File-based"
    print(f"Current mode: {mode}")
    
    # Force database mode (if available)
    try:
        db_query = TFTQuery(use_database=True)
        db_mode = "Database" if db_query.use_database else "Legacy (fallback)"
        print(f"Forced database mode: {db_mode}")
    except Exception as e:
        print(f"Database mode not available: {e}")
    
    # Force legacy mode
    try:
        legacy_query = TFTQuery(use_database=False)
        legacy_mode = "Database" if legacy_query.use_database else "Legacy File-based"
        print(f"Forced legacy mode: {legacy_mode}")
    except Exception as e:
        print(f"Legacy mode not available: {e}")
    
    print("\n" + "=" * 50)
    print("Example completed!")
    print("=" * 50)
    
    print("\nTips for usage:")
    print("- Use TFTQuery() for automatic mode detection")
    print("- Chain multiple filters for complex queries")
    print("- Use get_stats() for statistical summaries")
    print("- Use execute() for raw participant data")
    print("- Check cluster statistics for meta analysis")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)