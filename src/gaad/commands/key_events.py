"""Key Events commands: list, get, create, patch, delete."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from google.analytics.admin_v1beta import types as admin_types
from google.protobuf import field_mask_pb2
from rich.table import Table

from gaad.shared import (
    OutputFormat,
    console,
    enum_name,
    err_console,
    extract_id,
    get_client,
    render_csv,
    render_json,
)

key_events_app = typer.Typer(name="key-events", help="Key Events management commands")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _key_event_to_dict(ke) -> dict:
    """Convert a KeyEvent resource to a flat dict for JSON/CSV output.

    Args:
        ke: A GA4 KeyEvent resource object.

    Returns:
        A flat dictionary with all key event fields.
    """
    key_event_id = extract_id(ke.name)
    counting_method = enum_name(ke.counting_method)

    data: dict = {
        "key_event_id": key_event_id,
        "event_name": ke.event_name,
        "counting_method": counting_method,
        "deletable": ke.deletable,
        "custom": ke.custom,
        "create_time": str(ke.create_time),
    }

    if ke.default_value:
        data["default_numeric_value"] = ke.default_value.numeric_value
        data["default_currency_code"] = ke.default_value.currency_code

    return data


def _render_key_event(ke, output: OutputFormat) -> None:
    """Render a KeyEvent resource in the requested format.

    Args:
        ke: A GA4 KeyEvent resource object.
        output: The desired output format.
    """
    key_event_id = extract_id(ke.name)
    data = _key_event_to_dict(ke)
    fields = list(data.keys())

    if output == OutputFormat.json:
        render_json(data)
        return

    if output == OutputFormat.csv:
        render_csv([data], fieldnames=fields)
        return

    # Default: rich key/value table
    table = Table(title=f"Key Event {key_event_id}", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    for field in fields:
        table.add_row(field, str(data[field]))
    console.print(table)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@key_events_app.command("list")
def list_key_events(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """List all key events for a GA4 property."""
    client = get_client()
    key_events = list(client.list_key_events(parent=f"properties/{property_id}"))

    rows: list[dict] = [
        {
            "key_event_id": extract_id(ke.name),
            "event_name": ke.event_name,
            "counting_method": enum_name(ke.counting_method),
            "deletable": ke.deletable,
            "custom": ke.custom,
        }
        for ke in key_events
    ]

    if output == OutputFormat.json:
        render_json(rows)
        return

    if output == OutputFormat.csv:
        fieldnames = ["key_event_id", "event_name", "counting_method", "deletable", "custom"]
        render_csv(rows, fieldnames=fieldnames)
        return

    # Default: rich table
    table = Table(title=f"Key Events — Property {property_id}", show_header=True)
    table.add_column("Key Event ID", style="cyan")
    table.add_column("Event Name", style="white")
    table.add_column("Counting Method", style="green")
    table.add_column("Deletable", style="yellow")
    table.add_column("Custom", style="magenta")
    for row in rows:
        table.add_row(
            str(row["key_event_id"]),
            str(row["event_name"]),
            str(row["counting_method"]),
            str(row["deletable"]),
            str(row["custom"]),
        )
    console.print(table)


@key_events_app.command("get")
def get_key_event(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    key_event_id: Annotated[
        str,
        typer.Option("--key-event-id", help="Key Event ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Get details for a specific key event."""
    client = get_client()
    ke = client.get_key_event(
        name=f"properties/{property_id}/keyEvents/{key_event_id}"
    )
    _render_key_event(ke, output)


