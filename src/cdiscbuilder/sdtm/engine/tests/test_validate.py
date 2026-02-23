import os
import yaml
import pytest
from unittest.mock import patch, mock_open

from cdiscbuilder.sdtm.engine.validate import load_schema, validate_domain_config

@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open, read_data="schemas:\n  general_domain:\n    type: list\n")
def test_load_schema_exists(mock_open_file, mock_exists):
    mock_exists.return_value = True
    schema = load_schema()
    assert schema is not None
    assert 'schemas' in schema
    assert 'general_domain' in schema['schemas']

@patch('os.path.exists')
def test_load_schema_not_exists(mock_exists, capfd):
    mock_exists.return_value = False
    schema = load_schema()
    assert schema is None
    
    out, err = capfd.readouterr()
    assert "Schema file not found" in out

def test_validate_domain_config_no_schema():
    assert validate_domain_config("DM", [{"formoid": "f1"}], None) == True

def test_validate_general_domain():
    schema = {
        'schemas': {
            'general_domain': {
                'item_schema': {
                    'required': ['formoid']
                }
            }
        },
        'definitions': {}
    }
    
    # Valid general domain
    valid_config = [{"formoid": "FORM1", "columns": {}}]
    assert validate_domain_config("DM", valid_config, schema) == True
    
    # Invalid: not a list
    invalid_not_list = {"formoid": "FORM1"}
    assert validate_domain_config("DM", invalid_not_list, schema) == False
    
    # Invalid: list items are not dicts
    invalid_items = ["string"]
    assert validate_domain_config("DM", invalid_items, schema) == False
    
    # Invalid: missing required key
    invalid_missing_key = [{"other": "FORM1"}]
    assert validate_domain_config("DM", invalid_missing_key, schema) == False

def test_validate_findings_domain():
    schema = {
        'schemas': {
            'findings_domain': {
                'required': ['type', 'formoid']
            }
        },
        'definitions': {
            'column_findings': {
                'required': ['source']
            }
        }
    }
    
    # Valid findings domain
    valid_config = {
        "type": "FINDINGS",
        "formoid": "FORM1",
        "columns": [{"source": "COL1"}]
    }
    assert validate_domain_config("VS", valid_config, schema) == True
    
    # Invalid: missing required key 'formoid'
    invalid_missing = {
        "type": "FINDINGS",
        "columns": [{"source": "COL1"}]
    }
    assert validate_domain_config("VS", invalid_missing, schema) == False
    
    # Invalid: columns is not a list
    invalid_columns = {
        "type": "FINDINGS",
        "formoid": "FORM1",
        "columns": {}
    }
    assert validate_domain_config("VS", invalid_columns, schema) == False
    
    # Invalid: column items missing required 'source'
    invalid_column_items = {
        "type": "FINDINGS",
        "formoid": "FORM1",
        "columns": [{"other": "COL1"}]
    }
    assert validate_domain_config("VS", invalid_column_items, schema) == False

def test_validate_unrecognized_structure():
    schema = {
        'schemas': {
            'findings_domain': {},
            'general_domain': {}
        },
        'definitions': {}
    }
    
    assert validate_domain_config("UNKNOWN", {"key": "val"}, schema) == False
