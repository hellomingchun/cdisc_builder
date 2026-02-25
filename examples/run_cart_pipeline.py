import os
import sys
from pathlib import Path
import pandas as pd
import yaml

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from cdiscbuilder.sdtm.odm_parser import parse_odm_to_long_df
from cdiscbuilder.sdtm.sdtm import create_sdtm_datasets
from cdiscbuilder.adam.adam_derivation.engine import AdamDerivation

def main():
    base_dir = Path(__file__).parent
    xml_path = base_dir / "data" / "car-t-openclinica.xml"
    sdtm_dir = base_dir / "sdtm"
    adam_dir = base_dir / "adam"
    specs_dir = sdtm_dir / "specs" / "cart"
    long_csv = base_dir / "data" / "odm_long.csv"
    output_html = base_dir / "demo_cart.html"

    print(f"--- Step 1: Parsing CAR-T ODM XML ---")
    df = parse_odm_to_long_df(str(xml_path))
    df.to_csv(str(long_csv), index=False)
    print(f"Parsed {len(df)} rows.")

    print(f"\n--- Step 2: Generating SDTM Datasets ---")
    # Using the clean YAML files in examples/sdtm/specs/
    create_sdtm_datasets(str(specs_dir), str(long_csv), str(output_dir := sdtm_dir))

    print(f"\n--- Step 3: Generating ADaM ADSL ---")
    # adsl.yaml is already set to use DM
    engine = AdamDerivation(str(adam_dir / "specs" / "adsl.yaml"))
    engine.save()

    print(f"\n--- Step 4: Generating Demo HTML ---")
    dm_df = pd.read_parquet(sdtm_dir / "DM.parquet")
    ae_df = pd.read_parquet(sdtm_dir / "AE.parquet")
    vs_df = pd.read_parquet(sdtm_dir / "VS.parquet")
    adsl_df = pd.read_parquet(adam_dir / "adsl.parquet")

    # Filter to first 10 subjects for the demo
    top_10_subjects = dm_df['USUBJID'].unique()[:10]
    dm_df = dm_df[dm_df['USUBJID'].isin(top_10_subjects)]
    ae_df = ae_df[ae_df['USUBJID'].isin(top_10_subjects)]
    vs_df = vs_df[vs_df['USUBJID'].isin(top_10_subjects)]
    adsl_df = adsl_df[adsl_df['USUBJID'].isin(top_10_subjects)]

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CAR-T Study Showcase</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f1f3f5; padding: 20px; }}
        .card {{ margin-bottom: 25px; border-radius: 10px; border: none; box-shadow: 0 4px 10px rgba(0,0,0,0.08); }}
        .table {{ font-size: 0.8rem; }}
        table th, table td {{ text-align: center; vertical-align: middle; }}
        .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 40px; }}
    </style>
</head>
<body>
    <div class="header text-center">
        <h1>CAR-T Cell Therapy Study: CDISC Datasets</h1>
        <p>Real-world mapping from CAR-T OpenClinica ODM Export</p>
    </div>

    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <h3>SDTM Domains</h3>
                <div class="card"><div class="card-header bg-dark text-white">DM (Demographics)</div><div class="card-body">{dm_df.to_html(classes='table table-striped', index=False)}</div></div>
                <div class="card"><div class="card-header bg-dark text-white">AE (Adverse Events)</div><div class="card-body">{ae_df.to_html(classes='table table-striped', index=False)}</div></div>
                <div class="card"><div class="card-header bg-dark text-white">VS (Vital Signs - Sample)</div><div class="card-body">{vs_df.head(15).to_html(classes='table table-striped', index=False)}</div></div>
                
                <h3 class="mt-5">ADaM Datasets</h3>
                <div class="card"><div class="card-header bg-success text-white">ADSL (Subject-Level Analysis)</div><div class="card-body">{adsl_df.to_html(classes='table table-striped', index=False)}</div></div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    with open(output_html, "w") as f:
        f.write(html_content)
    print(f"\nDone! CAR-T Demo HTML generated at {output_html}")

if __name__ == "__main__":
    main()
