import pandas as pd
import os

from .classes.general import GeneralProcessor
from .classes.interventions import InterventionsProcessor
from .classes.events import EventsProcessor
from .classes.findings import FindingsProcessor
from .classes.special_purpose import SpecialPurposeProcessor


def _build_supp_dataset(domain_name, parent_df, supp_config):
    """
    Transpose supplemental qualifier columns from the parent domain into SUPP-- format.

    Args:
        domain_name: Parent domain abbreviation (e.g., "AE").
        parent_df: The fully-built parent domain DataFrame.
        supp_config: The 'supp' configuration dict from the YAML.

    Returns:
        A DataFrame in the standard SUPP-- tall structure, or None if no data.
    """
    idvar = supp_config.get("idvar")

    studyid_col = supp_config.get("studyid", "STUDYID")
    usubjid_col = supp_config.get("usubjid", "USUBJID")
    qorig = supp_config.get("qorig", "CRF")
    qeval = supp_config.get("qeval", "")

    supp_columns = supp_config.get("columns", {})
    if not supp_columns:
        print(f"Warning: SUPP{domain_name} config has no columns defined. Skipping.")
        return None

    # Validate that required ID columns exist in the parent
    required_cols = [(studyid_col, "studyid"), (usubjid_col, "usubjid")]
    if idvar:
        required_cols.append((idvar, "idvar"))
        
    for required_col, col_label in required_cols:
        if required_col not in parent_df.columns:
            print(f"Warning: SUPP{domain_name} requires '{required_col}' ({col_label}) but it is missing from parent domain. Skipping.")
            return None

    # Build the qualifier DataFrame from parent columns
    id_cols = [studyid_col, usubjid_col]
    if idvar:
        id_cols.append(idvar)
    qual_df = parent_df[id_cols].copy()

    resolved_qnam_cols = []
    qlabel_map = {}
    qorig_map = {}
    qeval_map = {}

    for qnam, qcfg in supp_columns.items():
        if isinstance(qcfg, str):
            qcfg = {"source": qcfg}

        label = qcfg.get("label", qnam)
        qlabel_map[qnam] = label
        
        qorig_map[qnam] = qcfg.get("qorig", qorig)
        qeval_map[qnam] = qcfg.get("qeval", qeval)

        # Resolve qualifier value
        if qnam in parent_df.columns:
            # Column already mapped in parent domain
            qual_df[qnam] = parent_df[qnam]
            resolved_qnam_cols.append(qnam)
        else:
            source_col = qcfg.get("source")
            literal_val = qcfg.get("literal")

            if source_col and source_col in parent_df.columns:
                qual_df[qnam] = parent_df[source_col]
                resolved_qnam_cols.append(qnam)
            elif literal_val is not None:
                qual_df[qnam] = literal_val
                resolved_qnam_cols.append(qnam)
            else:
                print(f"Warning: SUPP{domain_name}.{qnam} could not be resolved from parent domain. Skipping this qualifier.")

    if not resolved_qnam_cols:
        print(f"Warning: No qualifier columns could be resolved for SUPP{domain_name}. Skipping.")
        return None

    # Melt qualifier columns into tall format
    supp_tall = qual_df.melt(
        id_vars=id_cols,
        value_vars=resolved_qnam_cols,
        var_name="QNAM",
        value_name="QVAL",
    )

    # Drop rows where QVAL is blank/null
    supp_tall = supp_tall.dropna(subset=["QVAL"])
    supp_tall = supp_tall[supp_tall["QVAL"].astype(str).str.strip() != ""]

    if supp_tall.empty:
        return None

    # Assemble final SUPP-- structure
    result = pd.DataFrame(
        {
            "STUDYID": supp_tall[studyid_col].values,
            "RDOMAIN": domain_name.upper(),
            "USUBJID": supp_tall[usubjid_col].values,
            "IDVAR": idvar if idvar else "",
            "IDVARVAL": supp_tall[idvar].astype(str).values if idvar else "",
            "QNAM": supp_tall["QNAM"].values,
            "QLABEL": supp_tall["QNAM"].map(qlabel_map).values,
            "QVAL": supp_tall["QVAL"].astype(str).values,
            "QORIG": supp_tall["QNAM"].map(qorig_map).values,
            "QEVAL": supp_tall["QNAM"].map(qeval_map).values,
        }
    )

    return result


def process_domain(domain_name, sources, df_long, default_keys, output_dir, custom_to_standard=None, built_domains=None, form_mapping=None):
    # Normalize to list
    if isinstance(sources, dict):
        sources = [sources]

    if not sources:
        print(f"Warning: No configuration found for {domain_name}")
        return None

    # Separate SUPP blocks from regular source blocks
    supp_config = None
    regular_sources = []
    for s in sources:
        if "supp" in s:
            supp_config = s["supp"]
        else:
            regular_sources.append(s)

    if not regular_sources:
        print(f"Warning: No configuration found for {domain_name}")
        return None

    # Check type of first source to decide processor
    p_type = regular_sources[0].get("type", "general").lower() if regular_sources else "general"

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

    domain_dfs = processor.process(domain_name, regular_sources, df_long, default_keys, custom_to_standard=custom_to_standard, built_domains=built_domains, form_mapping=form_mapping)

    if not domain_dfs:
        print(f"Warning: No data found for domain {domain_name}")
        return None

    # Concatenate or Merge sources
    if not domain_dfs:
        return None

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
    for source in regular_sources:
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

    # SUPP-- Domain Generation (Post-Process)
    if supp_config:
        supp_df = _build_supp_dataset(domain_name, combined_df, supp_config)

        if supp_df is not None:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            supp_path = os.path.join(output_dir, f"supp{domain_name.lower()}.parquet")
            supp_df.to_parquet(supp_path, index=False)
            print(f"Saved SUPP{domain_name} to {supp_path} (Shape: {supp_df.shape})")

        # Strip qualifier columns from parent output
        supp_col_names = list(supp_config.get("columns", {}).keys())
        cols_to_drop = [c for c in supp_col_names if c in combined_df.columns]
        if cols_to_drop:
            combined_df.drop(columns=cols_to_drop, inplace=True)

    # Save to Parquet
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_path = os.path.join(output_dir, f"{domain_name.lower()}.parquet")
    combined_df.to_parquet(output_path, index=False)
    print(f"Saved {domain_name} to {output_path} (Shape: {combined_df.shape})")

    return combined_df
