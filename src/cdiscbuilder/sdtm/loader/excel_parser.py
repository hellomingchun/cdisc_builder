import pandas as pd
import yaml
import math
import io

def clean_val(val):
    if pd.isna(val):
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return str(val).strip()

def parse_excel_to_yaml_strings(excel_source):
    """
    Parses an Excel specification and returns a dictionary mapping
    sheet names (domains) to their corresponding YAML string definitions.
    
    :param excel_source: A path to an Excel file or a file-like object.
    :return: dict mapping domain names (e.g. 'DM') to YAML strings.
    """
    # Read the workbook
    xl = pd.ExcelFile(excel_source)
    parsed_domains = {}
    
    for sheet in xl.sheet_names:
        if sheet == 'Overview':
            continue
            
        # Try with default header (0) first, then header=1
        df = pd.read_excel(xl, sheet_name=sheet)
        if 'Variable' not in df.columns:
            df = pd.read_excel(xl, sheet_name=sheet, header=1)
            
        # Skip if the dataframe has no data rows or 'Variable' is still missing
        if df.empty or 'Variable' not in df.columns or len(df.dropna(subset=['Variable'])) == 0:
            continue
            
        columns_dict = {}
        
        for _, row in df.iterrows():
            variable = clean_val(row.get('Variable'))
            if not variable:
                continue
                
            col_def = {}
            # Map Excel columns to YAML fields based on schema definition
            if clean_val(row.get('Type')): col_def['type'] = clean_val(row.get('Type'))
            if clean_val(row.get('Label')): col_def['label'] = clean_val(row.get('Label'))
            if clean_val(row.get('Role')): col_def['role'] = clean_val(row.get('Role'))
            if clean_val(row.get('Core')): col_def['core'] = clean_val(row.get('Core'))
            if clean_val(row.get('Description')): col_def['description'] = clean_val(row.get('Description'))
            if clean_val(row.get('Origin')): col_def['origin'] = clean_val(row.get('Origin'))
            if clean_val(row.get('Derivation Rule')): col_def['derivation_rule'] = clean_val(row.get('Derivation Rule'))
            if clean_val(row.get('Source')): col_def['source'] = clean_val(row.get('Source'))
            if clean_val(row.get('Literal')): col_def['literal'] = clean_val(row.get('Literal'))
            if clean_val(row.get('Function')): col_def['function'] = clean_val(row.get('Function'))
            
            columns_dict[variable] = col_def
            
        # Prepare the final dictionary in the cdisc_builder format
        domain_dict = {
            sheet: [
                {
                    "type": "general",
                    "columns": columns_dict
                }
            ]
        }
        
        # Output as YAML string
        yaml_string = yaml.dump(domain_dict, sort_keys=False, default_flow_style=False)
        parsed_domains[sheet] = yaml_string
        
    return parsed_domains
