"""Configuration management for gaad-cli.

Manages ~/.config/gaad-cli/config.json.
Override the config directory with the GAAD_CONFIG_DIR environment variable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def get_config_path() -> Path:
    """Return the path to the config file.

    Respects the ``GAAD_CONFIG_DIR`` environment variable for testing.

    Returns:
        Path to ``config.json`` inside the config directory.
    """
    config_dir_env = os.environ.get("GAAD_CONFIG_DIR")
    if config_dir_env:
        config_dir = Path(config_dir_env)
    else:
        config_dir = Path.home() / ".config" / "gaad-cli"
    return config_dir / "config.json"


def load_config() -> dict:
    """Read the config file and return its contents as a dict.

    Returns:
        Parsed JSON dict, or an empty dict if the file does not exist.
    """
    config_file = get_config_path()
    if not config_file.exists():
        return {}
    return json.loads(config_file.read_text(encoding="utf-8"))


def save_config(data: dict) -> None:
    """Write *data* to the config file with 2-space indentation.

    Creates parent directories if they do not exist.

    Args:
        data: Mapping to serialise as JSON.
    """
    config_file = get_config_path()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get(key: str, default=None):
    """Return the value for *key* from the config, or *default* if absent.

    Args:
        key: Config key to look up.
        default: Value to return when *key* is not present.

    Returns:
        Config value or *default*.
    """
    return load_config().get(key, default)


def set(key: str, value) -> None:  # noqa: A001
    """Persist *value* under *key* in the config file.

    Loads current config, updates the key, then saves.

    Args:
        key: Config key to write.
        value: Value to store.
    """
    data = load_config()
    data[key] = value
    save_config(data)


def clear() -> None:
    """Reset the config file to an empty dict."""
    save_config({})
