import pandas as pd
from unittest.mock import patch, MagicMock

from cdiscbuilder.sdtm.engine.processor import process_domain


@patch("cdiscbuilder.sdtm.engine.processor.GeneralProcessor")
def test_process_domain_empty_sources(mock_gp, capsys):
    process_domain("DM", [], pd.DataFrame(), ["Subj"], "out_dir")
    out, err = capsys.readouterr()
    assert "Warning: No configuration found for DM" in out
    mock_gp.assert_not_called()


@patch("cdiscbuilder.sdtm.engine.processor.GeneralProcessor")
def test_process_domain_dict_normalized(mock_gp, tmp_path):
    mock_inst = MagicMock()
    mock_inst.process.return_value = [pd.DataFrame({"A": [1]})]
    mock_gp.return_value = mock_inst

    with patch("pandas.DataFrame.to_parquet"):
        # sources as dict instead of list
        sources = {"formoid": "F1"}
        process_domain("DM", sources, pd.DataFrame(), ["Subj"], str(tmp_path))

        # Check that process was called with the listified sources
        mock_inst.process.assert_called_once()
        args, kwargs = mock_inst.process.call_args
        assert isinstance(args[1], list)
        assert args[1][0] == {"formoid": "F1"}


@patch("cdiscbuilder.sdtm.engine.processor.GeneralProcessor")
def test_process_domain_general_empty_dfs(mock_gp, capsys):
    mock_inst = MagicMock()
    mock_inst.process.return_value = []
    mock_gp.return_value = mock_inst

    process_domain("DM", [{"formoid": "F1"}], pd.DataFrame(), ["Subj"], "out_dir")
    out, err = capsys.readouterr()
    assert "Warning: No data found for domain DM" in out


@patch("cdiscbuilder.sdtm.engine.processor.FindingsProcessor")
@patch("cdiscbuilder.sdtm.engine.processor.GeneralProcessor")
def test_process_domain_findings_processor(mock_gp, mock_fp, tmp_path):
    mock_inst = MagicMock()
    mock_inst.process.return_value = [pd.DataFrame({"A": [1]})]
    mock_fp.return_value = mock_inst

    with patch("pandas.DataFrame.to_parquet") as mock_to_parquet:
        sources = [{"type": "findings", "formoid": "F1"}]
        process_domain("VS", sources, pd.DataFrame(), ["Subj"], str(tmp_path))
        mock_fp.assert_called_once()
        mock_gp.assert_not_called()
        mock_to_parquet.assert_called_once()


@patch("cdiscbuilder.sdtm.engine.processor.GeneralProcessor")
def test_process_domain_append_blocks(mock_gp, tmp_path):
    mock_inst = MagicMock()
    df1 = pd.DataFrame({"USUBJID": ["001"], "AGE": [30]})
    df2 = pd.DataFrame({"USUBJID": ["002"], "AGE": [40]})
    # DataFrames generated don't have merge_on
    mock_inst.process.return_value = [df1, df2]
    mock_gp.return_value = mock_inst

    with patch("pandas.DataFrame.to_parquet") as mock_to_parquet:
        sources = [{"formoid": "F1"}, {"formoid": "F2"}]
        process_domain("DM", sources, pd.DataFrame(), ["Subj"], str(tmp_path))

        # Assert to_parquet was called with combined df
        args, kwargs = mock_to_parquet.call_args
        mock_to_parquet.call_args[0][0] if not args else args[0]
        # pandas mock might not capture self correctly, we can't easily inspect self DataFrame in mock_to_parquet
        # Let's mock the actual parquet write or use tempdir and read it back
        pass  # Better to let it write and read


def test_process_domain_append_real(tmp_path):
    # Integration style with real GeneralProcessor mocked process method
    with patch(
        "cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process"
    ) as mock_process:
        df1 = pd.DataFrame({"USUBJID": ["001"], "AGE": [30]})
        df2 = pd.DataFrame({"USUBJID": ["002"], "AGE": [40]})
        mock_process.return_value = [df1, df2]

        sources = [{"formoid": "F1"}, {"formoid": "F2"}]
        out_dir = tmp_path / "sdtm_out"
        process_domain("DM", sources, pd.DataFrame(), ["Subj"], str(out_dir))

        out_file = out_dir / "dm.parquet"
        assert out_file.exists()

        res_df = pd.read_parquet(out_file)
        assert len(res_df) == 2
        assert list(res_df["USUBJID"]) == ["001", "002"]


