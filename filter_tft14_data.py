"""
TFT Data Filtering Script

This script removes all matches that contain any TFT14_ or TFTEvent5YR_ prefixed items, traits, or units.
It also cleans the mapping CSV files to remove these entries.
"""

import json
import csv
import os
import argparse
from collections import defaultdict

def has_excluded_content(match_data):
    """
    Check if a match contains any TFT14_ or TFTEvent5YR_ prefixed content.
    
    :param match_data: Match data dictionary
    :return: True if match contains excluded content, False otherwise
    """
    participants = match_data.get('info', {}).get('participants', [])
    
    excluded_prefixes = ['TFT14_', 'TFTEvent5YR_']
    
    for participant in participants:
        # Check traits
        for trait in participant.get('traits', []):
            trait_name = trait.get('name', '')
            for prefix in excluded_prefixes:
                if trait_name.startswith(prefix):
                    return True
        
        # Check units and their items
        for unit in participant.get('units', []):
            # Check unit character_id
            char_id = unit.get('character_id', '')
            for prefix in excluded_prefixes:
                if char_id.startswith(prefix):
                    return True
            
            # Check unit items
            for item in unit.get('itemNames', []):
                for prefix in excluded_prefixes:
                    if item.startswith(prefix):
                        return True
    
    return False

def filter_matches(input_file, output_file):
    """
    Filter matches to remove any containing TFT14_ or TFTEvent5YR_ content.
    
    :param input_file: Input JSONL file path
    :param output_file: Output JSONL file path
    :return: Statistics dictionary
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found")
        return None
    
    total_matches = 0
    filtered_matches = 0
    kept_matches = 0
    
    print(f"Filtering matches from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            if not line.strip():
                continue
                
            try:
                match_data = json.loads(line.strip())
                total_matches += 1
                
                if has_excluded_content(match_data):
                    filtered_matches += 1
                    if total_matches % 1000 == 0:
                        print(f"   Processed {total_matches} matches, filtered {filtered_matches}")
                else:
                    # Keep this match
                    json.dump(match_data, outfile)
                    outfile.write('\n')
                    kept_matches += 1
                    
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line {line_num}: {e}")
                continue
    
    stats = {
        'total_matches': total_matches,
        'filtered_matches': filtered_matches,
        'kept_matches': kept_matches,
        'filter_percentage': (filtered_matches / total_matches * 100) if total_matches > 0 else 0
    }
    
    return stats

def clean_mapping_csv(csv_file):
    """
    Remove all TFT14_ and TFTEvent5YR_ entries from a mapping CSV file.
    
    :param csv_file: Path to CSV file to clean
    :return: Statistics about cleaned entries
    """
    if not os.path.exists(csv_file):
        print(f"Warning: Mapping file {csv_file} not found, skipping")
        return {'total_entries': 0, 'removed_entries': 0, 'kept_entries': 0}
    
    print(f"Cleaning mapping file: {csv_file}")
    
    # Read all entries
    all_entries = []
    total_entries = 0
    removed_entries = 0
    
    with open(csv_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        headers = reader.fieldnames
        
        for row in reader:
            total_entries += 1
            old_name = row.get('old_name', '')
            
            # Check if this entry should be removed
            if old_name.startswith('TFT14_') or old_name.startswith('TFTEvent5YR_'):
                removed_entries += 1
            else:
                all_entries.append(row)
    
    kept_entries = len(all_entries)
    
    # Write back the cleaned entries
    with open(csv_file, 'w', newline='', encoding='utf-8') as outfile:
        if headers and all_entries:
            writer = csv.DictWriter(outfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(all_entries)
    
    stats = {
        'total_entries': total_entries,
        'removed_entries': removed_entries,
        'kept_entries': kept_entries,
        'removal_percentage': (removed_entries / total_entries * 100) if total_entries > 0 else 0
    }
    
    return stats

def analyze_excluded_content(input_file):
    """
    Analyze what TFT14_ and TFTEvent5YR_ content is present in the data.
    
    :param input_file: Input JSONL file path
    :return: Analysis dictionary
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found")
        return None
    
    print(f"Analyzing TFT14_ and TFTEvent5YR_ content in {input_file}...")
    
    excluded_units = set()
    excluded_traits = set()
    excluded_items = set()
    matches_with_excluded = 0
    total_matches = 0
    excluded_prefixes = ['TFT14_', 'TFTEvent5YR_']
    
    with open(input_file, 'r', encoding='utf-8') as infile:
        for line_num, line in enumerate(infile, 1):
            if not line.strip():
                continue
                
            try:
                match_data = json.loads(line.strip())
                total_matches += 1
                match_has_excluded = False
                
                participants = match_data.get('info', {}).get('participants', [])
                
                for participant in participants:
                    # Check traits
                    for trait in participant.get('traits', []):
                        trait_name = trait.get('name', '')
                        for prefix in excluded_prefixes:
                            if trait_name.startswith(prefix):
                                excluded_traits.add(trait_name)
                                match_has_excluded = True
                    
                    # Check units and their items
                    for unit in participant.get('units', []):
                        # Check unit character_id
                        char_id = unit.get('character_id', '')
                        for prefix in excluded_prefixes:
                            if char_id.startswith(prefix):
                                excluded_units.add(char_id)
                                match_has_excluded = True
                        
                        # Check unit items
                        for item in unit.get('itemNames', []):
                            for prefix in excluded_prefixes:
                                if item.startswith(prefix):
                                    excluded_items.add(item)
                                    match_has_excluded = True
                
                if match_has_excluded:
                    matches_with_excluded += 1
                    
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line {line_num}: {e}")
                continue
    
    analysis = {
        'total_matches': total_matches,
        'matches_with_excluded': matches_with_excluded,
        'excluded_percentage': (matches_with_excluded / total_matches * 100) if total_matches > 0 else 0,
        'excluded_units': sorted(list(excluded_units)),
        'excluded_traits': sorted(list(excluded_traits)),
        'excluded_items': sorted(list(excluded_items)),
        'unique_excluded_units': len(excluded_units),
        'unique_excluded_traits': len(excluded_traits),
        'unique_excluded_items': len(excluded_items)
    }
    
    return analysis

