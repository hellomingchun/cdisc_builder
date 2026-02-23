import pandas as pd
import pytest
from cdiscbuilder.sdtm.engine.classes.finding import FindingProcessor

def test_finding_processor_process():
    processor = FindingProcessor()
    
    df_long = pd.DataFrame({
        'SubjectKey': ['001', '001', '002', '002'],
        'FormOID': ['F_VS', 'F_VS', 'F_VS', 'F_VS'],
        'ItemGroupOID': ['IG_VS', 'IG_VS', 'IG_VS', 'IG_VS'],
        'ItemOID': ['I_VS_SYSBP', 'I_VS_DIABP', 'I_VS_SYSBP', 'I_VS_DIABP'],
        'Value': ['120', '80', '130', '85'],
        'Question': ['Systolic Blood Pressure', 'Diastolic Blood Pressure', 'Systolic Blood Pressure', 'Diastolic Blood Pressure']
    })
    
    sources = [{
        'formoid': 'F_VS',
        'item_group_regex': 'IG_VS',
        'item_oid_regex': 'I_VS_.*',
        'columns': {
            'VSSEQ': {'group': 'SubjectKey'},
            'VSTESTCD': {'source': 'ItemOID', 'regex_extract': r'I_VS_(.*)'},
            'VSTEST': {'source': 'Question'},
            'VSORRES': {'source': 'Value'},
            'VSORRESU': {'literal': 'mmHg'}
        }
    }]
    
    default_keys = ['SubjectKey']
    
    dfs = processor.process('VS', sources, df_long, default_keys)
    assert len(dfs) == 1
    
    result_df = dfs[0]
    assert len(result_df) == 4
    
    # Check if columns are correct
    assert list(result_df.columns) == ['VSSEQ', 'VSTESTCD', 'VSTEST', 'VSORRES', 'VSORRESU']
    
    # Check sequence generated correctly per group
    assert list(result_df['VSSEQ']) == [1, 2, 1, 2] # 001 gets 1, 2, 002 gets 1, 2
    
    # Check values mapped from extract regex
    assert list(result_df['VSTESTCD']) == ['SYSBP', 'DIABP', 'SYSBP', 'DIABP']
    
    # Metadata lookup
    assert list(result_df['VSTEST']) == ['Systolic Blood Pressure', 'Diastolic Blood Pressure', 'Systolic Blood Pressure', 'Diastolic Blood Pressure']
    
    # Value lookup
    assert list(result_df['VSORRES']) == ['120', '80', '130', '85']
    
    # Literal
    assert list(result_df['VSORRESU']) == ['mmHg', 'mmHg', 'mmHg', 'mmHg']

def test_finding_processor_empty():
    processor = FindingProcessor()
    df_long = pd.DataFrame(columns=['SubjectKey', 'FormOID', 'ItemGroupOID', 'ItemOID', 'Value'])
    
    sources = [{
        'formoid': 'F_VS',
        'columns': {
            'VSTESTCD': {'source': 'ItemOID'}
        }
    }]
    
    dfs = processor.process('VS', sources, df_long, ['SubjectKey'])
    assert len(dfs) == 0

def test_finding_processor_value_mapping():
    processor = FindingProcessor()
    
    df_long = pd.DataFrame({
        'SubjectKey': ['001', '002'],
        'FormOID': ['F_IE', 'F_IE'],
        'ItemGroupOID': ['IG_IE', 'IG_IE'],
        'ItemOID': ['I_IE_ELIGIBLE', 'I_IE_ELIGIBLE'],
        'Value': ['Yes', 'No']
    })
    
    sources = [{
        'formoid': 'F_IE',
        'columns': {
            'IETESTCD': {'literal': 'ELIG'},
            'IEORRES': {
                'source': 'Value',
                'value_mapping': {'Yes': 'Y', 'No': 'N'}
            }
        }
    }]
    
    dfs = processor.process('IE', sources, df_long, ['SubjectKey'])
    assert len(dfs) == 1
    
    result_df = dfs[0]
    assert list(result_df['IEORRES']) == ['Y', 'N']
