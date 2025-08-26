"""
Add this to your streamlit_app.py as a new tab for data upload
"""

import streamlit as st
import json
import psycopg2
from datetime import datetime

def create_data_upload_tab():
    """Create a data upload tab for the Streamlit app"""
    
    st.header("📤 Data Upload")
    st.write("Upload your TFT match data to the database")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a JSONL file",
        type=['jsonl'],
        help="Upload your matches_filtered.jsonl file"
    )
    
    if uploaded_file is not None:
        st.write(f"File uploaded: {uploaded_file.name}")
        st.write(f"File size: {uploaded_file.size} bytes")
        
        # Preview first few lines
        if st.checkbox("Preview file content"):
            file_contents = uploaded_file.read().decode("utf-8")
            lines = file_contents.split('\n')[:3]  # First 3 lines
            for i, line in enumerate(lines, 1):
                if line.strip():
                    try:
                        data = json.loads(line)
                        st.write(f"Line {i}: Match ID {data['metadata']['match_id']}")
                    except:
                        st.write(f"Line {i}: Invalid JSON")
            uploaded_file.seek(0)  # Reset file pointer
        
        # Upload button
        if st.button("Upload to Database", type="primary"):
            try:
                # Get database connection
                database_url = st.secrets["database"]["DATABASE_URL"]
                conn = psycopg2.connect(database_url)
                cursor = conn.cursor()
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                file_contents = uploaded_file.read().decode("utf-8")
                lines = [line.strip() for line in file_contents.split('\n') if line.strip()]
                
                matches_imported = 0
                participants_imported = 0
                
                for line_num, line in enumerate(lines):
                    try:
                        match_data = json.loads(line)
                        
                        # Extract match info
                        match_info = match_data['info']
                        match_id = match_data['metadata']['match_id']
                        
                        # Convert timestamp
                        game_datetime = datetime.fromtimestamp(match_info['game_datetime'] / 1000)
                        
                        # Insert match
                        cursor.execute("""
                            INSERT INTO matches (
                                match_id, game_datetime, game_length, game_version,
                                set_core_name, queue_id, tft_set_number, raw_data
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (match_id) DO NOTHING
                        """, (
                            match_id,
                            game_datetime,
                            match_info.get('game_length'),
                            match_info.get('game_version'),
                            match_info.get('tft_set_core_name'),
                            match_info.get('queue_id'),
                            match_info.get('tft_set_number'),
                            json.dumps(match_data)
                        ))
                        
                        if cursor.rowcount > 0:
                            matches_imported += 1
                        
                        # Insert participants
                        for participant in match_info['participants']:
                            cursor.execute("""
                                INSERT INTO participants (
                                    match_id, puuid, placement, level, last_round,
                                    players_eliminated, total_damage_to_players,
                                    time_eliminated, companion, traits, units, augments
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (match_id, puuid) DO NOTHING
                            """, (
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
                            
                            if cursor.rowcount > 0:
                                participants_imported += 1
                        
                        # Update progress
                        progress = (line_num + 1) / len(lines)
                        progress_bar.progress(progress)
                        status_text.text(f"Processed {line_num + 1}/{len(lines)} matches...")
                        
                        # Commit every 50 matches
                        if (line_num + 1) % 50 == 0:
                            conn.commit()
                            
                    except Exception as e:
                        st.error(f"Error processing match {line_num + 1}: {e}")
                
                # Final commit
                conn.commit()
                cursor.close()
                conn.close()
                
                st.success(f"""
                Upload completed!
                - New matches imported: {matches_imported}
                - New participants imported: {participants_imported}
                """)
                
            except Exception as e:
                st.error(f"Database error: {e}")
    
    # Database status
    st.subheader("Database Status")
    try:
        database_url = st.secrets["database"]["DATABASE_URL"]
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM matches")
        match_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM participants")
        participant_count = cursor.fetchone()[0]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Matches", match_count)
        with col2:
            st.metric("Total Participants", participant_count)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Could not connect to database: {e}")


# Add this function call to your main streamlit_app.py tabs:
# with tab4:  # Add a new tab
#     create_data_upload_tab()