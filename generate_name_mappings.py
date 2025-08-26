import json
import csv
import re
import argparse

def clean_name(name):
    """Remove TFT prefixes from names while preserving the core name"""
    if not name:
        return name
    
    # Remove common TFT prefixes
    patterns = [
        r'^TFT\d*_Item_',      # TFT_Item_, TFT15_Item_, etc.
        r'^TFT\d*_',           # TFT_, TFT15_, TFT14_, etc.
        r'^tft\d*_',           # lowercase variants
    ]
    
    cleaned = name
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned

def extract_all_names_from_jsonl(file_path):
    """Extract all unique units, traits, and items from the JSONL file"""
    units = set()
    traits = set()
    items = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                    
                try:
                    match_data = json.loads(line)
                    participants = match_data.get('info', {}).get('participants', [])
                    
                    for participant in participants:
                        # Extract units
                        for unit in participant.get('units', []):
                            char_id = unit.get('character_id', '')
                            if char_id:
                                units.add(char_id)
                            
                            # Extract items from this unit
                            for item in unit.get('itemNames', []):
                                if item:
                                    items.add(item)
                        
                        # Extract traits
                        for trait in participant.get('traits', []):
                            trait_name = trait.get('name', '')
                            if trait_name:
                                traits.add(trait_name)
                                
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse line {line_num}: {e}")
                    continue
                    
    except FileNotFoundError:
        print(f"Error: File {file_path} not found")
        return set(), set(), set()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return set(), set(), set()
    
    return units, traits, items

def create_mapping_csv(names, output_file, category_name):
    """Create a CSV file with old_name and new_name columns"""
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['old_name', 'new_name'])
            
            for name in sorted(names):
                cleaned = clean_name(name)
                writer.writerow([name, cleaned])
                
        print(f"Created {output_file} with {len(names)} {category_name}")
        
    except Exception as e:
        print(f"Error creating {output_file}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Generate name mapping CSV files for TFT data')
    parser.add_argument('--input', default='matches.jsonl', 
                        help='Input JSONL file path (default: matches.jsonl)')
    parser.add_argument('--units-output', default='units_mapping.csv',
                        help='Output CSV file for units mapping (default: units_mapping.csv)')
    parser.add_argument('--traits-output', default='traits_mapping.csv',
                        help='Output CSV file for traits mapping (default: traits_mapping.csv)')
    parser.add_argument('--items-output', default='items_mapping.csv',
                        help='Output CSV file for items mapping (default: items_mapping.csv)')
    
    args = parser.parse_args()
    
    print(f"Extracting names from {args.input}...")
    units, traits, items = extract_all_names_from_jsonl(args.input)
    
    print(f"Found {len(units)} unique units, {len(traits)} unique traits, {len(items)} unique items")
    
    # Create the mapping CSV files
    create_mapping_csv(units, args.units_output, "units")
    create_mapping_csv(traits, args.traits_output, "traits") 
    create_mapping_csv(items, args.items_output, "items")
    
    print("\nMapping files created successfully!")
    print(f"- Units: {args.units_output}")
    print(f"- Traits: {args.traits_output}")
    print(f"- Items: {args.items_output}")
    print("\nYou can now edit the 'new_name' column in each CSV to customize the display names.")

if __name__ == "__main__":
    main()