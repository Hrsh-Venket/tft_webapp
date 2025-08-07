-- TFT Match Analysis Database Functions and Views
-- Migration 003: Helper Functions and Analytical Views
-- Version: 1.0.0
-- Created: 2024-08-06

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to extract augment names from JSONB array
CREATE OR REPLACE FUNCTION extract_augment_names(augments_jsonb JSONB)
RETURNS TEXT[] AS $$
BEGIN
    RETURN ARRAY(
        SELECT jsonb_array_elements_text(augments_jsonb)
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to extract trait names from traits JSONB
CREATE OR REPLACE FUNCTION extract_trait_names(traits_jsonb JSONB)
RETURNS TEXT[] AS $$
BEGIN
    RETURN ARRAY(
        SELECT t->>'name'
        FROM jsonb_array_elements(traits_jsonb) t
        WHERE (t->>'tier_current')::INTEGER > 0
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to extract unit names from units JSONB
CREATE OR REPLACE FUNCTION extract_unit_names(units_jsonb JSONB)
RETURNS TEXT[] AS $$
BEGIN
    RETURN ARRAY(
        SELECT u->>'character_id'
        FROM jsonb_array_elements(units_jsonb) u
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to calculate placement points (TFT-style scoring)
CREATE OR REPLACE FUNCTION calculate_placement_points(placement INTEGER)
RETURNS INTEGER AS $$
BEGIN
    RETURN CASE 
        WHEN placement = 1 THEN 8
        WHEN placement = 2 THEN 7
        WHEN placement = 3 THEN 6
        WHEN placement = 4 THEN 5
        WHEN placement = 5 THEN 4
        WHEN placement = 6 THEN 3
        WHEN placement = 7 THEN 2
        WHEN placement = 8 THEN 1
        ELSE 0
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to categorize placements
CREATE OR REPLACE FUNCTION categorize_placement(placement INTEGER)
RETURNS TEXT AS $$
BEGIN
    RETURN CASE 
        WHEN placement = 1 THEN 'Win'
        WHEN placement <= 4 THEN 'Top 4'
        WHEN placement <= 6 THEN 'Mid'
        ELSE 'Bottom'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to calculate match recency score
CREATE OR REPLACE FUNCTION match_recency_score(match_datetime TIMESTAMPTZ)
RETURNS DECIMAL AS $$
DECLARE
    days_ago INTEGER;
BEGIN
    days_ago := EXTRACT(DAY FROM NOW() - match_datetime);
    RETURN CASE 
        WHEN days_ago <= 1 THEN 1.0
        WHEN days_ago <= 7 THEN 0.8
        WHEN days_ago <= 30 THEN 0.6
        WHEN days_ago <= 90 THEN 0.4
        ELSE 0.2
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- ANALYTICAL FUNCTIONS
-- ============================================================================

-- Function to get player statistics
CREATE OR REPLACE FUNCTION get_player_stats(
    player_puuid VARCHAR(100),
    days_back INTEGER DEFAULT 30
)
RETURNS TABLE(
    total_games BIGINT,
    avg_placement DECIMAL,
    win_rate DECIMAL,
    top4_rate DECIMAL,
    avg_level DECIMAL,
    avg_damage DECIMAL,
    total_points INTEGER,
    most_common_traits TEXT[],
    most_common_units TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH player_matches AS (
        SELECT p.*
        FROM participants p
        JOIN matches m ON p.match_id = m.match_id
        WHERE p.puuid = player_puuid
        AND m.game_datetime >= NOW() - (days_back || ' days')::INTERVAL
    )
    SELECT 
        COUNT(*)::BIGINT as total_games,
        ROUND(AVG(pm.placement), 2) as avg_placement,
        ROUND(COUNT(*) FILTER (WHERE pm.placement = 1)::DECIMAL / COUNT(*) * 100, 2) as win_rate,
        ROUND(COUNT(*) FILTER (WHERE pm.placement <= 4)::DECIMAL / COUNT(*) * 100, 2) as top4_rate,
        ROUND(AVG(pm.level), 2) as avg_level,
        ROUND(AVG(pm.total_damage_to_players), 0) as avg_damage,
        SUM(calculate_placement_points(pm.placement))::INTEGER as total_points,
        array_agg(DISTINCT trait ORDER BY trait) FILTER (WHERE trait IS NOT NULL) as most_common_traits,
        array_agg(DISTINCT unit ORDER BY unit) FILTER (WHERE unit IS NOT NULL) as most_common_units
    FROM player_matches pm
    CROSS JOIN LATERAL unnest(extract_trait_names(pm.traits_raw)) as trait
    CROSS JOIN LATERAL unnest(extract_unit_names(pm.units_raw)) as unit;
END;
$$ LANGUAGE plpgsql;

-- Function to get match composition summary
CREATE OR REPLACE FUNCTION get_match_composition_summary(match_uuid UUID)
RETURNS TABLE(
    trait_name TEXT,
    trait_popularity INTEGER,
    avg_tier DECIMAL,
    avg_placement_with_trait DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    WITH match_traits AS (
        SELECT 
            p.placement,
            jsonb_array_elements(p.traits_raw) as trait_data
        FROM participants p
        WHERE p.match_id = match_uuid
    ),
    trait_stats AS (
        SELECT 
            (trait_data->>'name')::TEXT as trait_name,
            (trait_data->>'tier_current')::INTEGER as tier,
            placement
        FROM match_traits
        WHERE (trait_data->>'tier_current')::INTEGER > 0
    )
    SELECT 
        ts.trait_name,
        COUNT(*)::INTEGER as trait_popularity,
        ROUND(AVG(ts.tier), 2) as avg_tier,
        ROUND(AVG(ts.placement), 2) as avg_placement_with_trait
    FROM trait_stats ts
    GROUP BY ts.trait_name
    ORDER BY trait_popularity DESC, avg_placement_with_trait ASC;
END;
$$ LANGUAGE plpgsql;

-- Function to find similar compositions
CREATE OR REPLACE FUNCTION find_similar_compositions(
    target_traits TEXT[],
    target_units TEXT[],
    min_similarity DECIMAL DEFAULT 0.7,
    limit_results INTEGER DEFAULT 20
)
RETURNS TABLE(
    participant_id UUID,
    match_id UUID,
    placement INTEGER,
    similarity_score DECIMAL,
    common_traits TEXT[],
    common_units TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH composition_similarity AS (
        SELECT 
            p.participant_id,
            p.match_id,
            p.placement,
            extract_trait_names(p.traits_raw) as participant_traits,
            extract_unit_names(p.units_raw) as participant_units
        FROM participants p
    ),
    similarity_scores AS (
        SELECT 
            cs.*,
            -- Calculate Jaccard similarity for traits
            CASE 
                WHEN array_length(target_traits, 1) = 0 AND array_length(cs.participant_traits, 1) = 0 THEN 1.0
                WHEN array_length(target_traits, 1) = 0 OR array_length(cs.participant_traits, 1) = 0 THEN 0.0
                ELSE 
                    array_length(target_traits & cs.participant_traits, 1)::DECIMAL / 
                    array_length(target_traits | cs.participant_traits, 1)::DECIMAL
            END as trait_similarity,
            -- Calculate Jaccard similarity for units
            CASE 
                WHEN array_length(target_units, 1) = 0 AND array_length(cs.participant_units, 1) = 0 THEN 1.0
                WHEN array_length(target_units, 1) = 0 OR array_length(cs.participant_units, 1) = 0 THEN 0.0
                ELSE 
                    array_length(target_units & cs.participant_units, 1)::DECIMAL / 
                    array_length(target_units | cs.participant_units, 1)::DECIMAL
            END as unit_similarity
        FROM composition_similarity cs
    )
    SELECT 
        ss.participant_id,
        ss.match_id,
        ss.placement,
        ROUND((ss.trait_similarity * 0.6 + ss.unit_similarity * 0.4), 3) as similarity_score,
        target_traits & ss.participant_traits as common_traits,
        target_units & ss.participant_units as common_units
    FROM similarity_scores ss
    WHERE (ss.trait_similarity * 0.6 + ss.unit_similarity * 0.4) >= min_similarity
    ORDER BY similarity_score DESC
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ANALYTICAL VIEWS
-- ============================================================================

-- View: Player Performance Summary
CREATE OR REPLACE VIEW player_performance_summary AS
WITH player_stats AS (
    SELECT 
        p.puuid,
        p.summoner_name,
        COUNT(*) as total_games,
        ROUND(AVG(p.placement), 2) as avg_placement,
        COUNT(*) FILTER (WHERE p.placement = 1) as wins,
        COUNT(*) FILTER (WHERE p.placement <= 4) as top4_finishes,
        ROUND(AVG(p.level), 2) as avg_level,
        ROUND(AVG(p.total_damage_to_players), 0) as avg_damage,
        SUM(calculate_placement_points(p.placement)) as total_points,
        MAX(m.game_datetime) as last_played
    FROM participants p
    JOIN matches m ON p.match_id = m.match_id
    WHERE m.game_datetime >= NOW() - INTERVAL '90 days'  -- Last 90 days only
    GROUP BY p.puuid, p.summoner_name
    HAVING COUNT(*) >= 5  -- Minimum 5 games
)
SELECT 
    ps.*,
    ROUND(ps.wins::DECIMAL / ps.total_games * 100, 2) as win_rate,
    ROUND(ps.top4_finishes::DECIMAL / ps.total_games * 100, 2) as top4_rate,
    ROUND(ps.total_points::DECIMAL / ps.total_games, 2) as avg_points_per_game,
    categorize_placement(ROUND(ps.avg_placement)::INTEGER) as performance_category
FROM player_stats ps
ORDER BY ps.avg_placement ASC, ps.total_games DESC;

-- View: Meta Analysis (Popular Compositions)
CREATE OR REPLACE VIEW meta_analysis AS
WITH trait_popularity AS (
    SELECT 
        (trait->>'name')::TEXT as trait_name,
        COUNT(*) as games_played,
        ROUND(AVG((trait->>'tier_current')::INTEGER), 2) as avg_tier,
        ROUND(AVG(p.placement), 2) as avg_placement,
        COUNT(*) FILTER (WHERE p.placement <= 4) as top4_count,
        COUNT(*) FILTER (WHERE p.placement = 1) as wins
    FROM participants p
    JOIN matches m ON p.match_id = m.match_id
    CROSS JOIN jsonb_array_elements(p.traits_raw) trait
    WHERE m.game_datetime >= NOW() - INTERVAL '7 days'
    AND (trait->>'tier_current')::INTEGER > 0
    GROUP BY trait_name
    HAVING COUNT(*) >= 10  -- Minimum 10 occurrences
)
SELECT 
    tp.trait_name,
    tp.games_played,
    tp.avg_tier,
    tp.avg_placement,
    ROUND(tp.top4_count::DECIMAL / tp.games_played * 100, 2) as top4_rate,
    ROUND(tp.wins::DECIMAL / tp.games_played * 100, 2) as win_rate,
    ROUND(tp.games_played::DECIMAL / (SELECT COUNT(*) FROM participants p JOIN matches m ON p.match_id = m.match_id WHERE m.game_datetime >= NOW() - INTERVAL '7 days') * 100, 2) as popularity_percent
FROM trait_popularity tp
ORDER BY tp.games_played DESC, tp.avg_placement ASC;

-- View: Unit Performance Analysis
CREATE OR REPLACE VIEW unit_performance_analysis AS
WITH unit_stats AS (
    SELECT 
        (unit->>'character_id')::TEXT as unit_name,
        (unit->>'tier')::INTEGER as unit_tier,
        COUNT(*) as games_played,
        ROUND(AVG(p.placement), 2) as avg_placement,
        COUNT(*) FILTER (WHERE p.placement <= 4) as top4_count,
        COUNT(*) FILTER (WHERE (unit->>'chosen')::BOOLEAN = true) as chosen_count
    FROM participants p
    JOIN matches m ON p.match_id = m.match_id
    CROSS JOIN jsonb_array_elements(p.units_raw) unit
    WHERE m.game_datetime >= NOW() - INTERVAL '7 days'
    GROUP BY unit_name, unit_tier
    HAVING COUNT(*) >= 5
)
SELECT 
    us.unit_name,
    us.unit_tier,
    us.games_played,
    us.avg_placement,
    ROUND(us.top4_count::DECIMAL / us.games_played * 100, 2) as top4_rate,
    ROUND(us.chosen_count::DECIMAL / us.games_played * 100, 2) as chosen_rate
FROM unit_stats us
ORDER BY us.avg_placement ASC, us.games_played DESC;

-- View: Match Duration Analysis
CREATE OR REPLACE VIEW match_duration_analysis AS
SELECT 
    m.set_core_name,
    m.queue_type,
    COUNT(*) as match_count,
    AVG(EXTRACT(EPOCH FROM m.game_length)/60) as avg_duration_minutes,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM m.game_length)/60) as median_duration,
    MIN(EXTRACT(EPOCH FROM m.game_length)/60) as min_duration_minutes,
    MAX(EXTRACT(EPOCH FROM m.game_length)/60) as max_duration_minutes,
    ROUND(AVG(p.last_round), 1) as avg_last_round
FROM matches m
JOIN participants p ON m.match_id = p.match_id
WHERE m.game_datetime >= NOW() - INTERVAL '30 days'
GROUP BY m.set_core_name, m.queue_type
HAVING COUNT(*) >= 10
ORDER BY avg_duration_minutes DESC;

-- View: Clustering Performance Analysis
CREATE OR REPLACE VIEW clustering_performance_analysis AS
WITH cluster_stats AS (
    SELECT 
        pc.algorithm,
        pc.main_cluster_id,
        COUNT(*) as cluster_size,
        ROUND(AVG(p.placement), 2) as avg_placement,
        ROUND(AVG(p.level), 2) as avg_level,
        ROUND(AVG(p.total_damage_to_players), 0) as avg_damage,
        COUNT(*) FILTER (WHERE p.placement <= 4) as top4_count,
        ROUND(AVG(pc.silhouette_score), 4) as avg_silhouette_score
    FROM participant_clusters pc
    JOIN participants p ON pc.participant_id = p.participant_id
    WHERE pc.cluster_date >= NOW() - INTERVAL '7 days'
    GROUP BY pc.algorithm, pc.main_cluster_id
    HAVING COUNT(*) >= 5
)
SELECT 
    cs.*,
    ROUND(cs.top4_count::DECIMAL / cs.cluster_size * 100, 2) as top4_rate,
    categorize_placement(ROUND(cs.avg_placement)::INTEGER) as performance_category
FROM cluster_stats cs
ORDER BY cs.avg_placement ASC, cs.cluster_size DESC;

-- ============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ============================================================================

-- Materialized view for frequent meta queries
CREATE MATERIALIZED VIEW mv_current_meta AS
WITH recent_matches AS (
    SELECT m.match_id, m.game_datetime, m.set_core_name
    FROM matches m
    WHERE m.game_datetime >= NOW() - INTERVAL '3 days'
),
trait_performance AS (
    SELECT 
        (trait->>'name')::TEXT as trait_name,
        COUNT(*) as frequency,
        ROUND(AVG(p.placement), 2) as avg_placement,
        COUNT(*) FILTER (WHERE p.placement <= 4) as top4_count
    FROM participants p
    JOIN recent_matches rm ON p.match_id = rm.match_id
    CROSS JOIN jsonb_array_elements(p.traits_raw) trait
    WHERE (trait->>'tier_current')::INTEGER > 0
    GROUP BY trait_name
    HAVING COUNT(*) >= 5
)
SELECT 
    tp.trait_name,
    tp.frequency,
    tp.avg_placement,
    ROUND(tp.top4_count::DECIMAL / tp.frequency * 100, 2) as success_rate,
    CURRENT_TIMESTAMP as last_updated
FROM trait_performance tp
ORDER BY tp.frequency DESC, tp.avg_placement ASC;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_mv_current_meta_trait_name ON mv_current_meta (trait_name);
CREATE INDEX IF NOT EXISTS idx_mv_current_meta_frequency ON mv_current_meta (frequency DESC);

-- ============================================================================
-- REFRESH FUNCTIONS FOR MATERIALIZED VIEWS
-- ============================================================================

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_current_meta;
    
    -- Update match statistics
    INSERT INTO match_statistics (
        match_id, avg_level, avg_damage, total_rounds, 
        match_duration_minutes, top_traits, top_units, top_augments
    )
    SELECT 
        m.match_id,
        ROUND(AVG(p.level), 2),
        ROUND(AVG(p.total_damage_to_players), 2),
        MAX(p.last_round),
        ROUND(EXTRACT(EPOCH FROM m.game_length)/60),
        jsonb_agg(DISTINCT trait_name ORDER BY trait_name) FILTER (WHERE trait_name IS NOT NULL),
        jsonb_agg(DISTINCT unit_name ORDER BY unit_name) FILTER (WHERE unit_name IS NOT NULL),
        jsonb_agg(DISTINCT augment ORDER BY augment) FILTER (WHERE augment IS NOT NULL)
    FROM matches m
    JOIN participants p ON m.match_id = p.match_id
    CROSS JOIN LATERAL unnest(extract_trait_names(p.traits_raw)) as trait_name
    CROSS JOIN LATERAL unnest(extract_unit_names(p.units_raw)) as unit_name
    CROSS JOIN LATERAL unnest(extract_augment_names(p.augments)) as augment
    WHERE m.match_id NOT IN (SELECT match_id FROM match_statistics)
    AND m.game_datetime >= NOW() - INTERVAL '7 days'
    GROUP BY m.match_id, m.game_length
    ON CONFLICT (match_id) DO UPDATE SET
        calculated_at = NOW();
        
    PERFORM pg_notify('materialized_views_refreshed', 'All materialized views updated');
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- HELPER VIEWS FOR STREAMLIT APPLICATION
-- ============================================================================

-- View optimized for Streamlit dashboard
CREATE OR REPLACE VIEW streamlit_dashboard_data AS
SELECT 
    m.game_datetime::DATE as match_date,
    m.queue_type,
    m.set_core_name,
    COUNT(DISTINCT m.match_id) as total_matches,
    COUNT(*) as total_participants,
    ROUND(AVG(p.placement), 2) as avg_placement,
    ROUND(AVG(p.level), 2) as avg_level,
    ROUND(AVG(p.total_damage_to_players), 0) as avg_damage
FROM matches m
JOIN participants p ON m.match_id = p.match_id
WHERE m.game_datetime >= NOW() - INTERVAL '30 days'
GROUP BY m.game_datetime::DATE, m.queue_type, m.set_core_name
ORDER BY match_date DESC;

-- Add helpful comments
COMMENT ON FUNCTION get_player_stats(VARCHAR, INTEGER) IS 'Get comprehensive player statistics for a given time period';
COMMENT ON FUNCTION find_similar_compositions(TEXT[], TEXT[], DECIMAL, INTEGER) IS 'Find compositions similar to given traits and units';
COMMENT ON VIEW player_performance_summary IS 'Player performance metrics for the last 90 days';
COMMENT ON VIEW meta_analysis IS 'Current meta analysis showing popular traits and their success rates';
COMMENT ON MATERIALIZED VIEW mv_current_meta IS 'Materialized view of current meta for fast dashboard queries';

-- Migration completed successfully
SELECT 'Migration 003_functions_views.sql completed successfully' as status;