"""Properties commands: list, get, create, delete, patch, data-retention settings."""

from __future__ import annotations

import csv
import io
import json
from enum import Enum
from typing import Annotated, Optional

import typer
from google.analytics.admin_v1beta import types as admin_types
from google.analytics.admin_v1beta.types import ListPropertiesRequest
from google.protobuf import field_mask_pb2
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


# ---------------------------------------------------------------------------
# Shared helpers
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


_PROPERTY_FIELDS = [
    "property_id",
    "display_name",
    "property_type",
    "parent",
    "create_time",
    "update_time",
    "time_zone",
    "currency_code",
    "industry_category",
    "service_level",
    "deleted",
]


def _property_to_dict(prop) -> dict[str, str]:
    """Convert a Property resource to a flat dict suitable for JSON/CSV output.

    Args:
        prop: A GA4 Property protobuf object.

    Returns:
        A dictionary with string values for all relevant property fields.
    """
    property_id = prop.name.split("/")[-1]

    def _enum_str(val) -> str:
        if hasattr(val, "name"):
            return str(val.name)
        return str(val)

    return {
        "property_id": property_id,
        "display_name": prop.display_name,
        "property_type": _enum_str(prop.property_type),
        "parent": prop.parent,
        "create_time": str(prop.create_time),
        "update_time": str(prop.update_time),
        "time_zone": prop.time_zone,
        "currency_code": prop.currency_code,
        "industry_category": _enum_str(prop.industry_category),
        "service_level": _enum_str(prop.service_level),
        "deleted": str(prop.deleted),
    }


