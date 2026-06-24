import pandas as pd
from .engine.config import load_config
from .engine.processor import process_domain


def _extract_dependencies(domain_name, sources):
    """
    Scan a domain's source configs for cross-domain references (DOMAIN.COLUMN pattern).
    Returns a set of domain names that this domain depends on.
    """
    deps = set()

    if isinstance(sources, dict):
        sources = [sources]

    for source in sources:
        columns = source.get("columns", {})
        for col_name, col_cfg in columns.items():
            if isinstance(col_cfg, dict):
                # Check source field
                src = col_cfg.get("source", "")
                if isinstance(src, str) and "." in src:
                    ref_domain = src.split(".")[0]
                    if ref_domain.isupper() and 2 <= len(ref_domain) <= 4:
                        if ref_domain != domain_name:
                            deps.add(ref_domain)

                # Check function args
                args = col_cfg.get("args", [])
                for arg in args:
                    if isinstance(arg, str) and "." in arg:
                        ref_domain = arg.split(".")[0]
                        if ref_domain.isupper() and 2 <= len(ref_domain) <= 4:
                            if ref_domain != domain_name:
                                deps.add(ref_domain)
    return deps


def _topological_sort(domains_config):
    """
    Build a dependency graph and return domains in build order.
    Raises ValueError on circular dependencies.
    """
    all_domains = set(domains_config.keys())

    # Build dependency graph
    graph = {}
    for domain, sources in domains_config.items():
        if isinstance(sources, dict):
            sources = [sources]
        graph[domain] = _extract_dependencies(domain, sources)

    # DFS-based topological sort
    visited = set()
    temp_mark = set()
    order = []

    def visit(node):
        if node in temp_mark:
            raise ValueError(f"Circular dependency detected involving '{node}'")
        if node in visited:
            return
        temp_mark.add(node)
        for dep in graph.get(node, set()):
            if dep in all_domains:
                visit(dep)
        temp_mark.remove(node)
        visited.add(node)
        order.append(node)

    for domain in all_domains:
        visit(domain)

    return order  # Dependencies come first


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

    # Build dependency-ordered domain list
    try:
        domains = _topological_sort(config["domains"])
        print(f"Build order: {' → '.join(domains)}")
    except ValueError as e:
        print(f"Error: {e}")
        return

    built_domains = {}

    for domain in domains:
        settings_entry = config["domains"][domain]
        print(f"Processing domain: {domain}")

        # Normalize to list.
        if isinstance(settings_entry, list):
            sources = settings_entry
        else:
            sources = [settings_entry]

        result_df = process_domain(
            domain, sources, df_long, default_keys, output_dir,
            custom_to_standard=custom_to_standard,
            built_domains=built_domains,
        )

        if result_df is not None:
            built_domains[domain] = result_df
