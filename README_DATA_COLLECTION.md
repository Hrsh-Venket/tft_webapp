---
noteId: "a1b0e8c072b811f095e8a9866d35445a"
tags: []

---

# TFT Data Collection System - Database Integration

This document describes the updated TFT data collection system that now supports PostgreSQL database storage alongside the original JSONL file format.

## Overview

The data collection system has been enhanced to provide:

- **PostgreSQL Integration**: Store match data directly in a structured database
- **Batch Processing**: Efficient batch operations with transaction management  
- **Error Handling**: Robust error handling and retry logic
- **Progress Tracking**: Enhanced progress tracking with database statistics
- **Backward Compatibility**: Option to still output JSONL files
- **Data Validation**: Optional validation before database insertion
- **Duplicate Detection**: Automatic duplicate match detection and handling

## System Architecture

### Core Components

1. **`data_collection.py`** - Main collection script with database integration
2. **`database/data_import.py`** - Database import utilities and batch operations
3. **`database/migrations/004_insert_match_function.sql`** - Database functions for match insertion
4. **`test_database_integration.py`** - Test suite for database integration

### Database Schema

The system uses a normalized PostgreSQL schema with these main tables:

- **`matches`** - Match metadata (partitioned by date)
- **`participants`** - Player data for each match
- **`participant_units`** - Normalized unit composition data
- **`participant_traits`** - Normalized trait composition data
- **`participant_clusters`** - Clustering results (for analysis)

## Configuration

### Database Settings

Edit the configuration variables at the top of `data_collection.py`:

```python
# Database settings
USE_DATABASE = True            # Use PostgreSQL instead of JSONL
ENABLE_JSONL_BACKUP = False    # Also save to JSONL file as backup
DB_BATCH_SIZE = 25             # Database batch size (smaller for stability)
ENABLE_DB_VALIDATION = True    # Validate data before database insertion
```

### Environment Setup

1. **Database Connection**: Configure your database connection in `.env`:
   ```env
   DB_HOST=localhost
   DB_PORT=6432
   DB_NAME=tft_matches
   DB_USER=tft_user
   DB_PASSWORD=tft_password
   ```

2. **Database Migration**: Run the migration scripts:
   ```bash
   # Run all migrations (if not already done)
   python setup_database.py
   ```

3. **Test Integration**: Verify everything works:
   ```bash
   python test_database_integration.py
   ```

## Usage

### Basic Usage

Run with database integration (default):
```bash
python data_collection.py
```

### Configuration Options

The system automatically detects database availability and falls back to JSONL mode if needed.

**Key Features:**

- **Automatic Fallback**: If database is unavailable, automatically uses JSONL mode
- **Duplicate Handling**: Automatically skips matches that already exist in database
- **Progress Tracking**: Shows database statistics (inserted, duplicates, errors)
- **Batch Operations**: Processes matches in configurable batches for performance

### Command Line Output

With database integration enabled, you'll see output like:

```
TFT Data Collection System
==================================================
Started at: 2024-08-06 14:30:15

Testing database connection...
  ✓ Database connected: PostgreSQL 14.2
  ✓ Response time: 25ms
  ✓ Current database: 1,247 matches, 9,976 participants

Current Configuration:
  API Key: ****f7ee
  Tier: PLATINUM
  Regions: sg2 (players), sea (matches)
  Storage: PostgreSQL
  Database batch size: 25
  Validation: Enabled
  JSONL backup: Disabled
  API batch size: 50, Workers: 5
  Mode: Period-based collection from 2024-08-01 00:00:00

=== COLLECTING PLAYER LIST ===
Total players: 1,524
Remaining players: 1,524

=== COLLECTING PERIOD MATCHES ===

Player 1/1524: ExamplePlayer
   Found 15 matches in period timeframe
   Already downloaded globally: 3
   New matches to collect: 12
     Stored 12 matches: 10 inserted, 2 duplicates, 0 errors (12 session new)

   Progress: 1/1524 players (0.1%) | DB: 10 inserted, 2 duplicates, 0 errors | 60.0 players/min | ETA: 25min
```

## Database Operations

### Match Insertion Functions

The system provides several database functions:

1. **`insert_match_data(match_json JSONB)`** - Insert single match
2. **`batch_insert_matches(matches_json JSONB)`** - Batch insert multiple matches
3. **`match_exists(game_id TEXT)`** - Check if match exists
4. **`get_match_import_stats()`** - Get import statistics
5. **`validate_match_integrity(game_id TEXT)`** - Validate data integrity

### Direct SQL Usage

You can also use these functions directly in SQL:

