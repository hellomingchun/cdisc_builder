# CDISC Builder: SDTM Mapping Specification

This document provides a comprehensive specification for mapping clinical trial data from CDISC **ODM (Operational Data Model) XML** format to CDISC **SDTM (Study Data Tabulation Model)** datasets using the `cdiscbuilder` package. 

It is designed to serve as a complete reference for developers and AI agents (such as Claude and Gemini) to generate valid YAML mapping configurations.

---

## 1. Data Ingestion & Intermediate Format (`odm_long.csv`)

Before mapping configurations are applied, `cdiscbuilder` parses the source ODM XML file into a flat, long-format DataFrame (which is typically saved as `odm_long.csv`). 

Understanding this intermediate schema is critical because mapping configurations reference these column names as their inputs.

### Flat Schema Columns

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `StudyOID` | `str` | The unique identifier of the study, from `<Study OID="...">`. |
| `SubjectKey` | `str` | The unique identifier of the subject, from `<SubjectData SubjectKey="...">`. Fallback to `StudySubjectID` if missing. |
| `StudySubjectID` | `str` | The study-specific subject identifier. |
| `StudyEventOID` | `str` | The study event identifier, from `<StudyEventData StudyEventOID="...">`. |
| `StudyEventRepeatKey` | `str` | The repeat instance number for repeating events (defaults to `"1"` if not present). |
| `StudyEventStartDate` | `str` | The namespaced start date of the study event (extracted from the `StartDate` attribute). |
| `FormOID` | `str` | The form identifier, from `<FormData FormOID="...">`. |
| `ItemGroupOID` | `str` | The item group identifier, from `<ItemGroupData ItemGroupOID="...">`. |
| `ItemGroupRepeatKey` | `str` | The repeat instance number for repeating item groups. |
| `ItemOID` | `str` | The item identifier, from `<ItemData ItemOID="...">`. |
| `Value` | `str` | The raw clinical value stored in the item. |
| `Question` | `str` | The metadata translated text description/question associated with the `ItemOID`. |
| `ItemName` | `str` | The metadata definition name associated with the `ItemOID`. |

### Metadata Summary (Data Dictionary)

To make it easier for AI agents (like Claude and Gemini) to generate mapping configurations without parsing massive raw XML files, `cdiscbuilder` provides a **Metadata Summary** tool. This tool deduplicates variables, maps them to their respective forms, and extracts up to 3 non-empty sample values from the parsed data.

#### CLI Usage
To generate both the parsed clinical data and the data dictionary in a single command:
```bash
cdisc-sdtm --xml study_data.xml --csv odm_long.csv --metadata-summary metadata_summary.csv
```

#### Python API
```python
from cdiscbuilder.sdtm.odm_parser import parse_odm_to_long_df, extract_metadata_summary

# 1. Parse XML
df_long = parse_odm_to_long_df("study_data.xml")

# 2. Extract Data Dictionary
meta_df = extract_metadata_summary(df_long)
meta_df.to_csv("metadata_summary.csv", index=False)
```

#### Metadata Summary Columns
The output `metadata_summary.csv` contains the following columns:

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `FormOID` | `str` | The unique Form OID defining where the item is collected. |
| `ItemGroupOID` | `str` | The Item Group OID within the Form. |
| `ItemOID` | `str` | The Item OID (the target variable name). |
| `ItemName` | `str` | The definition name of the item. |
| `Question` | `str` | The translated question/description text for the item. |
| `SampleValues` | `str` | String representation of a list containing up to 3 distinct, non-empty clinical values (e.g., `['Male', 'Female']`). |

---

## 2. Configuration Structure & Domain Types

Mapping configurations are defined in YAML files located in a configuration directory. 

* The directory must contain a `defaults.yaml` file to define global defaults, keys, and custom ingestion/schema mappings.
* Each mapping file corresponds to one or more SDTM domains. The root key of the YAML file matches the target domain abbreviation (e.g., `DM`, `AE`, `VS`).
* Under the domain key, the configuration is structured as a **list of blocks**, each representing a different data source (Form/FormOID) to process.

