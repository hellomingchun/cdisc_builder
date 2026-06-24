import pandas as pd

def get_earliest_informed_consent_date(usubjid_series, built_domains=None, df_long=None, **kwargs):
    """
    Calculates RFICDTC (Date/Time of Informed Consent).
    Can scan the built DS domain OR raw df_long (to avoid circular dependencies).
    
    kwargs:
      raw_mode: bool. If True, searches df_long instead of built_domains (default: False)
      raw_formoid: If raw_mode=True, the FormOID to filter on (optional)
      term_col: The column (or ItemOID) to check for consent terms (default: 'DSDECOD' or 'DSTERM')
      consent_terms: List of terms indicating consent (default: ['INFORMED CONSENT OBTAINED'])
      date_col: The date column (or ItemOID) to extract (default: 'DSSTDTC' or 'DSSTDAT')
    """
    raw_mode = kwargs.get("raw_mode", False)
    consent_terms = kwargs.get("consent_terms", ["INFORMED CONSENT OBTAINED"])
    upper_terms = [t.upper() for t in consent_terms]
    
    if raw_mode:
        if df_long is None or df_long.empty:
            return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
            
        term_col = kwargs.get("term_col", "DSTERM")
        date_col = kwargs.get("date_col", "DSSTDAT")
        formoid = kwargs.get("raw_formoid")
        
        subset = df_long
        if formoid:
            subset = df_long[df_long["FormOID"] == formoid]
            
        # We need to find the SubjectKey where term_col has a consent term
        term_mask = (subset["ItemOID"] == term_col) & (subset["Value"].astype(str).str.upper().isin(upper_terms))
        consent_subjects = subset[term_mask]["SubjectKey"].unique()
        
        # Now find the date_col for those subjects
        # Wait, if multiple repeats exist, we should match on ItemGroupRepeatKey too
        # To keep it robust, let's just get all date_cols for those subjects on that form
        # and take the minimum date.
        date_mask = (subset["ItemOID"] == date_col) & (subset["SubjectKey"].isin(consent_subjects))
        valid = subset[date_mask].copy()
        
        if valid.empty:
            return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
            
        valid["DATETIME"] = pd.to_datetime(valid["Value"], errors='coerce', utc=True)
        valid = valid.dropna(subset=["DATETIME"])
        
        if valid.empty:
            return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
            
        idx = valid.groupby("SubjectKey")["DATETIME"].idxmin()
        # Map raw SubjectKey to our usubjid_series (assuming USUBJID ends with SubjectKey)
        # Note: In CDISC, USUBJID = STUDYID-SubjectKey.
        # But this function receives usubjid_series, so we might need to map via raw SubjectKey.
        # Instead, let's just match SubjectKey directly.
        res = valid.loc[idx].set_index("SubjectKey")["Value"]
        
        # Because usubjid_series is standard USUBJID (e.g. 'STUDY-001'), we need to strip study to match
        # Let's extract the subject key from the end
        subject_keys_from_usubjid = usubjid_series.astype(str).str.split("-").str[-1]
        mapped = subject_keys_from_usubjid.map(res)
        return mapped

    # --- BUILT DOMAIN MODE ---
    if not built_domains:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
        
    ds = built_domains.get("DS")
    if ds is None or ds.empty or "USUBJID" not in ds.columns:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
        
    term_col = kwargs.get("term_col", "DSDECOD")
    date_col = kwargs.get("date_col", "DSSTDTC")
    
    if term_col not in ds.columns or date_col not in ds.columns:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
        
    mask = ds[term_col].astype(str).str.upper().isin(upper_terms)
    valid = ds[mask].copy()
    
    if valid.empty:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
        
    valid["DATETIME"] = pd.to_datetime(valid[date_col], errors='coerce', utc=True)
    valid = valid.dropna(subset=["DATETIME"])
    
    if valid.empty:
        return pd.Series([None] * len(usubjid_series), index=usubjid_series.index)
        
    idx = valid.groupby("USUBJID")["DATETIME"].idxmin()
    res = valid.loc[idx].set_index("USUBJID")[date_col]
    
    return usubjid_series.map(res)
