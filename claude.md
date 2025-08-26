---
noteId: "1d095620824911f09c8005f6366662c3"
tags: []

---

# TFT Webapp Implementation Context

## Overview
Streamlit web app for analyzing TFT (Teamfight Tactics) match data with PostgreSQL database backend. Features cluster analysis, statistical querying, and data upload functionality.

## Core Architecture

### Main Files
- `streamlit_app.py` - Main Streamlit application with 4 tabs
- `simple_database.py` - Simplified PostgreSQL connection for Streamlit Cloud
- `querying.py` - Complex query system with legacy and database modes
- `database/` - Database connection, config, and operations
- `app.py` - HuggingFace Spaces entry point

### Database Schema
- `matches` - Match metadata (id, datetime, version, etc)
- `participants` - Player data per match (placement, level, units, traits, augments)
- Tables use JSONB for flexible data storage (units, traits, augments)

### Data Flow
1. Raw JSONL match data upload via Streamlit interface
2. Batch processing into PostgreSQL with optimizations
3. Query system supports both SQL (fast) and file-based (fallback)
4. Results displayed as statistics or raw participant data

## Key Components

### SimpleTFTQuery Class
- Main query interface with method chaining
- Filters: units, traits, levels, augments, items, rounds
- Logical operations: OR, NOT, XOR with complex SQL generation
- Auto-fallback from database to file-based queries

### Streamlit App Tabs
1. **Overview** - Database stats, connection status
2. **Clusters** - Hierarchical cluster analysis display
3. **Query** - Interactive TFT query interface with documentation
4. **Upload** - Optimized batch data import

### Database Connection
- Supabase PostgreSQL with pooler URL conversion
- IPv4-compatible URLs for Streamlit Cloud
- Automatic retry with fallback connections
- Connection caching and optimization

## Query System Features

### Filter Types
- Unit presence/absence/count/star level/items
- Trait activation tiers
- Player levels and elimination rounds
- Specific items on specific units
- Augments and patch versions
- Custom SQL conditions

### Logical Operations
```python
# OR: Unit A OR Unit B
TFTQuery().add_unit('Jinx').or_(TFTQuery().add_unit('Ahri'))

# NOT: Trait X but NOT Unit Y  
TFTQuery().add_trait('Star_Guardian').not_(TFTQuery().add_unit('Jinx'))

# XOR: Exactly one condition true
TFTQuery().add_unit('Jinx').xor(TFTQuery().add_unit('Ahri'))
```

## Deployment Configs
- **Streamlit Cloud**: Uses `streamlit_app.py`, secrets for DATABASE_URL
- **HuggingFace**: Uses `app.py` wrapper, requirements.txt
- **Heroku**: Procfile, app.json, production configs

## Data Processing
- JSONL batch processing with configurable batch sizes
- Raw data storage optional (saves 80% space when disabled)
- Conflict resolution with ON CONFLICT DO NOTHING
- Progress tracking and error handling

## Performance Optimizations
- PostgreSQL JSONB indexing for fast queries
- Batch inserts with synchronous_commit=off
- Query parameter caching and reuse
- Lazy loading of cluster data

## Known Issues
- Cluster filtering requires additional tables (placeholder implementation)
- Legacy file-based mode has limited performance with large datasets
- Complex XOR queries may hit parameter limits

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- Streamlit secrets: `database.DATABASE_URL`

## Testing
- `test_app_locally.py` - Local Streamlit testing
- `test_connection.py` - Database connectivity
- `test_querying.py` - Query system validation