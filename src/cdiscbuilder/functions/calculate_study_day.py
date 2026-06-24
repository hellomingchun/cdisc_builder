import pandas as pd


def calculate_study_day(date_series, rfstdtc_series):
    """
    Calculates SDTM Study Day (--DY).
    SDTM Rule:
    - If date is on or after RFSTDTC: (date - RFSTDTC) + 1
    - If date is before RFSTDTC: (date - RFSTDTC)
    - There is no Day 0.
    - Partial dates (missing day or month) cannot be used to calculate study day.
    """
    # Filter out partial dates (ISO 8601 YYYY-MM-DD is at least 10 chars)
    # This prevents pd.to_datetime from assuming the 1st of the month for 'YYYY-MM'
    valid_d = date_series.where(date_series.astype(str).str.len() >= 10)
    valid_rf = rfstdtc_series.where(rfstdtc_series.astype(str).str.len() >= 10)
    
    # Convert to datetime (utc=True prevents tz-naive/tz-aware subtraction issues if times exist)
    d = pd.to_datetime(valid_d, errors="coerce", utc=True)
    rf = pd.to_datetime(valid_rf, errors="coerce", utc=True)

    # Normalize to midnight to remove time components safely
    d = d.dt.normalize()
    rf = rf.dt.normalize()

    # Calculate difference in days
    diff = (d - rf).dt.days

    # Apply SDTM rules (no Day 0)
    dy = diff.apply(lambda x: (x + 1) if pd.notnull(x) and x >= 0 else x)
    
    # Cast to Int64 (nullable integer)
    return dy.astype("Int64")
