import xml.etree.ElementTree as ET
import pandas as pd

def parse_odm_to_long_df(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML file {xml_file}: {e}")
        return pd.DataFrame()

    def parse_metadata(root):
        item_metadata = {}
        ns = {'odm': 'http://www.cdisc.org/ns/odm/v1.3'}
        # Find MetaDataVersion - simplified lookup
        for study in root.findall('odm:Study', ns):
            for mdv in study.findall('odm:MetaDataVersion', ns):
                for item_def in mdv.findall('odm:ItemDef', ns):
                    oid = item_def.get('OID')
                    name = item_def.get('Name', "")
                    
                    # Try to find Question/TranslatedText
                    question = ""
                    q_elem = item_def.find('odm:Question', ns)
                    if q_elem is not None:
                        tt_elem = q_elem.find('odm:TranslatedText', ns)
                        if tt_elem is not None:
                            question = tt_elem.text.strip() if tt_elem.text else ""
                    
                    item_metadata[oid] = {'Question': question, 'ItemName': name}
        return item_metadata

    item_metadata = parse_metadata(root)

    data_rows = []

    def get_local_name(tag):
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag

    for cd in root:
        if get_local_name(cd.tag) == 'ClinicalData':
            study_oid = cd.get('StudyOID')
            for sd in cd:
                if get_local_name(sd.tag) == 'SubjectData':
                    subject_key = sd.get('SubjectKey')
                    
                    # Helper for attributes
                    def get_attrib(elem, partial_name):
                        if partial_name in elem.attrib:
                            return elem.attrib[partial_name]
                        for k, v in elem.attrib.items():
                            if k.endswith("}" + partial_name):
                                return v
                        return None

                    study_subject_id = get_attrib(sd, 'StudySubjectID') or get_attrib(sd, 'studysubjectid')
                    if not subject_key:
                        subject_key = study_subject_id

                    for child in sd:
                        tag = get_local_name(child.tag)
                        if tag == 'StudyEventData':
                            study_event_oid = child.get('StudyEventOID')
                            study_event_repeat_key = child.get('StudyEventRepeatKey') or "1"
                            
                            # Extract Namespaced StartDate
                            start_date = get_attrib(child, 'StartDate') or ""
                            
                            for form in child:
                                f_tag = get_local_name(form.tag)
                                if f_tag == 'FormData':
                                    form_oid = form.get('FormOID')
                                    
                                    for ig in form:
                                        ig_tag = get_local_name(ig.tag)
                                        if ig_tag == 'ItemGroupData':
                                            item_group_oid = ig.get('ItemGroupOID')
                                            item_group_repeat_key = ig.get('ItemGroupRepeatKey')
                                            
                                            for item in ig:
                                                i_tag = get_local_name(item.tag)
                                                if i_tag == 'ItemData':
                                                    item_oid = item.get('ItemOID')
                                                    value = item.get('Value')
                                                    
                                                    meta = item_metadata.get(item_oid, {})
                                                    data_rows.append({
                                                        'StudyOID': study_oid,
                                                        'SubjectKey': subject_key,
                                                        'StudySubjectID': study_subject_id,
                                                        'StudyEventOID': study_event_oid,
                                                        'StudyEventRepeatKey': study_event_repeat_key,
                                                        'StudyEventStartDate': start_date,
                                                        'FormOID': form_oid,
                                                        'ItemGroupOID': item_group_oid,
                                                        'ItemGroupRepeatKey': item_group_repeat_key,
                                                        'ItemOID': item_oid,
                                                        'Value': value,
                                                        'Question': meta.get('Question', ""),
                                                        'ItemName': meta.get('ItemName', "")
                                                    })

    df = pd.DataFrame(data_rows)
    return df

def extract_metadata_summary(df_long):
    """
    Extracts a deduplicated metadata summary / data dictionary from the flat long DataFrame.
    For each unique item, it retrieves up to 3 non-null, non-empty sample values.
    """
    if df_long is None or df_long.empty:
        return pd.DataFrame(columns=['FormOID', 'ItemGroupOID', 'ItemOID', 'ItemName', 'Question', 'SampleValues'])
    
    meta_cols = ['FormOID', 'ItemGroupOID', 'ItemOID', 'ItemName', 'Question']
    
    # Verify required columns exist
    missing_cols = [c for c in meta_cols if c not in df_long.columns]
    if missing_cols:
        raise ValueError(f"Input DataFrame is missing required metadata columns: {missing_cols}")
        
    # Deduplicate metadata records
    meta_df = df_long[meta_cols].drop_duplicates(subset=['FormOID', 'ItemGroupOID', 'ItemOID']).copy()
    
    # Sort for consistent ordering
    meta_df = meta_df.sort_values(by=['FormOID', 'ItemGroupOID', 'ItemOID']).reset_index(drop=True)
    
    # Extract distinct non-empty sample values for each item
    sample_values_list = []
    
    # Group by FormOID, ItemGroupOID, ItemOID for efficient query or loop
    for row in meta_df.itertuples():
        # Get actual clinical values from df_long matching this specific item
        val_filter = (
            (df_long['FormOID'] == row.FormOID) & 
            (df_long['ItemGroupOID'] == row.ItemGroupOID) & 
            (df_long['ItemOID'] == row.ItemOID) & 
            (df_long['Value'].notna())
        )
        values_series = df_long[val_filter]['Value'].astype(str).str.strip()
        values_series = values_series[values_series != '']
        
        # Get up to 3 unique values
        unique_vals = list(values_series.unique())[:3]
        sample_values_list.append(str(unique_vals))
        
    meta_df['SampleValues'] = sample_values_list
    return meta_df

