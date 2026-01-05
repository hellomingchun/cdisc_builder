import pandas as pd
import os
from .classes.general import GeneralProcessor
from .classes.findings import FindingsProcessor

def process_domain(domain_name, sources, df_long, default_keys, output_dir):
    # Determine type of the first block (assumes all blocks in a domain are same type)
    # New config schema: type at top level, or implied. 
    # Actually, config structure is usually:
    # DOMAIN: 
    #   - list of sources
    # In my new design for Findings, it was:
    # FA:
    #   type: FINDINGS
    # This structure is different from the list of blocks.
    # Let's see how load_config returns it.
    
    # If the user uses the new "dict" structure for FA, load_config needs to handle it.
    # Currently load_config merges dicts. 
    # If FA.yaml contains:
    # FA: {type: FINDINGS, ...}   <- Dict, not list
    # DM.yaml contains:
    # DM: [{...}, {...}]          <- List
    
    # process_domain receives 'sources' which is settings_entry.
    
    # Normalize to list
    if isinstance(sources, dict):
        sources = [sources]
        
    if not sources:
        print(f"Warning: No configuration found for {domain_name}")
        return

    # Determine type from the first block
    first_block = sources[0]
    domain_type = first_block.get('type', "GENERAL")
    
    processor = None
    if domain_type == 'FINDINGS':
        # Locate metadata relative to package
        # Assuming structure: sdtm_engine/processor.py -> ../metadata/test_codes.yaml
        # Base dir is parent of sdtm_engine? No, sdtm_engine is in src/cdisc_datasets/
        # metadata is in src/cdisc_datasets/metadata
        
        current_dir = os.path.dirname(__file__) # src/cdisc_builder/engine
        package_root = os.path.dirname(current_dir) # src/cdisc_builder
        metadata_path = os.path.join(package_root, "metadata", "test_codes.yaml")
        
        processor = FindingsProcessor(metadata_path)
    else:
        processor = GeneralProcessor()

    domain_dfs = processor.process(domain_name, sources, df_long, default_keys)

    if not domain_dfs:
        print(f"Warning: No data found for domain {domain_name}")
        return
        
    # Concatenate all sources for this domain
    combined_df = pd.concat(domain_dfs, ignore_index=True)
    
    # Save to Parquet
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_path = os.path.join(output_dir, f"{domain_name}.parquet")
    combined_df.to_parquet(output_path, index=False)
    print(f"Saved {domain_name} to {output_path} (Shape: {combined_df.shape})")
