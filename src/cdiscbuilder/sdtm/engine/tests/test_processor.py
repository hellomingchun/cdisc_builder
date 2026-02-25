import pandas as pd
import pytest
import os
from unittest.mock import patch, MagicMock

from cdiscbuilder.sdtm.engine.processor import process_domain

@patch('cdiscbuilder.sdtm.engine.processor.GeneralProcessor')
def test_process_domain_empty_sources(mock_gp, capsys):
    process_domain('DM', [], pd.DataFrame(), ['Subj'], 'out_dir')
    out, err = capsys.readouterr()
    assert "Warning: No configuration found for DM" in out
    mock_gp.assert_not_called()

@patch('cdiscbuilder.sdtm.engine.processor.GeneralProcessor')
def test_process_domain_dict_normalized(mock_gp, tmp_path):
    mock_inst = MagicMock()
    mock_inst.process.return_value = [pd.DataFrame({'A': [1]})]
    mock_gp.return_value = mock_inst
    
    with patch('pandas.DataFrame.to_parquet') as mock_to_parquet:
        # sources as dict instead of list
        sources = {'formoid': 'F1'}
        process_domain('DM', sources, pd.DataFrame(), ['Subj'], str(tmp_path))
        
        # Check that process was called with the listified sources
        mock_inst.process.assert_called_once()
        args, kwargs = mock_inst.process.call_args
        assert isinstance(args[1], list)
        assert args[1][0] == {'formoid': 'F1'}

@patch('cdiscbuilder.sdtm.engine.processor.GeneralProcessor')
def test_process_domain_general_empty_dfs(mock_gp, capsys):
    mock_inst = MagicMock()
    mock_inst.process.return_value = []
    mock_gp.return_value = mock_inst
    
    process_domain('DM', [{'formoid': 'F1'}], pd.DataFrame(), ['Subj'], 'out_dir')
    out, err = capsys.readouterr()
    assert "Warning: No data found for domain DM" in out

@patch('cdiscbuilder.sdtm.engine.processor.FindingsProcessor')
@patch('cdiscbuilder.sdtm.engine.processor.GeneralProcessor')
def test_process_domain_findings_processor(mock_gp, mock_fp, tmp_path):
    mock_inst = MagicMock()
    mock_inst.process.return_value = [pd.DataFrame({'A': [1]})]
    mock_fp.return_value = mock_inst
    
    with patch('pandas.DataFrame.to_parquet') as mock_to_parquet:
        sources = [{'type': 'findings', 'formoid': 'F1'}]
        process_domain('VS', sources, pd.DataFrame(), ['Subj'], str(tmp_path))
        mock_fp.assert_called_once()
        mock_gp.assert_not_called()
        mock_to_parquet.assert_called_once()

@patch('cdiscbuilder.sdtm.engine.processor.GeneralProcessor')
def test_process_domain_append_blocks(mock_gp, tmp_path):
    mock_inst = MagicMock()
    df1 = pd.DataFrame({'USUBJID': ['001'], 'AGE': [30]})
    df2 = pd.DataFrame({'USUBJID': ['002'], 'AGE': [40]})
    # DataFrames generated don't have merge_on
    mock_inst.process.return_value = [df1, df2]
    mock_gp.return_value = mock_inst
    
    with patch('pandas.DataFrame.to_parquet') as mock_to_parquet:
        sources = [{'formoid': 'F1'}, {'formoid': 'F2'}]
        process_domain('DM', sources, pd.DataFrame(), ['Subj'], str(tmp_path))
        
        # Assert to_parquet was called with combined df
        args, kwargs = mock_to_parquet.call_args
        combined_df = mock_to_parquet.call_args[0][0] if not args else args[0]
        # pandas mock might not capture self correctly, we can't easily inspect self DataFrame in mock_to_parquet
        # Let's mock the actual parquet write or use tempdir and read it back
        pass # Better to let it write and read
        