def test_process_domain_merge_blocks(tmp_path):
    with patch(
        "cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process"
    ) as mock_process:
        df1 = pd.DataFrame({"USUBJID": ["001", "002"], "AGE": [30, 45]})
        df1.attrs["merge_on"] = None

        df2 = pd.DataFrame({"USUBJID": ["001", "002"], "SEX": ["M", "F"]})
        df2.attrs["merge_on"] = ["USUBJID"]

        mock_process.return_value = [df1, df2]

        sources = [{"formoid": "F1"}, {"formoid": "F2"}]
        out_dir = tmp_path / "sdtm_out"
        process_domain("DM", sources, pd.DataFrame(), ["Subj"], str(out_dir))

        res_df = pd.read_parquet(out_dir / "dm.parquet")
        assert len(res_df) == 2
        assert "AGE" in res_df.columns
        assert "SEX" in res_df.columns
        assert list(res_df[res_df["USUBJID"] == "001"]["SEX"])[0] == "M"


def test_process_domain_merge_blocks_missing_keys(tmp_path, capsys):
    with patch(
        "cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process"
    ) as mock_process:
        df1 = pd.DataFrame({"USUBJID": ["001"], "AGE": [30]})
        df1.attrs["merge_on"] = None

        df2 = pd.DataFrame({"OTHER_ID": ["001"], "SEX": ["M"]})
        df2.attrs["merge_on"] = ["USUBJID"]  # Missing in df2

        mock_process.return_value = [df1, df2]

        sources = [{"formoid": "F1"}, {"formoid": "F2"}]
        out_dir = tmp_path / "sdtm_out"
        process_domain("DM", sources, pd.DataFrame(), ["Subj"], str(out_dir))

        out, err = capsys.readouterr()
        assert "missing keys: ['USUBJID']" in out

        res_df = pd.read_parquet(out_dir / "dm.parquet")
        # Appended instead of merged
        assert len(res_df) == 2
        assert "SEX" in res_df.columns


def test_process_domain_global_sequence(tmp_path):
    with patch(
        "cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process"
    ) as mock_process:
        # Initial dfs already processed, but we want post-processing sequence based on 'group' config in sources
        df1 = pd.DataFrame(
            {
                "USUBJID": ["001", "001", "002", "002"],
                "VISIT": ["VISIT 1", "VISIT 2", "VISIT 1", "VISIT 2"],
            }
        )

        mock_process.return_value = [df1]

        sources = [
            {
                "formoid": "F1",
                "columns": {
                    "USUBJID": {"source": "Subj"},
                    "VISIT": {"source": "Visit"},
                    "SEQ": {"group": "USUBJID", "sort_by": "VISIT"},
                },
            }
        ]

        out_dir = tmp_path / "sdtm_out"
        process_domain("DM", sources, pd.DataFrame(), ["Subj"], str(out_dir))

        res_df = pd.read_parquet(out_dir / "dm.parquet")
        assert "SEQ" in res_df.columns
        assert list(res_df["SEQ"]) == [1, 2, 1, 2]


# ==================== SUPP-- Domain Tests ====================


def test_supp_basic_transpose(tmp_path):
    """Verify basic SUPP generation with 2 qualifier columns."""
    with patch(
        "cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process"
    ) as mock_process:
        df = pd.DataFrame(
            {
                "STUDYID": ["S1", "S1"],
                "USUBJID": ["001", "002"],
                "AESEQ": [1, 1],
                "AETERM": ["Headache", "Nausea"],
                "AEACNDEV": ["NONE", "DOSE REDUCED"],
                "AEGRPID": ["GRP1", "GRP2"],
            }
        )
        mock_process.return_value = [df]

        sources = [
            {
                "formoid": "F_AE",
                "columns": {
                    "STUDYID": {"source": "StudyOID"},
                    "USUBJID": {"source": "SubjectKey"},
                    "AESEQ": {"group": ["USUBJID"]},
                    "AETERM": {"source": "I_AE_TERM"},
                    "AEACNDEV": {"source": "I_AE_ACNDEV"},
                    "AEGRPID": {"source": "I_AE_GRPID"},
                },
            },
            {
                "supp": {
                    "idvar": "AESEQ",
                    "columns": {
                        "AEACNDEV": {"label": "Action Taken with Device"},
                        "AEGRPID": {"label": "Group Identifier"},
                    },
                }
            },
        ]

        out_dir = tmp_path / "sdtm_out"
        process_domain("AE", sources, pd.DataFrame(), ["Subj"], str(out_dir))

        # Check SUPP file was created
        supp_file = out_dir / "suppae.parquet"
        assert supp_file.exists()

        supp_df = pd.read_parquet(supp_file)
        assert len(supp_df) == 4  # 2 subjects × 2 qualifiers
        assert set(supp_df.columns) == {
            "STUDYID", "RDOMAIN", "USUBJID", "IDVAR", "IDVARVAL",
            "QNAM", "QLABEL", "QVAL", "QORIG", "QEVAL",
        }
        assert list(supp_df["RDOMAIN"].unique()) == ["AE"]
        assert list(supp_df["IDVAR"].unique()) == ["AESEQ"]
        assert set(supp_df["QNAM"].unique()) == {"AEACNDEV", "AEGRPID"}


