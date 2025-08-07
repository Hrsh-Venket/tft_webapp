---
noteId: "1dd43fe073a611f095e8a9866d35445a"
tags: []

---

# TFT Querying Documentation

## Overview

The SimpleTFTQuery class provides comprehensive filtering and analysis capabilities for TFT match data. It supports complex queries with logical operations and returns both statistical summaries and detailed participant data.

## Basic Usage

```python
from simple_database import SimpleTFTQuery

# Create a query instance
query = SimpleTFTQuery()

# Add filters and get statistics
stats = query.add_unit('Aphelios').get_stats()
print(f"Aphelios play count: {stats['play_count']}")

# Or get detailed participant data
participants = query.add_unit('Jinx').execute()
```

## Available Methods

### Unit Filtering

#### `add_unit(unit_name)`
Filter for compositions containing a specific unit.

```python
# Find compositions with Aphelios
query.add_unit('Aphelios')

# Note: No need for TFT14_ prefix - data is pre-cleaned
query.add_unit('Jinx')  # ✅ Correct
query.add_unit('TFT14_Jinx')  # ❌ Not needed (but still works)
```

#### `add_unit_count(unit_name, count)`
Filter for compositions with an exact number of a specific unit.

```python
# Find compositions with exactly 2 copies of Jinx
query.add_unit_count('Jinx', 2)

# Find compositions with exactly 1 Aphelios
query.add_unit_count('Aphelios', 1)
```

#### `add_unit_star_level(unit_name, min_star=1, max_star=3)`
Filter units by their star level (upgrade tier).

```python
# Find 2-star or 3-star Aphelios
query.add_unit_star_level('Aphelios', min_star=2, max_star=3)

# Find only 3-star units
query.add_unit_star_level('Jinx', min_star=3, max_star=3)

# Find 1-star or 2-star units
query.add_unit_star_level('Aphelios', min_star=1, max_star=2)
```

#### `add_unit_item_count(unit_name, min_count=0, max_count=3)`
Filter units by the number of items they have equipped.

```python
# Find Aphelios with 2 or 3 items (typical carry setup)
query.add_unit_item_count('Aphelios', min_count=2, max_count=3)

# Find units with no items
query.add_unit_item_count('Malphite', min_count=0, max_count=0)

# Find units with exactly 1 item
query.add_unit_item_count('Vanguard', min_count=1, max_count=1)
```

#### `add_item_on_unit(unit_name, item_name)`
Filter for specific items on specific units.

```python
# Find Aphelios with Infinity Edge
query.add_item_on_unit('Aphelios', 'InfinityEdge')

# Find Jinx with Last Whisper
query.add_item_on_unit('Jinx', 'LastWhisper')

# Note: Item names are also cleaned - no TFT14_ prefix needed
query.add_item_on_unit('Aphelios', 'Bloodthirster')  # ✅ Correct
```

### Trait Filtering

#### `add_trait(trait_name, min_tier=1, max_tier=4)`
Filter by trait activation levels.

```python
# Find compositions with Vanguard trait active at tier 2 or higher
query.add_trait('Vanguard', min_tier=2)

# Find compositions with exactly tier 3 Rebel
query.add_trait('Rebel', min_tier=3, max_tier=3)

# Find any Sniper activation (tier 1+)
query.add_trait('Sniper', min_tier=1)

# Note: Trait names are cleaned - no TFT14_ prefix needed
query.add_trait('Demacia', min_tier=2)  # ✅ Correct
```

### Player Performance Filtering

#### `add_player_level(min_level=1, max_level=10)`
Filter by player level at game end.

```python
# Find high-level games (level 8+)
query.add_player_level(min_level=8)

# Find mid-game eliminations (level 6-7)
query.add_player_level(min_level=6, max_level=7)

# Find early eliminations (level 1-5)
query.add_player_level(min_level=1, max_level=5)
```

#### `add_last_round(min_round=1, max_round=50)`
Filter by the last round survived.

```python
# Find late-game compositions (survived past round 30)
query.add_last_round(min_round=30)

# Find mid-game eliminations (rounds 15-25)
query.add_last_round(min_round=15, max_round=25)

# Find early eliminations (before round 20)
query.add_last_round(min_round=1, max_round=19)
```

### Augment Filtering

#### `add_augment(augment_name)`
Filter by specific augments (Hextech Augments).

