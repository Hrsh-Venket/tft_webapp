# TFT Query System

Query TFT match data using `TFTQuery()`. All methods return `self` for chaining.

/
```

## Filter Methods

### Units
- `add_unit(unit_id: str, must_have: bool = True)` - Unit presence/absence
- `add_unit_count(unit_id: str, count: int)` - Exact unit count
- `add_unit_star_level(unit_id: str, min_star: int = 1, max_star: int = 3)` - Unit star level
- `add_unit_item_count(unit_id: str, min_count: int = 0, max_count: int = 3)` - Items on unit

### Items
- `add_item_on_unit(unit_id: str, item_id: str)` - Specific item on specific unit

### Traits
- `add_trait(trait_name: str, min_tier: int = 1, max_tier: int = 4)` - Trait tier

### Player Performance
- `add_player_level(min_level: int = 1, max_level: int = 10)` - Player level range
- `add_last_round(min_round: int = 1, max_round: int = 50)` - Elimination round
- `add_augment(augment_id: str)` - Specific augment

### Game/Patch
- `set_patch(patch_version: str)` - Filter by patch

### Clusters
- `set_sub_cluster(cluster_id: int)` - Sub-cluster filter
- `set_main_cluster(cluster_id: int)` - Main cluster filter

## Logical Operations

- `or_(self, *other_queries)` - Combine queries with OR logic
- `not_(self, other_query=None)` - NOT logic (negates existing conditions or other query)
- `xor(self, other_query)` - XOR logic (exactly one condition true)

```python
# Find Jinx OR Yasuo compositions
TFTQuery().add_unit('Jinx').or_(TFTQuery().add_unit('Yasuo'))

# High level but NOT 3-star units
TFTQuery().add_player_level(min_level=9).not_(TFTQuery().add_unit_star_level('Jinx', min_star=3))

# Either high level XOR 3-star carry (not both)
TFTQuery().add_player_level(min_level=9).xor(TFTQuery().add_unit_star_level('Jinx', min_star=3))

# Chaining applies to entire logical result: (A OR B) AND C
TFTQuery().add_unit('Jinx').or_(TFTQuery().add_unit('Yasuo')).add_trait('Star_Guardian', min_tier=2)
```

## Getting Results

### Statistics
```python
stats = query.get_stats()
# Returns: {'play_count': int, 'avg_placement': float, 'winrate': float, 'top4_rate': float}
```


## Examples

### Basic Unit Query
```python
TFTQuery().add_unit('Jinx').get_stats()
```

### Trait Requirements
```python
TFTQuery().add_trait('Star_Guardian', min_tier=3).get_stats()
```

### Complex Filtering
```python
TFTQuery().add_unit('Jinx').add_player_level(min_level=9).add_trait('Star_Guardian', min_tier=2).get_stats()
```

### Cluster Analysis
```python
TFTQuery().set_sub_cluster(15).get_stats()
```

### Item Analysis
```python
TFTQuery().add_item_on_unit('Jinx', 'Infinity_Edge').get_stats()
```

## Important Notes

- Multiple filters use AND logic by default
- Logical operations (OR, NOT, XOR) available for complex queries
- Unit/trait names: use display names from reference lists
- Check `play_count` in stats for sample size
- Database queries are faster than file-based queries