def test_supp_drops_blank_qval(tmp_path):
    """Confirm rows with null/blank QVAL are excluded."""
    with patch(
        "cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process"
    ) as mock_process:
        df = pd.DataFrame(
            {
                "STUDYID": ["S1", "S1", "S1"],
                "USUBJID": ["001", "002", "003"],
                "AESEQ": [1, 1, 1],
                "SUPPVAL": ["HAS_VALUE", None, "  "],
            }
        )
        mock_process.return_value = [df]

        sources = [
            {
                "formoid": "F_AE",
                "columns": {
                    "STUDYID": {"source": "StudyOID"},
                    "USUBJID": {"source": "SubjectKey"},
                    "AESEQ": {"group": ["USUBJID"]},
                    "SUPPVAL": {"source": "I_SUPPVAL"},
                },
            },
            {
                "supp": {
                    "idvar": "AESEQ",
                    "columns": {
                        "SUPPVAL": {"label": "Supplemental Value"},
                    },
                }
            },
        ]

        out_dir = tmp_path / "sdtm_out"
        process_domain("AE", sources, pd.DataFrame(), ["Subj"], str(out_dir))

        supp_df = pd.read_parquet(out_dir / "suppae.parquet")
        # Only subject 001 has a non-blank value
        assert len(supp_df) == 1
        assert supp_df.iloc[0]["QVAL"] == "HAS_VALUE"


def test_supp_strips_from_parent(tmp_path):
    """Verify qualifier columns are removed from parent output."""
    with patch(
        "cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process"
    ) as mock_process:
        df = pd.DataFrame(
            {
                "STUDYID": ["S1"],
                "USUBJID": ["001"],
                "AESEQ": [1],
                "AETERM": ["Headache"],
                "AEACNDEV": ["NONE"],
            }
        )
        mock_process.return_value = [df]

        sources = [
            {
                "formoid": "F_AE",
                "columns": {
                    "STUDYID": {"source": "StudyOID"},
                    "USUBJID": {"source": "SubjectKey"},
                    "AESEQ": {"group": ["USUBJID"]},
                    "AETERM": {"source": "I_AE_TERM"},
                    "AEACNDEV": {"source": "I_AE_ACNDEV"},
                },
            },
            {
                "supp": {
                    "idvar": "AESEQ",
                    "columns": {
                        "AEACNDEV": {"label": "Action Taken with Device"},
                    },
                }
            },
        ]

        out_dir = tmp_path / "sdtm_out"
        process_domain("AE", sources, pd.DataFrame(), ["Subj"], str(out_dir))

        # Parent AE should NOT contain the qualifier column
        parent_df = pd.read_parquet(out_dir / "ae.parquet")
        assert "AEACNDEV" not in parent_df.columns
        assert "AETERM" in parent_df.columns  # Non-supp column kept


