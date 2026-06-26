import pytest
import polars as pl
from unittest.mock import patch, MagicMock

from cdiscbuilder.adam.adam_derivation.derivations.function_derivation import FunctionDerivation

@pytest.fixture
def mock_target_df():
    return pl.DataFrame({
        "USUBJID": ["S1", "S2"],
        "HEIGHT": [1.8, 1.6],
        "WEIGHT": [80, 60]
    })

@pytest.fixture
def func_derivation(mock_target_df):
    deriv = FunctionDerivation()
    deriv.col_spec = {"name": "BMI", "derivation": {}}
    deriv.target_df = mock_target_df
    deriv.source_data = {}
    return deriv

def dummy_function(height, weight):
    return pl.Series([h + w for h, w in zip(height, weight)])

def test_derive_function_success(func_derivation):
    func_derivation.col_spec["derivation"] = {
        "function": "dummy",
        "height": "HEIGHT",
        "weight": "WEIGHT"
    }
    
    with patch.object(func_derivation, "_load_function") as mock_load:
        mock_load.return_value = dummy_function
        result = func_derivation.derive()
        
    assert result.to_list() == [81.8, 61.6]

def test_derive_function_missing_name(func_derivation):
    func_derivation.col_spec["derivation"] = {"height": "HEIGHT"}
    with pytest.raises(ValueError, match="requires 'function' field"):
        func_derivation.derive()

def test_derive_function_exception(func_derivation):
    func_derivation.col_spec["derivation"] = {"function": "dummy"}
    
    with patch.object(func_derivation, "_load_function") as mock_load:
        mock_load.side_effect = ValueError("test error")
        result = func_derivation.derive()
        
    assert result.to_list() == [None, None]

def test_load_module_function(func_derivation):
    func = func_derivation._load_module_function("polars.col")
    assert func is pl.col

def test_ensure_series_scalar(func_derivation):
    result = func_derivation._ensure_series(5)
    assert result.to_list() == [5, 5]

def test_ensure_series_list(func_derivation):
    result = func_derivation._ensure_series([1, 2])
    assert result.to_list() == [1, 2]

def test_ensure_series_list_broadcast(func_derivation):
    result = func_derivation._ensure_series([1])
    assert result.to_list() == [1, 1]

def test_ensure_series_list_wrong_length(func_derivation):
    with pytest.raises(ValueError, match="expected 2"):
        func_derivation._ensure_series([1, 2, 3])
