#!/usr/bin/env python3
"""
Test script to verify the TFT Streamlit app works correctly
with graceful database fallback handling.
"""

import sys
import os

def test_imports():
    """Test that all necessary imports work."""
    print("=== Testing Imports ===")
    try:
        # Test streamlit app imports
        import streamlit_app
        print("[OK] streamlit_app imported successfully")
        
        # Test querying imports
        from querying import TFTQuery, analyze_top_clusters, print_cluster_compositions
        print("[OK] querying module imported successfully")
        
        # Check what mode we're in
        import querying
        print(f"   Database support: {querying.HAS_DATABASE}")
        print(f"   File support: {querying.HAS_FILE_SUPPORT}")
        
        return True
    except Exception as e:
        print(f"[ERROR] Import error: {e}")
        return False

def test_data_loading():
    """Test data loading functions."""
    print("\n=== Testing Data Loading ===")
    try:
        import streamlit_app
        
        # Test main clusters loading
        main_clusters = streamlit_app.load_main_clusters()
        print(f"[OK] Main clusters loaded: {len(main_clusters)} clusters")
        
        # Test subclusters loading
        subclusters = streamlit_app.load_subcluster_files()
        print(f"[OK] Subclusters loaded: {len(subclusters)} main clusters")
        
        return True
    except Exception as e:
        print(f"[ERROR] Data loading error: {e}")
        return False

def test_query_functionality():
    """Test TFT query functionality."""
    print("\n=== Testing Query Functionality ===")
    try:
        import streamlit_app
        from querying import TFTQuery
        
        # Test basic query
        query = TFTQuery()
        query = query.add_unit('TFT14_Aphelios')
        stats = query.get_stats()
        print(f"[OK] Basic query works: {stats}")
        
        # Test query through streamlit app
        result = streamlit_app.execute_query("TFTQuery().add_unit('TFT14_Jinx').get_stats()")
        print(f"[OK] Streamlit query execution works: {result}")
        
        # Test error handling
        error_result = streamlit_app.execute_query("invalid_query_syntax")
        print(f"[OK] Error handling works: {error_result}")
        
        return True
    except Exception as e:
        print(f"[ERROR] Query functionality error: {e}")
        return False

def test_database_fallback():
    """Test database fallback handling."""
    print("\n=== Testing Database Fallback ===")
    try:
        import querying
        
        # Check current state
        if querying.HAS_DATABASE:
            print("[OK] Database support detected")
            query_type = "database-backed"
        elif querying.HAS_FILE_SUPPORT:
            print("[OK] File support detected (database unavailable)")
            query_type = "file-based"
        else:
            print("[OK] Fallback mode detected (minimal functionality)")
            query_type = "fallback"
        
        # Test that TFTQuery works regardless
        query = querying.TFTQuery()
        result = query.add_unit('TFT14_Aphelios').get_stats()
        print(f"[OK] {query_type} querying works: {result}")
        
        return True
    except Exception as e:
        print(f"[ERROR] Database fallback error: {e}")
        return False

def check_required_files():
    """Check if required files exist."""
    print("\n=== Checking Required Files ===")
    
    required_files = [
        ('hierarchical_clusters_main_clusters_analysis.csv', 'Main clusters analysis'),
        ('hierarchical_clusters.csv', 'Cluster assignments'),
        ('matches_filtered.jsonl', 'Match data'),
        ('hierarchical_clusters_detailed_analysis', 'Detailed analysis directory')
    ]
    
    all_exist = True
    for file_path, description in required_files:
        if os.path.exists(file_path):
            print(f"[OK] {description}: {file_path}")
        else:
            print(f"[MISSING] {description}: {file_path}")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests."""
    print("TFT Streamlit App - Functionality Test")
    print("=" * 50)
    
    tests = [
        ("Import functionality", test_imports),
        ("Required files", check_required_files),
        ("Data loading", test_data_loading),
        ("Query functionality", test_query_functionality),
        ("Database fallback", test_database_fallback)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_func():
            passed += 1
        else:
            print(f"\n[WARNING] {test_name} test failed!")
    
    print(f"\n{'=' * 50}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All tests passed! The TFT Streamlit app is working correctly.")
        print("\nTo run the app:")
        print("   streamlit run streamlit_app.py")
        print("\nThe app will work with:")
        print("   - PostgreSQL database (if available)")
        print("   - File-based legacy mode (fallback)")
        print("   - Minimal functionality mode (if no data available)")
    else:
        print("[FAILED] Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)