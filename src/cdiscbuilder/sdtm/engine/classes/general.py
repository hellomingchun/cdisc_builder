import pandas as pd


class GeneralProcessor:
    def __init__(self):
        self._ct_cache = {}

    def _load_value_mapping(self, mapping_ref):
        import yaml
        import json
        from pathlib import Path

        parts = mapping_ref.split(":", 1)
        filepath = parts[0]
        key = parts[1] if len(parts) > 1 else None

        if filepath not in self._ct_cache:
            path = Path(filepath)
            if not path.is_absolute():
                path = Path.cwd() / filepath
            
            if not path.exists():
                print(f"Warning: value_mapping_from file {filepath} not found.")
                self._ct_cache[filepath] = {}
            else:
                try:
                    with open(path, "r") as f:
                        if filepath.endswith(".json"):
                            self._ct_cache[filepath] = json.load(f)
                        else:
                            self._ct_cache[filepath] = yaml.safe_load(f)
                except Exception as e:
                    print(f"Warning: Failed to load {filepath}: {e}")
                    self._ct_cache[filepath] = {}

        data = self._ct_cache[filepath]
        if key:
            return data.get(key)
        return data
    def _expand_settings(self, settings):
        """
        Expands a settings dict into multiple settings dicts based on `observations` list or list-based sources/literals.
        """
        observations = settings.get("observations")
        if observations and isinstance(observations, list):
            expanded_list = []
            base_columns = settings.get("columns", {})
            for obs in observations:
                new_settings = settings.copy()
                new_cols = {}
                # deep copy base columns to avoid mutating
                for k, v in base_columns.items():
                    if isinstance(v, dict):
                        new_cols[k] = v.copy()
                    else:
                        new_cols[k] = v
                
                # Merge observation-specific column overrides
                for col_name, col_cfg in obs.items():
                    if isinstance(col_cfg, dict):
                        if col_name in new_cols and isinstance(new_cols[col_name], dict):
                            new_cols[col_name].update(col_cfg)
                        else:
                            new_cols[col_name] = col_cfg.copy()
                    else:
                        new_cols[col_name] = col_cfg

                new_settings["columns"] = new_cols
                new_settings.pop("observations", None)
                expanded_list.append(new_settings)
            
            return expanded_list

        # Find all columns that have a list for source or literal
        list_cols = {}
        list_len = 0

        columns = settings.get("columns", {})
        for col_name, col_cfg in columns.items():
            if isinstance(col_cfg, dict):
                src = col_cfg.get("source")
                lit = col_cfg.get("literal")

                # Check source
                if isinstance(src, list):
                    if list_len > 0 and len(src) != list_len:
                        raise ValueError(
                            f"Column '{col_name}' source list length {len(src)} mismatch with others {list_len}"
                        )
                    list_len = len(src)
                    list_cols[col_name] = "source"

                # Check literal
                if isinstance(lit, list):
                    if list_len > 0 and len(lit) != list_len:
                        raise ValueError(
                            f"Column '{col_name}' literal list length {len(lit)} mismatch with others {list_len}"
                        )
                    list_len = len(lit)
                    list_cols[col_name] = "literal"

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
                        param = list_cols[col_name]  # 'source' or 'literal'
                        # Extract the i-th element
                        val_list = col_cfg.get(param)
                        new_cfg[param] = val_list[i]
                    new_cols[col_name] = new_cfg
                else:
                    new_cols[col_name] = col_cfg

            new_settings["columns"] = new_cols
            expanded_list.append(new_settings)

        return expanded_list

    def _resolve_cross_domain(self, source_expr, col_config, final_df, pivoted, built_domains):
        """
        Resolve a cross-domain reference (e.g., 'DM.RFSTDTC') by merging from built_domains.
        Returns (series, resolved) where resolved is True if successfully resolved.
        """
        if not (isinstance(source_expr, str) and "." in source_expr):
            return None, False

        ref_domain, ref_col = source_expr.split(".", 1)
        if not (ref_domain.isupper() and 2 <= len(ref_domain) <= 4):
            return None, False

        if not built_domains or ref_domain not in built_domains:
            print(f"Warning: Referenced domain '{ref_domain}' not available for cross-domain ref '{source_expr}'")
            return pd.Series([None] * len(pivoted), index=final_df.index), True

        ref_df = built_domains[ref_domain]
        if ref_col not in ref_df.columns:
            print(f"Warning: Column '{ref_col}' not found in domain '{ref_domain}' for cross-domain ref '{source_expr}'")
            return pd.Series([None] * len(pivoted), index=final_df.index), True

        # Determine merge key
        merge_key = col_config.get("merge_on", ["USUBJID"]) if isinstance(col_config, dict) else ["USUBJID"]
        if isinstance(merge_key, str):
            merge_key = [merge_key]

        # Validate merge keys exist in both DataFrames
        valid_keys = [k for k in merge_key if k in final_df.columns and k in ref_df.columns]

        if not valid_keys:
            print(f"Warning: Merge keys {merge_key} missing for cross-domain ref '{source_expr}'")
            return pd.Series([None] * len(pivoted), index=final_df.index), True

        # Get unique ref values to avoid duplicating rows
        ref_cols_needed = valid_keys + [ref_col]
        ref_subset = ref_df[ref_cols_needed].drop_duplicates(subset=valid_keys)

        # Merge into final_df temporarily
        merged = final_df[valid_keys].merge(ref_subset, on=valid_keys, how="left")
        series = merged[ref_col]
        series.index = final_df.index  # Re-align index

        match_count = series.notna().sum()
        print(f"  ↳ Resolved cross-domain ref: {source_expr} ({match_count} matches via {valid_keys})")

        return series, True

    def process(self, domain_name, sources, df_long, default_keys, custom_to_standard=None, built_domains=None, form_mapping=None):
        domain_dfs = []

        # Pre-expand sources if they contain lists
        expanded_sources = []
        for s in sources:
            try:
                expanded_sources.extend(self._expand_settings(s))
            except Exception as e:
                print(f"Error expanding settings for {domain_name}: {e}")
                continue  # Skip invalid blocks

        for settings in expanded_sources:
            # 1. Filter by FormOID
            form_oid = settings.get("formoid")
            if not form_oid and form_mapping and domain_name in form_mapping:
                form_oid = form_mapping[domain_name]
                
            if form_oid:
                try:
                    if "FormOID" in df_long.columns:
                        # Filter for specific FormOID(s)
                        if isinstance(form_oid, list):
                            source_df = df_long[df_long["FormOID"].isin(form_oid)].copy()
                        else:
                            source_df = df_long[df_long["FormOID"] == form_oid].copy()
                    else:
                        print(f"Warning: 'FormOID' column missing in source data. Skipping FormOID filtering.")
                        source_df = df_long.copy()
                except Exception as e:
                    print(
                        f"Error filtering for {domain_name} (FormOID={form_oid}): {e}"
                    )
                    continue
            else:
                if "FormOID" in df_long.columns:
                    print(f"Warning: No formoid specified for a block in {domain_name}. Processing all forms.")
                source_df = df_long.copy()

            if source_df.empty:
                continue

            # 2. Key columns for pivoting (use block keys or defaults)
            keys = settings.get("keys", default_keys)
            if custom_to_standard:
                keys = [custom_to_standard.get(k, k) for k in keys]

            # 3. Pivot
            try:
                pivoted = source_df.pivot_table(
                    index=keys, columns="ItemOID", values="Value", aggfunc="first"
                ).reset_index()
            except Exception as e:
                print(f"Error pivoting for {domain_name}: {e}")
                continue

            # 4. Map columns
            final_df = pd.DataFrame()
            mappings = settings.get("columns", {})

            for target_col, col_config in mappings.items():
                source_expr = None
                literal_expr = None
                target_type = None
                value_map = None

                # Check if simple string or object config
                if isinstance(col_config, dict):
                    source_expr = col_config.get("source")
                    fallback_expr = col_config.get("fallback")
                    literal_expr = col_config.get("literal")
                    target_type = col_config.get("type")
                    # Support value_mapping (primary) and mapping_value (legacy/typo support)
                    value_map = col_config.get("value_mapping") or col_config.get(
                        "mapping_value"
                    )
                    value_mapping_from = col_config.get("value_mapping_from")
                    if not value_map and value_mapping_from:
                        value_map = self._load_value_mapping(value_mapping_from)
                    case_sensitive = col_config.get("case_sensitive", True)
                    group_cols = col_config.get("group")
                    sort_cols = col_config.get("sort_by")
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
                        print(
                            f"Warning: Group columns {missing_grp} not found in final_df for '{domain_name}.{target_col}'. SEQ generation skipped."
                        )
                        series = pd.Series([None] * len(pivoted))
                    else:
                        # Create temp DataFrame for sorting/grouping
                        # We use final_df columns. We need to preserve index alignment.
                        # final_df is currently built row-by-row matching pivoted's rows.
                        temp_df = final_df[group_cols].copy()

                        sort_keys = group_cols[:]  # Always sort by group first
                        ascending_list = [True] * len(group_cols)
                        
                        order_cfg = col_config.get("order")

                        if sort_cols:
                            if not isinstance(sort_cols, list):
                                sort_cols = [sort_cols]

                            if order_cfg:
                                if not isinstance(order_cfg, list):
                                    order_cfg = [order_cfg] * len(sort_cols)
                            else:
                                order_cfg = [True] * len(sort_cols)

                            for i, c in enumerate(sort_cols):
                                found = False
                                if c in final_df.columns:
                                    temp_df[c] = final_df[c]
                                    found = True
                                elif c in pivoted.columns:
                                    temp_df[c] = pivoted[c]
                                    found = True
                                else:
                                    print(f"Warning: Sort column '{c}' not found for '{domain_name}.{target_col}'.")

                                if found:
                                    sort_keys.append(c)
                                    o = order_cfg[i] if i < len(order_cfg) else True
                                    if str(o).lower() in ["desc", "descending", "false"]:
                                        ascending_list.append(False)
                                    else:
                                        ascending_list.append(True)

                        # Sort
                        temp_df = temp_df.sort_values(by=sort_keys, ascending=ascending_list)

                        # Calculate Cumcount + 1
                        seq_series = temp_df.groupby(group_cols, sort=False).cumcount() + 1

                        # Map back to original index
                        series = seq_series.sort_index()

                elif isinstance(col_config, dict) and col_config.get("function"):
                    func_name = col_config.get("function")
                    args = col_config.get("args", [])
                    kwargs = col_config.get("kwargs", {})

                    # Resolve Args
                    arg_series = []
                    for arg in args:
                        # Support cross-domain lookup
                        if arg in final_df.columns:
                            arg_series.append(final_df[arg])
                        elif arg in pivoted.columns:
                            arg_series.append(pivoted[arg])
                        else:
                            # Try cross-domain resolution
                            if isinstance(arg, str) and "." in arg:
                                cross_series, resolved = self._resolve_cross_domain(
                                    arg, {}, final_df, pivoted, built_domains
                                )
                                if resolved and cross_series is not None:
                                    arg_series.append(cross_series)
                                else:
                                    arg_series.append(pd.Series([None] * len(pivoted)))
                            else:
                                arg_series.append(pd.Series([None] * len(pivoted)))

                    import importlib
                    import importlib.util
                    from pathlib import Path
                    
                    def _load_function(fname):
                        if "." not in fname:
                            try:
                                from cdiscbuilder.functions import get_function_path
                                fname = get_function_path(fname)
                            except (ImportError, KeyError):
                                pass
                                
                        if "." in fname:
                            parts = fname.rsplit(".", 1)
                            module = importlib.import_module(parts[0])
                            return getattr(module, parts[1])
                        else:
                            # Local file
                            func_file = Path.cwd() / f"{fname}.py"
                            if func_file.exists():
                                spec = importlib.util.spec_from_file_location(fname, func_file)
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                                return getattr(module, fname)
                            raise ImportError(f"Function {fname} not found")

                    try:
                        import inspect
                        func = _load_function(func_name)
                        sig = inspect.signature(func)
                        
                        func_kwargs = kwargs.copy()
                        if "built_domains" in sig.parameters:
                            func_kwargs["built_domains"] = built_domains
                        if "df_long" in sig.parameters:
                            func_kwargs["df_long"] = df_long
                            
                        series = func(*arg_series, **func_kwargs)
                            
                        if not isinstance(series, pd.Series):
                            series = pd.Series(series)
                    except Exception as e:
                        print(
                            f"Warning: Failed to execute function {func_name} for {target_col}: {e}"
                        )
                        series = pd.Series([None] * len(pivoted))

                elif isinstance(col_config, dict) and col_config.get("conditions"):
                    import numpy as np
                    conditions_config = col_config.get("conditions")
                    
                    # Create an evaluation context combining raw domain data and current final_df
                    eval_df = pivoted.copy()
                    for c in final_df.columns:
                        eval_df[c] = final_df[c]
                        
                    cond_list = []
                    choice_list = []
                    
                    for cond in conditions_config:
                        expr = cond.get("if")
                        then_val = cond.get("then")
                        try:
                            # Evaluate condition string
                            mask = eval_df.eval(expr)
                            cond_list.append(mask)
                            choice_list.append(then_val)
                        except Exception as e:
                            print(f"Warning: Failed to evaluate condition '{expr}': {e}")
                            cond_list.append(pd.Series(False, index=eval_df.index))
                            choice_list.append(then_val)
                            
                    default_val = col_config.get("default", None)
                    if cond_list:
                        # np.select evaluates conditions in order
                        series = pd.Series(np.select(cond_list, choice_list, default=default_val), index=eval_df.index)
                    else:
                        series = pd.Series([default_val] * len(eval_df), index=eval_df.index)

                elif literal_expr is not None:
                    # Explicit literal value
                    series = pd.Series([literal_expr] * len(pivoted))
                elif source_expr:
                    # Check for cross-domain reference first
                    cross_series, resolved = self._resolve_cross_domain(
                        source_expr, col_config, final_df, pivoted, built_domains
                    )
                    if resolved:
                        series = cross_series
                    elif source_expr in pivoted.columns:
                        series = pivoted[source_expr].copy()
                    elif source_expr in final_df.columns:
                        series = final_df[source_expr].copy()
                    else:
                        # Source defined but not found.
                        print(
                            f"Warning: Source column '{source_expr}' not found for '{domain_name}.{target_col}'. Filling with NaN."
                        )
                        series = pd.Series([None] * len(pivoted))

                    # Auto-Strip Whitespace for strings
                    if series is not None and pd.api.types.is_object_dtype(series):
                        try:
                            series = series.astype(str).str.strip().replace("nan", None)
                        except:
                            pass
                else:
                    print(
                        f"Warning: No source or literal defined for '{domain_name}.{target_col}'. Filling with NaN."
                    )
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
                        print(
                            f"Warning: Fallback column '{fallback_expr}' not found for '{domain_name}.{target_col}'"
                        )

                # Apply Dependency Logic (Assign only if dependency column is not null)
                dependency = (
                    col_config.get("dependency")
                    if isinstance(col_config, dict)
                    else None
                )
                if dependency:
                    dep_series = None
                    if dependency in pivoted.columns:
                        dep_series = pivoted[dependency]
                    elif dependency in final_df.columns:
                        dep_series = final_df[dependency]

                    if dep_series is not None:
                        # Mask: Keep values where dependency is NOT null, else fill with False Value (default None)
                        false_val = col_config.get("dependency_false_value")
                        # Make sure false_val is treated as literal of correct type? pandas usually handles mixed.

                        series = series.where(dep_series.notna(), false_val)
                    else:
                        print(
                            f"Warning: Dependency column '{dependency}' not found for '{domain_name}.{target_col}'. Treating as all-null dependency."
                        )
                        false_val = col_config.get("dependency_false_value")
                        series = pd.Series([false_val] * len(pivoted))

                # Apply Substring Extraction (Before Value Mapping)
                if isinstance(col_config, dict):
                    sub_start = col_config.get("substring_start")
                    sub_len = col_config.get("substring_length")
                    if sub_start is not None and sub_len is not None:
                        # Ensure series is string
                        series = series.astype(str)
                        # Slice 0-indexed or 1-indexed? Python is 0-indexed.
                        # User said "position 3-5". If string is '1110023565' and target is '002',
                        # indices are 3,4,5. So slice[3:6].
                        # Let's assume user provides 0-based start index and length.
                        series = series.str[sub_start : sub_start + sub_len]

                # Apply Value Mapping
                mapping_default = (
                    col_config.get("mapping_default")
                    if isinstance(col_config, dict)
                    else None
                )
                mapping_default_source = (
                    col_config.get("mapping_default_source")
                    if isinstance(col_config, dict)
                    else None
                )

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
                            print(
                                f"Warning: Default source '{mapping_default_source}' not found for '{domain_name}.{target_col}'"
                            )
                            series = mapped_series  # Leave as NaN or original? mapped_series has NaNs.
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
                prefix = (
                    col_config.get("prefix") if isinstance(col_config, dict) else None
                )
                if prefix:
                    series = prefix + series.astype(str)

                # Apply Case
                string_case = (
                    col_config.get("case") if isinstance(col_config, dict) else None
                )
                if string_case and series is not None:
                    # mask missing values so they stay missing instead of becoming "nan"
                    mask = series.notna()
                    if string_case == "upper":
                        series.loc[mask] = series.loc[mask].astype(str).str.upper()
                    elif string_case == "lower":
                        series.loc[mask] = series.loc[mask].astype(str).str.lower()
                    elif string_case == "title":
                        series.loc[mask] = series.loc[mask].astype(str).str.title()

                # Apply Type Conversion
                if target_type:
                    try:
                        if target_type == "int":
                            series = pd.to_numeric(series, errors="coerce").astype(
                                "Int64"
                            )
                        elif target_type == "float":
                            series = pd.to_numeric(series, errors="coerce")
                        elif target_type == "str":
                            series = series.astype(str)
                        elif target_type == "bool":
                            series = series.astype(bool)
                        elif target_type == "date":
                            # Convert to datetime objects (handles multiple formats) then Format to YYYY-MM-DD string
                            series = pd.to_datetime(
                                series, errors="coerce", format="mixed"
                            ).dt.strftime("%Y-%m-%d")
                    except Exception as e:
                        print(f"Error converting {target_col} to {target_type}: {e}")

                final_df[target_col] = series

                # Store merge configuration
                final_df.attrs["merge_on"] = settings.get("merge_on")

                # Validation: max_missing_pct
                if isinstance(col_config, dict):
                    max_missing = col_config.get("max_missing_pct")
                    if max_missing is not None:
                        missing_count = series.isna().sum()
                        if target_type == "str":
                            missing_count += (series.isin(["nan", "None"])).sum()

                        total = len(series)
                        if total > 0:
                            pct = (missing_count / total) * 100
                            if pct > max_missing:
                                print(
                                    f"WARNING: [Validation] {domain_name}.{target_col} missing {pct:.2f}% (Limit: {max_missing:})"
                                )

            domain_dfs.append(final_df)

        return domain_dfs
