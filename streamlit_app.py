"""
TFT Composition Analysis - Streamlit App
Displays cluster analysis and integrates with existing querying functionality
"""

import streamlit as st
import pandas as pd
import os
from pathlib import Path

# Import your existing querying functionality
try:
    from querying import TFTQuery, analyze_top_clusters, print_cluster_compositions
    QUERYING_AVAILABLE = True
except ImportError as e:
    st.warning(f"Could not import querying functionality: {e}")
    QUERYING_AVAILABLE = False
    # Create dummy classes to prevent errors
    class TFTQuery:
        def __init__(self, *args, **kwargs):
            pass
        def add_unit(self, *args, **kwargs):
            return self
        def get_stats(self):
            return {"error": "Querying functionality not available - missing dependencies"}
    
    def analyze_top_clusters(*args, **kwargs):
        return []
    
    def print_cluster_compositions(*args, **kwargs):
        pass

# Page configuration
st.set_page_config(
    page_title="TFT Composition Analysis",
    page_icon="⚔️",
    layout="wide"
)

# ===============================
# DATA LOADING FUNCTIONS
# ===============================

@st.cache_data
def load_main_clusters():
    """Load main cluster analysis data"""
    file_path = "hierarchical_clusters_main_clusters_analysis.csv"
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return pd.DataFrame()

@st.cache_data
def load_subcluster_files():
    """Load all subcluster files from detailed analysis directory"""
    subcluster_dir = Path("hierarchical_clusters_detailed_analysis")
    subclusters = {}
    
    if subcluster_dir.exists():
        for file_path in subcluster_dir.glob("*.csv"):
            try:
                cluster_id = int(file_path.stem.split('_')[2])
                subclusters[cluster_id] = pd.read_csv(file_path)
            except (IndexError, ValueError):
                st.warning(f"Could not parse cluster ID from {file_path.name}")
    else:
        st.error("Subclusters directory not found: hierarchical_clusters_detailed_analysis/")
    
    return subclusters

# ===============================
# QUERY EXECUTION
# ===============================

def execute_query(query_text):
    """Execute TFT query and return results"""
    if not QUERYING_AVAILABLE:
        return {"error": "Querying functionality not available - missing dependencies"}
    
    try:
        # Create a local namespace with TFTQuery available
        local_vars = {
            'TFTQuery': TFTQuery,
        }
        
        # Execute the query
        result = eval(query_text, {"__builtins__": {}}, local_vars)
        return result
            
    except Exception as e:
        return {"error": str(e)}

# ===============================
# STREAMLIT APP
# ===============================

def main():
    st.title("⚔️ TFT Composition Analysis")
    st.markdown("---")
    
    # Load data
    main_clusters = load_main_clusters()
    subclusters = load_subcluster_files()
    
    if main_clusters.empty:
        st.error("No main cluster data available. Please ensure the CSV files are in the correct location.")
        return
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "🎯 Clusters", "🔍 Query"])
    
    # Tab 1: Overview
    with tab1:
        st.header("Dataset Overview")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Main Clusters", len(main_clusters))
        
        with col2:
            st.metric("Subcluster Files", len(subclusters))
        
        with col3:
            total_subclusters = sum(len(df) for df in subclusters.values())
            st.metric("Total Subclusters", total_subclusters)
        
        st.subheader("Main Clusters Summary")
        st.dataframe(main_clusters, use_container_width=True, height=400)
    
    # Tab 2: Clusters
    with tab2:
        st.header("Cluster Analysis")
        
        if not main_clusters.empty:
            # Cluster selection
            cluster_options = {}
            name_column = main_clusters.columns[1] if len(main_clusters.columns) > 1 else main_clusters.columns[0]
            
            for idx, row in main_clusters.iterrows():
                cluster_id = row.iloc[0] if len(row) > 0 else idx
                cluster_name = row.iloc[1] if len(row) > 1 else f"Cluster {cluster_id}"
                cluster_options[f"{cluster_id}: {cluster_name}"] = cluster_id
            
            selected_cluster = st.selectbox(
                "Select a cluster to view details:",
                options=list(cluster_options.keys())
            )
            
            if selected_cluster:
                cluster_id = cluster_options[selected_cluster]
                
                # Display main cluster info
                cluster_data = main_clusters[main_clusters.iloc[:, 0] == cluster_id]
                
                if not cluster_data.empty:
                    st.subheader(f"Main Cluster {cluster_id} Details")
                    st.dataframe(cluster_data, use_container_width=True)
                
                # Display subclusters if available
                if cluster_id in subclusters:
                    st.subheader(f"Subclusters for Cluster {cluster_id}")
                    subcluster_df = subclusters[cluster_id]
                    
                    if not subcluster_df.empty:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Number of Subclusters", len(subcluster_df))
                        with col2:
                            if 'avg_placement' in subcluster_df.columns:
                                avg_placement = subcluster_df['avg_placement'].mean()
                                st.metric("Average Placement", f"{avg_placement:.2f}")
                        
                        st.dataframe(subcluster_df, use_container_width=True, height=300)
                    else:
                        st.info("No subclusters found for this cluster.")
                else:
                    st.info(f"No subcluster data available for cluster {cluster_id}")
    
    # Tab 3: Query Interface
    with tab3:
        st.header("TFT Query Interface")
        st.write("Enter your TFT query using the same format as your existing querying system:")
        
        # Query input
        query_input = st.text_area(
            "Query:",
            placeholder="TFTQuery().add_unit('TFT14_Aphelios').get_stats()",
            height=100
        )
        
        # Examples
        with st.expander("Query Examples"):
            st.code("""
# Basic unit query
TFTQuery().add_unit('TFT14_Aphelios').get_stats()

# Trait query  
TFTQuery().add_trait('TFT14_Vanguard', min_tier=2).get_stats()

# Player level query
TFTQuery().add_player_level(min_level=8, max_level=10).get_stats()

# Cluster query
TFTQuery().set_sub_cluster(5).get_stats()

# Combined query
TFTQuery().add_unit('TFT14_Jinx').add_trait('TFT14_Rebel', min_tier=3).get_stats()
            """)
        
        # Execute query button
        if st.button("Execute Query", type="primary"):
            if query_input.strip():
                with st.spinner("Executing query..."):
                    result = execute_query(query_input)
                
                st.subheader("Query Results")
                if isinstance(result, dict) and "error" in result:
                    st.error(f"Query Error: {result['error']}")
                elif isinstance(result, dict):
                    # Display stats result
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Play Count", result.get('play_count', 0))
                    with col2:
                        st.metric("Avg Placement", result.get('avg_placement', 0))
                    with col3:
                        st.metric("Win Rate", f"{result.get('winrate', 0)}%")
                    with col4:
                        st.metric("Top 4 Rate", f"{result.get('top4_rate', 0)}%")
                elif isinstance(result, list):
                    # Display participant results
                    st.write(f"Found {len(result)} matching compositions")
                    if result:
                        # Convert to DataFrame for display
                        display_data = []
                        for p in result[:50]:  # Limit to first 50
                            display_data.append({
                                'Placement': p.get('placement', 'N/A'),
                                'Level': p.get('level', 'N/A'),
                                'Last Round': p.get('last_round', 'N/A'),
                                'Units': ', '.join([u['character_id'] for u in p.get('units', [])[:5]]) + '...'
                            })
                        st.dataframe(pd.DataFrame(display_data), use_container_width=True)
                else:
                    st.write(result)
            else:
                st.warning("Please enter a query")

if __name__ == "__main__":
    main()