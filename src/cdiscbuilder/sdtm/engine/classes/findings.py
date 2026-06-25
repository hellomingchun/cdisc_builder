import pandas as pd
from .general import GeneralProcessor


class FindingsProcessor(GeneralProcessor):
    """
    Processor for SDTM Findings class (e.g., LB, VS, QS).
    Typically tall format (one row per test/finding).
    """

    def __init__(self):
        super().__init__()
        self.class_name = "FINDINGS"

    def process(self, domain_name, sources, df_long, default_keys, custom_to_standard=None, built_domains=None):
        domain_dfs = []

        # Pre-expand sources if they contain lists or observations
        expanded_sources = []
        for s in sources:
            try:
                expanded_sources.extend(self._expand_settings(s))
            except Exception as e:
                print(f"Error expanding settings for {domain_name}: {e}")
                continue  # Skip invalid blocks

        for settings in expanded_sources:
            # 0. Filter by FormOID (optional but recommended)
            form_oid = settings.get("formoid")
            source_df = df_long.copy()
            if form_oid:
                if "FormOID" not in source_df.columns:
                    print(
                        f"Warning: 'FormOID' column missing in source data. Skipping FormOID filtering."
                    )
                else:
                    if isinstance(form_oid, list):
                        source_df = source_df[source_df["FormOID"].isin(form_oid)]
                    else:
                        source_df = source_df[source_df["FormOID"] == form_oid]

            # 1. Filter by ItemGroupOID (regex or list)
            item_group_match = settings.get("item_group_regex")
            if item_group_match:
                if "ItemGroupOID" not in source_df.columns:
                    print(
                        f"Warning: 'ItemGroupOID' column missing in source data. Skipping ItemGroupOID filtering."
                    )
                else:
                    source_df = source_df[
                        source_df["ItemGroupOID"].str.match(item_group_match, na=False)
                    ]

            # 2. Filter by ItemOID (regex)
            item_oid_match = settings.get("item_oid_regex")
            if item_oid_match:
                if "ItemOID" not in source_df.columns:
                    print(
                        f"Warning: 'ItemOID' column missing in source data. Skipping ItemOID filtering."
                    )
                else:
                    source_df = source_df[
                        source_df["ItemOID"].str.match(item_oid_match, na=False)
                    ]

            if source_df.empty:
                continue

            # 3. Create Base DataFrame (No Pivot)
            keys = settings.get("keys", default_keys)
            if custom_to_standard:
                keys = [custom_to_standard.get(k, k) for k in keys]

            base_cols = keys + ["ItemOID", "Value"]
            if "Question" in source_df.columns:
                base_cols.append("Question")
            if "ItemName" in source_df.columns:
                base_cols.append("ItemName")

            # Ensure all keys exist
            available_cols = [c for c in base_cols if c in source_df.columns]
            final_df = source_df[available_cols].copy()

            # 4. Map Columns
            mappings = settings.get("columns", {})

            for target_col, col_config in mappings.items():
                series = None
                source_expr = None
                literal_expr = None
                target_type = None
                regex_extract = None

                if isinstance(col_config, dict):
                    source_expr = col_config.get("source")
                    literal_expr = col_config.get("literal")
                    target_type = col_config.get("type")
                    regex_extract = col_config.get("regex_extract")
                    group_cols = col_config.get("group")
                    sort_cols = col_config.get("sort_by")
                else:
                    source_expr = col_config
                    group_cols = None
                    sort_cols = None

                # 0. Local Sequence Generation
                if group_cols:
                    if not isinstance(group_cols, list):
                        group_cols = [group_cols]
                    missing_grp = [c for c in group_cols if c not in final_df.columns]
                    if not missing_grp:
                        temp_df = final_df[group_cols].copy()
                        sort_keys = group_cols[:]
                        order_cfg = col_config.get("order") if isinstance(col_config, dict) else None
                        ascending_list = [True] * len(group_cols)

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
                                elif c in source_df.columns:
                                    temp_df[c] = source_df[c]
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

                        temp_df = temp_df.sort_values(by=sort_keys, ascending=ascending_list)
                        series = (
                            temp_df.groupby(group_cols, sort=False).cumcount() + 1
                        ).sort_index()

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
                        elif arg in source_df.columns:
                            arg_series.append(source_df[arg])
                        else:
                            # Try cross-domain resolution
                            if isinstance(arg, str) and "." in arg:
                                cross_series, resolved = self._resolve_cross_domain(
                                    arg, {}, final_df, source_df, built_domains
                                )
                                if resolved and cross_series is not None:
                                    arg_series.append(cross_series)
                                else:
                                    arg_series.append(pd.Series([None] * len(source_df), index=final_df.index))
                            else:
                                arg_series.append(pd.Series([None] * len(source_df), index=final_df.index))

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
                            series = pd.Series(series, index=final_df.index)
                        else:
                            series.index = final_df.index
                    except Exception as e:
                        print(
                            f"Warning: Failed to execute function {func_name} for {target_col}: {e}"
                        )
                        series = pd.Series([None] * len(source_df), index=final_df.index)

                elif literal_expr is not None:
                    series = pd.Series(
                        [literal_expr] * len(final_df), index=final_df.index
                    )

                elif source_expr:
                    if source_expr in final_df.columns:
                        series = final_df[source_expr]
                    elif source_expr in source_df.columns:
                        series = source_df[source_expr]

                    if series is not None and pd.api.types.is_object_dtype(series):
                        series = series.astype(str).str.strip().replace("nan", None)

                    if regex_extract and series is not None:
                        series = series.astype(str).str.extract(regex_extract)[0]

                # Value Map & Type Casting
                if series is not None:
                    value_map = None
                    if isinstance(col_config, dict):
                        value_map = col_config.get("value_mapping") or col_config.get(
                            "mapping_value"
                        )
                        value_mapping_from = col_config.get("value_mapping_from")
                        if not value_map and value_mapping_from:
                            value_map = self._load_value_mapping(value_mapping_from)

                    if value_map:
                        series = series.replace(value_map)

                    prefix = (
                        col_config.get("prefix")
                        if isinstance(col_config, dict)
                        else None
                    )
                    if prefix:
                        series = prefix + series.astype(str)

                    if target_type:
                        try:
                            if target_type == "int":
                                series = pd.to_numeric(series, errors="coerce").astype(
                                    "Int64"
                                )
                            elif target_type == "float":
                                series = pd.to_numeric(series, errors="coerce")
                            elif target_type == "date":
                                series = pd.to_datetime(
                                    series, errors="coerce", format="mixed"
                                ).dt.strftime("%Y-%m-%d")
                            elif target_type == "str":
                                series = series.astype(str).replace("nan", None)
                        except Exception as e:
                            print(
                                f"Error converting {target_col} to {target_type}: {e}"
                            )

                    final_df[target_col] = series

            # Keep only target columns
            final_df = final_df[list(mappings.keys())]
            domain_dfs.append(final_df)

        return domain_dfs