def test_supp_qlabel_from_label(tmp_path):
    """Verify QLABEL is populated from the label property."""
    with patch(
        "cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process"
    ) as mock_process:
        df = pd.DataFrame(
            {
                "STUDYID": ["S1"],
                "USUBJID": ["001"],
                "AESEQ": [1],
                "AEACNDEV": ["NONE"],
            }
        )
        mock_process.return_value = [df]

        sources = [
            {
                "formoid": "F_AE",
                "columns": {
                    "STUDYID": {"source": "StudyOID"},
                    "USUBJID": {"source": "SubjectKey"},
                    "AESEQ": {"group": ["USUBJID"]},
                    "AEACNDEV": {"source": "I_AE_ACNDEV"},
                },
            },
            {
                "supp": {
                    "idvar": "AESEQ",
                    "columns": {
                        "AEACNDEV": {"label": "Action Taken with Device"},
                    },
                }
            },
        ]

        out_dir = tmp_path / "sdtm_out"
        process_domain("AE", sources, pd.DataFrame(), ["Subj"], str(out_dir))

        supp_df = pd.read_parquet(out_dir / "suppae.parquet")
        assert supp_df.iloc[0]["QLABEL"] == "Action Taken with Device"


def test_supp_auto_resolves_rdomain(tmp_path):
    """Verify RDOMAIN is set to the parent domain name."""
    with patch(
        "cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process"
    ) as mock_process:
        df = pd.DataFrame(
            {
                "STUDYID": ["S1"],
                "USUBJID": ["001"],
                "CMSEQ": [1],
                "CMCLAS": ["ANALGESIC"],
            }
        )
        mock_process.return_value = [df]

        sources = [
            {
                "formoid": "F_CM",
                "columns": {
                    "STUDYID": {"source": "StudyOID"},
                    "USUBJID": {"source": "SubjectKey"},
                    "CMSEQ": {"group": ["USUBJID"]},
                    "CMCLAS": {"source": "I_CM_CLAS"},
                },
            },
            {
                "supp": {
                    "idvar": "CMSEQ",
                    "columns": {
                        "CMCLAS": {"label": "Medication Class"},
                    },
                }
            },
        ]

        out_dir = tmp_path / "sdtm_out"
        process_domain("CM", sources, pd.DataFrame(), ["Subj"], str(out_dir))

        supp_df = pd.read_parquet(out_dir / "suppcm.parquet")
        assert list(supp_df["RDOMAIN"].unique()) == ["CM"]


def test_no_supp_block(tmp_path):
    """Verify no SUPP file is created when no supp block exists."""
    with patch(
        "cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process"
    ) as mock_process:
        df = pd.DataFrame(
            {
                "STUDYID": ["S1"],
                "USUBJID": ["001"],
                "AETERM": ["Headache"],
            }
        )
        mock_process.return_value = [df]

        sources = [
            {
                "formoid": "F_AE",
                "columns": {
                    "STUDYID": {"source": "StudyOID"},
                    "USUBJID": {"source": "SubjectKey"},
                    "AETERM": {"source": "I_AE_TERM"},
                },
            },
        ]

        out_dir = tmp_path / "sdtm_out"
        process_domain("AE", sources, pd.DataFrame(), ["Subj"], str(out_dir))

        # Only the parent domain file should exist
        assert (out_dir / "ae.parquet").exists()
        assert not (out_dir / "suppae.parquet").exists()


# ==================== Cross-Domain Reference Tests ====================

import pytest
from cdiscbuilder.sdtm.sdtm import _extract_dependencies, _topological_sort


def test_topological_sort_basic():
    """DM has no deps, AE depends on DM, CM depends on DM and AE."""
    domains_config = {
        "DM": [{"formoid": "F_DM", "columns": {"STUDYID": {"source": "StudyOID"}}}],
        "AE": [{"formoid": "F_AE", "columns": {"RFSTDTC": {"source": "DM.RFSTDTC"}}}],
        "CM": [{"formoid": "F_CM", "columns": {
            "EPOCH": {"source": "AE.EPOCH"},
            "RFSTDTC": {"source": "DM.RFSTDTC"},
        }}],
    }

    order = _topological_sort(domains_config)
    assert order.index("DM") < order.index("AE")
    assert order.index("DM") < order.index("CM")
    assert order.index("AE") < order.index("CM")


def test_topological_sort_no_deps():
    """All independent domains should all appear in the output."""
    domains_config = {
        "DM": [{"formoid": "F_DM", "columns": {"A": {"source": "X"}}}],
        "AE": [{"formoid": "F_AE", "columns": {"B": {"source": "Y"}}}],
        "VS": [{"formoid": "F_VS", "columns": {"C": {"source": "Z"}}}],
    }

    order = _topological_sort(domains_config)
    assert set(order) == {"DM", "AE", "VS"}


