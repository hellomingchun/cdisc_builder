import os
import yaml
import pytest
import tempfile
from unittest.mock import patch, mock_open

from cdiscbuilder.sdtm.engine.config import load_config

def test_load_config_dir_not_exists():
    config = load_config("non_existent_dir")
    assert config == {'domains': {}, 'defaults': {}}

def test_load_config_with_valid_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Create a defaults.yaml
        with open(os.path.join(tmpdirname, "defaults.yaml"), "w") as f:
            yaml.dump({"global_setting": "value1"}, f)
        
        # Create a domain yaml
        with open(os.path.join(tmpdirname, "DM.yaml"), "w") as f:
            yaml.dump({"DM": [{"formoid": "FORM1"}]}, f)
        
        # Create an extra yaml with embedded defaults
        with open(os.path.join(tmpdirname, "AE.yaml"), "w") as f:
            yaml.dump({"AE": [{"formoid": "FORM2"}], "defaults": {"other_setting": "value2"}}, f)
        
        # Create schema.yaml which should be ignored
        with open(os.path.join(tmpdirname, "schema.yaml"), "w") as f:
            yaml.dump({"schemas": {}}, f)
        
        # Mock load_schema to return dummy schema and validate_domain_config to return True
        with patch('cdiscbuilder.sdtm.engine.config.load_schema', return_value={"mock": "schema"}), \
             patch('cdiscbuilder.sdtm.engine.config.validate_domain_config', return_value=True):
            
            config = load_config(tmpdirname)
            
            assert 'domains' in config
            assert 'DM' in config['domains']
            assert config['domains']['DM'] == [{"formoid": "FORM1"}]
            assert 'AE' in config['domains']
            assert config['domains']['AE'] == [{"formoid": "FORM2"}]
            
            assert 'defaults' in config
            assert config['defaults']['global_setting'] == "value1"
            assert config['defaults']['other_setting'] == "value2"

def test_load_config_invalid_yaml(capfd):
    with tempfile.TemporaryDirectory() as tmpdirname:
        with open(os.path.join(tmpdirname, "invalid.yaml"), "w") as f:
            f.write("invalid: [yaml: content")
            
        with patch('cdiscbuilder.sdtm.engine.config.load_schema', return_value=None):
            config = load_config(tmpdirname)
            
            # Check if warning was printed
            out, err = capfd.readouterr()
            assert "Error parsing YAML file" in out
            assert config == {'domains': {}, 'defaults': {}}
