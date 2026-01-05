import xml.etree.ElementTree as ET
import pandas as pd

def parse_odm_to_long_df(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    data_rows = []

    # Helper to clean tag
    def get_local_name(tag):
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag

    # Recurse strictly based on ODM hierarchy
    # ODM -> ClinicalData
    
    # We iterate direct children of root to find ClinicalData
    for clinical_data in root:
        if get_local_name(clinical_data.tag) != 'ClinicalData':
            continue
        
        study_oid = clinical_data.get('StudyOID')
        
        # ClinicalData -> SubjectData
        for subject_data in clinical_data:
            if get_local_name(subject_data.tag) != 'SubjectData':
                continue
            
            subject_key = subject_data.get('SubjectKey')
            if not subject_key:
                # Fallback for systems using StudySubjectID (e.g. OpenClinica sometimes)
                # Checking both CamelCase and lowercase as requested
                subject_key = subject_data.get('StudySubjectID') or subject_data.get('studysubjectid')
            
            # SubjectData -> StudyEventData
            for study_event_data in subject_data:
                if get_local_name(study_event_data.tag) != 'StudyEventData':
                    continue
                
                study_event_oid = study_event_data.get('StudyEventOID')
                
                # StudyEventData -> FormData
                for form_data in study_event_data:
                    if get_local_name(form_data.tag) != 'FormData':
                        continue
                    
                    form_oid = form_data.get('FormOID')
                    
                    # FormData -> ItemGroupData
                    for item_group_data in form_data:
                        if get_local_name(item_group_data.tag) != 'ItemGroupData':
                            continue
                        
                        item_group_oid = item_group_data.get('ItemGroupOID')
                        item_group_repeat_key = item_group_data.get('ItemGroupRepeatKey')
                        
                        # ItemGroupData -> ItemData
                        for item_data in item_group_data:
                            if get_local_name(item_data.tag) != 'ItemData':
                                continue
                            
                            item_oid = item_data.get('ItemOID')
                            value = item_data.get('Value')
                            
                            row = {
                                'StudyOID': study_oid,
                                'SubjectKey': subject_key,
                                'StudyEventOID': study_event_oid,
                                'FormOID': form_oid,
                                'ItemGroupOID': item_group_oid,
                                'ItemGroupRepeatKey': item_group_repeat_key,
                                'ItemOID': item_oid,
                                'Value': value
                            }
                            data_rows.append(row)

    df = pd.DataFrame(data_rows)
    return df


