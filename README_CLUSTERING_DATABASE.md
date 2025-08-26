---
noteId: "0feb014072d711f095e8a9866d35445a"
tags: []

---

# TFT Database-Backed Clustering System

This document describes the updated TFT clustering system that uses PostgreSQL for efficient data processing and storage instead of JSONL files.

## Overview

The database-backed clustering system provides:

- **Database Integration**: Reads match/participant data directly from PostgreSQL
- **Efficient Processing**: Uses PostgreSQL's JSON operations for optimized data extraction
- **Persistent Storage**: Stores clustering results in the `participant_clusters` table
- **Incremental Clustering**: Only processes new/unclustered matches
- **Advanced Analytics**: Leverages database views for comprehensive cluster analysis
- **Backward Compatibility**: Can still export CSV files for legacy workflows

## Key Components

### 1. Core Clustering Engine (`clustering.py`)
- `TFTClusteringEngine`: Main clustering class with database integration
- `run_database_clustering_pipeline()`: Full database-backed clustering
- `run_incremental_clustering_pipeline()`: Incremental clustering for new data
- Hierarchical clustering: Sub-clusters (exact carry matching) + Main clusters (2-3 common carries)

### 2. Database Operations (`database/clustering_operations.py`)
- `DatabaseClusteringEngine`: Database-optimized clustering operations
- Efficient data extraction using PostgreSQL JSON queries
- Batch processing for large datasets
- Cluster result storage and management

### 3. Database Schema
- `participant_clusters`: Stores clustering results
- `participant_cluster_analysis`: View for detailed sub-cluster analysis  
- `cluster_performance_stats`: View for main cluster performance metrics

## Usage Examples

### Basic Database Clustering
```bash
# Full clustering using database
python clustering.py --use-database

# Filter by TFT set and date range
python clustering.py --use-database --set-filter TFTSet14 --date-from 2024-08-01

# Export results to CSV for backward compatibility
python clustering.py --use-database --csv-export clusters.csv
```

### Incremental Clustering
```bash
# Only cluster new/unclustered matches
python clustering.py --use-database --incremental

# Force recluster all matches (clears existing clusters)
python clustering.py --use-database --incremental --force-recluster
```

### Advanced Filtering
```bash
# Filter by queue types and date range
python clustering.py --use-database --queue-types ranked hyper_roll --date-from 2024-08-01 --date-to 2024-08-06

# Adjust clustering parameters
python clustering.py --use-database --min-sub-cluster-size 10 --min-main-cluster-size 5
```

## Database Schema Details

### `participant_clusters` Table
```sql
- cluster_id (UUID): Unique identifier for cluster assignment
- participant_id (UUID): References participants table
- algorithm (VARCHAR): Clustering algorithm used ('hierarchical')
- main_cluster_id (INTEGER): Main cluster assignment (-1 if not clustered)
- sub_cluster_id (INTEGER): Sub-cluster assignment (-1 if not clustered)
- carry_units (TEXT[]): Array of carry unit character IDs
- cluster_metadata (JSONB): Additional metadata (similarity scores, algorithm version)
- parameters (JSONB): Clustering parameters used
- match_id (UUID): References matches table
- puuid (VARCHAR): Player UUID
- created_at (TIMESTAMPTZ): When clustering was performed
- updated_at (TIMESTAMPTZ): Last update timestamp
```

### Key Database Views

#### `participant_cluster_analysis`
Detailed performance analysis for each sub-cluster:
- Participant count, common carries, performance metrics
- Average placement, win rate, top 4 rate
- Statistical measures (standard deviation, best/worst placement)

#### `cluster_performance_stats`  
Aggregated statistics by main cluster:
- Sub-cluster count, total participants
- Carry unit frequencies within cluster
- Performance trends (recent vs overall)
- Date range coverage

## Programming Interface

### Python API Usage

```python
from clustering import run_database_clustering_pipeline, run_incremental_clustering_pipeline
from database.clustering_operations import get_cluster_performance_summary, get_carry_unit_analysis

# Run full clustering
results = run_database_clustering_pipeline(
    filters={'set_core_name': 'TFTSet14', 'queue_types': ['ranked']},
    min_sub_cluster_size=5,
    min_main_cluster_size=3
)

# Run incremental clustering
incremental_results = run_incremental_clustering_pipeline(
    filters={'date_from': '2024-08-01'},
    force_recluster=False
)

# Get performance analysis
performance = get_cluster_performance_summary()
carry_analysis = get_carry_unit_analysis()
```

