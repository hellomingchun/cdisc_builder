import pandas as pd
import os
from pathlib import Path

def main():
    base_dir = Path(__file__).parent
    sdtm_dir = base_dir / "sdtm"
    adam_dir = base_dir / "adam"
    output_html = base_dir / "demo.html"

    # Load data
    dm = pd.read_parquet(sdtm_dir / "DM.parquet")
    ae = pd.read_parquet(sdtm_dir / "AE.parquet")
    vs = pd.read_parquet(sdtm_dir / "VS.parquet")
    adsl = pd.read_parquet(adam_dir / "adsl.parquet")

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CDISC SDTM & ADaM Demo</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f8f9fa; padding: 20px; }}
        .card {{ margin-bottom: 20px; border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .nav-tabs {{ margin-bottom: 20px; }}
        .table {{ font-size: 0.85rem; }}
        .header {{ background: #004a99; color: white; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        table th, table td {{ text-align: center; vertical-align: middle; }}
    </style>
</head>
<body>
    <div class="header text-center">
        <h1>CDISC Builder: SDTM & ADaM Showcase</h1>
        <p>Demonstrating automated CDISC dataset generation from OpenClinica ODM XML</p>
    </div>

    <ul class="nav nav-tabs" id="demoTabs" role="tablist">
        <li class="nav-item" role="presentation">
            <button class="nav-link active" id="sdtm-tab" data-bs-toggle="tab" data-bs-target="#sdtm" type="button" role="tab">SDTM Domains</button>
        </li>
        <li class="nav-item" role="presentation">
            <button class="nav-link" id="adam-tab" data-bs-toggle="tab" data-bs-target="#adam" type="button" role="tab">ADaM Datasets</button>
        </li>
    </ul>

    <div class="tab-content" id="demoTabsContent">
        <!-- SDTM Tab -->
        <div class="tab-pane fade show active" id="sdtm" role="tabpanel">
            <div class="card">
                <div class="card-header bg-primary text-white">DM - Demographics</div>
                <div class="card-body">
                    {dm.to_html(classes='table table-hover', index=False)}
                </div>
            </div>
            <div class="card">
                <div class="card-header bg-primary text-white">AE - Adverse Events</div>
                <div class="card-body">
                    {ae.to_html(classes='table table-hover', index=False)}
                </div>
            </div>
            <div class="card">
                <div class="card-header bg-primary text-white">VS - Vital Signs (First 10 rows)</div>
                <div class="card-body">
                    {vs.head(10).to_html(classes='table table-hover', index=False)}
                </div>
            </div>
        </div>

        <!-- ADaM Tab -->
        <div class="tab-pane fade" id="adam" role="tabpanel">
            <div class="card">
                <div class="card-header bg-success text-white">ADSL - Subject Level Analysis</div>
                <div class="card-body">
                    {adsl.to_html(classes='table table-hover', index=False)}
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    with open(output_html, "w") as f:
        f.write(html_content)
    print(f"Demo HTML generated at {output_html}")

if __name__ == "__main__":
    main()
