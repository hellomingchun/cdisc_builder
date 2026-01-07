import pandas as pd


class FindingProcessor:
    def __init__(self):
        pass

    def process(self, domain_name, sources, df_long, default_keys):
        domain_dfs = []
        
        for settings in sources:
            # 0. Filter by FormOID (optional but recommended)
            form_oid = settings.get('formoid')
            source_df = df_long.copy()
            if form_oid:
                if isinstance(form_oid, list):
                    source_df = source_df[source_df['FormOID'].isin(form_oid)]
                else:
                    source_df = source_df[source_df['FormOID'] == form_oid]
            
            # 1. Filter by ItemGroupOID (regex or list)
            item_group_match = settings.get('item_group_regex')
            if item_group_match:
                 source_df = source_df[source_df['ItemGroupOID'].str.match(item_group_match, na=False)]
            
            # 2. Filter by ItemOID (regex)
            # This is crucial for "finding" domains - we want rows where ItemOID matches a pattern
            item_oid_match = settings.get('item_oid_regex')
            if item_oid_match:
                source_df = source_df[source_df['ItemOID'].str.match(item_oid_match, na=False)]
            
            if source_df.empty:
                continue
                
            # 3. Create Base DataFrame (No Pivot!)
            # 3. Create Base DataFrame (No Pivot!)
            # We treat every row as a potential finding
            # Base columns: Keys + ItemOID + Value
            keys = settings.get('keys', default_keys)
            
            # Check if Question exists in source_df (it should based on odm.py changes)
            base_cols = keys + ['ItemOID', 'Value']
            if 'Question' in source_df.columns:
                 base_cols.append('Question')

            final_df = source_df[base_cols].copy()
            
            # 4. Map Columns
            mappings = settings.get('columns', {})
            
            for target_col, col_config in mappings.items():
                series = None
                
                # Config can be simple string (source col) or dict
                source_expr = None
                literal_expr = None
                target_type = None
                regex_extract = None
                
                if isinstance(col_config, dict):
                    source_expr = col_config.get('source')
                    literal_expr = col_config.get('literal')
                    target_type = col_config.get('type')
                    regex_extract = col_config.get('regex_extract') # e.g. "I_ELIGI_(.*)"
                else:
                    source_expr = col_config # simplistic
                
                if literal_expr is not None:
                     series = pd.Series([literal_expr] * len(final_df), index=final_df.index)
                
                elif source_expr:
                    if source_expr == "ItemOID":
                        series = final_df['ItemOID']
                    elif source_expr == "Value":
                        series = final_df['Value']
                    elif source_expr in final_df.columns:
                        series = final_df[source_expr]
                    elif source_expr in source_df.columns:
                         series = source_df[source_expr]
                    
                    # Regex Extraction from source
                    if regex_extract and series is not None:
                         # Extract group 1
                         series = series.astype(str).str.extract(regex_extract)[0]
                
                # Apply Prefix
                prefix = None
                if isinstance(col_config, dict):
                    prefix = col_config.get('prefix')
                
                if prefix and series is not None:
                    series = prefix + series.astype(str)
                
                if series is not None:
                    # Type Conversion
                    if target_type:
                        try:
                            if target_type == 'int':
                                series = pd.to_numeric(series, errors='coerce').astype('Int64')
                            elif target_type == 'str':
                                series = series.astype(str)
                        except Exception:
                            pass
                    
                    final_df[target_col] = series
            
            # Filter to keep only target columns
            cols_to_keep = list(mappings.keys())
            final_df = final_df[cols_to_keep]
            
            domain_dfs.append(final_df)
            
        return domain_dfs