There are two primary paradigms of domains: **Wide Domains** and **Findings Domains**.

### 2.1 Global Defaults (`defaults.yaml`)

The `defaults.yaml` file configures global settings for the study. To support custom source systems (such as Medidata Rave) or bypass XML parsing to load existing flat CSV files with non-standard column names, you can specify custom mappings and keys here.

```yaml
# defaults.yaml

# 1. Custom keys to pivot, sort, and group on (e.g. including custom RecordPosition)
keys: ["StudyOID", "SubjectKey", "StudyEventOID", "RecordPosition"]

# 2. For XML parsing: Map standard logical keys to custom XML attributes
# (e.g. read the 'RecordPosition' attribute in the XML but standardize it to 'ItemGroupRepeatKey' in df_long)
xml_mapping:
  item_group_repeat_key: "RecordPosition"

# 3. For Tabular Loading (e.g. direct csv load): Map standard logical keys to custom CSV columns
# (The loader renames custom CSV columns to logical standard ones before processing)
csv_columns:
  item_group_repeat_key: "RecordPosition"
  subject_key: "SubjectID"
```

If the input dataset is missing specific structural columns (like `FormOID` or `StudyEventRepeatKey` in a non-XML tabular dataset), the engine will automatically skip filtering on those columns and degrade gracefully.

---

## 3. Wide Domains (Pivoted Mapping)

Wide domains are structured datasets where each observation is represented in a single row per event instance (e.g., Demographics `DM`, Adverse Events `AE`, Concomitant Medications `CM`). 

### Processing Engine Logic
1. **Filter**: Filters the intermediate `odm_long.csv` to rows matching the specified `formoid`.
2. **Pivot**: Pivots the data using `keys` as indices, turning each distinct `ItemOID` into a column name, and filling cells with the first found `Value`.
3. **Map**: Maps pivoted columns (i.e. `ItemOID`s) to target SDTM columns.

### Block Structure
* **`type`** (Optional): `general`, `special_purpose`, `events`, or `interventions`. If omitted, defaults to `general` (all use the same underlying processor).
* **`formoid`** (Required): The Form OID(s) to process. Can be a single string or a list of strings.
* **`keys`** (Optional): A list of columns to pivot/group on. If omitted, defaults to the keys defined in `defaults.yaml`.
* **`merge_on`** (Optional): A list of columns. If specified, this block's pivoted data will be left-merged with the previous blocks on these columns. If omitted, blocks are appended (concatenated).
* **`columns`** (Required): A dictionary mapping target SDTM column names to their mapping configurations.

### Column Mapping Properties

For each column in `columns`, the configuration can be a simple string (assumed to be a `source` column name) or a dictionary supporting these properties:

