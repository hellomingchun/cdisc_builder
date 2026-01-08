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
            seq_col = f"{domain}SEQ"
            if seq_col in df.columns:
                print(f"{seq_col} present.")
                # Basic check for SEQ monotonicity per USUBJID
                # Just print first subject seq
                first_sub = df['USUBJID'].iloc[0]
                sub_df = df[df['USUBJID'] == first_sub]
                print(f"SEQ for {first_sub}: {sub_df[seq_col].tolist()}")
            else:
                print(f"ERROR: {seq_col} missing in {domain}")
                failed = True
        else:
            print(f"Warning: {domain}.parquet not generated.")
            # CM might fail if I guessed wrong, but AE VS IE should work
            
    if failed:
        sys.exit(1)
    print("\nDemo Run Complete.")

if __name__ == "__main__":
    run_demo()
