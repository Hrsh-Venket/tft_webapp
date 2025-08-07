-- TFT Match Analysis Database Schema
-- Migration 005: Clustering Enhancements
-- Version: 1.1.0
-- Created: 2024-08-06

-- Add missing fields to participant_clusters table for hierarchical clustering support
ALTER TABLE participant_clusters 
ADD COLUMN IF NOT EXISTS match_id UUID REFERENCES matches(match_id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS puuid VARCHAR(100) NOT NULL,
ADD COLUMN IF NOT EXISTS carry_units TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS cluster_metadata JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Create indexes for efficient clustering queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_match_puuid 
ON participant_clusters (match_id, puuid);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_main_sub 
ON participant_clusters (main_cluster_id, sub_cluster_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_carry_units 
ON participant_clusters USING gin (carry_units);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_participant_clusters_created_at 
ON participant_clusters (created_at DESC);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_participant_clusters_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for automatic updated_at updates
DROP TRIGGER IF EXISTS trigger_participant_clusters_updated_at ON participant_clusters;
CREATE TRIGGER trigger_participant_clusters_updated_at
    BEFORE UPDATE ON participant_clusters
    FOR EACH ROW
    EXECUTE PROCEDURE update_participant_clusters_updated_at();

-- Create view for cluster performance analysis
CREATE OR REPLACE VIEW participant_cluster_analysis AS
SELECT 
    pc.main_cluster_id,
    pc.sub_cluster_id,
    COUNT(*) as participant_count,
    array_agg(DISTINCT carry_unit) as common_carries,
    AVG(p.placement) as avg_placement,
    COUNT(*) FILTER (WHERE p.placement = 1) * 100.0 / COUNT(*) as winrate,
    COUNT(*) FILTER (WHERE p.placement <= 4) * 100.0 / COUNT(*) as top4_rate,
    AVG(p.last_round) as avg_last_round,
    AVG(p.gold_left) as avg_gold_left,
    MIN(p.placement) as best_placement,
    MAX(p.placement) as worst_placement,
    STDDEV(p.placement) as placement_stddev
FROM participant_clusters pc
INNER JOIN participants p ON pc.participant_id = p.participant_id
CROSS JOIN LATERAL unnest(pc.carry_units) AS carry_unit
WHERE pc.main_cluster_id != -1 AND pc.sub_cluster_id != -1
GROUP BY pc.main_cluster_id, pc.sub_cluster_id
ORDER BY avg_placement ASC, participant_count DESC;

-- Create view for cluster performance stats by main cluster only
CREATE OR REPLACE VIEW cluster_performance_stats AS
SELECT 
    pc.main_cluster_id,
    COUNT(DISTINCT pc.sub_cluster_id) as sub_cluster_count,
    COUNT(*) as total_participants,
    array_agg(DISTINCT carry_unit ORDER BY carry_unit) as all_carries,
    AVG(p.placement) as avg_placement,
    COUNT(*) FILTER (WHERE p.placement = 1) * 100.0 / COUNT(*) as winrate,
    COUNT(*) FILTER (WHERE p.placement <= 4) * 100.0 / COUNT(*) as top4_rate,
    AVG(p.last_round) as avg_last_round,
    
    -- Calculate carry frequency within main cluster
    (
        SELECT jsonb_object_agg(
            carry_unit, 
            ROUND((COUNT(*)::float / pc_outer.total_participants * 100)::numeric, 1)
        )
        FROM (
            SELECT 
                unnest(pc_inner.carry_units) as carry_unit,
                COUNT(*) as carry_count
            FROM participant_clusters pc_inner
            WHERE pc_inner.main_cluster_id = pc.main_cluster_id
            AND pc_inner.main_cluster_id != -1
            GROUP BY unnest(pc_inner.carry_units)
        ) carry_freq,
        (SELECT COUNT(*) FROM participant_clusters pc_count 
         WHERE pc_count.main_cluster_id = pc.main_cluster_id) as total_participants
        GROUP BY total_participants
    ) as carry_frequencies,
    
    -- Date range for this cluster
    MIN(m.game_datetime) as earliest_match,
    MAX(m.game_datetime) as latest_match,
    
    -- Performance trend (last 7 days vs overall)
    AVG(p.placement) FILTER (WHERE m.game_datetime >= NOW() - INTERVAL '7 days') as avg_placement_recent
    
FROM participant_clusters pc
INNER JOIN participants p ON pc.participant_id = p.participant_id
INNER JOIN matches m ON p.match_id = m.match_id
CROSS JOIN LATERAL unnest(pc.carry_units) AS carry_unit
WHERE pc.main_cluster_id != -1
GROUP BY pc.main_cluster_id
ORDER BY avg_placement ASC, total_participants DESC;

-- Add comments for documentation
COMMENT ON TABLE participant_clusters IS 'Stores hierarchical clustering results for TFT compositions with both sub-cluster and main cluster assignments';
COMMENT ON COLUMN participant_clusters.main_cluster_id IS 'Main cluster ID - groups sub-clusters with 2-3 common carry units';
COMMENT ON COLUMN participant_clusters.sub_cluster_id IS 'Sub-cluster ID - exact carry unit matching for precise compositions';
COMMENT ON COLUMN participant_clusters.carry_units IS 'Array of carry unit character IDs (units with 2+ items)';
COMMENT ON COLUMN participant_clusters.cluster_metadata IS 'Additional clustering metadata including similarity scores and algorithm version';

COMMENT ON VIEW participant_cluster_analysis IS 'Detailed performance analysis for each sub-cluster within main clusters';
COMMENT ON VIEW cluster_performance_stats IS 'Aggregated performance statistics by main cluster with carry frequency analysis';