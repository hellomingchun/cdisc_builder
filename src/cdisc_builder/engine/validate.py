import yaml
import os

def load_schema():
    current_dir = os.path.dirname(__file__)
    # config_data is parallel to engine/
    pkg_root = os.path.dirname(os.path.dirname(__file__)) # src/cdisc_builder
    schema_path = os.path.join(pkg_root, "specs", "schema.yaml")
    
    if not os.path.exists(schema_path):
        print(f"Warning: Schema file not found at {schema_path}")
        return None
        
    with open(schema_path, 'r') as f:
        return yaml.safe_load(f)

def validate_domain_config(domain_name, config, schema):
    """
    Validates a single domain configuration against the schema.
    """
    if not schema:
        return True

    # Check if General (List) or Findings (Dict)
    is_general = isinstance(config, list)
    is_findings = isinstance(config, dict) and config.get('type') == 'FINDINGS'

    if is_general:
        return _validate_general(domain_name, config, schema['schemas']['general_domain'], schema['definitions'])
    elif is_findings:
        return _validate_findings(domain_name, config, schema['schemas']['findings_domain'], schema['definitions'])
    else:
        # Fallback or mixed type?
        # If dict but not FINDINGS, maybe it's a single general block (normalized usually)
        # But our loader usually normalizes.
        print(f"Validation Warning: {domain_name} structure unrecognized (Not List or Findings Dict).")
        return False

def _validate_general(domain, config, schema, definitions):
    if not isinstance(config, list):
        print(f"Schema Error: {domain} must be a list (General Domain). Got {type(config)}")
        return False
        
    for idx, block in enumerate(config):
        if not isinstance(block, dict):
            print(f"Schema Error: {domain}[{idx}] must be a dict. Got {type(block)}")
            return False

        # Validate required keys
        item_schema = schema.get('item_schema', {})
        for req in item_schema.get('required', []):
            if req not in block:
                print(f"Schema Error: {domain}[{idx}] missing required key '{req}'")
                return False
        
        # Validate columns
        columns = block.get('columns', {})
        if not isinstance(columns, dict):
             print(f"Schema Error: {domain}[{idx}].columns must be a dict.")
             return False
             
        for col_name, col_def in columns.items():
            # col_def must be dict usually, but we allow simple strings in some legacy?
            # Schema says dict.
            if not isinstance(col_def, dict):
                 # Legacy: mapped directly?
                 # Ignoring for strict schema
                 pass
            else:
                 # Check properties
                 pass # Detailed prop check can be added
                 
    return True

def _validate_findings(domain, config, schema, definitions):
    # Validate required
    for req in schema.get('required', []):
        if req not in config:
            print(f"Schema Error: {domain} missing required key '{req}'")
            return False

    # Validate Columns List
    cols = config.get('columns', [])
    if not isinstance(cols, list):
        print(f"Schema Error: {domain}.columns must be a list.")
        return False
        
    col_schema = definitions['column_findings']
    for idx, col in enumerate(cols):
        if not isinstance(col, dict):
             print(f"Schema Error: {domain}.columns[{idx}] must be a dict.")
             return False
             
        # Check required
        for req in col_schema.get('required', []):
            if req not in col:
                 print(f"Schema Error: {domain}.columns[{idx}] missing '{req}'")
                 return False

    return True
