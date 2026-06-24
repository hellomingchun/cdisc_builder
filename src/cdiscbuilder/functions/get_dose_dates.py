import pandas as pd

def _get_dose_date(usubjid_series, built_domains, mode="first", **kwargs):
    """
    Core logic to find the first or last dose date from EX or EC domains
    where the dose > 0.
    """
    if not built_domains:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
        
    ex_df = built_domains.get("EX")
    ec_df = built_domains.get("EC")
    
    # Get custom dose column names if provided in kwargs
    ex_dose_col = kwargs.get("ex_dose_col", "EXDOSE")
    ec_dose_col = kwargs.get("ec_dose_col", "ECDOSE")
    
    dfs = []
    
    # Process EX
    if ex_df is not None and not ex_df.empty:
        if "USUBJID" in ex_df.columns:
            date_col = "EXSTDTC" if mode == "first" else "EXENDTC"
            if date_col in ex_df.columns:
                valid = ex_df
                if ex_dose_col in ex_df.columns:
                    dose = pd.to_numeric(ex_df[ex_dose_col], errors='coerce')
                    valid = ex_df[dose > 0]
                dfs.append(valid[["USUBJID", date_col]].rename(columns={date_col: "DATE"}))
                
    # Process EC
    if ec_df is not None and not ec_df.empty:
        if "USUBJID" in ec_df.columns:
            date_col = "ECSTDTC" if mode == "first" else "ECENDTC"
            if date_col in ec_df.columns:
                valid = ec_df
                if ec_dose_col in ec_df.columns:
                    dose = pd.to_numeric(ec_df[ec_dose_col], errors='coerce')
                    valid = ec_df[dose > 0]
                dfs.append(valid[["USUBJID", date_col]].rename(columns={date_col: "DATE"}))
                
    if not dfs:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
        
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.dropna(subset=["DATE"])
    
    if combined.empty:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
    
    # Convert to proper datetime objects for robust chronological sorting
    # We do this to ensure "2026-05-01T08:00" and "2026-05-01" sort correctly as actual time
    # rather than just alphabetical strings.
    combined["DATETIME"] = pd.to_datetime(combined["DATE"], errors='coerce', utc=True)
    
    # Drop rows that couldn't be parsed as dates (e.g. completely invalid garbage)
    combined = combined.dropna(subset=["DATETIME"])
    
    if combined.empty:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
    
    # Find the index of the min/max datetime per subject
    if mode == "first":
        idx = combined.groupby("USUBJID")["DATETIME"].idxmin()
    else:
        idx = combined.groupby("USUBJID")["DATETIME"].idxmax()
        
    # Extract the original string format (with the 'T') using the found indices
    res = combined.loc[idx].set_index("USUBJID")["DATE"]
    
    # Map back to the exact input series sequence
    return usubjid_series.map(res)

def get_first_dose_date(usubjid_series, built_domains=None, **kwargs):
    """
    Calculates RFXSTDTC (First Study Treatment Date).
    Extracts minimum start date from EX or EC domains where dose > 0.
    """
    return _get_dose_date(usubjid_series, built_domains, mode="first", **kwargs)
    
def get_last_dose_date(usubjid_series, built_domains=None, **kwargs):
    """
    Calculates RFXENDTC (Last Study Treatment Date).
    Extracts maximum end date from EX or EC domains where dose > 0.
    """
    return _get_dose_date(usubjid_series, built_domains, mode="last", **kwargs)
