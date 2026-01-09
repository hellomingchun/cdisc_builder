import pandas as pd
import os
import shutil
import sys
from cdiscbuilder.odm import parse_odm_to_long_df
from cdiscbuilder.sdtm import create_sdtm_datasets

def run_demo():
    # Paths (relative to updated location)
    xml_path = "../car-t-openclinica.xml"
    input_csv = "odm_long.csv"
    output_dir = "output_datasets"
    config_dir = "study_specs"

    # Clean
    if os.path.exists(output_dir): shutil.rmtree(output_dir)
    if os.path.exists(input_csv): os.remove(input_csv)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Parsing {xml_path}...")
    df_long = parse_odm_to_long_df(xml_path)
    df_long.to_csv(input_csv, index=False)
    
    print("Generating SDTM...")
    create_sdtm_datasets(config_dir, input_csv, output_dir)
    
    print("Checking Outputs...")
    failed = False
    for domain in ['AE', 'CM', 'VS', 'IE']:
        p = os.path.join(output_dir, f"{domain}.parquet")
        if os.path.exists(p):
            df = pd.read_parquet(p)
            print(f"\n--- {domain} Head ---")
            print(df.head())
        else:
            print(f"Warning: {domain}.parquet not generated.")
            failed = True

    # Check VS units
    p_vs = os.path.join(output_dir, "VS.parquet")
    if os.path.exists(p_vs):
        df_vs = pd.read_parquet(p_vs)
        print("\n--- VS Unit Check ---")
        print(df_vs[['VSTESTCD', 'VSSTRESU', 'VSORRESU']].head(10))
        
        # Verify units exist (not NaN)
        valid_units = df_vs['VSSTRESU'].dropna().unique()
        print(f"Mapped Units: {valid_units}")
        if len(valid_units) == 0:
            print("ERROR: No units mapped in VS!")
            failed = True
            
    if failed:
        sys.exit(1)
    print("\nDemo Run Complete.")

if __name__ == "__main__":
    run_demo()
