import pandas as pd
import os
from .classes.general import GeneralProcessor


def process_domain(domain_name, sources, df_long, default_keys, output_dir):
    # Determine type of the first block (assumes all blocks in a domain are same type)
    # process_domain receives 'sources' which is settings_entry.
    
    # Normalize to list
    if isinstance(sources, dict):
        sources = [sources]
        
    if not sources:
        print(f"Warning: No configuration found for {domain_name}")
        return

    from .classes.finding import FindingProcessor

    # Check type of first source to decide processor
    p_type = sources[0].get('type', 'general') if sources else 'general'

    if p_type == 'finding':
        processor = FindingProcessor()
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