| Key | Type | Description |
| :--- | :--- | :--- |
| `source` | `str` | The pivoted column (either an `ItemOID` like `I_1DEMO_PTSEXEL` or a metadata key like `SubjectKey`) to extract the value from. |
| `literal` | `str\|int\|float\|bool` | A hardcoded value assigned to every row in the block. |
| `type` | `str` | Casts the output column to a specific type. Options: `str`, `int`, `float`, `bool`, `date` (formats inputs to `YYYY-MM-DD` strings). |
| `label` | `str` | Optional column description. |
| `prefix` | `str` | Prepend a static prefix to the value (e.g. `prefix: "CART-"`). *Note: `suffix` is not supported.* |
| `substring_start` | `int` | The 0-based index to start extracting characters from the source value. |
| `substring_length` | `int` | The number of characters to extract from the source value. |
| `fallback` | `str` | A column name to read if the primary `source` column contains a null/NaN value. |
| `value_mapping` | `dict` | Dictionary mapping raw input values to mapped target values (e.g., `{"Male": "M"}`). |
| `case_sensitive` | `bool` | Default `true`. If set to `false`, `value_mapping` lookup matches case-insensitively. |
| `mapping_default` | `str\|int\|float\|bool` | Value to assign if the source value is not found in the `value_mapping`. |
| `mapping_default_source` | `str` | Column name to fallback to if the source value is not found in the `value_mapping`. |
| `dependency` | `str` | Column name. The mapped value is kept only if the dependency column is not null. |
| `dependency_false_value` | `any` | Value to assign if the `dependency` column is null. Defaults to null. |
| `function` | `str` | Function to call. The only supported function is `calculate_study_day`. |
| `args` | `list` | Arguments to pass to `function`. For `calculate_study_day`, it must be a list of two columns: `[event_date, RFSTDTC]` (e.g., `[AESTDTC, DM.RFSTDTC]`). |
| `group` | `list` | List of columns. Combines with `sort_by` to generate sequential counts starting at 1. Can be used for block-level or global sequencing. |
| `sort_by` | `list` | List of columns to order the rows by before assigning sequence counts. |
| `max_missing_pct` | `float` | Validation threshold. Prints a warning if the percentage of missing values in the final column exceeds this value. |

---

## 4. Findings Domains (Tall Mapping)

Findings domains are tall, transactional datasets where each observation represents a single measurement or test result (e.g., Vital Signs `VS`, Laboratory Test Results `LB`, Questionnaires `QS`, Inclusion/Exclusion Criteria `IE`). 

### Processing Engine Logic
1. **Filter**: Filters the intermediate `odm_long.csv` to rows matching the `formoid` (optional), `item_group_regex` (optional), and `item_oid_regex` (optional).
2. **Tall Preservation**: Does **NOT** pivot. It keeps the data in its raw tall format, meaning each row in the output maps to a row in the filtered DataFrame.
3. **Map**: Maps target SDTM columns directly from tall columns (`ItemOID`, `ItemName`, `Value`, `Question`, `StudyEventStartDate`, etc.).

### Block Structure
* **`type`** (Required): Must be set to `findings`.
* **`formoid`** (Optional): The Form OID(s) to filter on. String or list of strings.
* **`item_group_regex`** (Optional): A regex string to filter the `ItemGroupOID` (e.g. `IG_ELIGI_.*`).
* **`item_oid_regex`** (Optional): A regex string to filter the `ItemOID` (e.g. `I_KITCH_(HEIGHT\|WEIGHT\|BP_SYS\|BP_DIA\|PULSE).1`).
* **`keys`** (Optional): List of index columns. Defaults to keys in `defaults.yaml`.
* **`columns`** (Required): A dictionary mapping target SDTM column names to their mapping configurations.

### Column Mapping Properties

For each column in `columns`, the configuration can be a simple string (assumed to be a `source` column name) or a dictionary. 

> [!WARNING]
> The findings processor only supports a subset of the column properties available in the wide processor. Features like `fallback`, `dependency`, `substring_start`, `case_sensitive`, and `mapping_default` are **NOT** supported.

Supported properties:

| Key | Type | Description |
| :--- | :--- | :--- |
| `source` | `str` | The column in the tall DataFrame (typically `ItemOID`, `ItemName`, `Value`, `Question`, or `StudyEventStartDate`) to extract from. |
| `literal` | `str\|int\|float\|bool` | A hardcoded value assigned to every row. |
| `type` | `str` | Casts the output column to a specific type: `str`, `int`, `float`, or `date` (formats inputs to `YYYY-MM-DD` strings). |
| `label` | `str` | Optional column description. |
| `prefix` | `str` | Prepend a static prefix to the value (e.g. `prefix: "CART-"`). |
| `regex_extract` | `str` | A regular expression pattern containing a single capture group. Used to extract a substring from the `source` column (e.g., `I_ELIGI_(.*)` to extract the test code). |
| `value_mapping` | `dict` | Dictionary mapping raw input values to target values. *Note: Lookup is strictly case-sensitive.* |
| `group` | `list` | List of columns. Generates sequential counts starting at 1 (e.g., `group: ["USUBJID"]`). |
| `sort_by` | `list` | List of columns to order the rows by before assigning sequence counts. |

