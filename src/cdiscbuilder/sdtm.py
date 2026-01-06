import pandas as pd
from .engine.config import load_config
from .engine.processor import process_domain

def create_sdtm_datasets(config_input, input_csv, output_dir):
    if isinstance(config_input, dict):
        config = config_input
        # We assume it's already structured correctly or validated
    else:
        config = load_config(config_input)
    
    # Get global defaults
    default_keys = config.get('defaults', {}).get('keys', ["StudyOID", "SubjectKey", "ItemGroupRepeatKey", "StudyEventOID"])

    print(f"Loading data from {input_csv}...")
    df_long = pd.read_csv(input_csv)

    for domain, settings_entry in config['domains'].items():
        print(f"DEBUG: Configured Domain: {domain}")
        print(f"Processing domain: {domain}")
        
        # Normalize to list.
        if isinstance(settings_entry, list):
            sources = settings_entry
        else:
            sources = [settings_entry]
            
        process_domain(domain, sources, df_long, default_keys, output_dir)


