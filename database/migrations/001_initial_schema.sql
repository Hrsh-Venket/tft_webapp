-- TFT Match Analysis Database Schema
-- Migration 001: Initial Schema Creation
-- Version: 1.0.0
-- Created: 2024-08-06

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create custom enum types
CREATE TYPE match_queue_type AS ENUM (
    'ranked', 'normal', 'tutorial', 'tournament', 
    'custom', 'double_up', 'hyper_roll'
);

CREATE TYPE game_mode AS ENUM (
    'classic', 'double_up', 'hyper_roll', 'tutorial', 'arena'
);

CREATE TYPE participant_placement_type AS ENUM (
    'first', 'second', 'third', 'fourth', 
    'fifth', 'sixth', 'seventh', 'eighth'
);

-- Create matches table (partitioned by date)
CREATE TABLE matches (
    match_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id VARCHAR(100) UNIQUE NOT NULL,
    game_datetime TIMESTAMPTZ NOT NULL,
    game_length INTERVAL NOT NULL,
    game_version VARCHAR(20) NOT NULL,
    queue_id INTEGER NOT NULL,
    queue_type match_queue_type NOT NULL,
    game_mode game_mode NOT NULL DEFAULT 'classic',
    set_core_name VARCHAR(50) NOT NULL,
    set_mutator VARCHAR(50),
    region VARCHAR(10) NOT NULL DEFAULT 'NA1',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (game_datetime);

-- Create partitions for matches table (monthly partitions)
-- Create partitions for current and next few months
CREATE TABLE matches_2024_07 PARTITION OF matches
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');

CREATE TABLE matches_2024_08 PARTITION OF matches
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');

CREATE TABLE matches_2024_09 PARTITION OF matches
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');

CREATE TABLE matches_2024_10 PARTITION OF matches
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');

CREATE TABLE matches_2024_11 PARTITION OF matches
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');

CREATE TABLE matches_2024_12 PARTITION OF matches
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

CREATE TABLE matches_2025_01 PARTITION OF matches
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Create participants table
CREATE TABLE participants (
    participant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    puuid VARCHAR(100) NOT NULL,
    summoner_name VARCHAR(50),
    summoner_level INTEGER,
    profile_icon_id INTEGER,
    
    -- Game performance
    placement INTEGER NOT NULL CHECK (placement BETWEEN 1 AND 8),
    placement_type participant_placement_type NOT NULL,
    level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 10),
    last_round INTEGER NOT NULL,
    players_eliminated INTEGER DEFAULT 0,
    time_eliminated INTERVAL,
    total_damage_to_players INTEGER DEFAULT 0,
    
    -- Economy
    gold_left INTEGER DEFAULT 0,
    
    -- Augments (stored as JSON array)
    augments JSONB DEFAULT '[]'::jsonb,
    
    -- Companion data (JSON object)
    companion JSONB DEFAULT '{}'::jsonb,
    
    -- Raw traits and units data (for backward compatibility)
    traits_raw JSONB DEFAULT '[]'::jsonb,
    units_raw JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(match_id, puuid)
);

-- Create participant_clusters table for clustering results
CREATE TABLE participant_clusters (
    cluster_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    participant_id UUID NOT NULL REFERENCES participants(participant_id) ON DELETE CASCADE,
    
    -- Clustering metadata
    algorithm VARCHAR(50) NOT NULL DEFAULT 'hierarchical',
    parameters JSONB DEFAULT '{}'::jsonb,
    cluster_date TIMESTAMPTZ DEFAULT NOW(),
    
    -- Cluster assignments
    main_cluster_id INTEGER NOT NULL,
    sub_cluster_id INTEGER,
    cluster_label VARCHAR(100),
    cluster_description TEXT,
    
    -- Cluster statistics
    cluster_size INTEGER,
    silhouette_score DECIMAL(5,4),
    distance_to_centroid DECIMAL(10,6),
    
    -- Feature importance
    feature_weights JSONB DEFAULT '{}'::jsonb,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(participant_id, algorithm, cluster_date)
);