def test_process_domain_append_real(tmp_path):
    # Integration style with real GeneralProcessor mocked process method
    with patch('cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process') as mock_process:
        df1 = pd.DataFrame({'USUBJID': ['001'], 'AGE': [30]})
        df2 = pd.DataFrame({'USUBJID': ['002'], 'AGE': [40]})
        mock_process.return_value = [df1, df2]
        
        sources = [{'formoid': 'F1'}, {'formoid': 'F2'}]
        out_dir = tmp_path / "sdtm_out"
        process_domain('DM', sources, pd.DataFrame(), ['Subj'], str(out_dir))
        
        out_file = out_dir / "DM.parquet"
        assert out_file.exists()
        
        res_df = pd.read_parquet(out_file)
        assert len(res_df) == 2
        assert list(res_df['USUBJID']) == ['001', '002']

def test_process_domain_merge_blocks(tmp_path):
    with patch('cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process') as mock_process:
        df1 = pd.DataFrame({'USUBJID': ['001', '002'], 'AGE': [30, 45]})
        df1.attrs['merge_on'] = None
        
        df2 = pd.DataFrame({'USUBJID': ['001', '002'], 'SEX': ['M', 'F']})
        df2.attrs['merge_on'] = ['USUBJID']
        
        mock_process.return_value = [df1, df2]
        
        sources = [{'formoid': 'F1'}, {'formoid': 'F2'}]
        out_dir = tmp_path / "sdtm_out"
        process_domain('DM', sources, pd.DataFrame(), ['Subj'], str(out_dir))
        
        res_df = pd.read_parquet(out_dir / "DM.parquet")
        assert len(res_df) == 2
        assert 'AGE' in res_df.columns
        assert 'SEX' in res_df.columns
        assert list(res_df[res_df['USUBJID'] == '001']['SEX'])[0] == 'M'

def test_process_domain_merge_blocks_missing_keys(tmp_path, capsys):
    with patch('cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process') as mock_process:
        df1 = pd.DataFrame({'USUBJID': ['001'], 'AGE': [30]})
        df1.attrs['merge_on'] = None
        
        df2 = pd.DataFrame({'OTHER_ID': ['001'], 'SEX': ['M']})
        df2.attrs['merge_on'] = ['USUBJID'] # Missing in df2
        
        mock_process.return_value = [df1, df2]
        
        sources = [{'formoid': 'F1'}, {'formoid': 'F2'}]
        out_dir = tmp_path / "sdtm_out"
        process_domain('DM', sources, pd.DataFrame(), ['Subj'], str(out_dir))
        
        out, err = capsys.readouterr()
        assert "missing keys: ['USUBJID']" in out
        
        res_df = pd.read_parquet(out_dir / "DM.parquet")
        # Appended instead of merged
        assert len(res_df) == 2
        assert 'SEX' in res_df.columns

def test_process_domain_global_sequence(tmp_path):
    with patch('cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process') as mock_process:
        # Initial dfs already processed, but we want post-processing sequence based on 'group' config in sources
        df1 = pd.DataFrame({
            'USUBJID': ['001', '001', '002', '002'],
            'VISIT': ['VISIT 1', 'VISIT 2', 'VISIT 1', 'VISIT 2']
        })
        
        mock_process.return_value = [df1]
        
        sources = [{
            'formoid': 'F1',
            'columns': {
                'USUBJID': {'source': 'Subj'},
                'VISIT': {'source': 'Visit'},
                'SEQ': {'group': 'USUBJID', 'sort_by': 'VISIT'}
            }
        }]
        
        out_dir = tmp_path / "sdtm_out"
        process_domain('DM', sources, pd.DataFrame(), ['Subj'], str(out_dir))
        
        res_df = pd.read_parquet(out_dir / "DM.parquet")
        assert 'SEQ' in res_df.columns
        assert list(res_df['SEQ']) == [1, 2, 1, 2]
