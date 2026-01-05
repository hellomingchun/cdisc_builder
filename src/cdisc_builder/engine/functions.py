import pandas as pd

def extract_value(df_long, form_oids, item_oids, return_col='Value', keys=None):
    """
    Generic extraction function for Findings.
    Args:
        df_long: The source long format dataframe.
        form_oids: List of FormOIDs to filter.
        item_oids: List (or single string) of ItemOIDs to filter.
        return_col: 'Value' (default) or 'ItemOID'. What to return as the column data.
        keys: List of key columns to include/index by.
    Returns:
        DataFrame containing Keys and the requested data column (renamed to 'Result' or similar).
    """
    # 1. Normalize inputs
    if isinstance(form_oids, str): form_oids = [form_oids]
    if isinstance(item_oids, str): item_oids = [item_oids]
    
    # 2. Filter Forms
    # Optimization: pre-filter df_long if passed repeatedly? 
    # For now, just filter.
    subset = df_long[df_long['FormOID'].isin(form_oids)].copy()
    
    if subset.empty:
        return pd.DataFrame()
        
    # 3. Filter Items
    # Note: If item_oids is empty/None, do we return everything? No, usually specific.
    if item_oids:
        subset = subset[subset['ItemOID'].isin(item_oids)]
    
    if subset.empty:
        return pd.DataFrame() # Return empty but valid DF?
        
    # 4. Select Columns
    # We always need Keys + the Return Col
    cols_to_keep = keys + [return_col] if keys else [return_col]
    
    # If keys are missing (logic error), handle gracefully
    available_cols = [c for c in cols_to_keep if c in subset.columns]
    result = subset[available_cols].copy()
    
    # 5. Rename return column for clarity? 
    # The caller will rename it to the target column (e.g. FAORRES).
    # But if return_col is 'Value' or 'ItemOID', we keep as is for now.
    
    return result
