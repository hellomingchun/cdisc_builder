import os
import pandas as pd
from pathlib import Path

# Fix relative imports from source tree
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cdiscbuilder.sdtm.sdtm import create_sdtm_datasets
from cdiscbuilder.adam import AdamDerivation

def run_pipeline():
    # Setup paths
    base_dir = os.path.abspath(os.path.dirname(__file__))
    input_csv = os.path.join(base_dir, "odm_long.csv")
    
    sdtm_config_dir = os.path.join(base_dir, "sdtm", "specs")
    sdtm_output_dir = os.path.join(base_dir, "sdtm")
    
    adam_spec_file = os.path.join(base_dir, "adam", "specs", "adsl.yaml")
    
    print("=== 1. Starting SDTM Generation ===")
    print(f"Using configs from: {sdtm_config_dir}")
    os.makedirs(sdtm_output_dir, exist_ok=True)
    
    try:
        create_sdtm_datasets(sdtm_config_dir, input_csv, sdtm_output_dir)
        print("SDTM Generation Complete.")
    except Exception as e:
        print(f"SDTM Generation Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    print("\n=== 2. Starting ADaM Generation ===")
    print(f"Using spec file: {adam_spec_file}")
    
    try:
        engine = AdamDerivation(adam_spec_file)
        df = engine.build()
        engine.save()
        print("ADaM Generation Complete.")
        print("\nADSL Head:")
        print(df.head())
    except Exception as e:
        print(f"ADaM Generation Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    return True

if __name__ == "__main__":
    success = run_pipeline()
    if not success:
        sys.exit(1)
    print("\nPipeline finished successfully!")
