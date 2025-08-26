#!/usr/bin/env python3
"""
Test script for database-backed TFT clustering system.

This script tests the complete clustering pipeline with database integration,
including data loading, clustering algorithms, and result storage.
"""

import sys
import time
import traceback
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_database_connection():
    """Test basic database connection."""
    print("=== Testing Database Connection ===")
    
    try:
        from database.connection import test_connection, health_check
        
        # Test connection
        connection_result = test_connection()
        
        if connection_result['success']:
            print("✓ Database connection successful")
            print(f"  - Response time: {connection_result['response_time_ms']}ms")
            print(f"  - Database version: {connection_result['database_version']}")
            print(f"  - Host: {connection_result['connection_info']['host']}:{connection_result['connection_info']['port']}")
        else:
            print("✗ Database connection failed")
            print(f"  - Error: {connection_result.get('error', 'Unknown error')}")
            return False
        
        # Health check
        print("\n--- Database Health Check ---")
        health = health_check()
        
        if health['overall_status'] == 'healthy':
            print("✓ Database health check passed")
            print(f"  - Tables in public schema: {health['query_test'].get('table_count', 'Unknown')}")
        else:
            print("⚠ Database health check warning")
            print(f"  - Status: {health['overall_status']}")
            
        return True
        
    except ImportError as e:
        print(f"✗ Database modules not available: {e}")
        return False
    except Exception as e:
        print(f"✗ Database connection test failed: {e}")
        traceback.print_exc()
        return False


def test_clustering_operations():
    """Test database clustering operations."""
    print("\n=== Testing Database Clustering Operations ===")
    
    try:
        from database.clustering_operations import DatabaseClusteringEngine, ClusteringConfig
        
        # Initialize clustering engine
        config = ClusteringConfig(
            min_sub_cluster_size=3,  # Lower threshold for testing
            min_main_cluster_size=2,
            batch_size=100
        )
        
        engine = DatabaseClusteringEngine(config)
        print("✓ Database clustering engine initialized")
        
        # Test data extraction
        print("\n--- Testing Data Extraction ---")
        
        # Extract sample data (limit to small batch for testing)
        compositions = engine.extract_carry_compositions(
            batch_size=50,
            filters={'queue_types': ['ranked']}  # Filter to reduce data size
        )
        
        print(f"✓ Extracted {len(compositions)} compositions with carries")
        
        if compositions:
            sample = compositions[0]
            print(f"  - Sample composition: {sample['game_id']} / {sample['puuid']}")
            print(f"  - Carry units: {list(sample['carries'])}")
            print(f"  - Placement: {sample['placement']}")
        
        # Test existing clusters retrieval
        print("\n--- Testing Existing Clusters ---")
        existing = engine.get_existing_clusters()
        print(f"✓ Found {len(existing)} existing cluster assignments")
        
        # Test statistics calculation
        print("\n--- Testing Statistics Calculation ---")
        stats = engine.calculate_cluster_statistics()
        
        if 'error' not in stats:
            basic = stats.get('basic_statistics', {})
            print("✓ Cluster statistics calculated")
            print(f"  - Total participants: {basic.get('total_participants', 0)}")
            print(f"  - Sub-clusters: {basic.get('unique_sub_clusters', 0)}")
            print(f"  - Main clusters: {basic.get('unique_main_clusters', 0)}")
        else:
            print(f"⚠ Statistics calculation had issues: {stats['error']}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Clustering operations modules not available: {e}")
        return False
    except Exception as e:
        print(f"✗ Clustering operations test failed: {e}")
        traceback.print_exc()
        return False


