import pytest
import polars as pl
from unittest.mock import patch, MagicMock

from cdiscbuilder.adam.adam_derivation.derivations.sql_derivation import SQLDerivation

@pytest.fixture
def mock_target_df():
    return pl.DataFrame({
        "USUBJID": ["S1", "S2"],
        "AGE": [30, 45]
    })

@pytest.fixture
def sql_derivation(mock_target_df):
    deriv = SQLDerivation()
    deriv.col_spec = {"name": "TEST", "_key_vars": ["USUBJID"], "derivation": {}}
    deriv.target_df = mock_target_df
    deriv.source_data = {
        "DM": pl.DataFrame({
            "USUBJID": ["S1", "S2"],
            "DM.AGE": [30, 45],
            "DM.SEX": ["M", "F"]
        }),
        "VS": pl.DataFrame({
            "USUBJID": ["S1", "S1", "S2"],
            "VS.VSORRES": [120, 125, 130],
            "VS.VSDTC": ["2023-01-01", "2023-01-02", "2023-01-01"]
        })
    }
    return deriv

def test_derive_constant(sql_derivation):
    sql_derivation.col_spec["derivation"] = {"constant": "Y"}
    result = sql_derivation.derive()
    assert result.to_list() == ["Y", "Y"]

def test_derive_source(sql_derivation):
    sql_derivation.col_spec["derivation"] = {"source": "DM.SEX"}
    result = sql_derivation.derive()
    assert result.to_list() == ["M", "F"]

def test_derive_source_target_col(sql_derivation):
    sql_derivation.col_spec["derivation"] = {"source": "AGE"}
    result = sql_derivation.derive()
    assert result.to_list() == [30, 45]

def test_derive_cut(sql_derivation):
    sql_derivation.col_spec["derivation"] = {
        "cut": {
            "<40": "Young",
            ">=40": "Old"
        },
        "source": "AGE"
    }
    result = sql_derivation.derive()
    assert result.to_list() == ["Young", "Old"]
    
def test_derive_cut_post_processing(sql_derivation):
    sql_derivation.col_spec["derivation"] = {
        "constant": 50,
        "cut": {
            "<40": "Young",
            ">=40": "Old"
        }
    }
    result = sql_derivation.derive()
    assert result.to_list() == ["Old", "Old"]

def test_apply_mapping(sql_derivation):
    sql_derivation.col_spec["derivation"] = {"source": "DM.SEX"}
    sql_derivation.col_spec["value_mapping"] = {"M": "Male", "F": "Female"}
    result = sql_derivation.derive()
    assert result.to_list() == ["Male", "Female"]
    
def test_apply_mapping_case_insensitive(sql_derivation):
    sql_derivation.col_spec["derivation"] = {"source": "DM.SEX"}
    sql_derivation.col_spec["value_mapping"] = {"m": "Male", "f": "Female"}
    sql_derivation.col_spec["case_sensitive"] = False
    result = sql_derivation.derive()
    assert result.to_list() == ["Male", "Female"]

def test_aggregation_max(sql_derivation):
    sql_derivation.col_spec["derivation"] = {
        "source": "VS.VSORRES",
        "aggregation": {"function": "max"}
    }
    result = sql_derivation.derive()
    assert result.to_list() == [125, 130]

def test_aggregation_closest(sql_derivation):
    # Add target date to target_df
    sql_derivation.target_df = sql_derivation.target_df.with_columns(
        pl.Series("DM.RFSTDTC", ["2023-01-02", "2023-01-01"])
    )
    sql_derivation.col_spec["derivation"] = {
        "source": "VS.VSORRES",
        "aggregation": {"function": "closest", "target": "DM.RFSTDTC"}
    }
    result = sql_derivation.derive()
    # S1 is closest to 02 -> 125, S2 is closest to 01 -> 130
    assert result.to_list() == [125, 130]
