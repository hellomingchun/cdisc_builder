import pandas as pd
import pytest
from cdiscbuilder.sdtm.engine.classes.general import GeneralProcessor


def test_general_processor_expand_settings():
    processor = GeneralProcessor()

    settings = {
        "columns": {
            "USUBJID": {"source": ["SUBJ_A", "SUBJ_B"]},
            "STUDYID": {"literal": ["STUDY_A", "STUDY_B"]},
        }
    }

    expanded = processor._expand_settings(settings)
    assert len(expanded) == 2
    assert expanded[0]["columns"]["USUBJID"]["source"] == "SUBJ_A"
    assert expanded[0]["columns"]["STUDYID"]["literal"] == "STUDY_A"
    assert expanded[1]["columns"]["USUBJID"]["source"] == "SUBJ_B"
    assert expanded[1]["columns"]["STUDYID"]["literal"] == "STUDY_B"


def test_general_processor_expand_settings_mismatch():
    processor = GeneralProcessor()
    settings = {
        "columns": {
            "USUBJID": {"source": ["SUBJ_A", "SUBJ_B"]},
            "STUDYID": {"literal": ["STUDY_A"]},
        }
    }
    with pytest.raises(ValueError, match="mismatch"):
        processor._expand_settings(settings)


def test_general_processor_process():
    processor = GeneralProcessor()

    df_long = pd.DataFrame(
        {
            "SubjectKey": ["001", "001", "002", "002"],
            "FormOID": ["FORM1", "FORM1", "FORM1", "FORM1"],
            "ItemOID": ["AGE", "SEX", "AGE", "SEX"],
            "Value": ["30", "M", "45", "F"],
        }
    )

    sources = [
        {
            "formoid": "FORM1",
            "columns": {
                "USUBJID": {"source": "SubjectKey", "prefix": "SUBJ-"},
                "AGE": {"source": "AGE", "type": "int"},
                "SEX": {
                    "source": "SEX",
                    "value_mapping": {"M": "Male", "F": "Female"},
                    "case_sensitive": False,
                },
                "BLANK_COL": {"literal": "Constant"},
            },
        }
    ]

    default_keys = ["SubjectKey"]

    dfs = processor.process("DM", sources, df_long, default_keys)
    assert len(dfs) == 1

    result_df = dfs[0]
    assert len(result_df) == 2
    assert "USUBJID" in result_df.columns
    assert "AGE" in result_df.columns
    assert "SEX" in result_df.columns
    assert "BLANK_COL" in result_df.columns

    assert list(result_df["USUBJID"]) == ["SUBJ-001", "SUBJ-002"]
    assert list(result_df["AGE"]) == [30, 45]
    assert list(result_df["SEX"]) == ["Male", "Female"]
    assert list(result_df["BLANK_COL"]) == ["Constant", "Constant"]


def test_general_processor_grouping():
    processor = GeneralProcessor()

    df_long = pd.DataFrame(
        {
            "SubjectKey": ["001", "001", "001", "002"],
            "FormOID": ["FORM_TRT", "FORM_TRT", "FORM_TRT", "FORM_TRT"],
            "ItemOID": ["TRT", "TRT", "TRT", "TRT"],  # Multiple treatments
            "Value": ["DrugA", "DrugB", "DrugC", "DrugA"],
            "VisitOID": ["V1", "V2", "V3", "V1"],  # used for sorting
        }
    )

    # We pivot by SubjectKey and VisitOID to get multiple rows per subject
    sources = [
        {
            "formoid": "FORM_TRT",
            "keys": ["SubjectKey", "VisitOID"],
            "columns": {
                "USUBJID": {"source": "SubjectKey"},
                "VISIT": {"source": "VisitOID"},
                "TRTDOSE": {"source": "TRT"},
                "TRTSEQ": {"group": "USUBJID", "sort_by": "VISIT"},
            },
        }
    ]

    dfs = processor.process("EX", sources, df_long, ["SubjectKey"])
    assert len(dfs) == 1

    result_df = dfs[0]
    # Check that sequence sorting worked correctly
    assert list(result_df["USUBJID"]) == ["001", "001", "001", "002"]
    assert list(result_df["TRTSEQ"]) == [1, 2, 3, 1]
