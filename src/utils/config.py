# -*- coding: utf-8 -*-

"""
Configuration utilities for csync.

This module provides functions for loading and managing configuration.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv


def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables and/or config file.
    
    This function will:
    1. Load environment variables from .env file if it exists
    2. Load from system environment variables
    3. Load from config file if it exists
    
    Returns:
        Dict[str, Any]: A dictionary containing configuration values.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    config = {}
    
    # Load from environment variables
    config.update(_load_from_env())
    
    # Load from config file if it exists
    config_file = _find_config_file()
    if config_file:
        config.update(_load_from_file(config_file))
    
    return config


def _load_from_env() -> Dict[str, str]:
    """
    Load configuration from environment variables.
    
    Returns:
        Dict[str, str]: A dictionary containing configuration values from env.
    """
    env_vars = {
        "CONFLUENCE_URL": os.environ.get("CONFLUENCE_URL", ""),
        "CONFLUENCE_USERNAME": os.environ.get("CONFLUENCE_USERNAME", ""),
        "ATLASSIAN_TOKEN": os.environ.get("ATLASSIAN_TOKEN", ""),
    }
    
    # Filter out empty values
    return {k: v for k, v in env_vars.items() if v}


def _find_config_file() -> Optional[Path]:
    """
    Find the configuration file in standard locations.
    
    Returns:
        Optional[Path]: Path to the config file if found, None otherwise.
    """
    # Check in current directory
    if Path(".csync.json").exists():
        return Path(".csync.json")
    
    # Check in user's home directory
    home_config = Path.home() / ".csync.json"
    if home_config.exists():
        return home_config
    
    # Check in XDG_CONFIG_HOME if defined
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        xdg_path = Path(xdg_config) / "csync" / "config.json"
        if xdg_path.exists():
            return xdg_path
    
    # Check in ~/.config
    default_config = Path.home() / ".config" / "csync" / "config.json"
    if default_config.exists():
        return default_config
    
    return None


def _load_from_file(config_file: Path) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_file (Path): Path to the configuration file.
    
    Returns:
        Dict[str, Any]: A dictionary containing configuration values from file.
    """
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # If there's an error reading the file, return an empty dict
        return {}


def save_config(
    config: Dict[str, Any], config_file: Optional[Path] = None
) -> None:
    """
    Save configuration to a JSON file.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary to save.
        config_file (Optional[Path]): Path to save the config to.
            If None, saves to ~/.config/csync/config.json
    """
    if config_file is None:
        config_dir = Path.home() / ".config" / "csync"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
    
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
