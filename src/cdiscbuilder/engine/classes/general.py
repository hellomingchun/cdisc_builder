import pandas as pd

class GeneralProcessor:
    def process(self, domain_name, sources, df_long, default_keys):
        domain_dfs = []
        
        for settings in sources:
            # 1. Filter by FormOID
            form_oid = settings.get('formoid')
            if form_oid:
                try:
                    # Filter for specific FormOID
                    source_df = df_long[df_long['FormOID'] == form_oid].copy()
                except Exception as e:
                    print(f"Error filtering for {domain_name} (FormOID={form_oid}): {e}")
                    continue
            else:
                print(f"Warning: No formoid specified for a block in {domain_name}")
                continue
                
            if source_df.empty:
                continue

            # 2. Key columns for pivoting (use block keys or defaults)
            keys = settings.get('keys', default_keys)
            
            # 3. Pivot
            try:
                pivoted = source_df.pivot_table(
                    index=keys, 
                    columns='ItemOID', 
                    values='Value', 
                    aggfunc='first'
                ).reset_index()
            except Exception as e:
                print(f"Error pivoting for {domain_name}: {e}")
                continue
                
            # 4. Map columns
            final_df = pd.DataFrame()
            mappings = settings.get('columns', {})
            
            for target_col, col_config in mappings.items():
                source_expr = None
                literal_expr = None
                target_type = None
                value_map = None

                # Check if simple string or object config
                if isinstance(col_config, dict):
                    source_expr = col_config.get('source')
                    literal_expr = col_config.get('literal')
                    target_type = col_config.get('type')
                    value_map = col_config.get('value_mapping')
                else:
                    source_expr = col_config
                    literal_expr = None
                
                # Extract Data
                series = None
                if literal_expr is not None:
                    # Explicit literal value
                    series = pd.Series([literal_expr] * len(pivoted))
                elif source_expr:
                    if source_expr in pivoted.columns:
                        series = pivoted[source_expr].copy()
                    elif source_expr in final_df.columns:
                        series = final_df[source_expr].copy()
                    else:
                        # Source defined but not found.
                        print(f"Warning: Source column '{source_expr}' not found for '{domain_name}.{target_col}'. Filling with NaN.")
                        series = pd.Series([None] * len(pivoted))
                else:
                    print(f"Warning: No source or literal defined for '{domain_name}.{target_col}'. Filling with NaN.")
                    series = pd.Series([None] * len(pivoted))
                
                # Apply Substring Extraction (Before Value Mapping)
                if isinstance(col_config, dict):
                    sub_start = col_config.get('substring_start')
                    sub_len = col_config.get('substring_length')
                    if sub_start is not None and sub_len is not None:
                        # Ensure series is string
                        series = series.astype(str)
                        # Slice 0-indexed or 1-indexed? Python is 0-indexed.
                        # User said "position 3-5". If string is '1110023565' and target is '002',
                        # indices are 3,4,5. So slice[3:6].
                        # Let's assume user provides 0-based start index and length.
                        series = series.str[sub_start : sub_start + sub_len]

                # Apply Value Mapping
                mapping_default = col_config.get('mapping_default') if isinstance(col_config, dict) else None
                mapping_default_source = col_config.get('mapping_default_source') if isinstance(col_config, dict) else None

                if value_map:
                    # Perform mapping (non-matches become NaN)
                    mapped_series = series.map(value_map)
                    
                    if mapping_default is not None:
                         # Strict mapping with default literal
                         series = mapped_series.fillna(mapping_default)
                    elif mapping_default_source is not None:
                         # Strict mapping with default from another column
                         fallback = None
                         if mapping_default_source in final_df.columns:
                             fallback = final_df[mapping_default_source]
                         elif mapping_default_source in pivoted.columns:
                             fallback = pivoted[mapping_default_source]
                        
                         if fallback is not None:
                             series = mapped_series.fillna(fallback)
                         else:
                             print(f"Warning: Default source '{mapping_default_source}' not found for '{domain_name}.{target_col}'")
                             series = mapped_series # Leave as NaN or original? mapped_series has NaNs.
                    else:
                         # Partial replacement (legacy: keep original values if not in map)
                         series = series.replace(value_map)

                # Apply Prefix
                prefix = col_config.get('prefix') if isinstance(col_config, dict) else None
                if prefix:
                    series = prefix + series.astype(str)

                # Apply Type Conversion
                if target_type:
                    try:
                        if target_type == 'int':
                            series = pd.to_numeric(series, errors='coerce').astype('Int64')
                        elif target_type == 'float':
                             series = pd.to_numeric(series, errors='coerce')
                        elif target_type == 'str':
                            series = series.astype(str)
                        elif target_type == 'bool':
                            series = series.astype(bool)
                    except Exception as e:
                        print(f"Error converting {target_col} to {target_type}: {e}")

                final_df[target_col] = series
                
                # Validation: max_missing_pct
                if isinstance(col_config, dict):
                    max_missing = col_config.get('max_missing_pct')
                    if max_missing is not None:
                        missing_count = series.isna().sum()
                        if target_type == 'str':
                             missing_count += (series.isin(['nan', 'None'])).sum()
                        
                        total = len(series)
                        if total > 0:
                            pct = (missing_count / total) * 100
                            if pct > max_missing:
                                print(f"WARNING: [Validation] {domain_name}.{target_col} missing {pct:.2f}% (Limit: {max_missing:})")
            
            domain_dfs.append(final_df)
            
        return domain_dfs
