"""
Utility functions for configuration management
"""
import os
import json

def get_config_path():
    """Get the path to the glconfig.json file"""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'glconfig.json')

def load_config():
    """Load configuration from glconfig.json"""
    config_path = get_config_path()
    with open(config_path) as json_file:
        return json.load(json_file)
