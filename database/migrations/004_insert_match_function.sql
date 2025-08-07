-- TFT Match Analysis Database Functions
-- Migration 004: Insert Match Data Function
-- Version: 1.0.0
-- Created: 2024-08-06

-- ============================================================================
-- MATCH DATA INSERTION FUNCTION
-- ============================================================================

-- Function to insert complete match data from JSON
CREATE OR REPLACE FUNCTION insert_match_data(match_json JSONB)
RETURNS TABLE(
    success BOOLEAN,
    match_id UUID,
    participants_inserted INTEGER,
    message TEXT
) AS $$
DECLARE
    v_match_id UUID;
    v_game_id TEXT;
    v_participants_inserted INTEGER := 0;
    v_participant JSONB;
    v_participant_id UUID;
    v_unit JSONB;
    v_trait JSONB;
    v_game_datetime TIMESTAMPTZ;
    v_game_length INTERVAL;
    v_queue_type match_queue_type;
    v_game_mode game_mode;
    v_placement_type participant_placement_type;
BEGIN
    -- Extract and validate basic match info
    v_game_id := match_json->'metadata'->>'match_id';
    
    IF v_game_id IS NULL THEN
        RETURN QUERY SELECT FALSE, NULL::UUID, 0, 'Missing match_id in metadata';
        RETURN;
    END IF;
    
    -- Check if match already exists
    SELECT m.match_id INTO v_match_id 
    FROM matches m 
    WHERE m.game_id = v_game_id;
    
    IF v_match_id IS NOT NULL THEN
        RETURN QUERY SELECT FALSE, v_match_id, 0, 'Match already exists: ' || v_game_id;
        RETURN;
    END IF;
    
    -- Parse match datetime
    v_game_datetime := to_timestamp((match_json->'info'->>'game_datetime')::BIGINT / 1000);
    
    -- Parse game length
    v_game_length := make_interval(secs => (match_json->'info'->>'game_length')::INTEGER);
    
    -- Map queue type (with fallback)
    v_queue_type := CASE (match_json->'info'->>'queue_type')
        WHEN 'Ranked TFT' THEN 'ranked'::match_queue_type
        WHEN 'Normal TFT' THEN 'normal'::match_queue_type
        WHEN 'Tutorial TFT' THEN 'tutorial'::match_queue_type
        WHEN 'Double Up' THEN 'double_up'::match_queue_type
        WHEN 'Hyper Roll' THEN 'hyper_roll'::match_queue_type
        ELSE 'normal'::match_queue_type
    END;
    
    -- Map game mode (with fallback)
    v_game_mode := CASE (match_json->'info'->>'game_mode')
        WHEN 'TFT' THEN 'classic'::game_mode
        WHEN 'DoubleUp' THEN 'double_up'::game_mode
        WHEN 'TFT_Tutorial' THEN 'tutorial'::game_mode
        WHEN 'Hyper_Roll' THEN 'hyper_roll'::game_mode
        ELSE 'classic'::game_mode
    END;
    
    BEGIN
        -- Insert match record
        INSERT INTO matches (
            game_id, game_datetime, game_length, game_version, 
            queue_id, queue_type, game_mode, set_core_name, set_mutator, region
        ) VALUES (
            v_game_id,
            v_game_datetime,
            v_game_length,
            match_json->'info'->>'game_version',
            (match_json->'info'->>'queue_id')::INTEGER,
            v_queue_type,
            v_game_mode,
            COALESCE(match_json->'info'->'tft_set_data'->>'set_core_name', 'Unknown'),
            NULLIF(match_json->'info'->'tft_set_data'->>'mutator', ''),
            COALESCE(match_json->'metadata'->>'data_version', 'unknown')
        ) RETURNING matches.match_id INTO v_match_id;
        
        -- Insert participants
        FOR v_participant IN SELECT * FROM jsonb_array_elements(match_json->'info'->'participants')
        LOOP
            -- Map placement to enum type
            v_placement_type := CASE (v_participant->>'placement')::INTEGER
                WHEN 1 THEN 'first'::participant_placement_type
                WHEN 2 THEN 'second'::participant_placement_type
                WHEN 3 THEN 'third'::participant_placement_type
                WHEN 4 THEN 'fourth'::participant_placement_type
                WHEN 5 THEN 'fifth'::participant_placement_type
                WHEN 6 THEN 'sixth'::participant_placement_type
                WHEN 7 THEN 'seventh'::participant_placement_type
                WHEN 8 THEN 'eighth'::participant_placement_type
                ELSE 'eighth'::participant_placement_type
            END;
            
            -- Insert participant
            INSERT INTO participants (
                match_id, puuid, summoner_name, summoner_level, profile_icon_id,
                placement, placement_type, level, last_round, players_eliminated,
                time_eliminated, total_damage_to_players, gold_left, 
                augments, companion, traits_raw, units_raw
            ) VALUES (
                v_match_id,
                v_participant->>'puuid',
                v_participant->>'summoner_name',
                COALESCE((v_participant->>'summoner_level')::INTEGER, 0),
                COALESCE((v_participant->>'profile_icon_id')::INTEGER, 0),
                (v_participant->>'placement')::INTEGER,
                v_placement_type,
                (v_participant->>'level')::INTEGER,
                (v_participant->>'last_round')::INTEGER,
                COALESCE((v_participant->>'players_eliminated')::INTEGER, 0),
                CASE 
                    WHEN (v_participant->>'time_eliminated')::INTEGER > 0 
                    THEN make_interval(secs => (v_participant->>'time_eliminated')::INTEGER)
                    ELSE NULL 
                END,
                COALESCE((v_participant->>'total_damage_to_players')::INTEGER, 0),
                COALESCE((v_participant->>'gold_left')::INTEGER, 0),
                COALESCE(v_participant->'augments', '[]'::jsonb),
                COALESCE(v_participant->'companion', '{}'::jsonb),
                COALESCE(v_participant->'traits', '[]'::jsonb),
                COALESCE(v_participant->'units', '[]'::jsonb)
            ) RETURNING participant_id INTO v_participant_id;
            
            v_participants_inserted := v_participants_inserted + 1;
            
            -- Insert normalized units
            FOR v_unit IN SELECT * FROM jsonb_array_elements(COALESCE(v_participant->'units', '[]'::jsonb))
            LOOP
                INSERT INTO participant_units (
                    participant_id, character_id, unit_name, tier, rarity,
                    chosen, items, item_names, unit_traits
                ) VALUES (
                    v_participant_id,
                    v_unit->>'character_id',
                    COALESCE(v_unit->>'name', v_unit->>'character_id'),
                    COALESCE((v_unit->>'tier')::INTEGER, 1),
                    COALESCE((v_unit->>'rarity')::INTEGER, 1),
                    COALESCE((v_unit->>'chosen')::BOOLEAN, FALSE),
                    COALESCE(v_unit->'itemNames', '[]'::jsonb),
                    COALESCE(v_unit->'itemNames', '[]'::jsonb),
                    COALESCE(v_unit->'character_traits', '[]'::jsonb)
                );
            END LOOP;
            
            -- Insert normalized traits (only active traits)
            FOR v_trait IN SELECT * FROM jsonb_array_elements(COALESCE(v_participant->'traits', '[]'::jsonb))
            WHERE (jsonb_array_elements->'tier_current')::INTEGER > 0
            LOOP
                INSERT INTO participant_traits (
                    participant_id, trait_name, current_tier, num_units,
                    style, tier_current, tier_total
                ) VALUES (
                    v_participant_id,
                    v_trait->>'name',
                    (v_trait->>'tier_current')::INTEGER,
                    COALESCE((v_trait->>'num_units')::INTEGER, 0),
                    COALESCE((v_trait->>'style')::INTEGER, 0),
                    (v_trait->>'tier_current')::INTEGER,
                    COALESCE((v_trait->>'tier_total')::INTEGER, 0)
                );
            END LOOP;
            
        END LOOP;
        
        -- Return success
        RETURN QUERY SELECT TRUE, v_match_id, v_participants_inserted, 
                           'Successfully inserted match ' || v_game_id || ' with ' || v_participants_inserted || ' participants';
        
    EXCEPTION
        WHEN unique_violation THEN
            -- Handle duplicate match
            RETURN QUERY SELECT FALSE, NULL::UUID, 0, 'Duplicate match: ' || v_game_id;
        WHEN OTHERS THEN
            -- Handle other errors
            RETURN QUERY SELECT FALSE, NULL::UUID, 0, 'Error inserting match: ' || SQLERRM;
    END;
    
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- BATCH MATCH INSERTION FUNCTION
-- ============================================================================