def _render_property(prop, output: OutputFormat) -> None:
    """Render a Property resource in the requested output format.

    Args:
        prop: A GA4 Property protobuf object.
        output: The desired output format (table, json, or csv).
    """
    data = _property_to_dict(prop)
    property_id = data["property_id"]

    if output == OutputFormat.json:
        typer.echo(json.dumps(data, indent=2))
        return

    if output == OutputFormat.csv:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_PROPERTY_FIELDS)
        writer.writeheader()
        writer.writerow(data)
        typer.echo(buf.getvalue().rstrip())
        return

    # Default: rich key/value table
    table = Table(title=f"Property {property_id}", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    for field in _PROPERTY_FIELDS:
        table.add_row(field, str(data[field]))
    console.print(table)


# ---------------------------------------------------------------------------
# Data retention rendering helpers
# ---------------------------------------------------------------------------

_RETENTION_FIELDS = [
    "event_data_retention",
    "user_data_retention",
    "reset_user_data_on_new_activity",
]


def _retention_to_dict(settings) -> dict:
    """Convert DataRetentionSettings to a flat dict.

    Args:
        settings: A GA4 DataRetentionSettings protobuf object.

    Returns:
        A dictionary with string/bool values for the settings fields.
    """
    return {
        "event_data_retention": str(settings.event_data_retention.name)
        if hasattr(settings.event_data_retention, "name")
        else str(settings.event_data_retention),
        "user_data_retention": str(settings.user_data_retention.name)
        if hasattr(settings.user_data_retention, "name")
        else str(settings.user_data_retention),
        "reset_user_data_on_new_activity": settings.reset_user_data_on_new_activity,
    }


def _render_retention(settings, property_id: str, output: OutputFormat) -> None:
    """Render DataRetentionSettings in the requested output format.

    Args:
        settings: A GA4 DataRetentionSettings protobuf object.
        property_id: The property ID string, used for table title.
        output: The desired output format (table, json, or csv).
    """
    data = _retention_to_dict(settings)

    if output == OutputFormat.json:
        typer.echo(json.dumps(data, indent=2))
        return

    if output == OutputFormat.csv:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_RETENTION_FIELDS)
        writer.writeheader()
        # Normalise bool to string for CSV row
        row = {k: str(v) for k, v in data.items()}
        writer.writerow(row)
        typer.echo(buf.getvalue().rstrip())
        return

    # Default: rich key/value table
    table = Table(title=f"Data Retention — Property {property_id}", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("event_data_retention", str(data["event_data_retention"]))
    table.add_row("user_data_retention", str(data["user_data_retention"]))
    reset_val = "Yes" if data["reset_user_data_on_new_activity"] else "No"
    table.add_row("reset_user_data_on_new_activity", reset_val)
    console.print(table)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@properties_app.command("list")
def list_properties(
    account_id: Annotated[
        Optional[str],
        typer.Option("--account-id", help="GA4 account ID — lists standard properties (parent:accounts/{id})"),
    ] = None,
    property_id: Annotated[
        Optional[str],
        typer.Option("--property-id", help="GA4 property ID — lists subproperties of a rollup (parent:properties/{id})"),
    ] = None,
    show_deleted: Annotated[
        bool,
        typer.Option("--show-deleted", help="Include soft-deleted properties"),
    ] = False,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """List GA4 properties.

    Use --account-id to list properties under an account.
    Use --property-id to list subproperties of a rollup/parent property.
    Exactly one of --account-id or --property-id is required.
    """
    if account_id and property_id:
        err_console.print("[red]Error:[/red] Provide either --account-id or --property-id, not both.")
        raise typer.Exit(code=1)
    if not account_id and not property_id:
        err_console.print("[red]Error:[/red] One of --account-id or --property-id is required.")
        raise typer.Exit(code=1)

    filter_str = (
        f"parent:accounts/{account_id}" if account_id else f"parent:properties/{property_id}"
    )
    client = _get_client()
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
    title = f"Properties for account {account_id}" if account_id else f"Subproperties of property {property_id}"
    table = Table(title=title, show_header=True)
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
    client = _get_client()
    prop = client.get_property(name=f"properties/{property_id}")

    # The legacy get command has a narrower field set; keep it compatible with
    # existing tests that expect only the original fields in JSON output.
    prop_id = prop.name.split("/")[-1]

    def _enum_str(val) -> str:
        if hasattr(val, "name"):
            return str(val.name)
        return str(val)

    data: dict[str, str] = {
        "property_id": prop_id,
        "display_name": prop.display_name,
        "create_time": str(prop.create_time),
        "update_time": str(prop.update_time),
        "currency_code": prop.currency_code,
        "time_zone": prop.time_zone,
        "industry_category": _enum_str(prop.industry_category),
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
        table.add_row(field, str(value))
    console.print(table)


@properties_app.command("create")
def create_property(
    account_id: Annotated[
        str,
        typer.Option("--account-id", help="GA4 account ID (parent)"),
    ],
    display_name: Annotated[
        str,
        typer.Option("--display-name", help="Display name for the new property"),
    ],
    time_zone: Annotated[
        str,
        typer.Option("--time-zone", help="Time zone (e.g. Europe/Dublin)"),
    ],
    currency_code: Annotated[
        Optional[str],
        typer.Option("--currency-code", help="ISO 4217 currency code (default: EUR)"),
    ] = None,
    industry_category: Annotated[
        Optional[str],
        typer.Option(
            "--industry-category",
            help=(
                "Industry category string. Common values: ARTS_AND_ENTERTAINMENT, "
                "AUTOMOTIVE, FINANCE, GAMES, SHOPPING, SPORTS, TECHNOLOGY, TRAVEL, OTHER"
            ),
        ),
    ] = None,
    property_type: Annotated[
        Optional[str],
        typer.Option(
            "--property-type",
            help=(
                "Property type. One of: PROPERTY_TYPE_ORDINARY (default), "
                "PROPERTY_TYPE_SUBPROPERTY, PROPERTY_TYPE_ROLLUP"
            ),
        ),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Create a new GA4 property."""
    client = _get_client()

    prop_obj = admin_types.Property(
        parent=f"accounts/{account_id}",
        display_name=display_name,
        time_zone=time_zone,
        currency_code=currency_code or "EUR",
    )
    if industry_category:
        prop_obj.industry_category = industry_category
    if property_type:
        prop_obj.property_type = property_type

    created = client.create_property(property=prop_obj)
    _render_property(created, output)


@properties_app.command("delete")
def delete_property(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 property ID"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Move a GA4 property to trash (soft-delete, recoverable from GA4 UI)."""
    client = _get_client()

    if not force:
        prop = client.get_property(name=f"properties/{property_id}")
        display_name = prop.display_name
        try:
            typer.confirm(
                f"Delete property {property_id} ({display_name})?",
                abort=True,
            )
        except typer.Abort:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete_property(name=f"properties/{property_id}")
    typer.echo(
        f"Property {property_id} moved to trash. "
        "It can be recovered from the GA4 UI before it is permanently purged."
    )


@properties_app.command("get-data-retention-settings")
def get_data_retention_settings(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 property ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Get data retention settings for a GA4 property."""
    client = _get_client()
    settings = client.get_data_retention_settings(
        name=f"properties/{property_id}/dataRetentionSettings"
    )
    _render_retention(settings, property_id, output)


@properties_app.command("patch")
def patch_property(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 property ID"),
    ],
    display_name: Annotated[
        Optional[str],
        typer.Option("--display-name", help="New display name"),
    ] = None,
    time_zone: Annotated[
        Optional[str],
        typer.Option("--time-zone", help="New time zone (e.g. Europe/Dublin)"),
    ] = None,
    currency_code: Annotated[
        Optional[str],
        typer.Option("--currency-code", help="New ISO 4217 currency code"),
    ] = None,
    industry_category: Annotated[
        Optional[str],
        typer.Option("--industry-category", help="New industry category string"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Update one or more fields on a GA4 property."""
    if not any([display_name, time_zone, currency_code, industry_category]):
        err_console.print(
            "[red]Error:[/red] At least one of --display-name, --time-zone, "
            "--currency-code, or --industry-category must be provided."
        )
        raise typer.Exit(code=1)

    client = _get_client()

    prop_obj = admin_types.Property(name=f"properties/{property_id}")
    mask_paths: list[str] = []

    if display_name:
        prop_obj.display_name = display_name
        mask_paths.append("display_name")
    if time_zone:
        prop_obj.time_zone = time_zone
        mask_paths.append("time_zone")
    if currency_code:
        prop_obj.currency_code = currency_code
        mask_paths.append("currency_code")
    if industry_category:
        prop_obj.industry_category = industry_category
        mask_paths.append("industry_category")

    mask = field_mask_pb2.FieldMask(paths=mask_paths)
    updated = client.update_property(property=prop_obj, update_mask=mask)
    _render_property(updated, output)


@properties_app.command("update-data-retention-settings")
def update_data_retention_settings(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 property ID"),
    ],
    event_data_retention: Annotated[
        Optional[str],
        typer.Option(
            "--event-data-retention",
            help=(
                "Event data retention duration. "
                "One of: TWO_MONTHS, FOURTEEN_MONTHS, TWENTY_SIX_MONTHS, "
                "THIRTY_EIGHT_MONTHS, FIFTY_MONTHS"
            ),
        ),
    ] = None,
    user_data_retention: Annotated[
        Optional[str],
        typer.Option(
            "--user-data-retention",
            help=(
                "User data retention duration. "
                "One of: TWO_MONTHS, FOURTEEN_MONTHS, TWENTY_SIX_MONTHS, "
                "THIRTY_EIGHT_MONTHS, FIFTY_MONTHS"
            ),
        ),
    ] = None,
    reset_user_data: Annotated[
        Optional[bool],
        typer.Option("--reset-user-data/--no-reset-user-data"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Update data retention settings for a GA4 property."""
    if event_data_retention is None and user_data_retention is None and reset_user_data is None:
        err_console.print(
            "[red]Error:[/red] At least one of --event-data-retention, "
            "--user-data-retention, or --reset-user-data/--no-reset-user-data must be provided."
        )
        raise typer.Exit(code=1)

    client = _get_client()

    settings = admin_types.DataRetentionSettings(
        name=f"properties/{property_id}/dataRetentionSettings"
    )
    mask_paths: list[str] = []

    if event_data_retention:
        settings.event_data_retention = event_data_retention
        mask_paths.append("event_data_retention")
    if user_data_retention:
        settings.user_data_retention = user_data_retention
        mask_paths.append("user_data_retention")
    if reset_user_data is not None:
        settings.reset_user_data_on_new_activity = reset_user_data
        mask_paths.append("reset_user_data_on_new_activity")

    mask = field_mask_pb2.FieldMask(paths=mask_paths)
    updated = client.update_data_retention_settings(
        data_retention_settings=settings,
        update_mask=mask,
    )
    _render_retention(updated, property_id, output)
