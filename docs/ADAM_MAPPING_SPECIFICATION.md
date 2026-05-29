# CDISC Builder: ADaM Mapping Specification

This document provides a comprehensive specification for deriving CDISC **ADaM (Analysis Data Model)** datasets from CDISC SDTM inputs using the `cdiscbuilder` package. 

It serves as a complete reference for developers and AI agents (such as Claude and Gemini) to generate valid ADaM YAML mapping configurations.

---

## 1. Specification Inheritance & Consolidation

ADaM configurations in `cdiscbuilder` support **hierarchical inheritance** (e.g., defining base templates at a global/project level and overriding or extending them at the study level).

* **`parents`**: A list of parent YAML files to inherit from.
* **Consolidation**: During processing, `cdiscbuilder` reads all parent specs in order, merging them using a `merge_by_key` strategy on the `columns` list using the `name` field.
* **Overrides**: Child specifications override parent specifications for fields with the same column `name`.
* **Dropping Columns**: Inherited columns can be dropped entirely in the child specification by specifying `drop: true` for the column.

---

## 2. YAML Configuration Root Schema

An ADaM YAML configuration contains the following root-level keys:

### Root Fields

| Key | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `domain` | `str` | **Yes** | ADaM dataset domain name. Must match the regex `^AD[A-Z0-9]{0,6}$` (e.g., `ADSL`, `ADAE`). |
| `dir` | `dict` | **Yes** | Paths to input and output directories (see [Directory Fields](#directory-fields) below). |
| `schema` | `str` | **Yes** | Relative path to the schema validation file. |
| `columns` | `list` | **Yes** | List of column mapping specifications. |
| `key` | `list` | No | List of unique row identifier variables for the dataset (e.g. `[USUBJID]`). Must contain 1 to 5 items. |
| `parents` | `list` | No | List of parent YAML files (relative paths) to inherit from. |
| `description` | `str` | No | A description of the dataset (max 200 characters). |
| `version` | `str` | No | Version number matching the pattern `^\d+\.\d+(\.\d+)?$`. |
| `metadata` | `dict` | No | Custom metadata key-value pairs. |

### Directory Fields (`dir`)

The `dir` object specifies where the input data resides and where to save the outputs:

* **`sdtm`** (Required): Relative or absolute path to the directory containing input SDTM datasets (stored as `.parquet` files).
* **`adam`** (Required): Relative or absolute path to the directory where derived ADaM `.parquet` files will be written.

---

## 3. Key Variable Rules

The variables specified under the root `key` field must follow strict architectural constraints:
1. **Column Definition**: All key variables must be explicitly defined in the `columns` list.
2. **Source Derivation Only**: Key variables can only be derived using the `source` derivation type (no `constant` or `function` allowed).
3. **Format**: The `source` path must follow the strict `DATASET.COLUMN` format (e.g. `DM.USUBJID`).
4. **Single Source Dataset**: All key variables must originate from the **same** source SDTM dataset (e.g., you cannot mix keys from `DM` and `SV` as the primary dataset key).
5. **No Duplicates**: The key variable combination must be unique in the source dataset. If duplicates are encountered during processing, the engine will write a warning and keep the first occurrence.

---

## 4. Column Mapping Schema

Each item in the `columns` list represents a single column specification.

### Required Fields
* **`name`** (Required): Column name. Must match the regex `^[A-Z][A-Z0-9_]{0,7}$` (uppercase, maximum 8 characters).
* **`type`** (Required): Output data type. Must be one of: `str`, `int`, `float`, `date`, `datetime`, `bool`.
* **`derivation`** (Required): Rules for deriving the column values (see [Derivation Types](#derivation-types) below).

### Optional Fields
* **`label`** (Optional): A description of the column (max 200 characters). Defaults to the column name if omitted.
* **`core`** (Optional): CDISC core designation. Options: `cdisc-required`, `org-required`, `optional`, `conditional`.
* **`codelist`** (Optional): Reference name for controlled terminology validation.
* **`drop`** (Optional): Set to `true` in a child YAML specification to remove this column from the inherited parent specification.
* **`validation`** (Optional): Custom validation rules for data checks (e.g., range limits, pattern matching).

---

## 5. Derivation Types

The `derivation` dictionary specifies how the column is derived. A column derivation must have at least one of the three primary derivation types: `source`, `constant`, or `function`.

> [!IMPORTANT]
> The `constant` key is **mutually exclusive** with `source`, `function`, and `condition`.

### Primary Derivations

| Key | Type | Description |
| :--- | :--- | :--- |
| `source` | `str` | Points directly to a source dataset variable in the format `DATASET.COLUMN` (e.g. `DM.RFSTDTC`). |
| `constant` | `str\|int\|float` | Assigns a static constant value. String literals in SQL derivations should be wrapped in single quotes (e.g. `constant: "'Y'"`). |
| `function` | `str` | Calls a specific python derivation function. |

### Advanced Derivation Rules

The following keys can be nested inside the `derivation` object to perform complex mapping, filtering, and aggregation:

#### 1. SQL-Like Filter (`filter`)
Applies a logical filter expression to the source dataset before deriving the value.
```yaml
derivation:
  source: AE.AETERM
  filter: "AESTDTC IS NOT NULL"
```

#### 2. Aggregations (`aggregation`)
Nested dictionary used to aggregate multiple source records.
* **`function`** (Required): Must be one of `first`, `last`, `mean`, `median`, `min`, `max`, `sum`, `count`, `closest`.
* **`target`** (Optional): Target value/date for the `closest` function.

```yaml
derivation:
  source: VS.VSORRES
  filter: "VSTESTCD = 'WEIGHT'"
  aggregation:
    function: last
```

#### 3. Value Mapping (`mapping`)
Translates source values to target values.
```yaml
derivation:
  source: DM.SEX
  mapping:
    "Male": "M"
    "Female": "F"
```

#### 4. Categorization (`cut`)
Categorizes continuous numeric variables into ranges.
```yaml
derivation:
  source: DM.AGE
  cut:
    "<18": "AGE < 18"
    "18-64": "AGE >= 18 AND AGE < 65"
    ">=65": "AGE >= 65"
```

#### 5. Conditional Rules (`condition`)
Defines conditional branching (`if-then-else` blocks). Each item in the list contains:
* **`when`** (Required): Condition expression to evaluate (e.g. `AGE >= 18`).
* **`then`** (Required): Derivation dict to apply if true.
* **`else`** (Optional): Default derivation dict if no conditions match.

```yaml
derivation:
  condition:
    - when: "DM.AGE >= 18"
      then:
        constant: "'ADULT'"
      else:
        constant: "'PEDIATRIC'"
```

---

## 6. Validation Rules (`validation`)

The `validation` key allows you to define constraints on the generated column. The validation engine will verify these post-derivation.

| Key | Type | Description |
| :--- | :--- | :--- |
| `unique` | `bool` | Verifies that all values in the column are unique. |
| `min` | `int\|float` | Verifies that values are greater than or equal to this limit. |
| `max` | `int\|float` | Verifies that values are less than or equal to this limit. |
| `min_length` | `int` | Minimum allowed string length (valid for type `str` only). |
| `max_length` | `int` | Maximum allowed string length (valid for type `str` only). |
| `allowed_values` | `list` | A list of standard codes or terms. |
| `pattern` | `str` | Regular expression string to check formatting. |
| `maximum_missing_percentage` | `float` | Maximum acceptable percentage of missing/null values (0-100). |

---

## 7. Example Specifications

### ADSL Specification Example (`adsl.yaml`)

```yaml
domain: ADSL
description: "Subject-Level Analysis Dataset"
version: "1.0.0"
schema: "./schema.yaml"
dir:
  sdtm: "../../sdtm"
  adam: ".."
key:
  - USUBJID
parents:
  - "./adsl_common.yaml"
columns:
  - name: STUDYID
    type: str
    label: "Study Identifier"
    derivation:
      source: DM.STUDYID
  - name: USUBJID
    type: str
    label: "Unique Subject Identifier"
    derivation:
      source: DM.USUBJID
  - name: AGE
    type: int
    label: "Age"
    derivation:
      source: DM.AGE
    validation:
      min: 0
      max: 120
      maximum_missing_percentage: 0.0
  - name: SAFFL
    type: str
    label: "Safety Population Flag"
    derivation:
      constant: "'Y'"
  - name: TRTSDT
    type: date
    label: "Start Date of Treatment"
    derivation:
      source: EX.EXSTDTC
      aggregation:
        function: first
```
