"""Properties commands: list, get."""

from __future__ import annotations

import csv
import io
import json
from enum import Enum
from typing import Annotated

import typer
from google.analytics.admin_v1beta.types import ListPropertiesRequest
from rich.console import Console
from rich.table import Table

from gaad import config as cfg
from gaad.auth import build_admin_client, get_credentials
from gaad.errors import AuthError

console = Console()
err_console = Console(stderr=True)

properties_app = typer.Typer(name="properties", help="Property management commands")


class OutputFormat(str, Enum):
    """Supported output formats."""

    table = "table"
    json = "json"
    csv = "csv"


@properties_app.command("list")
def list_properties(
    account_id: Annotated[
        str,
        typer.Option("--account-id", help="GA4 account ID to list properties for"),
    ],
    show_deleted: Annotated[
        bool,
        typer.Option("--show-deleted", help="Include soft-deleted properties"),
    ] = False,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """List GA4 properties for a given account."""
    config = cfg.load_config()
    try:
        creds = get_credentials(config)
    except AuthError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    client = build_admin_client(creds)
    filter_str = f"parent:accounts/{account_id}"
    request = ListPropertiesRequest(filter=filter_str, show_deleted=show_deleted)
    props = list(client.list_properties(request))

    rows: list[dict[str, str]] = [
        {
            "property_id": prop.name.split("/")[-1],
            "display_name": prop.display_name,
        }
        for prop in props
    ]

    if output == OutputFormat.json:
        typer.echo(json.dumps(rows, indent=2))
        return

    if output == OutputFormat.csv:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["property_id", "display_name"])
        writer.writeheader()
        writer.writerows(rows)
        typer.echo(buf.getvalue().rstrip())
        return

    # Default: rich table
    table = Table(title=f"Properties for account {account_id}", show_header=True)
    table.add_column("Property ID", style="cyan")
    table.add_column("Display Name", style="white")
    for row in rows:
        table.add_row(row["property_id"], row["display_name"])
    console.print(table)


@properties_app.command("get")
def get_property(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 property ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Get details for a single GA4 property."""
    config = cfg.load_config()
    try:
        creds = get_credentials(config)
    except AuthError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    client = build_admin_client(creds)
    prop = client.get_property(name=f"properties/{property_id}")

    prop_id = prop.name.split("/")[-1]
    data: dict[str, str] = {
        "property_id": prop_id,
        "display_name": prop.display_name,
        "create_time": str(prop.create_time),
        "update_time": str(prop.update_time),
        "currency_code": prop.currency_code,
        "time_zone": prop.time_zone,
        "industry_category": prop.industry_category,
    }

    if output == OutputFormat.json:
        typer.echo(json.dumps(data, indent=2))
        return

    if output == OutputFormat.csv:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(data.keys()))
        writer.writeheader()
        writer.writerow(data)
        typer.echo(buf.getvalue().rstrip())
        return

    # Default: rich table (key-value)
    table = Table(title=f"Property {prop_id}", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    for field, value in data.items():
        table.add_row(field, value)
    console.print(table)
