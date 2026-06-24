import pandas as pd

def coalesce(*series_list, **kwargs):
    """
    Returns the first non-null value across a list of Pandas Series.
    Similar to SQL COALESCE.
    """
    if not series_list:
        raise ValueError("coalesce requires at least one argument")
        
    # Start with the first series
    result = series_list[0].copy()
    
    # Iterate through remaining series and fill missing values
    for s in series_list[1:]:
        # Ensure 's' is a Series (in case a literal was passed somehow, though general.py doesn't currently do that)
        if not isinstance(s, pd.Series):
            s = pd.Series([s] * len(result), index=result.index)
            
        result = result.combine_first(s)
        
    return result
