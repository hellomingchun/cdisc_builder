import pandas as pd

class GeneralProcessor:
    def _expand_settings(self, settings):
        """
        Expands a settings dict with list-based sources/literals into multiple settings dicts.
        """
        # Find all columns that have a list for source or literal
        list_cols = {}
        list_len = 0
        
        columns = settings.get('columns', {})
        for col_name, col_cfg in columns.items():
            if isinstance(col_cfg, dict):
                src = col_cfg.get('source')
                lit = col_cfg.get('literal')
                
                # Check source
                if isinstance(src, list):
                    if list_len > 0 and len(src) != list_len:
                        raise ValueError(f"Column '{col_name}' source list length {len(src)} mismatch with others {list_len}")
                    list_len = len(src)
                    list_cols[col_name] = 'source'
                
                # Check literal
                if isinstance(lit, list):
                    if list_len > 0 and len(lit) != list_len:
                        raise ValueError(f"Column '{col_name}' literal list length {len(lit)} mismatch with others {list_len}")
                    list_len = len(lit)
                    list_cols[col_name] = 'literal'
                    
        if list_len == 0:
            return [settings]
            
        # Expand
        expanded_list = []
        for i in range(list_len):
            new_settings = settings.copy()
            new_cols = {}
            for col_name, col_cfg in columns.items():
                if isinstance(col_cfg, dict):
                    new_cfg = col_cfg.copy()
                    if col_name in list_cols:
                        param = list_cols[col_name] # 'source' or 'literal'
                         # Extract the i-th element
                        val_list = col_cfg.get(param)
                        new_cfg[param] = val_list[i]
                    new_cols[col_name] = new_cfg
                else:
                    new_cols[col_name] = col_cfg
            
            new_settings['columns'] = new_cols
            expanded_list.append(new_settings)
            
        return expanded_list

    def process(self, domain_name, sources, df_long, default_keys):
        domain_dfs = []
        
        # Pre-expand sources if they contain lists
        expanded_sources = []
        for s in sources:
            try:
                expanded_sources.extend(self._expand_settings(s))
            except Exception as e:
                print(f"Error expanding settings for {domain_name}: {e}")
                continue # Skip invalid blocks
        
        for settings in expanded_sources:
            # 1. Filter by FormOID
            form_oid = settings.get('formoid')
            if form_oid:
                try:
                    # Filter for specific FormOID(s)
                    if isinstance(form_oid, list):
                        source_df = df_long[df_long['FormOID'].isin(form_oid)].copy()
                    else:
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
                    fallback_expr = col_config.get('fallback')
                    literal_expr = col_config.get('literal')
                    target_type = col_config.get('type')
                    # Support value_mapping (primary) and mapping_value (legacy/typo support)
                    value_map = col_config.get('value_mapping') or col_config.get('mapping_value')
                    case_sensitive = col_config.get('case_sensitive', True)
                    group_cols = col_config.get('group')
                    sort_cols = col_config.get('sort_by')
                else:
                    source_expr = col_config
                    literal_expr = None
                    fallback_expr = None
                    value_map = None
                    case_sensitive = True
                    group_cols = None
                    sort_cols = None
                
                # Extract Data
                series = None
                
                # 0. Group-Based Sequence Generation (High Priority)
                if group_cols:
                    if not isinstance(group_cols, list):
                        group_cols = [group_cols]
                    
                    # Validate existence of group columns
                    missing_grp = [c for c in group_cols if c not in final_df.columns]
                    if missing_grp:
                        print(f"Warning: Group columns {missing_grp} not found in final_df for '{domain_name}.{target_col}'. SEQ generation skipped.")
                        series = pd.Series([None] * len(pivoted))
                    else:
                        # Create temp DataFrame for sorting/grouping
                        # We use final_df columns. We need to preserve index alignment.
                        # final_df is currently built row-by-row matching pivoted's rows.
                        temp_df = final_df[group_cols].copy()
                        
                        sort_keys = group_cols[:] # Always sort by group first
                        
                        if sort_cols:
                            if not isinstance(sort_cols, list):
                                sort_cols = [sort_cols]
                                
                            missing_sort = [c for c in sort_cols if c not in final_df.columns]
                            if missing_sort:
                                print(f"Warning: Sort columns {missing_sort} not found for '{domain_name}.{target_col}'. using partial/no sort.")
                            else:
                                for c in sort_cols:
                                    temp_df[c] = final_df[c]
                                sort_keys.extend(sort_cols)
                        
                        # Sort
                        temp_df = temp_df.sort_values(by=sort_keys)
                        
                        # Calculate Cumcount + 1
                        seq_series = temp_df.groupby(group_cols).cumcount() + 1
                        
                        # Map back to original index
                        series = seq_series.sort_index()

                elif literal_expr is not None:
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

                # Apply Fallback
                if fallback_expr:
                    fallback_series = None
                    if fallback_expr in pivoted.columns:
                        fallback_series = pivoted[fallback_expr]
                    elif fallback_expr in final_df.columns:
                        fallback_series = final_df[fallback_expr]
                    
                    if fallback_series is not None:
                        series = series.fillna(fallback_series)
                    else:
                         print(f"Warning: Fallback column '{fallback_expr}' not found for '{domain_name}.{target_col}'")
                
                # Apply Dependency Logic (Assign only if dependency column is not null)
                dependency = col_config.get('dependency') if isinstance(col_config, dict) else None
                if dependency:
                    dep_series = None
                    if dependency in pivoted.columns:
                        dep_series = pivoted[dependency]
                    elif dependency in final_df.columns:
                        dep_series = final_df[dependency]
                    
                    if dep_series is not None:
                         # Mask: Keep values where dependency is NOT null, else fill with False Value (default None)
                         false_val = col_config.get('dependency_false_value')
                         # Make sure false_val is treated as literal of correct type? pandas usually handles mixed.
                         
                         series = series.where(dep_series.notna(), false_val)
                    else:
                         print(f"Warning: Dependency column '{dependency}' not found for '{domain_name}.{target_col}'. Treating as all-null dependency.")
                         false_val = col_config.get('dependency_false_value')
                         series = pd.Series([false_val] * len(pivoted))
                
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
                    # Perform mapping
                    if not case_sensitive:
                         # Case Insensitive Mapping
                         # Clean map of nulls if needed, then lowercase keys
                         clean_map = {k: v for k, v in value_map.items()}
                         lower_map = {str(k).lower(): v for k, v in clean_map.items()}
                         
                         # Convert series to lower for mapping lookup
                         series_lower = series.astype(str).str.lower()
                         mapped_series = series_lower.map(lower_map)
                    else:
                         # Strict mapping
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
                         # Partial replacement (keep original values if not in map)
                         # If strict, .map() gave NaNs. combine_first puts original back.
                         if not case_sensitive:
                             # For case insensitive, mapped_series has mapped values or NaN. 
                             # We fill NaN with original series.
                             series = mapped_series.combine_first(series)
                         else:
                             # For strict, .replace() behavior is desired (partial)
                             # series.map() returns NaNs for non-matches.
                             # series.replace() keeps originals.
                             # But valid map might map VALID keys to None/NaN. 
                             # So using replace() is safer for partial.
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
                        elif target_type == 'date':
                            # Convert to datetime objects (handles multiple formats) then Format to YYYY-MM-DD string
                            series = pd.to_datetime(series, errors='coerce', format='mixed').dt.strftime('%Y-%m-%d')
                    except Exception as e:
                        print(f"Error converting {target_col} to {target_type}: {e}")

                final_df[target_col] = series
                
                # Store merge configuration
                final_df.attrs['merge_on'] = settings.get('merge_on')
                
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
