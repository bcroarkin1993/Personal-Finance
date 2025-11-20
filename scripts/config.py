import os
from configparser import ConfigParser

# Get project root (two levels up from this script)
base_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to reach the project root
project_root = os.path.abspath(os.path.join(base_dir, ".."))
# Set the path to the config.ini file
config_path = os.path.join(project_root, "config", "config.ini")

# Load config
config = ConfigParser()
config.read(config_path)

# Access run mode
RUN_MODE = config.get("ENVIRONMENT", "run_mode").lower()