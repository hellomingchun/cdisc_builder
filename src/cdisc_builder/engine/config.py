import yaml
import os

from .validate import load_schema, validate_domain_config

def load_config(config_dir):
    """
    Loads all YAML configuration files from the specified directory.
    Validates them against schema.yaml.
    """
    config = {
        'domains': {},
        'defaults': {}
    }

    schema = load_schema()

    if not os.path.exists(config_dir):
        # Fallback to package data if default path doesn't exist?
        # Assuming config_dir provided is valid or we expect empty.
        return config

    for filename in os.listdir(config_dir):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            file_path = os.path.join(config_dir, filename)
            
            # Skip schema itself if present in same dir
            if filename == "schema.yaml":
                continue

            with open(file_path, "r") as f:
                try:
                    data = yaml.safe_load(f)
                    
                    if filename == 'defaults.yaml':
                        # Defaults file - likely flat dict
                        config['defaults'].update(data)
                        continue

                    # Merge data
                    for key, value in data.items():
                        if key == 'defaults':
                             # Fallback if someone put defaults: inside another file
                            config['defaults'].update(value)
                        else:
                            # It's a domain
                            # Validate!
                            if schema:
                                if not validate_domain_config(key, value, schema):
                                    print(f"Warning: {filename} failed schema validation. Proceeding with caution.")
                                    
                            config['domains'][key] = value

                except yaml.YAMLError as exc:
                    print(f"Error parsing YAML file {filename}: {exc}")
    
    return config
