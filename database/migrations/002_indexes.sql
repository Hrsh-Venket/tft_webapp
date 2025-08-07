-- TFT Match Analysis Database Indexes
-- Migration 002: Index Creation for Performance
-- Version: 1.0.0
-- Created: 2024-08-06

-- ============================================================================
-- MATCHES TABLE INDEXES
-- ============================================================================

-- Primary lookup indexes for matches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_game_id 
    ON matches (game_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_datetime 
    ON matches (game_datetime DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_queue_type 
    ON matches (queue_type, game_datetime DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_set_core 
    ON matches (set_core_name, game_datetime DESC);

-- Composite indexes for common queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_queue_set_datetime 
    ON matches (queue_type, set_core_name, game_datetime DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_region_datetime 
    ON matches (region, game_datetime DESC);

-- Game version analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_version_datetime 
    ON matches (game_version, game_datetime DESC);

-- ============================================================================
-- PARTICIPANTS TABLE INDEXES
-- ============================================================================

-- Foreign key and lookup indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_match_id 
    ON participants (match_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_puuid 
    ON participants (puuid);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_summoner_name 
    ON participants (summoner_name);

-- Performance analysis indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_placement 
    ON participants (placement);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_level 
    ON participants (level DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_damage 
    ON participants (total_damage_to_players DESC);

-- Composite indexes for leaderboards and analytics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_puuid_placement 
    ON participants (puuid, placement, match_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_level_placement 
    ON participants (level DESC, placement);

-- Economic analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_gold_placement 
    ON participants (gold_left DESC, placement);

-- Time-based analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_time_eliminated 
    ON participants (time_eliminated DESC) WHERE time_eliminated IS NOT NULL;

-- ============================================================================
-- JSONB INDEXES FOR AUGMENTS, TRAITS, AND UNITS
-- ============================================================================

-- Augments analysis (GIN indexes for JSONB arrays)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_augments_gin 
    ON participants USING GIN (augments);

-- Traits analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_traits_gin 
    ON participants USING GIN (traits_raw);

-- Units analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_units_gin 
    ON participants USING GIN (units_raw);

-- Companion analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_companion_gin 
    ON participants USING GIN (companion);

-- Specific JSONB path indexes for common queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_augments_array 
    ON participants USING GIN ((augments -> '$[*]'::text[]));

-- ============================================================================
-- PARTICIPANT_CLUSTERS TABLE INDEXES
-- ============================================================================

-- Primary lookup indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_participant_id 
    ON participant_clusters (participant_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_main_cluster 
    ON participant_clusters (main_cluster_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_sub_cluster 
    ON participant_clusters (sub_cluster_id) WHERE sub_cluster_id IS NOT NULL;

-- Algorithm and date analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_algorithm_date 
    ON participant_clusters (algorithm, cluster_date DESC);

-- Performance analysis indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_silhouette 
    ON participant_clusters (silhouette_score DESC) WHERE silhouette_score IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_distance 
    ON participant_clusters (distance_to_centroid) WHERE distance_to_centroid IS NOT NULL;

-- Cluster statistics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_size 
    ON participant_clusters (cluster_size DESC) WHERE cluster_size IS NOT NULL;

-- Feature importance analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_features_gin 
    ON participant_clusters USING GIN (feature_weights);

-- ============================================================================
-- PARTICIPANT_UNITS TABLE INDEXES
-- ============================================================================

-- Foreign key and lookup indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_units_participant_id 
    ON participant_units (participant_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_units_character_id 
    ON participant_units (character_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_units_name 
    ON participant_units (unit_name);

-- Unit properties analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_units_tier 
    ON participant_units (tier DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_units_rarity 
    ON participant_units (rarity DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_units_chosen 
    ON participant_units (chosen) WHERE chosen = TRUE;

-- Items analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_units_items_gin 
    ON participant_units USING GIN (items);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_units_item_names_gin 
    ON participant_units USING GIN (item_names);

-- Traits analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_units_traits_gin 
    ON participant_units USING GIN (unit_traits);

-- Composite indexes for unit composition analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_units_char_tier_rarity 
    ON participant_units (character_id, tier, rarity);

-- ============================================================================
-- PARTICIPANT_TRAITS TABLE INDEXES
-- ============================================================================

-- Foreign key and lookup indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_traits_participant_id 
    ON participant_traits (participant_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_traits_name 
    ON participant_traits (trait_name);

-- Trait strength analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_traits_tier 
    ON participant_traits (current_tier DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_traits_units 
    ON participant_traits (num_units DESC);

-- Composite indexes for trait combination analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_traits_name_tier 
    ON participant_traits (trait_name, current_tier DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_traits_name_units 
    ON participant_traits (trait_name, num_units DESC);

-- Style and tier analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_traits_style 
    ON participant_traits (style) WHERE style > 0;

-- ============================================================================
-- MATCH_STATISTICS TABLE INDEXES
-- ============================================================================

-- Primary lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_statistics_match_id 
    ON match_statistics (match_id);

-- Performance metrics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_statistics_avg_level 
    ON match_statistics (avg_level DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_statistics_avg_damage 
    ON match_statistics (avg_damage DESC);

-- Duration analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_statistics_duration 
    ON match_statistics (match_duration_minutes DESC);

-- Popular compositions (GIN indexes for JSONB)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_statistics_top_traits_gin 
    ON match_statistics USING GIN (top_traits);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_statistics_top_units_gin 
    ON match_statistics USING GIN (top_units);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_statistics_top_augments_gin 
    ON match_statistics USING GIN (top_augments);

-- Calculation timestamp
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_statistics_calculated_at 
    ON match_statistics (calculated_at DESC);

-- ============================================================================
-- AUDIT_LOG TABLE INDEXES
-- ============================================================================

-- Primary lookup indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_table_name 
    ON audit_log (table_name);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_record_id 
    ON audit_log (record_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_operation 
    ON audit_log (operation);

-- Time-based analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_changed_at 
    ON audit_log (changed_at DESC);

-- User tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_changed_by 
    ON audit_log (changed_by);

-- Composite indexes for audit queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_table_record_time 
    ON audit_log (table_name, record_id, changed_at DESC);

-- JSONB indexes for audit data
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_old_values_gin 
    ON audit_log USING GIN (old_values);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_new_values_gin 
    ON audit_log USING GIN (new_values);

-- ============================================================================
-- CROSS-TABLE ANALYTICS INDEXES
-- ============================================================================

-- Match-participant performance analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_participant_performance 
    ON participants (match_id, placement, total_damage_to_players DESC);

-- Player performance tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_performance_tracking 
    ON participants (puuid, placement, match_id);

-- Cluster-performance correlation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cluster_performance_analysis 
    ON participant_clusters (main_cluster_id, participant_id);

-- ============================================================================
-- PARTIAL INDEXES FOR SPECIFIC USE CASES
-- ============================================================================

-- High-performing participants only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_top_performers 
    ON participants (puuid, total_damage_to_players DESC, placement) 
    WHERE placement <= 4;

-- Recent matches only (last 30 days)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_recent_matches 
    ON participants (puuid, placement, match_id) 
    WHERE created_at > (NOW() - INTERVAL '30 days');

-- Non-eliminated participants
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_active 
    ON participants (match_id, level DESC) 
    WHERE time_eliminated IS NULL;

-- High-level participants
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_high_level 
    ON participants (level DESC, placement, total_damage_to_players DESC) 
    WHERE level >= 7;

-- ============================================================================
-- EXPRESSION INDEXES FOR CALCULATED VALUES
-- ============================================================================

-- Damage per level ratio
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_damage_per_level 
    ON participants ((total_damage_to_players::DECIMAL / GREATEST(level, 1)) DESC) 
    WHERE total_damage_to_players > 0;

-- Win rate calculation support (for materialized views)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_wins 
    ON participants (puuid, (CASE WHEN placement = 1 THEN 1 ELSE 0 END));

-- Top 4 finish rate
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participants_top4 
    ON participants (puuid, (CASE WHEN placement <= 4 THEN 1 ELSE 0 END));

-- ============================================================================
-- MAINTENANCE AND MONITORING
-- ============================================================================

-- Create function to analyze index usage
CREATE OR REPLACE FUNCTION analyze_index_usage()
RETURNS TABLE(
    schemaname TEXT,
    tablename TEXT,
    indexname TEXT,
    num_scans BIGINT,
    tuples_read BIGINT,
    tuples_fetched BIGINT,
    usage_ratio DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname::TEXT,
        tablename::TEXT,
        indexname::TEXT,
        idx_scan as num_scans,
        idx_tup_read as tuples_read,
        idx_tup_fetch as tuples_fetched,
        CASE 
            WHEN idx_scan = 0 THEN 0 
            ELSE ROUND(idx_tup_fetch::DECIMAL / idx_scan, 2) 
        END as usage_ratio
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public'
    ORDER BY idx_scan DESC;
END;
$$ LANGUAGE plpgsql;

-- Create function to find unused indexes
CREATE OR REPLACE FUNCTION find_unused_indexes()
RETURNS TABLE(
    schema_name TEXT,
    table_name TEXT,
    index_name TEXT,
    index_size TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname::TEXT,
        tablename::TEXT,
        indexname::TEXT,
        pg_size_pretty(pg_relation_size(i.indexrelid))::TEXT
    FROM pg_stat_user_indexes i
    JOIN pg_index idx ON i.indexrelid = idx.indexrelid
    WHERE i.idx_scan = 0
    AND NOT idx.indisunique
    AND schemaname = 'public'
    ORDER BY pg_relation_size(i.indexrelid) DESC;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON FUNCTION analyze_index_usage() IS 'Analyzes index usage statistics for performance monitoring';
COMMENT ON FUNCTION find_unused_indexes() IS 'Identifies potentially unused indexes for cleanup';

-- Migration completed successfully
SELECT 'Migration 002_indexes.sql completed successfully' as status;