import pandas as pd

def get_last_participation_date(usubjid_series, built_domains=None, **kwargs):
    """
    Calculates RFENDTC (Reference End Date).
    Finds the absolute maximum date across specified domains and date columns
    for each subject.
    
    kwargs:
      domain_dates: dictionary mapping domain names to a list of date columns to check.
                    Defaults to scanning DS, EX, AE, and SV.
    """
    if not built_domains:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
        
    # Default domains and columns to scan if not explicitly provided
    domain_dates = kwargs.get("domain_dates", {
        "DS": ["DSSTDTC"],
        "EX": ["EXSTDTC", "EXENDTC"],
        "EC": ["ECSTDTC", "ECENDTC"],
        "AE": ["AESTDTC", "AEENDTC"],
        "SV": ["SVSTDTC", "SVENDTC"]
    })
    
    dfs = []
    
    for domain, cols in domain_dates.items():
        df = built_domains.get(domain)
        if df is not None and not df.empty and "USUBJID" in df.columns:
            # For each specified date column, melt it down so we can find the global max
            for col in cols:
                if col in df.columns:
                    valid = df[["USUBJID", col]].dropna(subset=[col]).rename(columns={col: "DATE"})
                    dfs.append(valid)
                    
    if not dfs:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
        
    combined = pd.concat(dfs, ignore_index=True)
    
    # Convert to datetime for mathematical maximum comparison
    combined["DATETIME"] = pd.to_datetime(combined["DATE"], errors='coerce', utc=True)
    combined = combined.dropna(subset=["DATETIME"])
    
    if combined.empty:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
        
    # Find the index of the max datetime per subject
    idx = combined.groupby("USUBJID")["DATETIME"].idxmax()
    
    # Extract the exact string (preserving any 'T' time component)
    res = combined.loc[idx].set_index("USUBJID")["DATE"]
    
    # Map back to the input series sequence
    return usubjid_series.map(res)
