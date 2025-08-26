"""
Simple test for TFT Streamlit app
"""

print("TFT Streamlit App Test")
print("=" * 30)

# Test 1: Files exist
import os
print("\n1. Checking files:")
files = [
    'streamlit_app.py',
    'querying.py', 
    'hierarchical_clusters_main_clusters_analysis.csv'
]

for f in files:
    status = "OK" if os.path.exists(f) else "MISSING"
    print(f"   {f}: {status}")

# Test 2: Imports work
print("\n2. Testing imports:")
try:
    import streamlit as st
    print("   streamlit: OK")
except Exception as e:
    print(f"   streamlit: ERROR - {e}")

try:
    from streamlit_app import load_main_clusters
    print("   streamlit_app: OK")
except Exception as e:
    print(f"   streamlit_app: ERROR - {e}")

try:
    from querying import TFTQuery
    print("   querying: OK")
except Exception as e:
    print(f"   querying: ERROR - {e}")

# Test 3: Data loading
print("\n3. Testing data loading:")
try:
    from streamlit_app import load_main_clusters, load_subcluster_files
    clusters = load_main_clusters()
    subclusters = load_subcluster_files()
    print(f"   Main clusters: {len(clusters)} rows")
    print(f"   Subcluster files: {len(subclusters)} files")
except Exception as e:
    print(f"   Data loading: ERROR - {e}")

# Test 4: Query functionality
print("\n4. Testing queries:")
try:
    query = TFTQuery()
    result = query.add_unit('TFT14_Aphelios').get_stats()
    print(f"   Query result: {result}")
except Exception as e:
    print(f"   Query: ERROR - {e}")

print("\n" + "=" * 30)
print("Test complete!")
print("\nTo run the app:")
print("  streamlit run streamlit_app.py")
print("Then open: http://localhost:8501")