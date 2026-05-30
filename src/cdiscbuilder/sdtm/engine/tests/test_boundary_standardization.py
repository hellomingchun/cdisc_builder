import os
import tempfile
import pandas as pd
import pytest
import yaml
from cdiscbuilder.sdtm.odm_parser import parse_odm_to_long_df
from cdiscbuilder.sdtm.sdtm import create_sdtm_datasets


def test_parse_odm_to_long_df_boundary_standardization():
    # Simple XML string with Medidata style attributes
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <ODM>
      <ClinicalData StudyOID="STUDY_XYZ">
        <SubjectData SubjectKey="SUBJ123">
          <StudyEventData StudyEventOID="SE_VISIT" StartDate="2026-05-29">
            <FormData FormOID="F_AE">
              <ItemGroupData ItemGroupOID="IG_AE" RecordPosition="2">
                <ItemData ItemOID="AE_TERM" Value="Headache"/>
              </ItemGroupData>
            </FormData>
          </StudyEventData>
        </SubjectData>
      </ClinicalData>
    </ODM>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(xml_content)
        temp_xml_path = f.name

    try:
        # Test parsing with custom xml_mapping.
        # Should map the RecordPosition attribute to standard ItemGroupRepeatKey column in df
        xml_mapping = {"item_group_repeat_key": "RecordPosition"}

        df = parse_odm_to_long_df(temp_xml_path, xml_mapping=xml_mapping)

        # Verify output columns are standard (no RecordPosition column is outputted;
        # it is standardized to ItemGroupRepeatKey)
        assert "ItemGroupRepeatKey" in df.columns
        assert "RecordPosition" not in df.columns
        assert df.iloc[0]["ItemGroupRepeatKey"] == "2"
    finally:
        try:
            os.remove(temp_xml_path)
        except Exception:
            pass


def test_create_sdtm_datasets_boundary_standardization(tmp_path):
    # df_long with custom columns: RecordPosition, SubjectID, and no FormOID
    df_long = pd.DataFrame(
        [
            {
                "StudyOID": "STUDY01",
                "SubjectID": "001",
                "RecordPosition": 1,
                "ItemOID": "AETERM",
                "Value": "Headache",
            },
            {
                "StudyOID": "STUDY01",
                "SubjectID": "001",
                "RecordPosition": 1,
                "ItemOID": "AESTDTC",
                "Value": "2026-05-29",
            },
            {
                "StudyOID": "STUDY01",
                "SubjectID": "001",
                "RecordPosition": 2,
                "ItemOID": "AETERM",
                "Value": "Nausea",
            },
            {
                "StudyOID": "STUDY01",
                "SubjectID": "001",
                "RecordPosition": 2,
                "ItemOID": "AESTDTC",
                "Value": "2026-05-30",
            },
        ]
    )

    input_csv = tmp_path / "long.csv"
    df_long.to_csv(input_csv, index=False)

    # Create domain spec directory
    spec_dir = tmp_path / "specs"
    os.makedirs(spec_dir)

    # Create defaults.yaml
    defaults = {
        "keys": ["StudyOID", "SubjectID", "RecordPosition"],
        "csv_columns": {
            "item_group_repeat_key": "RecordPosition",
            "subject_key": "SubjectID",
        },
    }
    with open(spec_dir / "defaults.yaml", "w") as f:
        yaml.dump(defaults, f)

    # Create AE.yaml
    ae_config = {
        "AE": [
            {
                # Note: no formoid specified! So we test proceeding without FormOID filtering.
                "type": "events",
                "columns": {
                    "STUDYID": {"source": "StudyOID"},
                    "USUBJID": {"source": "SubjectKey"},
                    "AETERM": {"source": "AETERM"},
                    "AESTDTC": {"source": "AESTDTC"},
                    "AESEQ": {"group": ["USUBJID"], "sort_by": ["AESTDTC"]},
                },
            }
        ]
    }
    with open(spec_dir / "AE.yaml", "w") as f:
        yaml.dump(ae_config, f)

    output_dir = tmp_path / "sdtm_out"

    # Generate datasets
    create_sdtm_datasets(str(spec_dir), str(input_csv), str(output_dir))

    # Verify dataset exists
    out_file = output_dir / "AE.parquet"
    assert out_file.exists()

    res_df = pd.read_parquet(out_file)
    assert len(res_df) == 2
    assert "AETERM" in res_df.columns
    assert list(res_df["AETERM"]) == ["Headache", "Nausea"]
    assert list(res_df["AESEQ"]) == [1, 2]
