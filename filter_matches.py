#!/usr/bin/env python3
"""
Filter and transform match data by applying name mappings for units, items, and traits.
Converts raw match data with internal game IDs to human-readable names.
"""

import json
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Any

def load_mapping_csv(filepath: str) -> Dict[str, str]:
    """Load a CSV mapping file and return as a dictionary."""
    mapping = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_name = row['old_name'].strip()
                new_name = row['new_name'].strip()
                if old_name and new_name:  # Skip empty rows
                    mapping[old_name] = new_name
    except FileNotFoundError:
        print(f"Warning: Mapping file {filepath} not found. Skipping.")
    except Exception as e:
        print(f"Error loading mapping file {filepath}: {e}")
    return mapping

def apply_mappings_to_match(match_data: Dict[str, Any], 
                          units_mapping: Dict[str, str],
                          items_mapping: Dict[str, str], 
                          traits_mapping: Dict[str, str]) -> Dict[str, Any]:
    """Apply name mappings to a single match."""
    
    # Deep copy to avoid modifying original data
    filtered_match = json.loads(json.dumps(match_data))
    
    # Process each participant
    if 'info' in filtered_match and 'participants' in filtered_match['info']:
        for participant in filtered_match['info']['participants']:
            
            # Map unit character_ids
            if 'units' in participant:
                for unit in participant['units']:
                    if 'character_id' in unit:
                        old_id = unit['character_id']
                        if old_id in units_mapping:
                            unit['character_id'] = units_mapping[old_id]
                    
                    # Map item names
                    if 'itemNames' in unit:
                        mapped_items = []
                        for item in unit['itemNames']:
                            mapped_items.append(items_mapping.get(item, item))
                        unit['itemNames'] = mapped_items
            
            # Map trait names
            if 'traits' in participant:
                for trait in participant['traits']:
                    if 'name' in trait:
                        old_name = trait['name']
                        if old_name in traits_mapping:
                            trait['name'] = traits_mapping[old_name]
    
    return filtered_match

def filter_matches(input_file: str, output_file: str, 
                  units_mapping_file: str, items_mapping_file: str, traits_mapping_file: str):
    """Filter all matches in the input file and write to output file."""
    
    # Load mappings
    print("Loading mapping files...")
    units_mapping = load_mapping_csv(units_mapping_file)
    items_mapping = load_mapping_csv(items_mapping_file)
    traits_mapping = load_mapping_csv(traits_mapping_file)
    
    print(f"Loaded {len(units_mapping)} unit mappings")
    print(f"Loaded {len(items_mapping)} item mappings") 
    print(f"Loaded {len(traits_mapping)} trait mappings")
    
    # Process matches
    matches_processed = 0
    
    try:
        with open(input_file, 'r', encoding='utf-8') as infile, \
             open(output_file, 'w', encoding='utf-8') as outfile:
            
            for line in infile:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    match_data = json.loads(line)
                    filtered_match = apply_mappings_to_match(
                        match_data, units_mapping, items_mapping, traits_mapping
                    )
                    
                    # Write filtered match to output file
                    outfile.write(json.dumps(filtered_match, separators=(',', ':')) + '\n')
                    matches_processed += 1
                    
                    if matches_processed % 100 == 0:
                        print(f"Processed {matches_processed} matches...")
                        
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON on line {matches_processed + 1}: {e}")
                    continue
                except Exception as e:
                    print(f"Error processing match {matches_processed + 1}: {e}")
                    continue
    
    except FileNotFoundError:
        print(f"Error: Input file {input_file} not found.")
        return
    except Exception as e:
        print(f"Error: {e}")
        return
    
    print(f"Successfully processed {matches_processed} matches")
    print(f"Filtered data saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Filter TFT match data with name mappings")
    parser.add_argument('--input', default='matches.jsonl', 
                       help='Input JSONL file with match data (default: matches.jsonl)')
    parser.add_argument('--output', default='matches_filtered.jsonl',
                       help='Output JSONL file for filtered data (default: matches_filtered.jsonl)')
    parser.add_argument('--units-mapping', default='units_mapping.csv',
                       help='CSV file with unit name mappings (default: units_mapping.csv)')
    parser.add_argument('--items-mapping', default='items_mapping.csv', 
                       help='CSV file with item name mappings (default: items_mapping.csv)')
    parser.add_argument('--traits-mapping', default='traits_mapping.csv',
                       help='CSV file with trait name mappings (default: traits_mapping.csv)')
    
    args = parser.parse_args()
    
    # Verify input file exists
    if not Path(args.input).exists():
        print(f"Error: Input file {args.input} does not exist.")
        return 1
    
    filter_matches(
        args.input, 
        args.output,
        args.units_mapping,
        args.items_mapping, 
        args.traits_mapping
    )
    
    return 0

if __name__ == '__main__':
    exit(main())