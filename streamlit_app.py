"""
TFT Composition Analysis - Streamlit App
Displays cluster analysis and integrates with existing querying functionality
"""

import streamlit as st
import pandas as pd
import os
import json
import psycopg2No
from datetime import datetime
import io
from pathlib import Path

# Import database functionality - try simple version first
try:
    from simple_database import SimpleTFTQuery as TFTQuery, test_connection, get_match_stats
    QUERYING_AVAILABLE = True
    DATABASE_TYPE = "simple"
    st.success("✅ Using simplified database connection")
except ImportError as e:
    st.warning(f"Simple database not available: {e}")
    # Try complex querying system
    try:
        from querying import TFTQuery, analyze_top_clusters, print_cluster_compositions
        QUERYING_AVAILABLE = True
        DATABASE_TYPE = "complex"
        st.info("🔧 Using complex database system")
    except ImportError as e2:
        st.error(f"No database connection available: {e2}")
        QUERYING_AVAILABLE = False
        DATABASE_TYPE = "none"
        # Create dummy classes to prevent errors
        class TFTQuery:
            def __init__(self, *args, **kwargs):
                pass
            def add_unit(self, *args, **kwargs):
                return self
            def get_stats(self):
                return {"error": "No database connection available"}
        
        def test_connection():
            return False
        
        def get_match_stats():
            return {'matches': 0, 'participants': 0}

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
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🎯 Clusters", "🔍 Query", "📤 Upload"])
    
    # Tab 1: Overview
    with tab1:
        st.header("Dataset Overview")
        
        # Test database connection
        if QUERYING_AVAILABLE and DATABASE_TYPE == "simple":
            if test_connection():
                st.success("✅ Database connection successful!")
                db_stats = get_match_stats()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Matches", f"{db_stats['matches']:,}")
                
                with col2:
                    st.metric("Total Participants", f"{db_stats['participants']:,}")
                
                with col3:
                    if db_stats['matches'] > 0:
                        avg_participants = db_stats['participants'] / db_stats['matches']
                        st.metric("Avg Players/Match", f"{avg_participants:.1f}")
                
                st.subheader("📊 Database Status")
                st.info(f"Connected to TFT match database with {db_stats['matches']:,} matches")
                
            else:
                st.error("❌ Database connection failed - check network and credentials")
                st.info("Falling back to file-based data...")
        
        # Fallback to file-based data or show cluster info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Main Cluster Files", len(main_clusters))
        
        with col2:
            st.metric("Subcluster Files", len(subclusters))
        
        with col3:
            total_subclusters = sum(len(df) for df in subclusters.values())
            st.metric("Total Subclusters", total_subclusters)
        
        if not main_clusters.empty:
            st.subheader("Main Clusters Summary")
            st.dataframe(main_clusters, use_container_width=True, height=400)
        else:
            st.warning("No cluster analysis files found. Upload your data to see cluster analysis.")
    
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
        st.write("Enter your TFT query using SimpleTFTQuery with comprehensive filtering capabilities:")
        
        # Query input
        query_input = st.text_area(
            "Query:",
            placeholder="SimpleTFTQuery().add_unit('Aphelios').get_stats()",
            height=300
        )
        
        # Reference Lists
        with st.expander("📋 Unit, Trait & Item Reference", expanded=False):
            ref_col1, ref_col2, ref_col3 = st.columns(3)
            
            with ref_col1:
                st.markdown("#### 🎯 **Units**")
                st.markdown("""
                - Aatrox
                - Ahri
                - Akali
                - Ashe
                - Braum
                - Caitlyn
                - Darius
                - Dr._Mundo
                - Ekko
                - Ezreal
                - Galio
                - Gangplank
                - Garen
                - Gnar
                - Gwen
                - Janna
                - JarvanIV
                - Jayce
                - Jhin
                - Jinx
                - K'Sante
                - Kai'Sa
                - Kalista
                - Karma
                - Katarina
                - Kayle
                - Kennen
                - Kobuko
                - Kog'Maw
                - Lee_Sin
                - Leona
                - Lucian
                - Lux
                - Malphite
                - Malzahar
                - Naafiri
                - Neeko
                - Poppy
                - Rakan
                - Rammus
                - Rell
                - Ryze
                - Samira
                - Senna
                - Seraphine
                - Sett
                - Shen
                - Sivir
                - Smolder
                - Swain
                - Syndra
                - Twisted_Fate
                - Udyr
                - Varus
                - Vi
                - Viego
                - Volibear
                - Xayah
                - Xin_Zhao
                - Yasuo
                - Yone
                - Yuumi
                - Zac
                - Ziggs
                - Zyra
                """)
            
            with ref_col2:
                st.markdown("#### ⚡ **Traits**")
                st.markdown("""
                - Bastion
                - Battle_Academia
                - Captain
                - Executioner
                - Stance_Master
                - Duelist
                - Edgelord
                - The_Champ
                - Wraith
                - Crystal_Gambit
                - Heavyweight
                - Juggernaut
                - Luchador
                - Monster_Trainer
                - Mentor
                - Prodigy
                - Protector
                - Rosemother
                - Mighty_Mech
                - Sniper
                - SoulFighter
                - Sorcerer
                - Star_Guardian
                - Strategist
                - Supreme_Cells
                - Crew
                """)
            
            with ref_col3:
                st.markdown("#### 🛡️ **Items**")
                st.markdown("""
                - Bastion_Emblem
                - Battle_Academia_Emblem
                - Challenger_Emblem
                - Crystal_Rose_Emblem
                - Executioner_Emblem
                - Edgelord_Emblem
                - Wraith_EmblemItem
                - Heavyweight_Emblem
                - Juggernaut_Emblem
                - Prodigy_Emblem
                - Protector_Emblem
                - RingKingsEmblem
                - ShotcallerEmblem
                - Sniper_Emblem
                - Soul_Fighter_Emblem
                - Sorcerer_Emblem
                - Star_Guardian_Emblem
                - Supreme_Cells_Emblem
                - Mech_Core
                - Mech_Slicer
                - Mech_Sword
                - Death's_Defiance
                - Infinity_Force
                - Muramana
                - Randuin's_Sanctum
                - Gold_Collector
                - Zhonya's_Paradox
                - BF_Sword
                - Bloodthirster
                - Blue_Buff
                - Bramble_Vest
                - Chain_Vest
                - Chalice
                - Crownguard
                - Deathblade
                - Dragons_Claw
                - Empty_Bag
                - Tactician's_Crown
                - Protector's_Vow
                - Frying_Pan
                - Gargoyle_Stoneplate
                - Giant's_Belt
                - Edge_Of_Night
                - Guinsoos_Rageblade
                - Hextech_Gunblade
                - Infinity_Edge
                - Ionic_Spark
                - Jeweled_Gauntlet
                - Last_Whisper
                - Steadfast_Heart
                - Morellonomicon
                - Quicksilver
                - Archangels_Staff
                - Adaptive_Helm
                - Runaans_Hurricane
                - Spear_Of_Shojin
                - Statikk_Shiv
                - Steraks_Gage
                - Titans_Resolve
                - Warmogs_Armor
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
    
    # Tab 4: Data Upload (Optimized)
    with tab4:
        st.header("📤 Optimized Data Upload")
        st.write("Upload TFT match data efficiently to the database")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a JSONL file",
            type=['jsonl'],
            help="Upload your matches_filtered.jsonl file"
        )
        
        if uploaded_file is not None:
            st.write(f"File: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
            # Preview toggle
            if st.checkbox("Preview file content"):
                # Use streaming to preview without loading entire file
                preview_lines = []
                text_io = io.TextIOWrapper(uploaded_file, encoding='utf-8')
                for i, line in enumerate(text_io):
                    if i >= 3:  # Only first 3 lines
                        break
                    if line.strip():
                        try:
                            data = json.loads(line)
                            preview_lines.append(f"Line {i+1}: Match ID {data['metadata']['match_id']}")
                        except:
                            preview_lines.append(f"Line {i+1}: Invalid JSON")
                for line in preview_lines:
                    st.write(line)
                uploaded_file.seek(0)
            
            # Upload options
            col1, col2 = st.columns(2)
            with col1:
                batch_size = st.selectbox("Batch Size", [100, 500, 1000], index=1, help="Higher values = faster upload but more memory")
            with col2:
                skip_raw_data = st.checkbox("Skip raw data storage", value=True, help="Reduces storage by 80% but loses match details")
            
            # Upload button
            if st.button("🚀 Upload to Database", type="primary"):
                try:
                    # Connection with optimized settings
                    database_url = st.secrets.get("database", {}).get("DATABASE_URL") or os.environ.get("DATABASE_URL")
                    if not database_url:
                        st.error("DATABASE_URL not found in secrets or environment")
                        return
                        
                    conn = psycopg2.connect(
                        database_url,
                        options='-c synchronous_commit=off'  # Faster commits
                    )
                    cursor = conn.cursor()
                    
                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Batch processing variables
                    match_batch = []
                    participant_batch = []
                    matches_imported = 0
                    participants_imported = 0
                    line_count = 0
                    
                    # Stream processing
                    text_io = io.TextIOWrapper(uploaded_file, encoding='utf-8')
                    
                    for line in text_io:
                        line = line.strip()
                        if not line:
                            continue
                            
                        line_count += 1
                        
                        try:
                            match_data = json.loads(line)
                            match_info = match_data['info']
                            match_id = match_data['metadata']['match_id']
                            game_datetime = datetime.fromtimestamp(match_info['game_datetime'] / 1000)
                            
                            # Prepare match data
                            match_batch.append((
                                match_id,
                                game_datetime,
                                match_info.get('game_length'),
                                match_info.get('game_version'),
                                match_info.get('tft_set_core_name'),
                                match_info.get('queue_id'),
                                match_info.get('tft_set_number'),
                                None if skip_raw_data else json.dumps(match_data)
                            ))
                            
                            # Prepare participant data
                            for participant in match_info['participants']:
                                participant_batch.append((
                                    match_id,
                                    participant['puuid'],
                                    participant.get('placement'),
                                    participant.get('level'),
                                    participant.get('last_round'),
                                    participant.get('players_eliminated'),
                                    participant.get('total_damage_to_players'),
                                    participant.get('time_eliminated'),
                                    json.dumps(participant.get('companion', {})),
                                    json.dumps(participant.get('traits', [])),
                                    json.dumps(participant.get('units', [])),
                                    participant.get('augments', [])
                                ))
                            
                            # Batch insert when batch size reached
                            if len(match_batch) >= batch_size:
                                # Batch insert matches
                                cursor.executemany("""
                                    INSERT INTO matches (
                                        match_id, game_datetime, game_length, game_version,
                                        set_core_name, queue_id, tft_set_number, raw_data
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (match_id) DO NOTHING
                                """, match_batch)
                                matches_imported += cursor.rowcount
                                
                                # Batch insert participants
                                cursor.executemany("""
                                    INSERT INTO participants (
                                        match_id, puuid, placement, level, last_round,
                                        players_eliminated, total_damage_to_players,
                                        time_eliminated, companion, traits, units, augments
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (match_id, puuid) DO NOTHING
                                """, participant_batch)
                                participants_imported += cursor.rowcount
                                
                                # Commit and reset
                                conn.commit()
                                match_batch = []
                                participant_batch = []
                                
                                status_text.text(f"Processed {line_count:,} matches... (M: {matches_imported:,}, P: {participants_imported:,})")
                                
                        except Exception as e:
                            st.warning(f"Skipped line {line_count}: {str(e)[:100]}...")
                    
                    # Process remaining batch
                    if match_batch:
                        cursor.executemany("""
                            INSERT INTO matches (
                                match_id, game_datetime, game_length, game_version,
                                set_core_name, queue_id, tft_set_number, raw_data
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (match_id) DO NOTHING
                        """, match_batch)
                        matches_imported += cursor.rowcount
                        
                        cursor.executemany("""
                            INSERT INTO participants (
                                match_id, puuid, placement, level, last_round,
                                players_eliminated, total_damage_to_players,
                                time_eliminated, companion, traits, units, augments
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (match_id, puuid) DO NOTHING
                        """, participant_batch)
                        participants_imported += cursor.rowcount
                        
                        conn.commit()
                    
                    progress_bar.progress(1.0)
                    cursor.close()
                    conn.close()
                    
                    st.success(f"""
                    ✅ Upload completed efficiently!
                    - **Matches processed**: {line_count:,}
                    - **New matches imported**: {matches_imported:,}
                    - **New participants imported**: {participants_imported:,}
                    - **Storage saved**: {'~80%' if skip_raw_data else '0%'} (raw data skipped)
                    """)
                    
                except Exception as e:
                    st.error(f"Upload failed: {e}")
                    
        # Database status
        st.subheader("📊 Database Status")
        try:
            database_url = st.secrets.get("database", {}).get("DATABASE_URL") or os.environ.get("DATABASE_URL")
            if database_url:
                conn = psycopg2.connect(database_url)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM matches")
                match_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM participants")
                participant_count = cursor.fetchone()[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Matches", f"{match_count:,}")
                with col2:
                    st.metric("Total Participants", f"{participant_count:,}")
                
                cursor.close()
                conn.close()
            else:
                st.warning("Database connection not configured")
                
        except Exception as e:
            st.error(f"Database status unavailable: {e}")

if __name__ == "__main__":
    main()