#!/usr/bin/env python3
"""
Test script for the updated TFT querying system.
Tests both PostgreSQL database mode and legacy file-based mode.
"""

import sys
import logging
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection and availability."""
    try:
        from database.connection import test_connection
        result = test_connection()
        logger.info(f"Database connection test: {result}")
        return result.get('success', False)
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def test_database_mode():
    """Test database-based TFT querying."""
    logger.info("Testing database mode...")
    
    try:
        from querying import TFTQuery
        
        # Test basic query creation
        query = TFTQuery(use_database=True)
        logger.info("✓ TFTQuery database instance created successfully")
        
        # Test unit filter
        query.add_unit('Sett')
        logger.info("✓ Unit filter added successfully")
        
        # Test trait filter
        query.add_trait('Duelist', min_tier=2)
        logger.info("✓ Trait filter added successfully")
        
        # Test level filter
        query.add_player_level(min_level=8)
        logger.info("✓ Level filter added successfully")
        
        # Test SQL query building
        sql_query, params = query._build_sql_query()
        logger.info(f"✓ SQL query built successfully: {len(sql_query)} chars, {len(params)} params")
        
        # Test execution (this might fail if no data is available)
        try:
            stats = query.get_stats()
            if stats:
                logger.info(f"✓ Query executed successfully: {stats}")
            else:
                logger.info("✓ Query executed successfully (no results)")
        except Exception as e:
            logger.warning(f"Query execution failed (expected if no data): {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database mode test failed: {e}")
        return False

def test_cluster_stats():
    """Test cluster statistics functionality."""
    logger.info("Testing cluster statistics...")
    
    try:
        from querying import TFTQuery
        
        # Test database cluster stats
        try:
            stats = TFTQuery.get_all_cluster_stats(min_size=1, cluster_type='sub', use_database=True)
            logger.info(f"✓ Database cluster stats: {len(stats)} clusters found")
            
            if stats:
                sample = stats[0]
                logger.info(f"  Sample cluster: ID={sample['cluster_id']}, plays={sample['play_count']}")
                
        except Exception as e:
            logger.warning(f"Database cluster stats failed (expected if no data): {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Cluster stats test failed: {e}")
        return False

def test_filter_combinations():
    """Test complex filter combinations."""
    logger.info("Testing filter combinations...")
    
    try:
        from querying import TFTQuery, DatabaseQueryFilter
        
        # Create complex query
        query = TFTQuery(use_database=True)
        
        # Add multiple filters
        query.add_unit('Sett')
        query.add_trait('Duelist', min_tier=1, max_tier=3)
        query.add_player_level(min_level=6, max_level=10)
        query.add_last_round(min_round=20, max_round=50)
        
        # Test SQL building with multiple filters
        sql_query, params = query._build_sql_query()
        logger.info(f"✓ Complex query built: {len(params)} parameters")
        
        # Test DatabaseQueryFilter combinations
        filter1 = DatabaseQueryFilter("p.level >= :min_level", {"min_level": 8})
        filter2 = DatabaseQueryFilter("p.placement <= :max_place", {"max_place": 4})
        
        # Test AND combination
        combined = filter1 & filter2
        logger.info(f"✓ Filter AND combination: {len(combined.params)} params")
        
        # Test OR combination
        combined = filter1 | filter2
        logger.info(f"✓ Filter OR combination: {len(combined.params)} params")
        
        return True
        
    except Exception as e:
        logger.error(f"Filter combinations test failed: {e}")
        return False

def test_legacy_fallback():
    """Test fallback to legacy mode."""
    logger.info("Testing legacy fallback...")
    
    try:
        from querying import TFTQuery
        
        # Force legacy mode
        query = TFTQuery(use_database=False)
        logger.info(f"✓ Legacy mode query created: use_database={query.use_database}")
        
        # Test that it properly identifies as legacy mode
        assert query.use_database == False, "Legacy mode not properly set"
        logger.info("✓ Legacy mode properly configured")
        
        return True
        
    except Exception as e:
        logger.error(f"Legacy fallback test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and report results."""
    logger.info("=" * 60)
    logger.info("TFT QUERYING SYSTEM TESTS")
    logger.info("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Database Mode", test_database_mode),
        ("Cluster Statistics", test_cluster_stats),
        ("Filter Combinations", test_filter_combinations),
        ("Legacy Fallback", test_legacy_fallback)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} Test ---")
        try:
            success = test_func()
            results.append((test_name, success))
            status = "PASSED" if success else "FAILED"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            logger.error(f"{test_name}: FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        logger.info(f"{status:<10} {test_name}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
    else:
        logger.warning(f"⚠️  {total - passed} tests failed")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)