```python
# Find compositions with Combat Training
query.add_augment('CombatTraining')

# Find compositions with Treasure Trove
query.add_augment('TreasureTrove')

# Find compositions with specific augments
query.add_augment('BandOfThieves')
```

### Meta Filtering

#### `set_patch(patch_version)`
Filter by game patch version.

```python
# Find compositions from patch 14.22
query.set_patch('14.22')

# Find compositions from patch 14.21
query.set_patch('14.21')

# Note: Uses partial matching, so '14.22' matches 'Version 14.22.x'
```

### Cluster Filtering (Advanced)

#### `set_sub_cluster(cluster_id)` / `set_main_cluster(cluster_id)` / `set_cluster(cluster_id)`
Filter by composition clusters (if cluster data is available).

```python
# Filter to specific sub-cluster
query.set_sub_cluster(5)

# Filter to specific main cluster
query.set_main_cluster(2)

# Legacy method (defaults to sub-cluster)
query.set_cluster(3)

# Note: Requires cluster tables in database - currently shows placeholder behavior
```

### Custom Filtering

#### `add_custom_filter(sql_condition, params=None)`
Add custom SQL WHERE conditions for advanced filtering.

```python
# Find top 2 placements
query.add_custom_filter("placement <= %s", [2])

# Find high damage dealers
query.add_custom_filter("total_damage_to_players > %s", [15000])

# Complex custom condition
query.add_custom_filter("level >= %s AND players_eliminated >= %s", [8, 2])
```

## Query Execution

### `get_stats()`
Returns statistical summary of filtered compositions.

```python
stats = query.add_unit('Aphelios').get_stats()

# Returns dictionary with:
# {
#     'play_count': 24,           # Number of matching compositions
#     'avg_placement': 4.17,      # Average final placement
#     'winrate': 12.5,           # Percentage of 1st place finishes
#     'top4_rate': 50.0          # Percentage of top 4 finishes
# }
```

### `execute()`
Returns detailed participant data for filtered compositions.

```python
participants = query.add_unit('Jinx').execute()

# Returns list of participant dictionaries with:
# [
#     {
#         'match_id': 'NA1_1234567890',
#         'puuid': 'player-uuid',
#         'placement': 1,
#         'level': 9,
#         'last_round': 35,
#         'units': [...],          # Unit details
#         'traits': [...],         # Trait details  
#         'augments': [...],       # Augment list
#         # ... other participant data
#     },
#     # ... more participants
# ]
```

## Complex Queries with Method Chaining

All filter methods can be chained together. Multiple filters are combined with **AND** logic by default.

```python
# Complex carry composition analysis
stats = (SimpleTFTQuery()
    .add_unit('Aphelios')                          # Must have Aphelios
    .add_unit_star_level('Aphelios', min_star=2)   # 2-star or better
    .add_unit_item_count('Aphelios', min_count=2)  # With 2+ items
    .add_trait('Sniper', min_tier=2)               # Sniper 2+ active
    .add_player_level(min_level=8)                 # High level games
    .add_last_round(min_round=25)                  # Survived late game
    .get_stats())

# Meta analysis
patch_stats = (SimpleTFTQuery()
    .set_patch('14.22')                            # Current patch
    .add_player_level(min_level=8)                 # High level only
    .add_last_round(min_round=30)                  # Late game
    .get_stats())

# Item optimization
item_analysis = (SimpleTFTQuery()
    .add_unit('Jinx')                              # Jinx compositions
    .add_item_on_unit('Jinx', 'InfinityEdge')     # With IE
    .add_unit_star_level('Jinx', min_star=2)       # 2-star+
    .execute())  # Get detailed data for analysis
```

## Logical Operations (Future Enhancement)

While the current implementation uses AND logic between filters, the original TFTQuery supports complex logical operations. Here's how they would work:

### AND Operations (Default)
Multiple filters are automatically combined with AND logic.

```python
# This finds compositions that have BOTH Aphelios AND are level 8+
query.add_unit('Aphelios').add_player_level(min_level=8)
# Equivalent to: "has Aphelios" AND "level >= 8"
```

### OR Operations (Planned)
Find compositions matching ANY of the specified conditions.

