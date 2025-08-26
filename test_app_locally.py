"""
Test script to verify TFT Streamlit app is working properly
Run this before deploying to make sure everything works
"""

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    try:
        import streamlit as st
        import pandas as pd
        print("  [OK] Streamlit and Pandas imported")
        
        from streamlit_app import load_main_clusters, load_subcluster_files
        print("  [OK] Streamlit app functions imported")
        
        from querying import TFTQuery
        print("  [OK] TFTQuery imported")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Import error: {e}")
        return False

def test_data_loading():
    """Test data loading functionality"""
    print("Testing data loading...")
    try:
        from streamlit_app import load_main_clusters, load_subcluster_files
        
        main_clusters = load_main_clusters()
        print(f"  [OK] Main clusters loaded: {len(main_clusters)} rows")
        
        subclusters = load_subcluster_files()
        print(f"  [OK] Subcluster files loaded: {len(subclusters)} files")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Data loading error: {e}")
        return False

def test_querying():
    """Test query functionality"""
    print("Testing query functionality...")
    try:
        from querying import TFTQuery
        
        # Test basic query
        query = TFTQuery()
        result = query.add_unit('TFT14_Aphelios').get_stats()
        print(f"  [OK] Basic query working: {result}")
        
        # Test complex query
        result2 = query.add_trait('TFT14_Vanguard', min_tier=2).get_stats()
        print(f"  [OK] Complex query working: {result2}")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Query error: {e}")
        return False

def test_files_exist():
    """Test required files exist"""
    print("Testing file existence...")
    import os
    
    required_files = [
        'hierarchical_clusters_main_clusters_analysis.csv',
        'hierarchical_clusters_detailed_analysis',
        'streamlit_app.py',
        'querying.py',
        'requirements.txt'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"  [OK] {file} exists")
        else:
            print(f"  [MISSING] {file} missing")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests"""
    print("=" * 50)
    print("TFT Streamlit App - Local Testing")
    print("=" * 50)
    
    tests = [
        ("File Existence", test_files_exist),
        ("Imports", test_imports),
        ("Data Loading", test_data_loading),
        ("Query Functionality", test_querying),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"  [ERROR] Test failed with exception: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED! App is ready to run.")
        print("\nTo start the app, run:")
        print("  streamlit run streamlit_app.py")
        print("\nThen open: http://localhost:8501")
    else:
        print("[FAILED] Some tests failed. Check the errors above.")
    print("=" * 50)

if __name__ == "__main__":
    main()