def test_topological_sort_circular():
    """Detect circular dependency."""
    domains_config = {
        "AE": [{"formoid": "F_AE", "columns": {"X": {"source": "CM.Y"}}}],
        "CM": [{"formoid": "F_CM", "columns": {"Y": {"source": "AE.X"}}}],
    }

    with pytest.raises(ValueError, match="Circular dependency"):
        _topological_sort(domains_config)


def test_extract_dependencies_basic():
    """Extract cross-domain dependencies from source configs."""
    sources = [
        {"formoid": "F_AE", "columns": {
            "RFSTDTC": {"source": "DM.RFSTDTC"},
            "EPOCH": {"source": "SE.EPOCH"},
            "AETERM": {"source": "I_AE_TERM"},  # Not a cross-domain ref
        }}
    ]
    deps = _extract_dependencies("AE", sources)
    assert deps == {"DM", "SE"}


def test_extract_dependencies_function_args():
    """Extract deps from function args too."""
    sources = [
        {"formoid": "F_AE", "columns": {
            "AESTDY": {"function": "calculate_study_day", "args": ["AESTDTC", "DM.RFSTDTC"]},
        }}
    ]
    deps = _extract_dependencies("AE", sources)
    assert deps == {"DM"}


def test_cross_domain_source_merge(tmp_path):
    """AE pulls DM.RFSTDTC via USUBJID merge."""
    df_long = pd.DataFrame(
        {
            "SubjectKey": ["001", "002"],
            "FormOID": ["F_AE", "F_AE"],
            "ItemOID": ["I_AE_TERM", "I_AE_TERM"],
            "Value": ["Headache", "Nausea"],
        }
    )

    dm_df = pd.DataFrame(
        {
            "STUDYID": ["S1", "S1"],
            "USUBJID": ["001", "002"],
            "RFSTDTC": ["2026-01-01", "2026-02-01"],
        }
    )

    sources = [
        {
            "formoid": "F_AE",
            "columns": {
                "USUBJID": {"source": "SubjectKey"},
                "AETERM": {"source": "I_AE_TERM"},
                "RFSTDTC": {"source": "DM.RFSTDTC"},
            },
        },
    ]

    out_dir = tmp_path / "sdtm_out"
    built_domains = {"DM": dm_df}
    result = process_domain(
        "AE", sources, df_long, ["SubjectKey"], str(out_dir),
        built_domains=built_domains,
    )

    res_df = pd.read_parquet(out_dir / "ae.parquet")
    assert "RFSTDTC" in res_df.columns
    assert list(res_df["RFSTDTC"]) == ["2026-01-01", "2026-02-01"]


def test_cross_domain_missing_domain(tmp_path, capsys):
    """Graceful warning when referenced domain not found."""
    df_long = pd.DataFrame(
        {
            "SubjectKey": ["001"],
            "FormOID": ["F_AE"],
            "ItemOID": ["I_AE_TERM"],
            "Value": ["Headache"],
        }
    )

    sources = [
        {
            "formoid": "F_AE",
            "columns": {
                "USUBJID": {"source": "SubjectKey"},
                "AETERM": {"source": "I_AE_TERM"},
                "EPOCH": {"source": "SE.EPOCH"},
            },
        },
    ]

    out_dir = tmp_path / "sdtm_out"
    built_domains = {}  # SE not built
    process_domain(
        "AE", sources, df_long, ["SubjectKey"], str(out_dir),
        built_domains=built_domains,
    )

    out, _ = capsys.readouterr()
    assert "Referenced domain 'SE' not available" in out


def test_process_domain_returns_dataframe(tmp_path):
    """process_domain should return the built DataFrame."""
    with patch(
        "cdiscbuilder.sdtm.engine.classes.general.GeneralProcessor.process"
    ) as mock_process:
        df = pd.DataFrame({"STUDYID": ["S1"], "USUBJID": ["001"]})
        mock_process.return_value = [df]

        sources = [{"formoid": "F_DM", "columns": {
            "STUDYID": {"source": "StudyOID"},
            "USUBJID": {"source": "SubjectKey"},
        }}]

        out_dir = tmp_path / "sdtm_out"
        result = process_domain("DM", sources, pd.DataFrame(), ["Subj"], str(out_dir))

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1