def test_clustering_pipeline():
    """Test the complete clustering pipeline."""
    print("\n=== Testing Complete Clustering Pipeline ===")
    
    try:
        from clustering import run_database_clustering_pipeline
        
        print("Running small-scale database clustering test...")
        
        # Run clustering with filters to limit data size
        test_filters = {
            'queue_types': ['ranked'],
            'date_from': '2024-08-01',  # Recent data
            'set_core_name': 'TFTSet14'  # Specific set
        }
        
        start_time = time.time()
        
        result = run_database_clustering_pipeline(
            filters=test_filters,
            min_sub_cluster_size=3,  # Lower thresholds for testing
            min_main_cluster_size=2,
            save_to_csv=False  # Don't create CSV for test
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if result and 'error' not in result:
            print("✓ Clustering pipeline completed successfully")
            print(f"  - Processing time: {processing_time:.2f} seconds")
            
            if 'total_compositions' in result:
                print(f"  - Total compositions: {result['total_compositions']}")
            
            if 'sub_clusters' in result:
                sub_stats = result['sub_clusters']
                print(f"  - Sub-clusters created: {sub_stats.get('count', 0)}")
                print(f"  - Compositions in sub-clusters: {sub_stats.get('compositions_clustered', 0)}")
            
            if 'main_clusters' in result:
                main_stats = result['main_clusters']
                print(f"  - Main clusters created: {main_stats.get('count', 0)}")
                print(f"  - Compositions in main clusters: {main_stats.get('compositions_clustered', 0)}")
            
            return True
        else:
            print("✗ Clustering pipeline failed")
            if result and 'error' in result:
                print(f"  - Error: {result['error']}")
            return False
            
    except ImportError as e:
        print(f"✗ Clustering pipeline modules not available: {e}")
        return False
    except Exception as e:
        print(f"✗ Clustering pipeline test failed: {e}")
        traceback.print_exc()
        return False


def test_incremental_clustering():
    """Test incremental clustering functionality."""
    print("\n=== Testing Incremental Clustering ===")
    
    try:
        from clustering import run_incremental_clustering_pipeline
        
        print("Testing incremental clustering detection...")
        
        # Test filters
        test_filters = {
            'queue_types': ['ranked'],
            'set_core_name': 'TFTSet14'
        }
        
        start_time = time.time()
        
        result = run_incremental_clustering_pipeline(
            filters=test_filters,
            min_sub_cluster_size=3,
            min_main_cluster_size=2,
            save_to_csv=False,
            force_recluster=False  # Test incremental mode
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if result and 'error' not in result:
            print("✓ Incremental clustering completed")
            print(f"  - Processing time: {processing_time:.2f} seconds")
            
            if 'message' in result:
                print(f"  - Message: {result['message']}")
            elif 'total_compositions' in result:
                print(f"  - New compositions processed: {result['total_compositions']}")
            
            return True
        else:
            print("✗ Incremental clustering failed")
            if result and 'error' in result:
                print(f"  - Error: {result['error']}")
            return False
            
    except ImportError as e:
        print(f"✗ Incremental clustering modules not available: {e}")
        return False
    except Exception as e:
        print(f"✗ Incremental clustering test failed: {e}")
        traceback.print_exc()
        return False


def test_analysis_functions():
    """Test advanced analysis functions."""
    print("\n=== Testing Analysis Functions ===")
    
    try:
        from database.clustering_operations import (
            get_cluster_performance_summary,
            get_carry_unit_analysis
        )
        
        # Test cluster performance summary
        print("--- Testing Cluster Performance Summary ---")
        performance = get_cluster_performance_summary()
        
        if 'error' not in performance:
            summary = performance.get('summary', {})
            clusters = performance.get('clusters', [])
            
            print("✓ Cluster performance summary retrieved")
            print(f"  - Total clusters analyzed: {summary.get('total_clusters', 0)}")
            print(f"  - Average cluster size: {summary.get('avg_cluster_size', 0)}")
            
            if clusters:
                best = clusters[0]
                print(f"  - Best performing cluster: #{best['main_cluster_id']} "
                      f"(avg placement: {best['avg_placement']})")
        else:
            print(f"⚠ Cluster performance summary had issues: {performance['error']}")
        
        # Test carry unit analysis
        print("\n--- Testing Carry Unit Analysis ---")
        carry_analysis = get_carry_unit_analysis()
        
        if 'error' not in carry_analysis:
            summary = carry_analysis.get('summary', {})
            carries = carry_analysis.get('top_carries', [])
            
            print("✓ Carry unit analysis retrieved")
            print(f"  - Carries analyzed: {summary.get('total_carries_analyzed', 0)}")
            print(f"  - Most popular: {summary.get('most_popular', 'N/A')}")
            print(f"  - Best performer: {summary.get('best_performer', 'N/A')}")
            print(f"  - Most versatile: {summary.get('most_versatile', 'N/A')}")
            
            if carries:
                top = carries[0]
                print(f"  - Top carry details: {top['unit_name']} "
                      f"({top['total_appearances']} appearances, "
                      f"avg placement: {top['avg_placement']})")
        else:
            print(f"⚠ Carry unit analysis had issues: {carry_analysis['error']}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Analysis function modules not available: {e}")
        return False
    except Exception as e:
        print(f"✗ Analysis functions test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all database clustering tests."""
    print("TFT Database-Backed Clustering System Test Suite")
    print("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Clustering Operations", test_clustering_operations),
        ("Clustering Pipeline", test_clustering_pipeline),
        ("Incremental Clustering", test_incremental_clustering),
        ("Analysis Functions", test_analysis_functions)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            if test_func():
                passed += 1
                print(f"\n✓ {test_name} PASSED")
            else:
                print(f"\n✗ {test_name} FAILED")
        except KeyboardInterrupt:
            print(f"\n⚠ {test_name} INTERRUPTED")
            break
        except Exception as e:
            print(f"\n✗ {test_name} ERROR: {e}")
    
    # Final results
    print(f"\n{'='*60}")
    print("TEST RESULTS")
    print(f"{'='*60}")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All tests passed! Database clustering system is ready.")
        return True
    else:
        print("⚠ Some tests failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)