### Database Queries

```sql
-- Get top performing main clusters
SELECT 
    main_cluster_id,
    total_participants,
    avg_placement,
    winrate,
    top4_rate,
    all_carries
FROM cluster_performance_stats
ORDER BY avg_placement ASC, total_participants DESC
LIMIT 10;

-- Get carry unit performance across all clusters
SELECT 
    unit_name,
    COUNT(*) as appearances,
    AVG(p.placement) as avg_placement,
    COUNT(*) FILTER (WHERE p.placement = 1) * 100.0 / COUNT(*) as winrate
FROM participant_clusters pc
CROSS JOIN unnest(pc.carry_units) AS unit_name
INNER JOIN participants p ON pc.participant_id = p.participant_id
WHERE array_length(pc.carry_units, 1) > 0
GROUP BY unit_name
ORDER BY appearances DESC;
```

## Performance Optimizations

### Database Indexes
The system includes optimized indexes for clustering operations:
- GIN index on `units_raw` for efficient carry extraction
- Composite indexes on clustering lookup fields
- Date-based indexes for temporal filtering

### Batch Processing
- Configurable batch sizes for memory management
- Transaction-based processing with rollback support
- Efficient bulk insert operations

### Query Optimization
- PostgreSQL JSON operations for carry unit extraction
- Materialized views for complex aggregations
- Partition-aware queries for large datasets

## Monitoring and Debugging

### Test Suite
Run the comprehensive test suite:
```bash
python test_database_clustering.py
```

### Health Checks
```python
from database.connection import health_check

# Check database connectivity and performance
health = health_check()
print(health)
```

### Performance Monitoring
```python
from database.clustering_operations import DatabaseClusteringEngine

engine = DatabaseClusteringEngine()
stats = engine.calculate_cluster_statistics()

# Monitor clustering coverage and quality
print(f"Total participants: {stats['basic_statistics']['total_participants']}")
print(f"Clustering rate: {stats['basic_statistics']['sub_clustering_rate']}%")
```

## Migration from JSONL System

### Backward Compatibility
- Legacy functions remain available
- CSV export functionality preserved
- Existing analysis scripts continue to work

### Migration Steps
1. Ensure database is set up and populated with match data
2. Run initial full clustering: `python clustering.py --use-database`
3. Set up incremental clustering for ongoing updates
4. Migrate analysis workflows to use database views
5. Optional: Export CSV files for legacy tools

## Configuration

### Environment Variables
```bash
# Database connection (see database/config.py)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tft_matches
DB_USER=tft_app_user
DB_PASSWORD=your_password

# Clustering parameters (optional)
TFT_CLUSTERING_MIN_SUB_SIZE=5
TFT_CLUSTERING_MIN_MAIN_SIZE=3
TFT_CLUSTERING_BATCH_SIZE=1000
```

### Clustering Parameters
- `min_sub_cluster_size`: Minimum compositions for valid sub-clusters (default: 5)
- `min_main_cluster_size`: Minimum sub-clusters for valid main clusters (default: 3)
- `similarity_threshold`: Threshold for main cluster grouping (default: 0.6)
- `carry_item_threshold`: Minimum items to be considered a carry (default: 2)

## Troubleshooting

### Common Issues

1. **Database Connection Failures**
   - Check database configuration in `database/config.py`
   - Ensure PostgreSQL is running and accessible
   - Verify user permissions and database exists

2. **No Compositions Found**
   - Check if match data exists in database
   - Verify filters aren't too restrictive
   - Ensure units have item data for carry detection

3. **Clustering Results Empty**
   - Lower minimum cluster size thresholds
   - Check if carry units are being detected correctly
   - Verify similarity threshold isn't too strict

4. **Performance Issues**
   - Increase batch size for better throughput
   - Check database indexes are created
   - Monitor memory usage and adjust limits

### Debugging Commands
```bash
# Test database connectivity
python -c "from database.connection import test_connection; print(test_connection())"

# Check clustering operations
python -c "from database.clustering_operations import DatabaseClusteringEngine; engine = DatabaseClusteringEngine(); print(len(engine.extract_carry_compositions(batch_size=10)))"

# Run incremental clustering with verbose output
python clustering.py --use-database --incremental --csv-export debug_clusters.csv
```

## Future Enhancements

- Real-time clustering updates via triggers
- Machine learning-based similarity metrics  
- Advanced visualization and dashboards
- API endpoints for external integrations
- Multi-dimensional clustering (traits, items, augments)