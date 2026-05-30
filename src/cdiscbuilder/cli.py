import os
import argparse
from .sdtm.odm_parser import parse_odm_to_long_df, extract_metadata_summary
from .sdtm.sdtm import create_sdtm_datasets


def main():
    parser = argparse.ArgumentParser(description="Convert ODM XML to SDTM Datasets")
    # Determine default config path inside package
    current_dir = os.path.dirname(__file__)
    default_config_path = os.path.join(current_dir, "specs")

    parser.add_argument("--xml", required=True, help="Path to input ODM XML file")
    parser.add_argument(
        "--csv", default="odm_long.csv", help="Path to intermediate long CSV file"
    )
    parser.add_argument(
        "--metadata-summary",
        "-m",
        help="Path to output metadata summary CSV file (Data Dictionary)",
    )
    parser.add_argument(
        "--configs",
        default=default_config_path,
        help="Path to SDTM configuration directory",
    )
    parser.add_argument(
        "--output", default="sdtm_output", help="Path to output SDTM directory"
    )

    args = parser.parse_args()

    # Load defaults from configs directory if present
    defaults = {}
    if args.configs and os.path.exists(args.configs):
        defaults_path = os.path.join(args.configs, "defaults.yaml")
        if os.path.exists(defaults_path):
            import yaml
            try:
                with open(defaults_path, "r") as f:
                    defaults = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load defaults.yaml from {defaults_path}: {e}")

    xml_mapping = defaults.get("xml_mapping")

    # Step 1: ODM XML -> Long CSV
    print(f"--- Step 1: Parsing ODM XML from {args.xml} ---")
    try:
        df = parse_odm_to_long_df(args.xml, xml_mapping=xml_mapping)
        print(f"Parsed {len(df)} rows.")
        df.to_csv(args.csv, index=False)
        print(f"Saved intermediate data to {args.csv}")

        # Generating Metadata Summary
        if args.metadata_summary:
            print("\n--- Generating Metadata Summary (Data Dictionary) ---")
            meta_df = extract_metadata_summary(df)
            meta_df.to_csv(args.metadata_summary, index=False)
            print(
                f"Saved metadata summary to {args.metadata_summary} (Shape: {meta_df.shape})"
            )
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return

    # Step 2: Long CSV -> SDTM Datasets
    print(
        f"\n--- Step 2: Generating SDTM Datasets using configs from {args.configs} ---"
    )
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    try:
        create_sdtm_datasets(args.configs, args.csv, args.output)
        print(f"\nSuccess! SDTM datasets created in {args.output}")
    except Exception as e:
        print(f"Error creating SDTM datasets: {e}")


if __name__ == "__main__":
    main()