@key_events_app.command("create")
def create_key_event(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    event_name: Annotated[
        str,
        typer.Option("--event-name", help="Event name for the key event (immutable after creation)"),
    ],
    counting_method: Annotated[
        str,
        typer.Option(
            "--counting-method",
            help="Counting method: ONCE_PER_EVENT or ONCE_PER_SESSION",
        ),
    ],
    default_numeric_value: Annotated[
        Optional[float],
        typer.Option("--default-numeric-value", help="Default numeric value for the key event"),
    ] = None,
    default_currency_code: Annotated[
        Optional[str],
        typer.Option("--default-currency-code", help="Default currency code (ISO 4217)"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Create a new key event for a GA4 property."""
    # Validate that default value fields are provided together
    has_numeric = default_numeric_value is not None
    has_currency = bool(default_currency_code)
    if has_numeric != has_currency:
        err_console.print(
            "[red]Error:[/red] --default-numeric-value and --default-currency-code "
            "must both be provided together."
        )
        raise typer.Exit(code=1)

    client = get_client()

    ke = admin_types.KeyEvent(
        event_name=event_name,
        counting_method=counting_method,
    )
    if default_numeric_value is not None and default_currency_code:
        ke.default_value = admin_types.KeyEvent.DefaultValue(
            numeric_value=default_numeric_value,
            currency_code=default_currency_code,
        )

    created = client.create_key_event(
        parent=f"properties/{property_id}",
        key_event=ke,
    )
    _render_key_event(created, output)


@key_events_app.command("patch")
def patch_key_event(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    key_event_id: Annotated[
        str,
        typer.Option("--key-event-id", help="Key Event ID"),
    ],
    counting_method: Annotated[
        Optional[str],
        typer.Option(
            "--counting-method",
            help="New counting method: ONCE_PER_EVENT or ONCE_PER_SESSION",
        ),
    ] = None,
    default_numeric_value: Annotated[
        Optional[float],
        typer.Option("--default-numeric-value", help="New default numeric value"),
    ] = None,
    default_currency_code: Annotated[
        Optional[str],
        typer.Option("--default-currency-code", help="New default currency code (ISO 4217)"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Update a key event's counting method and/or default value."""
    has_numeric = default_numeric_value is not None
    has_currency = bool(default_currency_code)

    # Validate partial default_value args
    if has_numeric != has_currency:
        err_console.print(
            "[red]Error:[/red] --default-numeric-value and --default-currency-code "
            "must both be provided together."
        )
        raise typer.Exit(code=1)

    # Require at least one patchable field
    if not counting_method and not (has_numeric and has_currency):
        err_console.print(
            "[red]Error:[/red] At least one of --counting-method or both "
            "--default-numeric-value and --default-currency-code must be provided."
        )
        raise typer.Exit(code=1)

    client = get_client()

    ke = admin_types.KeyEvent(
        name=f"properties/{property_id}/keyEvents/{key_event_id}"
    )
    mask_paths: list[str] = []

    if counting_method:
        ke.counting_method = counting_method
        mask_paths.append("counting_method")

    if has_numeric and has_currency:
        ke.default_value = admin_types.KeyEvent.DefaultValue(
            numeric_value=default_numeric_value,
            currency_code=default_currency_code,
        )
        mask_paths.append("default_value")

    mask = field_mask_pb2.FieldMask(paths=mask_paths)
    updated = client.update_key_event(key_event=ke, update_mask=mask)
    _render_key_event(updated, output)


@key_events_app.command("delete")
def delete_key_event(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    key_event_id: Annotated[
        str,
        typer.Option("--key-event-id", help="Key Event ID"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Delete a key event (permanent)."""
    client = get_client()

    # Always fetch the key event to check deletable and get event_name for the message
    ke = client.get_key_event(
        name=f"properties/{property_id}/keyEvents/{key_event_id}"
    )

    if not ke.deletable:
        err_console.print(
            "[red]Error:[/red] This key event cannot be deleted (deletable=False)."
        )
        raise typer.Exit(code=1)

    event_name = ke.event_name

    if not force:
        try:
            typer.confirm(
                f"Delete key event '{event_name}' ({key_event_id})?",
                abort=True,
            )
        except typer.Abort:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete_key_event(name=f"properties/{property_id}/keyEvents/{key_event_id}")
    typer.echo(f"Key event '{event_name}' ({key_event_id}) deleted.")
