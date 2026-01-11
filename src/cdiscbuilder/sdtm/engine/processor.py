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
        
    # Concatenate or Merge sources
    if not domain_dfs:
        return

    combined_df = domain_dfs[0]
    
    for i in range(1, len(domain_dfs)):
        current_df = domain_dfs[i]
        merge_on = current_df.attrs.get('merge_on')
        
        if merge_on:
             # Merge logic
             # Check if merge keys exist in both
             missing_keys = [k for k in merge_on if k not in combined_df.columns or k not in current_df.columns]
             if missing_keys:
                 print(f"Warning: Cannot merge block {i} on {merge_on}, missing keys: {missing_keys}. Appending instead.")
                 combined_df = pd.concat([combined_df, current_df], ignore_index=True)
             else:
                 # Perform merge (left merge to keep base subjects, or outer?)
                 # Usually detailed info (Age) is added to base (Demog), so Left Merge is safer?
                 # Or Outer to include subjects only in Eligibility? CDISC implies DM comes from Demog.
                 # Let's use left join by default to preserve base population.
                 # Actually, if creating DM, we usually want all subjects.
                 # But if block 2 is just attributes, 'left' on block 1 is typical.
                 # Let's use 'left' but print info.
                 print(f"Merging block on {merge_on}")
                 combined_df = combined_df.merge(current_df, on=merge_on, how='left', suffixes=('', '_y'))
                 
                 # Drop duplicate columns ending in _y if they are not meaningful (or keep them?)
                 # Usually we don't want collisions.
                 cols_to_drop = [c for c in combined_df.columns if c.endswith('_y')]
                 if cols_to_drop:
                     combined_df.drop(columns=cols_to_drop, inplace=True)
        else:
             # Default Append
             combined_df = pd.concat([combined_df, current_df], ignore_index=True)

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
        
        if not isinstance(group_cols, list):
            group_cols = [group_cols]
        
        missing_grp = [c for c in group_cols if c not in combined_df.columns]
        if missing_grp:
             print(f"Warning: Group cols {missing_grp} missing for GLOBAL SEQ {target_col}")
             continue

        # Create sort view
        temp_df = combined_df[group_cols].copy()
        sort_keys = group_cols[:]
        
        if sort_cols:
            if not isinstance(sort_cols, list):
                sort_cols = [sort_cols]
            missing_sort = [c for c in sort_cols if c not in combined_df.columns]
            if not missing_sort:
                for c in sort_cols:
                    temp_df[c] = combined_df[c]
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
