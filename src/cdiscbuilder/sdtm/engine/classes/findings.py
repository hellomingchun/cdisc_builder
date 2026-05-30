import pandas as pd


class FindingsProcessor:
    """
    Processor for SDTM Findings class (e.g., LB, VS, QS).
    Typically tall format (one row per test/finding).
    """

    def __init__(self):
        self.class_name = "FINDINGS"

    def process(self, domain_name, sources, df_long, default_keys, custom_to_standard=None):
        domain_dfs = []

        for settings in sources:
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
                        if sort_cols:
                            if not isinstance(sort_cols, list):
                                sort_cols = [sort_cols]
                            for c in sort_cols:
                                if c in final_df.columns:
                                    temp_df[c] = final_df[c]
                                    sort_keys.append(c)

                        temp_df = temp_df.sort_values(by=sort_keys)
                        series = (
                            temp_df.groupby(group_cols).cumcount() + 1
                        ).sort_index()

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
