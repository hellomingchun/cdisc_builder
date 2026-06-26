# Hi, I'm Ming-Chun 👋

I am a Clinical Data Scientist specializing in technical architecture and clinical data standards. I build tools that bridge the gap between data engineering and clinical compliance.

---

# 🛠️ cdisc_builder

`cdisc_builder` is a Python package designed to streamline the generation and validation of CDISC-compliant clinical trial datasets (such as SDTM and ADaM). 

Historically, these pipelines are heavily reliant on legacy systems. This package brings modern, fast, and reproducible data engineering practices to clinical trial programming using Python.

## 🚀 Quick Start

### Installation
Install the package directly from source (or PyPI if published):

```bash
pip install git+https://github.com/hellomingchun/cdisc_builder.git
```

### Basic Example
The easiest way to generate SDTM datasets is by using the parser and builder pipeline. Here is an example of a `run_sdtm.py` script that handles the end-to-end derivation:

```python
from cdiscbuilder.sdtm.odm_parser import parse_odm_to_long_df
from cdiscbuilder.sdtm.sdtm import create_sdtm_datasets

# 1. Parse raw ODM XML to an intermediate long CSV format
xml_path = "data/openclinica_data.xml"
csv_path = "data/odm_long.csv"

df = parse_odm_to_long_df(xml_path)
df.to_csv(csv_path, index=False)

# 2. Generate SDTM Datasets using your YAML specifications
configs_dir = "sdtm/specs/sample"
output_dir = "sdtm_output"

create_sdtm_datasets(configs_dir, csv_path, output_dir)
print(f"Success! SDTM datasets created in {output_dir}")
```

You can also run the built-in CLI command directly from your terminal:
```bash
cdisc-sdtm --xml data/openclinica_data.xml --configs sdtm/specs/sample --output sdtm_output
```

## 🤖 AI-Driven Clinical Programming

`cdisc_builder` is uniquely designed to act as a bridge between **Large Language Models (LLMs)** and clinical data standards. 

Traditional clinical programming relies heavily on imperative languages (like SAS) where logic is deeply embedded in custom scripts. `cdisc_builder` shifts this paradigm by abstracting transformations into a strictly validated, declarative **YAML Domain-Specific Language (DSL)**.

This makes it the perfect companion for AI agents (such as Claude, Gemini, or ChatGPT) to automate mapping tasks:

1. **Schema-Driven Rules**: Because all mappings conform strictly to `schema.yaml`, an AI can easily read the schema documentation and guarantee syntactically correct derivations.

2. **Metadata Summaries**: Raw ODM XML files are often too large for AI context windows. `cdisc_builder` can generate lightweight "Data Dictionaries" (metadata summaries) containing only the essential variable information and sample values, allowing the AI to perfectly understand the source data.

3. **Automated Derivation**: An AI agent can read your source data dictionary and output the exact ADaM or SDTM YAML mapping specifications required to build compliant datasets, drastically reducing manual programming time.

## 📬 Connect with Me
Feel free to check out the source code, open an issue, or contribute to the project on GitHub.
