"""
Function registry for CDISC builder (SDTM and ADaM).
Maps short function names to full module paths for cleaner specifications.
"""

from .get_bmi import get_bmi
from .calculate_study_day import calculate_study_day
from .extract_value import extract_value
from .get_dose_dates import get_first_dose_date, get_last_dose_date
from .coalesce import coalesce
from .get_last_participation_date import get_last_participation_date
from .get_earliest_informed_consent_date import get_earliest_informed_consent_date

# Function registry mapping short names to full paths
FUNCTION_REGISTRY = {
    # ADaM functions
    "get_bmi": "cdiscbuilder.functions.get_bmi.get_bmi",
    
    # SDTM functions
    "calculate_study_day": "cdiscbuilder.functions.calculate_study_day.calculate_study_day",
    "extract_value": "cdiscbuilder.functions.extract_value.extract_value",
    "get_first_dose_date": "cdiscbuilder.functions.get_dose_dates.get_first_dose_date",
    "get_last_dose_date": "cdiscbuilder.functions.get_dose_dates.get_last_dose_date",
    "coalesce": "cdiscbuilder.functions.coalesce.coalesce",
    "get_last_participation_date": "cdiscbuilder.functions.get_last_participation_date.get_last_participation_date",
    "get_earliest_informed_consent_date": "cdiscbuilder.functions.get_earliest_informed_consent_date.get_earliest_informed_consent_date",
}


def get_function_path(short_name: str) -> str:
    """
    Get the full function path from a short name.

    Args:
        short_name: Short function name (e.g., "get_bmi")

    Returns:
        Full module path (e.g., "cdiscbuilder.functions.get_bmi.get_bmi")

    Raises:
        KeyError: If short name is not found in registry
    """
    if short_name not in FUNCTION_REGISTRY:
        raise KeyError(
            f"Function '{short_name}' not found in registry. "
            f"Available: {list(FUNCTION_REGISTRY.keys())}"
        )

    return FUNCTION_REGISTRY[short_name]


def list_available_functions() -> list[str]:
    """List all available short function names."""
    return list(FUNCTION_REGISTRY.keys())


def register_function(short_name: str, full_path: str) -> None:
    """
    Register a new function mapping.

    Args:
        short_name: Short name to use in specifications
        full_path: Full module path to the function
    """
    FUNCTION_REGISTRY[short_name] = full_path


# Export the main functions
__all__ = [
    "get_bmi",
    "calculate_study_day",
    "extract_value",
    "get_first_dose_date",
    "get_last_dose_date",
    "coalesce",
    "get_last_participation_date",
    "get_earliest_informed_consent_date",
    "get_function_path",
    "list_available_functions",
    "register_function",
    "FUNCTION_REGISTRY",
]
