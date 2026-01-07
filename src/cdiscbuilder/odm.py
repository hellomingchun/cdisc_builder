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
        item_question_map = {}
        ns = {'odm': 'http://www.cdisc.org/ns/odm/v1.3'}
        # Find MetaDataVersion - simplified lookup
        for study in root.findall('odm:Study', ns):
            for mdv in study.findall('odm:MetaDataVersion', ns):
                for item_def in mdv.findall('odm:ItemDef', ns):
                    oid = item_def.get('OID')
                    
                    # Try to find Question/TranslatedText
                    question = ""
                    q_elem = item_def.find('odm:Question', ns)
                    if q_elem is not None:
                        tt_elem = q_elem.find('odm:TranslatedText', ns)
                        if tt_elem is not None:
                            question = tt_elem.text.strip() if tt_elem.text else ""
                    
                    item_question_map[oid] = question
        return item_question_map

    item_question_map = parse_metadata(root)

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
                                                        'Question': item_question_map.get(item_oid, "")
                                                    })

    df = pd.DataFrame(data_rows)
    return df