-- Function to insert multiple matches from JSONB array
CREATE OR REPLACE FUNCTION batch_insert_matches(matches_json JSONB)
RETURNS TABLE(
    total_processed INTEGER,
    successful_inserts INTEGER,
    duplicates_skipped INTEGER,
    errors_encountered INTEGER,
    processing_time_seconds DECIMAL,
    messages TEXT[]
) AS $$
DECLARE
    v_match JSONB;
    v_total INTEGER := 0;
    v_success INTEGER := 0;
    v_duplicates INTEGER := 0;
    v_errors INTEGER := 0;
    v_start_time TIMESTAMP;
    v_end_time TIMESTAMP;
    v_messages TEXT[] := ARRAY[]::TEXT[];
    v_result RECORD;
BEGIN
    v_start_time := clock_timestamp();
    
    -- Process each match in the array
    FOR v_match IN SELECT * FROM jsonb_array_elements(matches_json)
    LOOP
        v_total := v_total + 1;
        
        -- Call insert_match_data for each match
        SELECT * INTO v_result FROM insert_match_data(v_match);
        
        IF v_result.success THEN
            v_success := v_success + 1;
            v_messages := array_append(v_messages, v_result.message);
        ELSE
            -- Check if it's a duplicate or error
            IF v_result.message LIKE '%already exists%' OR v_result.message LIKE '%Duplicate%' THEN
                v_duplicates := v_duplicates + 1;
            ELSE
                v_errors := v_errors + 1;
            END IF;
            v_messages := array_append(v_messages, v_result.message);
        END IF;
    END LOOP;
    
    v_end_time := clock_timestamp();
    
    RETURN QUERY SELECT 
        v_total,
        v_success,
        v_duplicates,
        v_errors,
        EXTRACT(EPOCH FROM (v_end_time - v_start_time))::DECIMAL,
        v_messages;
        
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- UTILITY FUNCTIONS FOR MATCH MANAGEMENT
-- ============================================================================

