---
noteId: "e758bc2072d811f095e8a9866d35445a"
tags: []

---

# TFT Querying System Migration to PostgreSQL

This document describes the migration of the TFT querying system from file-based operations (JSONL/CSV) to PostgreSQL database operations.

## Overview

The updated querying system provides:
- **PostgreSQL Database Mode**: High-performance queries using SQL and database indexes
- **Legacy File Mode**: Backward compatibility with existing JSONL/CSV files
- **Automatic Fallback**: Seamless switching between modes based on availability
- **Same API**: Identical interface for both modes to maintain compatibility

## Key Changes

### 1. New TFTQueryDB Class

The main `TFTQuery` class is now an alias to `TFTQueryDB`, which provides:
- SQL-based filtering using PostgreSQL JSON operations
- Efficient database queries with proper indexing
- Automatic connection management and error handling
- Fallback to legacy mode when needed

### 2. Database Schema Integration

The system leverages these database tables:
- `participants` - Core participant data with JSONB columns
- `participant_clusters` - Hierarchical clustering results
- `matches` - Match metadata
- Views: `participant_cluster_analysis`, `cluster_performance_stats`

### 3. SQL Filter Generation

Python filter conditions are converted to efficient SQL WHERE clauses:

```python
# Python (Legacy)
lambda p, c, m: any(u['character_id'] == 'TFT14_Aphelios' for u in p['units'])

# SQL (Database Mode)
EXISTS (
    SELECT 1 FROM jsonb_array_elements(p.units_raw) AS unit_data
    WHERE unit_data->>'character_id' = 'TFT14_Aphelios'
)
```

## Usage Examples

### Basic Usage (Auto-Detection)

```python
from querying import TFTQuery

# Auto-detects database availability
query = TFTQuery()
stats = query.add_unit('TFT14_Aphelios').get_stats()
```

### Explicit Database Mode

```python
from querying import TFTQuery

# Force database mode
query = TFTQuery(use_database=True)
stats = query.add_unit('TFT14_Aphelios').add_trait('TFT14_Vanguard', min_tier=2).get_stats()
```

### Legacy File Mode

```python
from querying import TFTQueryLegacy

# Use legacy file-based operations
query = TFTQueryLegacy('matches.jsonl', 'clusters.csv')
stats = query.add_unit('TFT14_Aphelios').get_stats()
```

### Complex Queries

```python
# Database mode with complex filtering
query = TFTQuery(use_database=True)
stats = (query
    .add_unit('TFT14_Aphelios')
    .add_trait('TFT14_Vanguard', min_tier=2, max_tier=4)
    .add_player_level(min_level=8)
    .set_sub_cluster(5)
    .get_stats())
```

### Cluster Statistics

```python
# Get all cluster stats from database
cluster_stats = TFTQuery.get_all_cluster_stats(
    min_size=10, 
    cluster_type='sub', 
    use_database=True
)
```

## Performance Benefits

### Database Mode Advantages:
- **Indexing**: Proper indexes on commonly queried fields
- **JSON Operations**: PostgreSQL native JSON operators (`->`, `->>`, `@>`)
- **Aggregations**: SQL-based statistics and grouping
- **Memory Efficiency**: Processes only matching records
- **Concurrency**: Multiple concurrent queries
- **Filtering**: Server-side filtering reduces data transfer

### Legacy Mode:
- **Full Scan**: Reads entire files into memory
- **Python Processing**: All filtering done in Python
- **Memory Usage**: Higher memory requirements for large datasets

## Query Method Support

All existing query methods are supported in database mode:

| Method | Database Mode | Legacy Mode | Notes |
|--------|---------------|-------------|--------|
| `add_unit()` | ✅ JSON EXISTS | ✅ Python filter | |
| `add_trait()` | ✅ JSON EXISTS | ✅ Python filter | |
| `add_player_level()` | ✅ Direct column | ✅ Python filter | |
| `add_last_round()` | ✅ Direct column | ✅ Python filter | |
| `add_unit_star_level()` | ✅ JSON casting | ✅ Python filter | |
| `add_unit_item_count()` | ✅ JSON length | ✅ Python filter | |
| `add_augment()` | ✅ JSON array | ✅ Python filter | |
| `set_patch()` | ✅ LIKE pattern | ✅ Python filter | |
| `set_sub_cluster()` | ✅ JOIN clusters | ✅ CSV lookup | |
| `set_main_cluster()` | ✅ JOIN clusters | ✅ CSV lookup | |
| `add_custom_filter()` | ✅ SQL condition | ❌ Not supported | Database only |
| `add_or_group()` | ✅ SQL OR | ✅ Python any() | Limited SQL support |

## Fallback Behavior

The system automatically falls back to legacy mode when:
1. Database is not available (import fails)
2. Database connection fails
3. Query execution fails
4. Complex Python lambdas are used (not convertible to SQL)

## Configuration

### Command Line Usage

```bash
# Auto-detect mode (default)
python querying.py

# Force database mode
python querying.py --use-database

# Force legacy mode
python querying.py --force-legacy

# Legacy file specification (only in legacy mode)
python querying.py --force-legacy --input matches.jsonl --clusters clusters.csv
```

### Environment Setup

Database mode requires:
- PostgreSQL connection available
- Database tables populated with match data
- `database` module properly configured

Legacy mode requires:
- JSONL match files
- CSV cluster files
- `clustering` module for file reading

## Migration Steps

1. **Import Data**: Ensure match data is loaded into PostgreSQL
2. **Run Clustering**: Generate cluster assignments in database
3. **Test Queries**: Verify database queries return expected results
4. **Update Code**: Switch from `TFTQueryLegacy` to `TFTQuery`
5. **Performance Check**: Compare query performance between modes

## Error Handling

The system includes comprehensive error handling:
- Database connection failures → automatic fallback to legacy
- Query execution errors → fallback to legacy
- Missing data → graceful empty results
- Invalid parameters → clear error messages

## Debugging

Enable debug logging to see mode selection and query execution:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from querying import TFTQuery
query = TFTQuery()  # Will log mode selection
stats = query.add_unit('TFT14_Aphelios').get_stats()  # Will log query execution
```

## Testing

Run the test suite to verify functionality:

```bash
python test_querying.py
```

This tests:
- Database connection
- Query building and execution
- Filter combinations
- Legacy fallback
- Cluster statistics

## Backward Compatibility

The migration maintains full backward compatibility:
- Existing code using `TFTQuery` continues to work
- Same return data structures
- Same statistical calculations
- Same error handling patterns

Only internal implementation changed from file-based to database-based operations.