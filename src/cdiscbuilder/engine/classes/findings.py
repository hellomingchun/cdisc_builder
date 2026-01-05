import pandas as pd
import yaml
import os

from ..functions import extract_value

# Map string names to actual functions
FUNCTION_MAP = {
    'extract_value': extract_value
}

class FindingsProcessor:
    def __init__(self, metadata_path):
        self.metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                self.metadata = yaml.safe_load(f)
        else:
            print(f"Warning: Metadata file not found at {metadata_path}")

    def process(self, domain_name, sources, df_long, default_keys):
        domain_dfs = []
        
        # Normalize dict to list if single config
        if isinstance(sources, dict):
            sources = [sources]
        
        for settings in sources:
            # Check for 'columns' list with functions (New Strategy)
            columns_cfg = settings.get('columns', [])
            
            # If columns is a dict (old style), convert or warn? 
            # The new FA.yaml uses list of dicts.
            
            is_functional = isinstance(columns_cfg, list) and any('function' in c for c in columns_cfg)
            
            if is_functional:
                # --- Functional Strategy ---
                
                # We need to build the "Main" DF from the backbone columns (those with multiple items)
                # and "Attribute" DFs from single-item columns, then merge.
                
                # 1. Group columns by their ItemOID signature (to identify backbone vs attributes)
                # Keys are always required for joining.
                # To prevent cross-form contamination (e.g. Form A Repeat 1 joining to Form B Repeat 1),
                # we SHOULD include FormOID in the join keys if we are mixing forms.
                # We assume FormOID is available in df_long.
                
                config_keys = settings.get('keys', default_keys)
                keys = config_keys # Alias for compatibility
                
                # Check if we should enforce FormOID joining
                # If simplified config, we likely want strict form isolation.
                join_keys = config_keys.copy()
                if 'FormOID' not in join_keys and 'FormOID' in df_long.columns:
                     join_keys.append('FormOID')
                
                # Store resulting dataframes 
                
                # To identify the "Backbone" (which determines the number of rows), we look for the list of items.
                # Actually, with the Naive Merge strategy (Full Outer Join or Left Join on Main?), 
                # we usually treat the "Test Code" column as the driver.
                
                # Let's iterate and collect data for each column.
                
                # Optimization: Cache `func_fa` results if forms/items are identical? 
                
                # We need a primary DF to merge into.
                # Usually FATESTCD or FAORRES defines the rows.
                
                # Let's try: Generate DF for EACH column, then merge them all.
                # Merge logic:
                # - If signature (forms, items) is identical: Merge on Keys + ItemOID.
                # - If signature is different (e.g. single item vs list): Merge on Keys only?
                #   - Wait, if we merge 'DATE' (1 row per subject) to 'AESEV' (1 row per subject), 
                #     on Keys -> Cartesian product if there are multiple AE records?
                #     SDTM Keys: USUBJID, FASEQ.
                #     ODM Keys: StudyOID, SubjectKey, ItemGroupRepeatKey.
                #     If keys are unique per finding, 1:1 merge works.
                #     If mult-items (Backbone) share keys?
                #     e.g. Form.AE has 1 record (RepeatKey 1). Contains AESEV, AEREL.
                #     func_fa(AESEV+AEREL) -> 2 rows (ItemOID AESEV, ItemOID AEREL). Same RepeatKey.
                #     func_fa(DATE) -> 1 row (ItemOID DATE). Same RepeatKey.
                #     Merge: DATE should join to BOTH AESEV and AEREL.
                #     So Left Join from Backbone to Attribute on Keys is correct.
                
                primary_df = pd.DataFrame()
                attribute_dfs = []
                
                for col_def in columns_cfg:
                    name = col_def.get('name')
                    func_name = col_def.get('function')
                    
                    if not func_name:
                        # Literal or simple mapping logic handles later?
                        # Or maybe standard 'source' mapping?
                        continue
                        
                    if func_name in ['func_fa', 'extract_value']:
                        form_oids = col_def.get('formoid')
                        item_oids = col_def.get('itemoid')
                        
                        if name == 'VISIT':
                             pass # Removed Debug
                        
                        # Normalize to list
                        if not isinstance(form_oids, list): 
                            form_oids = [form_oids] if form_oids else []
                        col_type = col_def.get('type', 'str')
                         
                        # Determine return_col
                        # ... lines 105-108 ...
                        return_col = 'Value'
                        if name in ['FATESTCD', 'LBTESTCD', 'VSTESTCD', 'QSTESTCD']:
                            return_col = 'ItemOID'
                            
                # Call function
                        df_res = extract_value(df_long, form_oids, item_oids, return_col=return_col, keys=join_keys)

                        # Removed Debug
                        
                        if df_res.empty:
                            print(f"Warning: No data for {name}")
                            continue
                            
                        # Rename result column to target name
                        # func_fa returns Keys + [return_col]
                        # If return_col was 'Value', it's now named 'Value'.
                        # We rename it to `name` (e.g. FAORRES).
                        df_res = df_res.rename(columns={return_col: name})
                        
                        # Identify if this is Backbone or Attribute
                        # Heuristic: If name implies Topic/Result (TESTCD, ORRES) AND it has multiple items, 
                        # it is Backbone.
                        # Attributes (like DTC) might have multiple items (to search across forms) but are not Row Generators.
                        
                        is_result = 'ORRES' in name or 'STRES' in name or 'STAT' in name or 'REASND' in name or 'TERM' in name or 'DECOD' in name or 'VISIT' in name or 'DTC' in name
                        is_backbone_col = name.endswith('TESTCD') or is_result or name.endswith('OBJ')
                        is_list = isinstance(item_oids, list) and len(item_oids) > 1 and is_backbone_col
                        
                        if is_list:
                            # This is part of the Backbone.
                            # We merge these on Keys + ItemOID? 
                            # Wait, if we have FATESTCD (Values: AESEV, AEREL) and FAORRES (Values: MILD, POSSIBLE).
                            # Both have 'ItemOID' column from source? NO.
                            # func_fa returns Keys + Result. It DROPS ItemOID column unless return_col='ItemOID'.
                            # Converting FATESTCD: returns Keys + FATESTCD (values are AESEV, AEREL).
                            # Converting FAORRES:  returns Keys + FAORRES (values are MILD, POSSIBLE).
                            # BUT we lost the link that MILD belongs to AESEV!
                            # CRITICAL: func_fa MUST return ItemOID column to allow aligning Backbone columns!
                            
                            # Re-calling func_fa to get 'ItemOID' for alignment.
                            # Or update func_fa to always return ItemOID?
                            # For FAORRES, we definitely need ItemOID to know which test it is.
                            
                            # FIX for extract_value usage here:
                            # We always ask for ItemOID as a key for merging.
                            df_res_with_id = extract_value(df_long, form_oids, item_oids, return_col=return_col, keys=join_keys + ['ItemOID'])
                            
                            # Create target column instead of renaming, to preserve ItemOID key
                            # If return_col is 'ItemOID', it's the same column.
                            # If return_col is 'Value', we have both.
                            
                            # Handle duplicate column issue from func_fa if return_col in keys
                            df_res_with_id = df_res_with_id.loc[:, ~df_res_with_id.columns.duplicated()]
                            
                            if return_col in df_res_with_id.columns:
                                df_res_with_id[name] = df_res_with_id[return_col]
                                if return_col != 'ItemOID' and return_col != name:
                                     # Drop original value col if not needed and not ItemOID
                                     # Actually, we keep ItemOID for join. We can drop 'Value' after copy.
                                     df_res_with_id = df_res_with_id.drop(columns=[return_col])
                            else:
                                # Should not happen if func_fa works
                                print(f"Warning: return column {return_col} missing in func_fa result for {name}")

                            if is_backbone_col:
                                if primary_df.empty:
                                    primary_df = df_res
                                else:
                                    # Merge logic
                                    primary_df = pd.merge(primary_df, df_res, on=join_keys, how='outer')
                            else:
                                # Attribute (Single item, e.g. DATE)
                                # We just need Keys + Value. ItemOID is not a join key for the backbone.
                                 attribute_dfs.append(df_res)
                        
                        else:
                            # Single Item Logic (df_res already computed and renamed at top)
                            if is_backbone_col:
                                if primary_df.empty:
                                    primary_df = df_res
                                else:
                                    primary_df = pd.merge(primary_df, df_res, on=join_keys, how='outer')
                            else:
                                attribute_dfs.append(df_res)
                
                # If we built a primary DF, merge attributes
                if not primary_df.empty:
                    final_df = primary_df
                    
                    for att_df in attribute_dfs:
                        # Join on keys only
                        final_df = pd.merge(final_df, att_df, on=join_keys, how='left')
                        
                    # Now populate other columns and Enforce Types
                    for col_def in columns_cfg:
                        name = col_def.get('name')
                        col_type = col_def.get('type', 'str')
                        source = col_def.get('source')
                        
                        # logic to overwrite if source is present
                        if name in final_df.columns and not source:
                            # Already populated by func_fa and no override requested
                            pass
                        elif source and source in final_df.columns:
                             # Overwrite or Populate from Source
                             final_df[name] = final_df[source]
                        else:
                            # Populate missing columns
                            series = None
                            literal = col_def.get('literal')
                            
                            if literal:
                                 series = pd.Series([literal] * len(final_df), index=final_df.index)
                                 
                            # Defaults Logic (Legacy / Backup)
                            elif name == 'STUDYID' and 'StudyOID' in keys:
                                 if 'StudyOID' in final_df.columns: 
                                     series = final_df['StudyOID']
                            elif name == 'USUBJID':
                                 if 'StudySubjectID' in final_df.columns:
                                     series = final_df['StudySubjectID']
                                 elif 'SubjectKey' in final_df.columns: 
                                     series = final_df['SubjectKey']
                            elif name == 'FASEQ' and 'ItemGroupRepeatKey' in keys:
                                 if 'ItemGroupRepeatKey' in final_df.columns: 
                                     series = final_df['ItemGroupRepeatKey']
                            elif name == 'DOMAIN':
                                 series = pd.Series([domain_name] * len(final_df), index=final_df.index)
                                 
                            # Metadata Lookup
                            elif name == 'FATEST' and 'FATESTCD' in final_df.columns:
                                 series = final_df['FATESTCD'].apply(lambda x: self.metadata.get(x, {}).get('test', x))
                            elif name == 'FAOBJ' and 'FATESTCD' in final_df.columns:
                                 series = final_df['FATESTCD'].apply(lambda x: self.metadata.get(x, {}).get('obj', None))
                            
                            else:
                                # Fallback: Empty
                                series = pd.Series([None] * len(final_df), index=final_df.index)
                                
                            if series is not None:
                                final_df[name] = series

                        # Type Enforcement (Apply to ALL columns, whether func_fa or fallback)
                        if col_type == 'int':
                             final_df[name] = pd.to_numeric(final_df[name], errors='coerce').astype('Int64')
                        elif col_type == 'float':
                             final_df[name] = pd.to_numeric(final_df[name], errors='coerce')
                        else:
                             # String cleanup
                             final_df[name] = final_df[name].astype(str).replace('nan', None).replace('None', None)

                    # Store Variable Labels in df.attrs["labels"]
                    labels = {col['name']: col.get('label', '') for col in columns_cfg if 'label' in col}
                    final_df.attrs['labels'] = labels
                    
                    domain_dfs.append(final_df)

            else:
                continue

        return domain_dfs
