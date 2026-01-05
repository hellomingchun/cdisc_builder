# CDISC Builder
 
A Python package to convert ODM XML to SDTM and ADaM datasets.

## Overview

**Source:** https://cdiscdataset.com/  
**Download Date:** January 2, 2026  
**Format:** CSV (Comma-Separated Values)  
**Purpose:** Educational and research purposes for clinical data standards

## Dataset Standards

This collection includes datasets from three major CDISC standards:

### 1. SDTM (Study Data Tabulation Model)

The Study Data Tabulation Model organizes clinical data into standardized datasets with consistent variables, allowing for efficient regulatory submissions.

**Location:** `SDTM/`  
**Datasets Included:**
- **DM** - Demographics: Subject demographics and characteristics
- **AE** - Adverse Events: Adverse events reported during the study
- **LB** - Laboratory Tests: Laboratory test results
- **VS** - Vital Signs: Vital signs measurements taken during the study
- **CM** - Concomitant Medications: Medications taken during the study period
- **EX** - Exposure: Exposure to protocol-specified study treatment
- **MH** - Medical History: Subject-relevant medical history
- **DS** - Disposition: Subject disposition information including completion/discontinuation

### 2. ADaM (Analysis Data Model)

The Analysis Data Model provides standards for creating analysis datasets that are clear, reproducible, and support efficient generation of statistical analyses.

**Location:** `ADaM/`  
**Datasets Included:**
- **ADSL** - Subject Level Analysis Dataset: Analysis-ready subject characteristics dataset
- **ADAE** - Adverse Events Analysis Dataset: Analysis-ready adverse events dataset
- **ADLB** - Laboratory Analysis Dataset: Analysis-ready laboratory tests dataset
- **ADVS** - Vital Signs Analysis Dataset: Analysis-ready vital signs dataset

### 3. SEND (Standard for Exchange of Nonclinical Data)

The Standard for Exchange of Nonclinical Data provides a way to standardize nonclinical or preclinical research data for regulatory submissions.

**Location:** `SEND/`  
**Datasets Included:**
- **DM** - Demographics: Demographics and characteristics of test subjects
- **LB** - Laboratory Test Results: Laboratory test results from samples collected
- **BW** - Body Weight: Body weight measurements over time
- **CL** - Clinical Observations: Clinical signs and observations
- **MA** - Macroscopic Findings: Gross pathology/necropsy findings
- **MI** - Microscopic Findings: Microscopic/histopathology findings

## Dataset Parameters

All datasets were generated with the following parameters:

- **Number of Subjects:** 100 (SDTM/ADaM), 50 (SEND)
- **Treatment Arms:** 3
- **Therapeutic Area:** Oncology (SDTM/ADaM), Toxicology (SEND)
- **Output Format:** CSV

## CLI Usage

These datasets were generated using a command-line interface (CLI) tool.

### Installation

```bash
pip install cdisc_builder
```

### Example Usage

To generate SDTM datasets:

```bash
cdisc-sdtm generate --sdtm --num-subjects 100 --output-dir ./sdtm_data
```

To generate ADaM datasets:

```bash
cdisc-sdtm generate --adam --num-subjects 100 --output-dir ./adam_data
```

To generate SEND datasets:

```bash
cdisc-sdtm generate --send --num-subjects 50 --output-dir ./send_data
```

For more options:

```bash
cdisc-sdtm generate --help
```

### XML Generation (Advanced)

The `cdisc_builder` package also supports generating CDISC XML files directly from the CLI.

Example:

```bash
cdisc-sdtm --xml path/to/data.xml
```

(Note: The package name is `cdisc_builder`, but the CLI command remains `cdisc-sdtm`)

## File Naming Convention

Files follow this naming pattern:
```
{standard}_{domain}_{timestamp}.csv
```

Example: `sdtm_dm_20260102_213137.csv`
- `sdtm` - Standard type
- `dm` - Domain code
- `20260102_213137` - Timestamp (YYYYMMDD_HHMMSS)

## Dataset Sizes

### SDTM Datasets
- sdtm_dm: 21K (Demographics)
- sdtm_ae: 49K (Adverse Events)
- sdtm_lb: 1.3M (Laboratory Tests)
- sdtm_vs: 433K (Vital Signs)
- sdtm_cm: 45K (Concomitant Medications)
- sdtm_ex: 55K (Exposure)
- sdtm_mh: 19K (Medical History)
- sdtm_ds: 49K (Disposition)

### ADaM Datasets
- adam_adsl: 28K (Subject Level)
- adam_adae: 69K (Adverse Events Analysis)
- adam_adlb: 2.4M (Laboratory Analysis)
- adam_advs: 775K (Vital Signs Analysis)

### SEND Datasets
- send_dm: 5.8K (Demographics)
- send_lb: 181K (Laboratory Tests)
- send_bw: 31K (Body Weight)
- send_cl: 15K (Clinical Observations)
- send_ma: 11K (Macroscopic Findings)
- send_mi: 19K (Microscopic Findings)

## Usage

These datasets are synthetic and generated for:
- **Training:** Learning CDISC standards and data structures
- **Testing:** Testing clinical data management systems
- **Development:** Developing statistical analysis programs
- **Research:** Understanding clinical trial data organization

## Important Notes

1. **Synthetic Data:** All data is computer-generated and does not represent real patients or studies
2. **Not for Regulatory Use:** These datasets are for educational purposes only and should not be used for actual regulatory submissions
3. **CDISC Compliance:** Datasets follow CDISC standards but may not include all possible variables or validation rules
4. **File Retention:** Files on the source server are automatically deleted after 1 hour of generation

## API Information

These datasets were downloaded using the CDISC Dataset Generator API:

**Base URL:** https://cdiscdataset.com  
**API Version:** v1.1  
**Authentication:** None required for development/testing

### Key API Endpoints Used:
- `POST /api/generate-sdtm` - Generate SDTM datasets
- `POST /api/generate-adam` - Generate ADaM datasets
- `POST /api/generate-send` - Generate SEND datasets

For more information, visit: https://cdiscdataset.com/api-docs

## Additional Resources

### CDISC Standards Documentation
- **CDISC Official Website:** https://www.cdisc.org/
- **SDTM Implementation Guide:** https://www.cdisc.org/standards/foundational/sdtm
- **ADaM Implementation Guide:** https://www.cdisc.org/standards/foundational/adam
- **SEND Implementation Guide:** https://www.cdisc.org/standards/foundational/send

### Regulatory Resources
- **FDA CDISC Standards:** https://www.fda.gov/industry/fda-data-standards-advisory-board/study-data-standards-resources

## License

These datasets are provided by cdiscdataset.com for educational and research purposes. Please refer to the source website for specific terms of use.

## Contact

For questions about the datasets or the generation tool:
- **Website:** https://cdiscdataset.com/
- **Email:** info@cdiscdataset.com
- **Support:** Available 24/7 via the website

---

**Generated by:** CDISC Dataset Downloader Script  
**Date:** January 2, 2026  
**Total Datasets:** 18 (8 SDTM + 4 ADaM + 6 SEND)
