import pytest
from unittest.mock import patch, MagicMock
import polars as pl

from cdiscbuilder.adam.adam_derivation.engine import AdamDerivation


@pytest.fixture
def mock_spec():
    with patch("cdiscbuilder.adam.adam_derivation.engine.AdamSpec") as mock:
        spec_instance = mock.return_value
        spec_instance._errors = []
        spec_instance.domain = "ADSL"
        spec_instance.key = ["USUBJID"]
        spec_instance.sdtm_dir = "/fake/sdtm"
        spec_instance.adam_dir = "/fake/adam"
        spec_instance.get_data_dependency.return_value = [
            {"adam_variable": "USUBJID", "sdtm_data": "DM", "sdtm_variable": "USUBJID"},
            {"adam_variable": "AGE", "sdtm_data": "DM", "sdtm_variable": "AGE"},
        ]
        spec_instance.get_column_specs.return_value = [
            {"name": "USUBJID", "type": "str"},
            {"name": "AGE", "type": "int", "derivation": {"source": "DM.AGE"}},
        ]
        yield spec_instance


@pytest.fixture
def mock_sdtm_loader():
    with patch("cdiscbuilder.adam.adam_derivation.engine.SDTMLoader") as mock:
        loader_instance = mock.return_value

        # Mock source datasets
        loader_instance.load_datasets.return_value = {
            "DM": pl.DataFrame({"USUBJID": ["SUBJ1", "SUBJ2"], "DM.AGE": [30, 45]})
        }
        yield loader_instance


def test_adam_derivation_init(mock_spec, mock_sdtm_loader):
    engine = AdamDerivation("fake_spec.yaml")
    assert engine.spec is mock_spec
    assert engine.sdtm_loader is mock_sdtm_loader


def test_adam_derivation_build(mock_spec, mock_sdtm_loader):
    engine = AdamDerivation("fake_spec.yaml")

    # Mock derivation behaviour
    with patch.object(engine, "_get_derivation") as mock_get_deriv:
        mock_deriv_instance = MagicMock()
        mock_deriv_instance.derive.return_value = pl.Series([30, 45])
        mock_get_deriv.return_value = mock_deriv_instance

        df = engine.build()

        # Verify
        assert isinstance(df, pl.DataFrame)
        assert df.height == 2
        assert list(df.columns) == ["USUBJID", "AGE"]


def test_adam_derivation_save(mock_spec, mock_sdtm_loader, tmp_path):
    mock_spec.adam_dir = str(tmp_path / "adam")
    engine = AdamDerivation("fake_spec.yaml")

    # Mock build
    with patch.object(
        engine, "build", return_value=pl.DataFrame({"USUBJID": ["SUBJ1"], "AGE": [30]})
    ):
        output_path = engine.save()

        assert output_path.exists()
        df_saved = pl.read_parquet(output_path)
        assert df_saved.height == 1
        assert "AGE" in df_saved.columns


def test_apply_final_type_casting(mock_spec, mock_sdtm_loader):
    engine = AdamDerivation("fake_spec.yaml")

    # Test casting to int
    series = pl.Series(["1", "2"])
    casted = engine._apply_final_type_casting(series, {"name": "TEST", "type": "int"})
    assert casted.dtype == pl.Int64

    # Test casting to bool
    series_bool = pl.Series("TEST", ["yes", "no"])
    casted_bool_expr = engine._apply_final_type_casting(
        series_bool, {"name": "TEST", "type": "bool"}
    )
    # It returns an expression when casting strings to bool
    df = pl.DataFrame([series_bool]).with_columns(casted_bool_expr.alias("TEST"))
    casted_bool = df["TEST"]
    assert casted_bool.dtype == pl.Boolean
    assert casted_bool.to_list() == [True, False]
