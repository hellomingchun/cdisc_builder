import pandas as pd


def calculate_study_day(date_series, rfstdtc_series):
    """
    Calculates SDTM Study Day (--DY).
    SDTM Rule:
    - If date is on or after RFSTDTC: (date - RFSTDTC) + 1
    - If date is before RFSTDTC: (date - RFSTDTC)
    - There is no Day 0.
    """
    # Convert to datetime
    d = pd.to_datetime(date_series, errors="coerce")
    rf = pd.to_datetime(rfstdtc_series, errors="coerce")

    # Calculate difference in days
    # Note: Using .dt.days to get integer difference
    diff = (d - rf).dt.days

    # Apply SDTM rules (no Day 0)
    # x + 1 if x >= 0 else x
    dy = diff.apply(lambda x: (x + 1) if pd.notnull(x) and x >= 0 else x)
    return dy
