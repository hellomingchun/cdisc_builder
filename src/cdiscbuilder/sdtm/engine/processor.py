import pandas as pd
import os

from .classes.general import GeneralProcessor
from .classes.interventions import InterventionsProcessor
from .classes.events import EventsProcessor
from .classes.findings import FindingsProcessor
from .classes.special_purpose import SpecialPurposeProcessor


def process_domain(domain_name, sources, df_long, default_keys, output_dir, custom_to_standard=None):
    # Normalize to list
    if isinstance(sources, dict):
        sources = [sources]

    if not sources:
        print(f"Warning: No configuration found for {domain_name}")
        return

    # Check type of first source to decide processor
    p_type = sources[0].get("type", "general").lower() if sources else "general"

    if p_type == "interventions":
        processor = InterventionsProcessor()
    elif p_type == "events":
        processor = EventsProcessor()
    elif p_type == "findings":
        processor = FindingsProcessor()
    elif p_type == "special_purpose":
        processor = SpecialPurposeProcessor()
    else:
        processor = GeneralProcessor()

    domain_dfs = processor.process(domain_name, sources, df_long, default_keys, custom_to_standard=custom_to_standard)

    if not domain_dfs:
        print(f"Warning: No data found for domain {domain_name}")
        return

    # Concatenate or Merge sources
    if not domain_dfs:
        return

    combined_df = domain_dfs[0]

    for i in range(1, len(domain_dfs)):
        current_df = domain_dfs[i]
        merge_on = current_df.attrs.get("merge_on")

        if merge_on:
            # Merge logic
            # Check if merge keys exist in both
            missing_keys = [
                k
                for k in merge_on
                if k not in combined_df.columns or k not in current_df.columns
            ]
            if missing_keys:
                print(
                    f"Warning: Cannot merge block {i} on {merge_on}, missing keys: {missing_keys}. Appending instead."
                )
                combined_df = pd.concat([combined_df, current_df], ignore_index=True)
            else:
                print(f"Merging block on {merge_on}")
                combined_df = combined_df.merge(
                    current_df, on=merge_on, how="left", suffixes=("", "_y")
                )

                cols_to_drop = [c for c in combined_df.columns if c.endswith("_y")]
                if cols_to_drop:
                    combined_df.drop(columns=cols_to_drop, inplace=True)
        else:
            # Default Append
            combined_df = pd.concat([combined_df, current_df], ignore_index=True)

    # Global Sequence Generation (Post-Process)
    # Scan all sources for columns with 'group' attribute
    seq_configs = {}
    for source in sources:
        mappings = source.get("columns", {})
        for col_name, col_cfg in mappings.items():
            if isinstance(col_cfg, dict) and col_cfg.get("group"):
                seq_configs[col_name] = col_cfg

    for target_col, col_config in seq_configs.items():
        group_cols = col_config.get("group")
        sort_cols = col_config.get("sort_by")

        order_cfg = col_config.get("order")

        if not isinstance(group_cols, list):
            group_cols = [group_cols]

        missing_grp = [c for c in group_cols if c not in combined_df.columns]
        if missing_grp:
            print(
                f"Warning: Group cols {missing_grp} missing for GLOBAL SEQ {target_col}"
            )
            continue

        # Create sort view
        temp_df = combined_df[group_cols].copy()
        sort_keys = group_cols[:]
        
        # Determine sorting order (ascending by default)
        ascending_list = [True] * len(group_cols)

        if sort_cols:
            if not isinstance(sort_cols, list):
                sort_cols = [sort_cols]
            missing_sort = [c for c in sort_cols if c not in combined_df.columns]
            if not missing_sort:
                for c in sort_cols:
                    temp_df[c] = combined_df[c]
                sort_keys.extend(sort_cols)
                
                # Apply custom order if provided
                if order_cfg:
                    if not isinstance(order_cfg, list):
                        order_cfg = [order_cfg]
                    
                    # Map "asc"/"desc" to True/False for the sort_cols
                    for o in order_cfg:
                        if str(o).lower() in ["desc", "descending", "false"]:
                            ascending_list.append(False)
                        else:
                            ascending_list.append(True)
                else:
                    ascending_list.extend([True] * len(sort_cols))

        # Sort
        temp_df = temp_df.sort_values(by=sort_keys, ascending=ascending_list)
        # Cumcount + 1
        seq_series = temp_df.groupby(group_cols, sort=False).cumcount() + 1
        # Re-align to combined_df index
        combined_df[target_col] = seq_series.sort_index()

    # Save to Parquet
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_path = os.path.join(output_dir, f"{domain_name.lower()}.parquet")
    combined_df.to_parquet(output_path, index=False)
    print(f"Saved {domain_name} to {output_path} (Shape: {combined_df.shape})")
