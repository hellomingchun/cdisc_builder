import pandas as pd
from .engine.config import load_config
from .engine.processor import process_domain


def create_sdtm_datasets(config_input, input_csv, output_dir):
    if isinstance(config_input, dict):
        config = config_input
        # We assume it's already structured correctly or validated
    else:
        config = load_config(config_input)

    # Get global defaults
    defaults = config.get("defaults", {})
    default_keys = defaults.get(
        "keys", ["StudyOID", "SubjectKey", "ItemGroupRepeatKey", "StudyEventOID"]
    )

    print(f"Loading data from {input_csv}...")
    df_long = pd.read_csv(input_csv)

    # Invert mapping to go from custom CSV column name -> standard logical column name
    # e.g., "RecordPosition" -> "ItemGroupRepeatKey"
    csv_columns = defaults.get("csv_columns") or {}
    STANDARD_LOGICAL_COLUMNS = {
        "study_oid": "StudyOID",
        "subject_key": "SubjectKey",
        "study_subject_id": "StudySubjectID",
        "study_event_oid": "StudyEventOID",
        "study_event_repeat_key": "StudyEventRepeatKey",
        "study_event_start_date": "StudyEventStartDate",
        "form_oid": "FormOID",
        "item_group_oid": "ItemGroupOID",
        "item_group_repeat_key": "ItemGroupRepeatKey",
        "item_oid": "ItemOID",
        "value": "Value",
        "question": "Question",
        "item_name": "ItemName",
    }

    custom_to_standard = {}
    rename_map = {}
    for logical_key, custom_col in csv_columns.items():
        if logical_key in STANDARD_LOGICAL_COLUMNS:
            standard_col = STANDARD_LOGICAL_COLUMNS[logical_key]
            rename_map[custom_col] = standard_col
            custom_to_standard[custom_col] = standard_col

    # Perform rename if map is not empty
    if rename_map:
        df_long.rename(columns=rename_map, inplace=True)
        # Translate default_keys to match the standardized DataFrame
        default_keys = [custom_to_standard.get(k, k) for k in default_keys]

    # Prioritize DM domain processing
    domains = list(config["domains"].keys())
    if "DM" in domains:
        domains.remove("DM")
        domains.insert(0, "DM")

    for domain in domains:
        settings_entry = config["domains"][domain]
        print(f"Processing domain: {domain}")

        # Normalize to list.
        if isinstance(settings_entry, list):
            sources = settings_entry
        else:
            sources = [settings_entry]

        process_domain(domain, sources, df_long, default_keys, output_dir, custom_to_standard=custom_to_standard)
