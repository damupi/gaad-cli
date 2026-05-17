"""Shared helpers re-exported for convenience."""

from gaad.shared.client import get_client
from gaad.shared.console import console, err_console
from gaad.shared.output import OutputFormat, render_csv, render_json
from gaad.shared.utils import enum_name, extract_id

__all__ = [
    "get_client",
    "console",
    "err_console",
    "OutputFormat",
    "render_json",
    "render_csv",
    "extract_id",
    "enum_name",
]
