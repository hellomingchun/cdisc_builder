import pandas as pd
from cdiscbuilder.sdtm.engine.classes.findings import FindingsProcessor


def test_findings_processor_process():
    processor = FindingsProcessor()
    df_long = pd.DataFrame(
        {
            "StudyOID": ["S1", "S1"],
            "SubjectKey": ["001", "001"],
            "FormOID": ["F1", "F1"],
            "ItemGroupOID": ["IG1", "IG1"],
            "ItemOID": ["IT1", "IT2"],
            "Value": ["V1", "V2"],
        }
    )

    sources = [
        {
            "type": "findings",
            "formoid": "F1",
            "columns": {
                "USUBJID": {"source": "SubjectKey"},
                "VSTESTCD": {"source": "ItemOID"},
                "VSORRES": {"source": "Value"},
            },
        }
    ]

    res = processor.process("VS", sources, df_long, ["StudyOID", "SubjectKey"])
    assert len(res) == 1
    df = res[0]
    assert len(df) == 2
    assert list(df["VSTESTCD"]) == ["IT1", "IT2"]


def test_findings_processor_empty():
    processor = FindingsProcessor()
    df_long = pd.DataFrame(
        columns=["StudyOID", "SubjectKey", "FormOID", "ItemOID", "Value"]
    )
    sources = [{"type": "findings", "formoid": "F1", "columns": {"A": "Value"}}]
    res = processor.process("VS", sources, df_long, [])
    assert len(res) == 0


def test_findings_processor_value_mapping():
    processor = FindingsProcessor()
    df_long = pd.DataFrame({"ItemOID": ["I1", "I2"], "Value": ["1", "2"]})
    sources = [
        {
            "columns": {
                "TEST": {"source": "Value", "value_mapping": {"1": "ONE", "2": "TWO"}}
            }
        }
    ]
    res = processor.process("VS", sources, df_long, [])
    assert list(res[0]["TEST"]) == ["ONE", "TWO"]
