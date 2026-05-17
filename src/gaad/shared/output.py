"""Shared output format helpers."""

from __future__ import annotations

import csv
import io
import json
from enum import Enum

import typer


class OutputFormat(str, Enum):
    """Supported output formats."""

    table = "table"
    json = "json"
    csv = "csv"


def render_json(data: "dict | list") -> None:
    """Print *data* as indented JSON to stdout.

    Args:
        data: A dict or list to serialise.
    """
    typer.echo(json.dumps(data, indent=2, default=str))


def render_csv(rows: list[dict], fieldnames: list[str]) -> None:
    """Print *rows* as CSV (with header) to stdout.

    Args:
        rows: A list of dicts, one per row.
        fieldnames: Ordered list of field names for the CSV header.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    typer.echo(buf.getvalue().rstrip())
