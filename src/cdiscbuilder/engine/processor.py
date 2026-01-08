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

    # Global Sequence Generation (Post-Process)
    # Scan all sources for columns with 'group' attribute
    seq_configs = {}
    for source in sources:
        mappings = source.get('columns', {})
        for col_name, col_cfg in mappings.items():
            if isinstance(col_cfg, dict) and col_cfg.get('group'):
                # Store config. Overwrite if duplicate (assumes consistent config across blocks for same col)
                seq_configs[col_name] = col_cfg

    for target_col, col_config in seq_configs.items():
        group_cols = col_config.get('group')
        sort_cols = col_config.get('sort_by')
        
        if not isinstance(group_cols, list): group_cols = [group_cols]
        
        missing_grp = [c for c in group_cols if c not in combined_df.columns]
        if missing_grp:
             print(f"Warning: Group cols {missing_grp} missing for GLOBAL SEQ {target_col}")
             continue

        # Create sort view
        temp_df = combined_df[group_cols].copy()
        sort_keys = group_cols[:]
        
        if sort_cols:
            if not isinstance(sort_cols, list): sort_cols = [sort_cols]
            missing_sort = [c for c in sort_cols if c not in combined_df.columns]
            if not missing_sort:
                for c in sort_cols: temp_df[c] = combined_df[c]
                sort_keys.extend(sort_cols)
        
        # Sort
        temp_df = temp_df.sort_values(by=sort_keys)
        # Cumcount + 1
        seq_series = temp_df.groupby(group_cols).cumcount() + 1
        # Re-align to combined_df index
        combined_df[target_col] = seq_series.sort_index()
    
    # Save to Parquet
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_path = os.path.join(output_dir, f"{domain_name}.parquet")
    combined_df.to_parquet(output_path, index=False)
    print(f"Saved {domain_name} to {output_path} (Shape: {combined_df.shape})")