-- Function to check if match exists
CREATE OR REPLACE FUNCTION match_exists(p_game_id TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS(SELECT 1 FROM matches WHERE game_id = p_game_id);
END;
$$ LANGUAGE plpgsql;

-- Function to get match statistics
CREATE OR REPLACE FUNCTION get_match_import_stats()
RETURNS TABLE(
    total_matches BIGINT,
    total_participants BIGINT,
    total_units BIGINT,
    total_traits BIGINT,
    earliest_match TIMESTAMPTZ,
    latest_match TIMESTAMPTZ,
    recent_matches_24h BIGINT,
    average_participants_per_match DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM matches)::BIGINT,
        (SELECT COUNT(*) FROM participants)::BIGINT,
        (SELECT COUNT(*) FROM participant_units)::BIGINT,
        (SELECT COUNT(*) FROM participant_traits)::BIGINT,
        (SELECT MIN(game_datetime) FROM matches),
        (SELECT MAX(game_datetime) FROM matches),
        (SELECT COUNT(*) FROM matches WHERE game_datetime >= NOW() - INTERVAL '24 hours')::BIGINT,
        (SELECT ROUND(AVG(participant_count), 2) 
         FROM (SELECT COUNT(*) as participant_count 
               FROM participants GROUP BY match_id) subq);
END;
$$ LANGUAGE plpgsql;

-- Function to clean up incomplete matches (less than 8 participants)
CREATE OR REPLACE FUNCTION cleanup_incomplete_matches()
RETURNS TABLE(
    matches_deleted INTEGER,
    participants_deleted INTEGER
) AS $$
DECLARE
    v_matches_deleted INTEGER := 0;
    v_participants_deleted INTEGER := 0;
    incomplete_match RECORD;
BEGIN
    -- Find matches with less than 8 participants
    FOR incomplete_match IN 
        SELECT m.match_id, COUNT(p.participant_id) as participant_count
        FROM matches m
        LEFT JOIN participants p ON m.match_id = p.match_id
        GROUP BY m.match_id
        HAVING COUNT(p.participant_id) < 8
    LOOP
        -- Count participants to be deleted
        SELECT COUNT(*) INTO v_participants_deleted 
        FROM participants 
        WHERE match_id = incomplete_match.match_id;
        
        -- Delete the match (participants will be deleted via CASCADE)
        DELETE FROM matches WHERE match_id = incomplete_match.match_id;
        v_matches_deleted := v_matches_deleted + 1;
        
        v_participants_deleted := v_participants_deleted + incomplete_match.participant_count;
    END LOOP;
    
    RETURN QUERY SELECT v_matches_deleted, v_participants_deleted;
END;
$$ LANGUAGE plpgsql;

-- Function to validate match data integrity
CREATE OR REPLACE FUNCTION validate_match_integrity(p_game_id TEXT DEFAULT NULL)
RETURNS TABLE(
    game_id TEXT,
    participant_count INTEGER,
    missing_placements TEXT[],
    duplicate_placements TEXT[],
    issues_found INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH match_validation AS (
        SELECT 
            m.game_id,
            COUNT(p.participant_id)::INTEGER as participant_count,
            array_agg(DISTINCT p.placement ORDER BY p.placement) as all_placements,
            array_agg(p.placement) as all_placements_with_dupes
        FROM matches m
        LEFT JOIN participants p ON m.match_id = p.match_id
        WHERE p_game_id IS NULL OR m.game_id = p_game_id
        GROUP BY m.match_id, m.game_id
    ),
    validation_results AS (
        SELECT 
            mv.game_id,
            mv.participant_count,
            CASE 
                WHEN mv.participant_count < 8 THEN
                    ARRAY(SELECT generate_series(1, 8) 
                          EXCEPT 
                          SELECT unnest(mv.all_placements))::TEXT[]
                ELSE ARRAY[]::TEXT[]
            END as missing_placements,
            CASE 
                WHEN array_length(mv.all_placements_with_dupes, 1) > array_length(mv.all_placements, 1) THEN
                    ARRAY(SELECT placement::TEXT
                          FROM unnest(mv.all_placements_with_dupes) placement
                          GROUP BY placement
                          HAVING COUNT(*) > 1)
                ELSE ARRAY[]::TEXT[]
            END as duplicate_placements
        FROM match_validation mv
    )
    SELECT 
        vr.game_id,
        vr.participant_count,
        vr.missing_placements,
        vr.duplicate_placements,
        (CASE WHEN vr.participant_count != 8 THEN 1 ELSE 0 END +
         CASE WHEN array_length(vr.missing_placements, 1) > 0 THEN 1 ELSE 0 END +
         CASE WHEN array_length(vr.duplicate_placements, 1) > 0 THEN 1 ELSE 0 END)::INTEGER as issues_found
    FROM validation_results vr
    WHERE vr.participant_count != 8 
       OR array_length(vr.missing_placements, 1) > 0 
       OR array_length(vr.duplicate_placements, 1) > 0
    ORDER BY issues_found DESC, vr.game_id;
END;
$$ LANGUAGE plpgsql;

-- Add helpful comments
COMMENT ON FUNCTION insert_match_data(JSONB) IS 'Insert complete match data from Riot API JSON response';
COMMENT ON FUNCTION batch_insert_matches(JSONB) IS 'Batch insert multiple matches from JSONB array';
COMMENT ON FUNCTION match_exists(TEXT) IS 'Check if a match exists by game_id';
COMMENT ON FUNCTION get_match_import_stats() IS 'Get comprehensive statistics about imported match data';
COMMENT ON FUNCTION cleanup_incomplete_matches() IS 'Remove matches with less than 8 participants';
COMMENT ON FUNCTION validate_match_integrity(TEXT) IS 'Validate match data integrity and find issues';

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION insert_match_data(JSONB) TO tft_app_user;
GRANT EXECUTE ON FUNCTION batch_insert_matches(JSONB) TO tft_app_user;
GRANT EXECUTE ON FUNCTION match_exists(TEXT) TO tft_app_user;
GRANT EXECUTE ON FUNCTION get_match_import_stats() TO tft_app_user;
GRANT EXECUTE ON FUNCTION cleanup_incomplete_matches() TO tft_app_user;
GRANT EXECUTE ON FUNCTION validate_match_integrity(TEXT) TO tft_app_user;

-- Migration completed successfully
SELECT 'Migration 004_insert_match_function.sql completed successfully' as status;