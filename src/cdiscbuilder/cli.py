import os
import argparse
from .odm import parse_odm_to_long_df
from .sdtm import create_sdtm_datasets

def main():
    parser = argparse.ArgumentParser(description="Convert ODM XML to SDTM Datasets")
    # Determine default config path inside package
    current_dir = os.path.dirname(__file__)
    default_config_path = os.path.join(current_dir, "specs")
    
    parser.add_argument("--xml", required=True, help="Path to input ODM XML file")
    parser.add_argument("--csv", default="odm_long.csv", help="Path to intermediate long CSV file")
    parser.add_argument("--configs", default=default_config_path, help="Path to SDTM configuration directory")
    parser.add_argument("--output", default="sdtm_output", help="Path to output SDTM directory")
    
    args = parser.parse_args()

    # Step 1: ODM XML -> Long CSV
    print(f"--- Step 1: Parsing ODM XML from {args.xml} ---")
    try:
        df, metadata = parse_odm_to_long_df(args.xml)
        print(f"Parsed {len(df)} rows.")
        df.to_csv(args.csv, index=False)
        print(f"Saved intermediate data to {args.csv}")
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return

    # Step 2: Long CSV -> SDTM Datasets
    print(f"\n--- Step 2: Generating SDTM Datasets using configs from {args.configs} ---")
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        
    try:
        create_sdtm_datasets(args.configs, args.csv, args.output, metadata)
        print(f"\nSuccess! SDTM datasets created in {args.output}")
    except Exception as e:
        print(f"Error creating SDTM datasets: {e}")

if __name__ == "__main__":
    main()
