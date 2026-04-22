"""Accounts commands: list, get, delete, get-data-sharing-settings, patch."""

from __future__ import annotations

import csv
import io
import json
from enum import Enum
from typing import Annotated, Optional

import typer
from google.analytics.admin_v1beta import types as admin_types
from google.protobuf import field_mask_pb2
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


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _get_client():
    """Load config, authenticate, and return an admin API client.

    Raises:
        typer.Exit: with code 1 when authentication fails.
    """
    config = cfg.load_config()
    try:
        creds = get_credentials(config)
    except AuthError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    return build_admin_client(creds)


# ---------------------------------------------------------------------------
# Shared account rendering
# ---------------------------------------------------------------------------

def _account_to_dict(account) -> dict:
    """Convert an account resource to a flat dict for JSON/CSV output."""
    account_id = account.name.split("/")[-1]
    return {
        "account_id": account_id,
        "display_name": account.display_name,
        "create_time": str(account.create_time),
        "update_time": str(account.update_time),
        "region_code": account.region_code,
        "deleted": account.deleted,
    }


_ACCOUNT_FIELDS = [
    "account_id",
    "display_name",
    "create_time",
    "update_time",
    "region_code",
    "deleted",
]


def _render_account(account, output: OutputFormat) -> None:
    """Render an account resource in the requested format."""
    account_id = account.name.split("/")[-1]
    data = _account_to_dict(account)

    if output == OutputFormat.json:
        typer.echo(json.dumps(data, indent=2, default=str))
        return

    if output == OutputFormat.csv:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_ACCOUNT_FIELDS)
        writer.writeheader()
        writer.writerow(data)
        typer.echo(buf.getvalue().rstrip())
        return

    # Default: rich key/value table
    table = Table(title=f"Account {account_id}", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    for field in _ACCOUNT_FIELDS:
        table.add_row(field, str(data[field]))
    console.print(table)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@accounts_app.command("list")
def list_accounts(
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """List all GA4 accounts accessible to the authenticated user."""
    client = _get_client()
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


@accounts_app.command("get")
def get_account(
    account_id: Annotated[
        str,
        typer.Option("--account-id", help="GA4 Account ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Get details for a specific GA4 account."""
    client = _get_client()
    account = client.get_account(name=f"accounts/{account_id}")
    _render_account(account, output)


@accounts_app.command("delete")
def delete_account(
    account_id: Annotated[
        str,
        typer.Option("--account-id", help="GA4 Account ID"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Move a GA4 account to trash (recoverable within 30 days)."""
    client = _get_client()

    if not force:
        account = client.get_account(name=f"accounts/{account_id}")
        display_name = account.display_name
        try:
            typer.confirm(
                f"Delete account {account_id} ({display_name})?",
                abort=True,
            )
        except typer.Abort:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete_account(name=f"accounts/{account_id}")
    typer.echo(
        f"Account {account_id} moved to trash. "
        "It can be recovered from the GA4 UI within 30 days."
    )


@accounts_app.command("get-data-sharing-settings")
def get_data_sharing_settings(
    account_id: Annotated[
        str,
        typer.Option("--account-id", help="GA4 Account ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Get data sharing settings for a GA4 account."""
    client = _get_client()
    settings = client.get_data_sharing_settings(
        name=f"accounts/{account_id}/dataSharingSettings"
    )

    # Ordered list of (field_name, label) tuples
    fields = [
        ("sharing_with_google_support_enabled", "Sharing With Google Support"),
        ("sharing_with_google_assigned_sales_enabled", "Sharing With Google Assigned Sales"),
        ("sharing_with_google_any_sales_enabled", "Sharing With Google Any Sales (Deprecated)"),
        ("sharing_with_google_products_enabled", "Sharing With Google Products"),
        ("sharing_with_others_enabled", "Sharing With Others"),
    ]

    data: dict[str, bool] = {
        field: getattr(settings, field) for field, _ in fields
    }

    if output == OutputFormat.json:
        typer.echo(json.dumps(data, indent=2))
        return

    if output == OutputFormat.csv:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["setting", "enabled"])
        for field, _ in fields:
            writer.writerow([field, data[field]])
        typer.echo(buf.getvalue().rstrip())
        return

    # Default: rich table
    table = Table(title=f"Data Sharing Settings — Account {account_id}", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Enabled", style="white")
    for field, label in fields:
        value = "Yes" if data[field] else "No"
        table.add_row(label, value)
    console.print(table)


@accounts_app.command("patch")
def patch_account(
    account_id: Annotated[
        str,
        typer.Option("--account-id", help="GA4 Account ID"),
    ],
    display_name: Annotated[
        str,
        typer.Option("--display-name", help="New display name for the account"),
    ],
    region_code: Annotated[
        Optional[str],
        typer.Option("--region-code", help="New region code (e.g. IE, US)"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Update a GA4 account's display name and/or region code."""
    client = _get_client()

    account = admin_types.Account(
        name=f"accounts/{account_id}",
        display_name=display_name,
    )
    mask_paths = ["display_name"]

    if region_code:
        account.region_code = region_code
        mask_paths.append("region_code")

    mask = field_mask_pb2.FieldMask(paths=mask_paths)
    updated = client.update_account(account=account, update_mask=mask)
    _render_account(updated, output)
