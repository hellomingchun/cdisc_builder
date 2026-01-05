# CDISC Builder

**`cdiscbuilder`** is a Python package designed to simplify the transformation of clinical trial data from **ODM (Operational Data Model)** XML format into **CDISC SDTM (Study Data Tabulation Model)** and **ADaM (Analysis Data Model)** datasets.

It provides a flexible, configuration-driven approach to data mapping, allowing users to define rules using simple YAML files or Python dictionaries without harcoding complex logic.

## Key Features

-   **ODM XML Parsing**: Efficiently parses CDISC ODM strings and files into workable dataframes.
-   **Configurable Mappings**: Define your mapping rules (source columns, hardcoded values, custom logic) in YAML.
-   **Schema Validation**: Ensures your configuration files adhere to strict standards before processing.
-   **Metadata-Driven Findings**: Powerful processor for Findings domains (VS, LB, FA, etc.) using granular metadata.
-   **Excel/Parquet Output**: Generates regulatory-compliant datasets in modern formats.

## Installation

```bash
pip install cdiscbuilder
```

## Quick Start

### 1. Command Line Interface

You can generate datasets directly from your terminal:

```bash
# Generate SDTM datasets from an ODM XML file
cdisc-sdtm --xml study_data.xml --output ./sdtm_data
```

### 2. Python API

```python
from cdiscbuilder.sdtm import create_sdtm_datasets

# Define paths
xml_file = "study_data.xml"
config_dir = "path/to/my/specs" 
output_dir = "./sdtm_outputs"

# Generate Datasets
create_sdtm_datasets(config_dir, xml_file, output_dir)
```

## Configuration

The package comes with standard configurations for common domains (`DM`, `AE`, `VS`, etc.) in `src/cdisc_builder/specs`. You can override these or add new ones by creating your own configuration directory.

### Example YAML (`DM.yaml`)

```yaml
DM:
    - formoid: "FORM.DEMOG"
      columns:
          STUDYID:
              source: StudyOID
              type: str
          USUBJID:
              source: SubjectKey
              type: str
          AGE:
              source: IT.AGE
              type: int
          SEX:
              source: IT.SEX
              type: str
```

## License

[MIT License](LICENSE)