def main():
    parser = argparse.ArgumentParser(
        description="Filter TFT data to remove TFT14_ content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python filter_tft14_data.py --input matches.jsonl --output matches_filtered.jsonl
  python filter_tft14_data.py --analyze-only --input matches.jsonl
  python filter_tft14_data.py --clean-mappings-only
        """
    )
    
    parser.add_argument('--input', type=str, default='matches.jsonl',
                       help='Input JSONL file (default: matches.jsonl)')
    parser.add_argument('--output', type=str, default='matches_filtered.jsonl',
                       help='Output JSONL file (default: matches_filtered.jsonl)')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze TFT14_/TFTEvent5YR_ content, do not filter')
    parser.add_argument('--clean-mappings-only', action='store_true',
                       help='Only clean mapping CSV files, do not filter matches')
    parser.add_argument('--skip-mappings', action='store_true',
                       help='Skip cleaning mapping CSV files')
    
    args = parser.parse_args()
    
    print("TFT Data Content Filter (TFT14_ and TFTEvent5YR_)")
    print("=" * 55)
    
    # Analyze content if requested
    if args.analyze_only:
        analysis = analyze_excluded_content(args.input)
        if analysis:
            print(f"\nExcluded Content Analysis (TFT14_ and TFTEvent5YR_):")
            print(f"  Total matches: {analysis['total_matches']}")
            print(f"  Matches with excluded content: {analysis['matches_with_excluded']} ({analysis['excluded_percentage']:.1f}%)")
            print(f"  Unique excluded units: {analysis['unique_excluded_units']}")
            print(f"  Unique excluded traits: {analysis['unique_excluded_traits']}")
            print(f"  Unique excluded items: {analysis['unique_excluded_items']}")
            
            if analysis['excluded_units']:
                print(f"\nSample excluded units: {', '.join(analysis['excluded_units'][:5])}")
            if analysis['excluded_traits']:
                print(f"Sample excluded traits: {', '.join(analysis['excluded_traits'][:5])}")
            if analysis['excluded_items']:
                print(f"Sample excluded items: {', '.join(analysis['excluded_items'][:5])}")
        return
    
    # Clean mapping files if not skipped
    if not args.skip_mappings or args.clean_mappings_only:
        print("\nCleaning mapping CSV files...")
        mapping_files = ['units_mapping.csv', 'traits_mapping.csv', 'items_mapping.csv']
        
        total_mapping_stats = {'total_entries': 0, 'removed_entries': 0, 'kept_entries': 0}
        
        for mapping_file in mapping_files:
            stats = clean_mapping_csv(mapping_file)
            total_mapping_stats['total_entries'] += stats['total_entries']
            total_mapping_stats['removed_entries'] += stats['removed_entries']
            total_mapping_stats['kept_entries'] += stats['kept_entries']
            
            if stats['total_entries'] > 0:
                print(f"  {mapping_file}: {stats['removed_entries']}/{stats['total_entries']} entries removed ({stats['removal_percentage']:.1f}%)")
        
        if total_mapping_stats['total_entries'] > 0:
            print(f"\nTotal mapping cleanup:")
            print(f"  Removed: {total_mapping_stats['removed_entries']}/{total_mapping_stats['total_entries']} entries")
            print(f"  Percentage: {total_mapping_stats['removed_entries']/total_mapping_stats['total_entries']*100:.1f}%")
    
    # Filter matches if not mappings-only
    if not args.clean_mappings_only:
        print(f"\nFiltering matches...")
        stats = filter_matches(args.input, args.output)
        
        if stats:
            print(f"\nFiltering Results:")
            print(f"  Input file: {args.input}")
            print(f"  Output file: {args.output}")
            print(f"  Total matches processed: {stats['total_matches']}")
            print(f"  Matches filtered out: {stats['filtered_matches']} ({stats['filter_percentage']:.1f}%)")
            print(f"  Matches kept: {stats['kept_matches']}")
            
            # Update global match tracker if it exists
            tracker_file = 'global_matches_downloaded.json'
            if os.path.exists(tracker_file):
                print(f"\nNote: You may want to regenerate {tracker_file} since matches were filtered")
    
    print(f"\n{'='*60}")
    print("TFT14_ CONTENT FILTERING COMPLETE")
    print(f"{'='*60}")
    
    if not args.clean_mappings_only:
        print(f"Filtered data saved to: {args.output}")
    print("Mapping files cleaned of TFT14_ entries")
    print("\nNext steps:")
    print("  - Run clustering on filtered data: python clustering.py --input matches_filtered.jsonl")
    print("  - Update any scripts to use the filtered data file")

if __name__ == "__main__":
    main()