---

## 5. Standard Mapping Examples

Below are standard mapping patterns for a Wide Domain (`DM.yaml`) and a Findings Domain (`VS.yaml`).

### Wide Domain Example: Demographics (`DM.yaml`)

```yaml
DM:
  # First Block: Main demographics form
  - type: special_purpose
    formoid: "F_1DEMOGRAPHIC"
    columns:
      STUDYID: 
        source: "StudyOID"
        type: "str"
        label: "Study Identifier"
      DOMAIN: 
        literal: "DM"
        type: "str"
        label: "Domain Abbreviation"
      USUBJID: 
        source: "SubjectKey"
        prefix: "CART-"
        type: "str"
        label: "Unique Subject Identifier"
      SUBJID: 
        source: "SubjectKey"
        type: "str"
        label: "Subject Identifier"
      RFSTDTC: 
        source: "I_1DEMO_TODAY"
        type: "date"
        label: "Subject Reference Start Date"
      SEX: 
        source: "I_1DEMO_PTSEXEL"
        type: "str"
        label: "Sex"
        value_mapping:
          "Male": "M"
          "Female": "F"
        case_sensitive: false
      RACE: 
        source: "I_1DEMO_PTRACE"
        type: "str"
        label: "Race"
      ETHNIC: 
        source: "I_1DEMO_HISP"
        type: "str"
        label: "Ethnicity"
        value_mapping:
          "Yes": "HISPANIC OR LATINO"
          "No": "NOT HISPANIC OR LATINO"
        mapping_default: "UNKNOWN"
      COUNTRY: 
        literal: "USA"
        type: "str"
        label: "Country"

  # Second Block: Merge Age from Eligibility form
  - type: special_purpose
    formoid: "F_ELIGIBILITY"
    merge_on: ["USUBJID"]
    columns:
      USUBJID: 
        source: "SubjectKey"
        prefix: "CART-"
        type: "str"
      AGE: 
        source: "I_ELIGI_PTAGE"
        type: "int"
        label: "Age"
      AGEU: 
        literal: "YEARS"
        type: "str"
        label: "Age Units"
```

### Findings Domain Example: Vital Signs (`VS.yaml`)

```yaml
VS:
  - type: findings
    formoid: "F_KITCHENSINK"
    # Match height, weight, systolic/diastolic BP, and pulse
    item_oid_regex: "I_KITCH_(HEIGHT|WEIGHT|BP_SYS|BP_DIA|PULSE).*"
    columns:
      STUDYID:
        source: "StudyOID"
        type: "str"
        label: "Study Identifier"
      DOMAIN:
        literal: "VS"
        type: "str"
        label: "Domain Abbreviation"
      USUBJID:
        source: "SubjectKey"
        prefix: "CART-"
        type: "str"
        label: "Unique Subject Identifier"
      VSTESTCD:
        source: "ItemOID"
        # Extract the short test name from the ItemOID (e.g. I_KITCH_HEIGHT_1 -> HEIGHT)
        regex_extract: "I_KITCH_([A-Z_]+).*"
        type: "str"
        label: "Vital Signs Test Short Name"
      VSTEST:
        source: "ItemName"
        type: "str"
        label: "Vital Signs Test Name"
      VSORRES:
        source: "Value"
        type: "str"
        label: "Result or Finding in Original Units"
      VSDTC:
        source: "StudyEventStartDate"
        type: "date"
        label: "Date/Time of Measurements"
      VSSEQ:
        group: ["USUBJID"]
        sort_by: ["VSDTC", "VSTESTCD"]
        type: "int"
        label: "Sequence Number"
```
