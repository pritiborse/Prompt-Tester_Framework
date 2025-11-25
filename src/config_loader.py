# src/config_loader.py
import yaml
import os


class ConfigLoader:
    def __init__(self, config_file: str):
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_file}")
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def get(self, section: str, key: str = None, default=None):
        """
        Safely get a value from the config.
        - section: top-level key (e.g., 'models')
        - key: nested key (e.g., 'wait_time')
        - default: returned if key or section not found
        """
        if not self.config:
            return default

        section_data = self.config.get(section, {})
        if key is None:
            return section_data if section_data else default
        return section_data.get(key, default)

