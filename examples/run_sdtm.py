import argparse
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from cdiscbuilder.sdtm.odm_parser import parse_odm_to_long_df, extract_metadata_summary
from cdiscbuilder.sdtm.sdtm import create_sdtm_datasets

def main():
    base_dir = Path(__file__).parent
    
    parser = argparse.ArgumentParser(description="Run SDTM mapping pipeline.")
    parser.add_argument("--xml", default=str(base_dir / "data" / "openclinica_comprehensive_sample.xml"), help="Path to input ODM XML file")
    parser.add_argument("--configs", default=str(base_dir / "sdtm" / "specs" / "sample"), help="Path to SDTM configuration directory")
    parser.add_argument("--output", default=str(base_dir / "sdtm"), help="Path to output SDTM directory")
    parser.add_argument("--csv", default=str(base_dir / "data" / "odm_long.csv"), help="Path to intermediate long CSV file")
    parser.add_argument("--metadata-summary", "-m", help="Path to output metadata summary CSV file (Data Dictionary)")
    
    args = parser.parse_args()

    print(f"--- Step 1: Parsing ODM XML from {Path(args.xml).name} ---")
    df = parse_odm_to_long_df(args.xml)
    if df.empty:
        print("Error: Parsed DataFrame is empty.")
        return
        
    Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.csv, index=False)
    print(f"Parsed {len(df)} rows. Saved to {Path(args.csv).name}")

    if args.metadata_summary:
        print(f"\n--- Generating Metadata Summary (Data Dictionary) ---")
        meta_df = extract_metadata_summary(df)
        Path(args.metadata_summary).parent.mkdir(parents=True, exist_ok=True)
        meta_df.to_csv(args.metadata_summary, index=False)
        print(f"Saved metadata summary to {Path(args.metadata_summary).name} (Shape: {meta_df.shape})")

    print(f"\n--- Step 2: Generating SDTM Datasets using configs from {Path(args.configs).name} ---")
    Path(args.output).mkdir(parents=True, exist_ok=True)
    create_sdtm_datasets(args.configs, args.csv, args.output)
    print(f"\nSuccess! SDTM datasets created in {args.output}")

if __name__ == "__main__":
    main()

