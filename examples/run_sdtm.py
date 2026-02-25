import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from cdiscbuilder.sdtm.odm_parser import parse_odm_to_long_df
from cdiscbuilder.sdtm.sdtm import create_sdtm_datasets

def main():
    base_dir = Path(__file__).parent
    xml_path = base_dir / "data" / "openclinica_comprehensive_sample.xml"
    specs_dir = base_dir / "sdtm" / "specs" / "sample"
    output_dir = base_dir / "sdtm"
    long_csv = base_dir / "data" / "odm_long.csv"

    print(f"--- Step 1: Parsing ODM XML from {xml_path.name} ---")
    df = parse_odm_to_long_df(str(xml_path))
    df.to_csv(str(long_csv), index=False)
    print(f"Parsed {len(df)} rows. Saved to {long_csv.name}")

    print(f"\n--- Step 2: Generating SDTM Datasets ---")
    create_sdtm_datasets(str(specs_dir), str(long_csv), str(output_dir))
    print(f"\nSuccess! SDTM datasets created in {output_dir}")

if __name__ == "__main__":
    main()
