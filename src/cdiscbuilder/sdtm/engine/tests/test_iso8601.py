import pytest
import pandas as pd
from cdiscbuilder.sdtm.engine.utils.iso8601 import parse_iso8601

def test_parse_iso8601_valid_dates():
    assert parse_iso8601("2026-05-15") == "2026-05-15"
    assert parse_iso8601("2026/05/15") == "2026-05-15"
    assert parse_iso8601("15-MAY-2026") == "2026-05-15"
    assert parse_iso8601("15/05/2026") == "2026-05-15"
    assert parse_iso8601("2026.05.15") == "2026-05-15"

def test_parse_iso8601_partial_dates():
    # ISO 8601 partial dates (Missing Day)
    assert parse_iso8601("2026-05-UNK") == "2026-05"
    assert parse_iso8601("UN-MAY-2026") == "2026-05"
    assert parse_iso8601("2026/05/UN") == "2026-05"
    assert parse_iso8601("UN/05/2026") == "2026-05"

    # ISO 8601 partial dates (Missing Month and Day)
    assert parse_iso8601("2026-UNK-UNK") == "2026"
    assert parse_iso8601("UN-UN-2026") == "2026"
    assert parse_iso8601("UN/UNK/2026") == "2026"
    
def test_parse_iso8601_missing_year():
    # If year is unknown, the whole date is unknown in SDTM
    assert parse_iso8601("UNK-05-15") is None
    assert parse_iso8601("15-MAY-UNK") is None
    assert parse_iso8601("UNK-UNK-UNK") is None
    assert parse_iso8601(None) is None
    assert parse_iso8601("") is None

def test_parse_iso8601_with_time():
    assert parse_iso8601("2026-05-15T12:30:00") == "2026-05-15T12:30:00"
    assert parse_iso8601("2026-05-15 12:30:00") == "2026-05-15T12:30:00"
    
    # Partial date with time (usually time is dropped or invalid, but we keep if possible)
    # Actually, SDTM ISO8601 says you can't have time without complete date.
    # Our function drops time if day is UNK? Wait, if time has UNK, we drop it.
    assert parse_iso8601("2026-05-15TUNK") == "2026-05-15"
