import pandas as pd
from abc import ABC, abstractmethod


class BaseProcessor(ABC):
    def __init__(self):
        self.class_name = "GENERAL"

    @abstractmethod
    def process(self, domain_name, sources, df_long, default_keys, built_domains=None):
        """Main entry point for processing a domain."""
        pass

    def _get_common_identifiers(self, domain_name):
        """Returns standard identifiers for the domain class."""
        return ["STUDYID", "DOMAIN", "USUBJID"]

    def _validate_class_variables(self, df, domain_name):
        """Validates if required variables for the class are present."""
        # This can be expanded based on SDTM spec
        pass

    def _apply_standard_mappings(self, series, col_config):
        """Applies standard SDTM mappings like type conversion and value mapping."""
        if series is None:
            return None

        target_type = col_config.get("type")
        value_map = col_config.get("value_mapping") or col_config.get("mapping_value")
        case_sensitive = col_config.get("case_sensitive", True)

        # 1. Value Mapping
        if value_map:
            if not case_sensitive:
                clean_map = {str(k).lower(): v for k, v in value_map.items()}
                series = (
                    series.astype(str).str.lower().map(clean_map).combine_first(series)
                )
            else:
                series = series.replace(value_map)

        # 2. Prefix
        prefix = col_config.get("prefix")
        if prefix:
            series = prefix + series.astype(str)

        # 3. Type Conversion
        if target_type:
            try:
                if target_type == "int":
                    series = pd.to_numeric(series, errors="coerce").astype("Int64")
                elif target_type == "float":
                    series = pd.to_numeric(series, errors="coerce")
                elif target_type == "date":
                    series = pd.to_datetime(
                        series, errors="coerce", format="mixed"
                    ).dt.strftime("%Y-%m-%d")
                elif target_type == "iso8601":
                    from cdiscbuilder.sdtm.engine.utils.iso8601 import parse_iso8601
                    series = series.apply(parse_iso8601)
                elif target_type == "str":
                    series = series.astype(str).replace("nan", None)
            except Exception as e:
                print(f"Error converting to {target_type}: {e}")

        return series