```sql
-- Insert a match from JSON
SELECT * FROM insert_match_data('{"metadata": {...}, "info": {...}}');

-- Check if match exists
SELECT match_exists('NA1_4567890123');

-- Get import statistics
SELECT * FROM get_match_import_stats();

-- Validate data integrity
SELECT * FROM validate_match_integrity();
```

## Performance Considerations

### Batch Sizes

- **API Batch Size** (`BATCH_SIZE`): Number of matches to fetch concurrently (default: 50)
- **Database Batch Size** (`DB_BATCH_SIZE`): Number of matches to insert per transaction (default: 25)

### Optimization Tips

1. **Use smaller database batch sizes** (20-30) for stability
2. **Enable connection pooling** in database configuration
3. **Monitor database performance** during large imports
4. **Use JSONL backup** for very large datasets as safety net

### Expected Performance

- **Database insertion**: ~5-15 matches/second (depends on hardware)
- **API fetching**: Limited by Riot API rate limits (20 requests/second)
- **Memory usage**: ~50-100MB for typical operations

## Error Handling

### Automatic Recovery

The system includes comprehensive error handling:

- **Database connection failures**: Automatic fallback to JSONL mode
- **Duplicate matches**: Automatically detected and logged
- **API failures**: Retry logic with exponential backoff
- **Data validation errors**: Skip invalid matches with detailed logging

### Error Types

1. **Connection Errors**: Database unavailable → fallback to JSONL
2. **Validation Errors**: Invalid match data → skip with warning
3. **Duplicate Errors**: Match already exists → log and continue
4. **API Errors**: Riot API issues → retry with backoff

## Monitoring and Statistics

### Real-time Progress

During collection, monitor:
- Matches inserted vs duplicates vs errors
- Processing rate (matches/minute)
- Database response time
- API rate limit usage

### Database Statistics

Get comprehensive statistics:

```python
from database.data_import import get_database_stats
stats = get_database_stats()
print(f"Total matches: {stats['matches']}")
print(f"Total participants: {stats['participants']}")
```

### Health Checks

Test system health:

```python
from database.connection import health_check
status = health_check()
print(f"Database status: {status['overall_status']}")
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify connection details in `.env`
   - Test with: `python test_database_integration.py`

2. **Import Errors**
   - Run database migrations: `python setup_database.py`
   - Check database permissions
   - Verify table structure exists

3. **Performance Issues**
   - Reduce `DB_BATCH_SIZE` (try 10-20)
   - Enable connection pooling
   - Monitor database logs

4. **Data Validation Errors**
   - Check Riot API response format
   - Verify match data structure
   - Disable validation temporarily: `ENABLE_DB_VALIDATION = False`

### Getting Help

1. **Test Integration**: Run `python test_database_integration.py`
2. **Check Logs**: Monitor console output for detailed error messages
3. **Database Logs**: Check PostgreSQL logs for database-specific issues
4. **Fallback Mode**: System automatically falls back to JSONL if database fails

## Migration from JSONL

### Converting Existing Data

To migrate existing JSONL files to database:

```python
from database.data_import import MatchDataImporter
import json

importer = MatchDataImporter()

# Load and insert existing matches
with open('matches.jsonl', 'r') as f:
    matches = []
    for line in f:
        if line.strip():
            matches.append(json.loads(line.strip()))
    
    # Batch insert
    stats = importer.batch_insert_matches(matches, batch_size=25)
    print(f"Migrated {stats.matches_inserted} matches")
```

### Hybrid Mode

You can run in hybrid mode by setting:

```python
USE_DATABASE = True
ENABLE_JSONL_BACKUP = True
```

This stores data in both database and JSONL files.

## Advanced Usage

### Custom Batch Processing

For custom batch processing needs:

```python
from database.data_import import MatchDataImporter

importer = MatchDataImporter()

# Process matches with custom logic
for batch in your_match_batches:
    stats = importer.batch_insert_matches(batch, batch_size=20)
    print(f"Batch complete: {stats.matches_inserted} inserted, {stats.matches_duplicate} duplicates")
```

### Data Validation

Implement custom validation:

```python
from database.data_import import MatchDataImporter

importer = MatchDataImporter()

# Validate before insertion
is_valid, errors = importer.validate_match_data(match_json)
if is_valid:
    success, message = importer.insert_match_data(match_json)
else:
    print(f"Validation failed: {errors}")
```

---

## Summary

The enhanced data collection system provides:

- ✅ **Robust database integration** with PostgreSQL
- ✅ **Automatic fallback** to JSONL mode
- ✅ **Batch processing** with transaction management
- ✅ **Comprehensive error handling** and recovery
- ✅ **Real-time progress tracking** and statistics
- ✅ **Data validation** and integrity checks
- ✅ **Backward compatibility** with existing workflows

The system is production-ready and can handle thousands of matches per hour with proper configuration and hardware.