#!/usr/bin/env python3
"""
Test Database Integration for TFT Data Collection

This script tests the database integration functionality before running
the full data collection system.
"""

import os
import sys
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Test database connection and setup."""
    print("=== Testing Database Connection ===")
    
    try:
        from database.connection import test_connection, get_database_stats
        
        # Test connection
        connection_test = test_connection()
        if connection_test['success']:
            print(f"✓ Database connected successfully")
            print(f"✓ Database version: {connection_test['database_version']}")
            print(f"✓ Response time: {connection_test['response_time_ms']}ms")
            return True
        else:
            print(f"✗ Database connection failed: {connection_test.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"✗ Database connection test failed: {e}")
        return False

def test_migration_functions():
    """Test the database migration functions."""
    print("\n=== Testing Migration Functions ===")
    
    try:
        from database.connection import execute_query
        
        # Test if functions exist
        functions_to_test = [
            'insert_match_data',
            'batch_insert_matches',
            'match_exists',
            'get_match_import_stats',
            'validate_match_integrity'
        ]
        
        for func_name in functions_to_test:
            try:
                result = execute_query(
                    f"SELECT proname FROM pg_proc WHERE proname = '{func_name}'"
                )
                if result:
                    print(f"✓ Function {func_name} exists")
                else:
                    print(f"✗ Function {func_name} missing")
                    return False
            except Exception as e:
                print(f"✗ Error checking function {func_name}: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Migration function test failed: {e}")
        return False

def test_data_import_utilities():
    """Test the data import utilities."""
    print("\n=== Testing Data Import Utilities ===")
    
    try:
        from database.data_import import MatchDataImporter, get_database_stats
        
        # Test importer initialization
        importer = MatchDataImporter()
        print("✓ MatchDataImporter initialized")
        
        # Test database stats
        stats = get_database_stats()
        print(f"✓ Database stats retrieved: {stats.get('matches', 0)} matches")
        
        return True
        
    except Exception as e:
        print(f"✗ Data import utilities test failed: {e}")
        return False

def test_sample_match_insertion():
    """Test inserting a sample match."""
    print("\n=== Testing Sample Match Insertion ===")
    
    # Create a minimal valid match structure for testing
    sample_match = {
        "metadata": {
            "match_id": "TEST_MATCH_" + datetime.now().strftime("%Y%m%d_%H%M%S"),
            "data_version": "test"
        },
        "info": {
            "game_datetime": int(datetime.now().timestamp() * 1000),
            "game_length": 1800,  # 30 minutes in seconds
            "game_version": "Version 14.1.1",
            "queue_id": 1160,
            "queue_type": "Ranked TFT",
            "game_mode": "TFT",
            "tft_set_data": {
                "set_core_name": "TFTSet14",
                "mutator": ""
            },
            "participants": []
        }
    }
    
    # Add 8 test participants
    for i in range(8):
        participant = {
            "puuid": f"test_puuid_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "summoner_name": f"TestPlayer{i}",
            "summoner_level": 30,
            "profile_icon_id": 1,
            "placement": i + 1,
            "level": 8,
            "last_round": 25,
            "players_eliminated": 0,
            "time_eliminated": 0 if i < 4 else 1500 + (i * 100),
            "total_damage_to_players": 5000 + (i * 500),
            "gold_left": 10 - i,
            "augments": ["TFT14_Augment_Test1", "TFT14_Augment_Test2"],
            "companion": {"content_ID": "test_companion", "item_ID": 1, "skin_ID": 1, "species": "Test"},
            "traits": [
                {"name": "Shapeshifter", "num_units": 2, "tier_current": 1, "tier_total": 3, "style": 1},
                {"name": "Invoker", "num_units": 3, "tier_current": 2, "tier_total": 4, "style": 2}
            ],
            "units": [
                {
                    "character_id": "TFT14_TestUnit1",
                    "name": "Test Unit 1",
                    "tier": 3,
                    "rarity": 2,
                    "chosen": False,
                    "itemNames": ["BF Sword", "Chain Vest"],
                    "character_traits": ["Shapeshifter"]
                },
                {
                    "character_id": "TFT14_TestUnit2", 
                    "name": "Test Unit 2",
                    "tier": 2,
                    "rarity": 1,
                    "chosen": True,
                    "itemNames": ["Rod of Ages"],
                    "character_traits": ["Invoker"]
                }
            ]
        }
        sample_match["info"]["participants"].append(participant)
    
    try:
        from database.data_import import insert_match_data
        
        # Test match insertion
        success, message = insert_match_data(sample_match)
        
        if success:
            print(f"✓ Sample match inserted successfully: {message}")
            return True
        else:
            print(f"✗ Sample match insertion failed: {message}")
            return False
            
    except Exception as e:
        print(f"✗ Sample match insertion test failed: {e}")
        return False

def test_data_collection_config():
    """Test data collection configuration."""
    print("\n=== Testing Data Collection Configuration ===")
    
    try:
        # Import the data collection module to test configuration
        import data_collection
        
        # Check if database imports are available
        if hasattr(data_collection, 'DATABASE_AVAILABLE'):
            if data_collection.DATABASE_AVAILABLE:
                print("✓ Database functionality available in data_collection")
            else:
                print("✗ Database functionality not available in data_collection")
                return False
        
        # Test configuration constants
        config_items = [
            'USE_DATABASE',
            'ENABLE_JSONL_BACKUP', 
            'DB_BATCH_SIZE',
            'ENABLE_DB_VALIDATION'
        ]
        
        for item in config_items:
            if hasattr(data_collection, item):
                value = getattr(data_collection, item)
                print(f"✓ Config {item}: {value}")
            else:
                print(f"✗ Config {item} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Data collection configuration test failed: {e}")
        return False

def cleanup_test_data():
    """Clean up test data."""
    print("\n=== Cleaning Up Test Data ===")
    
    try:
        from database.connection import execute_query
        
        # Remove test matches
        result = execute_query(
            "DELETE FROM matches WHERE game_id LIKE 'TEST_MATCH_%'"
        )
        print("✓ Test data cleaned up")
        return True
        
    except Exception as e:
        print(f"✗ Cleanup failed: {e}")
        return False

def main():
    """Run all database integration tests."""
    print("TFT Database Integration Test Suite")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Migration Functions", test_migration_functions),
        ("Data Import Utilities", test_data_import_utilities),
        ("Sample Match Insertion", test_sample_match_insertion),
        ("Data Collection Config", test_data_collection_config),
        ("Cleanup", cleanup_test_data)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            break
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {failed}")
    print(f"Success rate: {passed/(passed+failed)*100:.1f}%" if (passed+failed) > 0 else "No tests run")
    
    if failed == 0:
        print("\n✓ All tests passed! Database integration is ready.")
        print("You can now run data_collection.py with database integration enabled.")
    else:
        print(f"\n✗ {failed} test(s) failed. Please check the database setup.")
        print("Make sure PostgreSQL is running and the database is properly migrated.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)