import pytest
import pandas as pd
from cdiscbuilder.sdtm.odm_parser import extract_metadata_summary


def test_extract_metadata_summary_empty():
    # Test with None input
    df_none = extract_metadata_summary(None)
    assert isinstance(df_none, pd.DataFrame)
    assert list(df_none.columns) == [
        "FormOID",
        "ItemGroupOID",
        "ItemOID",
        "ItemName",
        "Question",
        "SampleValues",
    ]
    assert len(df_none) == 0

    # Test with empty DataFrame
    df_empty = extract_metadata_summary(pd.DataFrame())
    assert len(df_empty) == 0


def test_extract_metadata_summary_missing_cols():
    # DataFrame missing required columns
    df_invalid = pd.DataFrame({"FormOID": ["F1"], "ItemOID": ["I1"]})
    with pytest.raises(ValueError) as excinfo:
        extract_metadata_summary(df_invalid)
    assert "missing required metadata columns" in str(excinfo.value)


def test_extract_metadata_summary_valid():
    # Sample long format DataFrame
    data = {
        "FormOID": ["F1", "F1", "F1", "F2", "F1"],
        "ItemGroupOID": ["IG1", "IG1", "IG1", "IG2", "IG1"],
        "ItemOID": ["I1", "I1", "I2", "I3", "I1"],
        "ItemName": ["ITEM1", "ITEM1", "ITEM2", "ITEM3", "ITEM1"],
        "Question": ["Q1", "Q1", "Q2", "Q3", "Q1"],
        "Value": ["Val1", "Val2", "Val3", "Val4", "Val1"],
    }
    df_long = pd.DataFrame(data)

    meta_df = extract_metadata_summary(df_long)

    # Check shape and column names
    assert len(meta_df) == 3  # F1/IG1/I1, F1/IG1/I2, F2/IG2/I3
    assert list(meta_df.columns) == [
        "FormOID",
        "ItemGroupOID",
        "ItemOID",
        "ItemName",
        "Question",
        "SampleValues",
    ]

    # Check deduplication and sorting
    # Sorted order should be: F1/IG1/I1, F1/IG1/I2, F2/IG2/I3
    assert meta_df.iloc[0]["ItemOID"] == "I1"
    assert meta_df.iloc[1]["ItemOID"] == "I2"
    assert meta_df.iloc[2]["ItemOID"] == "I3"

    # Check sample values extraction (up to 3 unique, non-null values)
    # For I1, we have values ['Val1', 'Val2', 'Val3' is for I2, 'Val4' is for I3, 'Val1'] -> unique should be ['Val1', 'Val2']
    assert meta_df.iloc[0]["SampleValues"] == str(["Val1", "Val2"])
    assert meta_df.iloc[1]["SampleValues"] == str(["Val3"])
    assert meta_df.iloc[2]["SampleValues"] == str(["Val4"])


def test_extract_metadata_summary_with_nulls():
    # Sample DataFrame with nulls and empty strings
    data = {
        "FormOID": ["F1", "F1", "F1", "F1"],
        "ItemGroupOID": ["IG1", "IG1", "IG1", "IG1"],
        "ItemOID": ["I1", "I1", "I1", "I1"],
        "ItemName": ["ITEM1", "ITEM1", "ITEM1", "ITEM1"],
        "Question": ["Q1", "Q1", "Q1", "Q1"],
        "Value": [None, "   ", "A", "B"],
    }
    df_long = pd.DataFrame(data)

    meta_df = extract_metadata_summary(df_long)

    # Should ignore None and whitespace-only strings
    assert len(meta_df) == 1
    assert meta_df.iloc[0]["SampleValues"] == str(["A", "B"])
