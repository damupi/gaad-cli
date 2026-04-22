"""Accounts commands: list."""

from __future__ import annotations

import csv
import io
import json
from enum import Enum
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from gaad import config as cfg
from gaad.auth import build_admin_client, get_credentials
from gaad.errors import AuthError

console = Console()
err_console = Console(stderr=True)

accounts_app = typer.Typer(name="accounts", help="Account management commands")


class OutputFormat(str, Enum):
    """Supported output formats."""

    table = "table"
    json = "json"
    csv = "csv"


@accounts_app.command("list")
def list_accounts(
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """List all GA4 accounts accessible to the authenticated user."""
    config = cfg.load_config()
    try:
        creds = get_credentials(config)
    except AuthError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    client = build_admin_client(creds)
    accounts = list(client.list_accounts())

    rows: list[dict[str, str]] = [
        {
            "account_id": acct.name.split("/")[-1],
            "display_name": acct.display_name,
        }
        for acct in accounts
    ]

    if output == OutputFormat.json:
        typer.echo(json.dumps(rows, indent=2))
        return

    if output == OutputFormat.csv:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["account_id", "display_name"])
        writer.writeheader()
        writer.writerows(rows)
        typer.echo(buf.getvalue().rstrip())
        return

    # Default: rich table
    table = Table(title="GA4 Accounts", show_header=True)
    table.add_column("Account ID", style="cyan")
    table.add_column("Display Name", style="white")
    for row in rows:
        table.add_row(row["account_id"], row["display_name"])
    console.print(table)