-- Create normalized participant_units table
CREATE TABLE participant_units (
    unit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    participant_id UUID NOT NULL REFERENCES participants(participant_id) ON DELETE CASCADE,
    
    -- Unit identification
    character_id VARCHAR(50) NOT NULL,
    unit_name VARCHAR(100) NOT NULL,
    
    -- Unit properties
    tier INTEGER NOT NULL CHECK (tier BETWEEN 1 AND 5),
    rarity INTEGER NOT NULL CHECK (rarity BETWEEN 1 AND 5),
    chosen BOOLEAN DEFAULT FALSE,
    
    -- Items (stored as JSON array of item IDs)
    items JSONB DEFAULT '[]'::jsonb,
    item_names JSONB DEFAULT '[]'::jsonb,
    
    -- Unit traits (JSON array)
    unit_traits JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create normalized participant_traits table
CREATE TABLE participant_traits (
    trait_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    participant_id UUID NOT NULL REFERENCES participants(participant_id) ON DELETE CASCADE,
    
    -- Trait identification
    trait_name VARCHAR(100) NOT NULL,
    
    -- Trait properties
    current_tier INTEGER NOT NULL CHECK (current_tier BETWEEN 0 AND 10),
    num_units INTEGER NOT NULL DEFAULT 0,
    
    -- Trait style/type
    style INTEGER DEFAULT 0,
    tier_current INTEGER DEFAULT 0,
    tier_total INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(participant_id, trait_name)
);

-- Create match_stats materialized view base table for quick analytics
CREATE TABLE match_statistics (
    stat_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    
    -- Match-level statistics
    avg_level DECIMAL(4,2),
    avg_damage DECIMAL(10,2),
    total_rounds INTEGER,
    match_duration_minutes INTEGER,
    
    -- Popular compositions
    top_traits JSONB DEFAULT '[]'::jsonb,
    top_units JSONB DEFAULT '[]'::jsonb,
    top_augments JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(match_id)
);

-- Create audit table for tracking data changes
CREATE TABLE audit_log (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(50) NOT NULL,
    record_id UUID NOT NULL,
    operation VARCHAR(20) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100) DEFAULT current_user,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create function to automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at timestamps
CREATE TRIGGER update_matches_updated_at 
    BEFORE UPDATE ON matches 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_participants_updated_at 
    BEFORE UPDATE ON participants 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function for automatic partition management
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name TEXT, start_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    end_date DATE;
BEGIN
    partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
    end_date := start_date + INTERVAL '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I
                    FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- Create function to automatically create partitions
CREATE OR REPLACE FUNCTION auto_create_partitions()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM create_monthly_partition('matches', date_trunc('month', NEW.game_datetime)::date);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic partition creation
CREATE TRIGGER auto_partition_matches
    BEFORE INSERT ON matches
    FOR EACH ROW EXECUTE FUNCTION auto_create_partitions();

-- Grant permissions for application user
-- These will be applied when the application user is created
DO $$
BEGIN
    -- Create application role if it doesn't exist
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tft_app_user') THEN
        CREATE ROLE tft_app_user WITH LOGIN PASSWORD 'tft_app_password';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE tft_matches TO tft_app_user;
GRANT USAGE ON SCHEMA public TO tft_app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tft_app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tft_app_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO tft_app_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tft_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO tft_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO tft_app_user;

-- Add helpful comments
COMMENT ON TABLE matches IS 'Core match data partitioned by game_datetime';
COMMENT ON TABLE participants IS 'Player participation data for each match';
COMMENT ON TABLE participant_clusters IS 'Clustering results and analysis data';
COMMENT ON TABLE participant_units IS 'Normalized unit composition data';
COMMENT ON TABLE participant_traits IS 'Normalized trait composition data';
COMMENT ON TABLE match_statistics IS 'Pre-calculated match statistics for performance';
COMMENT ON TABLE audit_log IS 'Audit trail for data changes';

-- Create initial data validation function
CREATE OR REPLACE FUNCTION validate_match_data(
    p_game_id VARCHAR,
    p_participant_count INTEGER DEFAULT 8
) RETURNS BOOLEAN AS $$
DECLARE
    participant_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO participant_count 
    FROM participants p
    JOIN matches m ON p.match_id = m.match_id
    WHERE m.game_id = p_game_id;
    
    RETURN participant_count = p_participant_count;
END;
$$ LANGUAGE plpgsql;

-- Migration completed successfully
SELECT 'Migration 001_initial_schema.sql completed successfully' as status;