```python
# This would find compositions with EITHER Aphelios OR Jinx
query.add_or_group(
    lambda q: q.add_unit('Aphelios'),
    lambda q: q.add_unit('Jinx')
)
# Equivalent to: "has Aphelios" OR "has Jinx"
```

### XOR Operations (Planned) 
Find compositions matching EXACTLY ONE of the conditions.

```python
# This would find compositions with EITHER Aphelios OR Jinx, but NOT both
query.add_xor_group(
    lambda q: q.add_unit('Aphelios'),
    lambda q: q.add_unit('Jinx')
)
# Equivalent to: ("has Aphelios" OR "has Jinx") AND NOT ("has Aphelios" AND "has Jinx")
```

### NOT Operations (Planned)
Find compositions that do NOT match the condition.

```python
# This would find compositions WITHOUT Vanguard trait
query.add_not_filter(lambda q: q.add_trait('Vanguard'))
# Equivalent to: NOT "has Vanguard trait"
```

### Complex Logical Combinations (Planned)
```python
# Find compositions that:
# - Have Aphelios OR Jinx (but not both)
# - AND have level 8+  
# - AND do NOT have Vanguard trait
query = (SimpleTFTQuery()
    .add_xor_group(
        lambda q: q.add_unit('Aphelios'),
        lambda q: q.add_unit('Jinx')
    )
    .add_player_level(min_level=8)
    .add_not_filter(lambda q: q.add_trait('Vanguard')))
```

## Performance Tips

1. **Use specific filters first**: More specific filters (like exact unit names) are processed more efficiently than broad filters.

2. **Limit result sets**: The `execute()` method automatically limits to 1000 results for performance.

3. **Combine related filters**: Chain multiple related filters rather than running separate queries.

4. **Use custom filters for complex conditions**: For very specific SQL needs, `add_custom_filter()` can be more efficient than multiple method calls.

## Example Use Cases

### Carry Analysis
```python
# Analyze Aphelios carry performance
aphelios_carry = (SimpleTFTQuery()
    .add_unit('Aphelios')
    .add_unit_item_count('Aphelios', min_count=2)
    .add_unit_star_level('Aphelios', min_star=2)
    .get_stats())
```

### Meta Snapshot
```python
# Current patch high-level meta
current_meta = (SimpleTFTQuery()
    .set_patch('14.22')
    .add_player_level(min_level=8)
    .add_last_round(min_round=25)
    .get_stats())
```

### Item Optimization
```python
# Compare different items on Jinx
ie_jinx = SimpleTFTQuery().add_unit('Jinx').add_item_on_unit('Jinx', 'InfinityEdge').get_stats()
bt_jinx = SimpleTFTQuery().add_unit('Jinx').add_item_on_unit('Jinx', 'Bloodthirster').get_stats()
```

### Trait Scaling Analysis
```python
# Compare different Vanguard tier performance
vanguard_2 = SimpleTFTQuery().add_trait('Vanguard', min_tier=2, max_tier=2).get_stats()
vanguard_4 = SimpleTFTQuery().add_trait('Vanguard', min_tier=4, max_tier=4).get_stats()
```

### Augment Impact Study
```python
# Analyze augment impact on performance
with_combat_training = SimpleTFTQuery().add_augment('CombatTraining').add_player_level(min_level=7).get_stats()
without_combat_training = SimpleTFTQuery().add_player_level(min_level=7).get_stats()
```

## Error Handling

The system includes comprehensive error handling:

- **Invalid parameters**: Automatically cleaned and validated
- **Database connection issues**: Graceful fallback with error messages
- **Empty result sets**: Returns zero stats instead of crashing
- **SQL errors**: Logged with detailed error messages

```python
# This will return safe zero stats if something goes wrong
stats = SimpleTFTQuery().add_unit('InvalidUnit').get_stats()
# Returns: {'play_count': 0, 'avg_placement': 0, 'winrate': 0, 'top4_rate': 0}
```

## Data Format Notes

- **Unit names**: Pre-cleaned, no TFT set prefixes needed
- **Item names**: Pre-cleaned, use standard item names
- **Trait names**: Pre-cleaned, use standard trait names
- **Augment names**: Use internal augment IDs (e.g., 'CombatTraining')
- **Patch versions**: Use format like '14.22' (automatically expands to full version matching)

This comprehensive querying system provides powerful analysis capabilities for TFT match data with an intuitive, chainable API.