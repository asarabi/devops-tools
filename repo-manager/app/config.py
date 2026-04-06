import os
import yaml

CONFIG_PATH = os.environ.get("CONFIG_PATH", "/app/config.yaml")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)
