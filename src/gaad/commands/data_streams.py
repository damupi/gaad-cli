"""Data Streams commands: list, get, create, patch, delete."""

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

data_streams_app = typer.Typer(name="data-streams", help="Data Streams management commands")


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


def _stream_to_dict(stream) -> dict:
    """Convert a data stream resource to a flat dict for JSON/CSV output.

    Args:
        stream: A GA4 DataStream resource object.

    Returns:
        A flat dictionary with all stream fields including type-specific ones.
    """
    stream_id = stream.name.split("/")[-1]
    stream_type = stream.type_.name if hasattr(stream.type_, "name") else str(stream.type_)

    data: dict = {
        "stream_id": stream_id,
        "display_name": stream.display_name,
        "type": stream_type,
        "create_time": str(stream.create_time),
        "update_time": str(stream.update_time),
    }

    # WEB_DATA_STREAM type-specific fields
    if stream.web_stream_data:
        data["measurement_id"] = stream.web_stream_data.measurement_id
        data["default_uri"] = stream.web_stream_data.default_uri
        data["firebase_app_id"] = stream.web_stream_data.firebase_app_id

    # ANDROID_APP_DATA_STREAM type-specific fields
    if stream.android_app_stream_data:
        data["package_name"] = stream.android_app_stream_data.package_name
        data["firebase_app_id"] = stream.android_app_stream_data.firebase_app_id

    # IOS_APP_DATA_STREAM type-specific fields
    if stream.ios_app_stream_data:
        data["bundle_id"] = stream.ios_app_stream_data.bundle_id
        data["firebase_app_id"] = stream.ios_app_stream_data.firebase_app_id

    return data


def _render_stream(stream, output: OutputFormat) -> None:
    """Render a data stream resource in the requested format.

    Args:
        stream: A GA4 DataStream resource object.
        output: The desired output format.
    """
    stream_id = stream.name.split("/")[-1]
    data = _stream_to_dict(stream)
    fields = list(data.keys())

    if output == OutputFormat.json:
        typer.echo(json.dumps(data, indent=2, default=str))
        return

    if output == OutputFormat.csv:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        writer.writerow(data)
        typer.echo(buf.getvalue().rstrip())
        return

    # Default: rich key/value table
    table = Table(title=f"Data Stream {stream_id}", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    for field in fields:
        table.add_row(field, str(data[field]))
    console.print(table)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@data_streams_app.command("list")
def list_data_streams(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """List all data streams for a GA4 property."""
    client = _get_client()
    streams = list(client.list_data_streams(parent=f"properties/{property_id}"))

    rows: list[dict[str, str]] = [
        {
            "stream_id": s.name.split("/")[-1],
            "display_name": s.display_name,
            "type": s.type_.name if hasattr(s.type_, "name") else str(s.type_),
        }
        for s in streams
    ]

    if output == OutputFormat.json:
        typer.echo(json.dumps(rows, indent=2))
        return

    if output == OutputFormat.csv:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["stream_id", "display_name", "type"])
        writer.writeheader()
        writer.writerows(rows)
        typer.echo(buf.getvalue().rstrip())
        return

    # Default: rich table
    table = Table(title=f"Data Streams — Property {property_id}", show_header=True)
    table.add_column("Stream ID", style="cyan")
    table.add_column("Display Name", style="white")
    table.add_column("Type", style="green")
    for row in rows:
        table.add_row(row["stream_id"], row["display_name"], row["type"])
    console.print(table)


@data_streams_app.command("get")
def get_data_stream(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    stream_id: Annotated[
        str,
        typer.Option("--stream-id", help="Data Stream ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Get details for a specific data stream."""
    client = _get_client()
    stream = client.get_data_stream(
        name=f"properties/{property_id}/dataStreams/{stream_id}"
    )
    _render_stream(stream, output)


@data_streams_app.command("create")
def create_data_stream(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    display_name: Annotated[
        str,
        typer.Option("--display-name", help="Display name for the data stream"),
    ],
    stream_type: Annotated[
        str,
        typer.Option(
            "--type",
            help="Stream type: WEB_DATA_STREAM, ANDROID_APP_DATA_STREAM, IOS_APP_DATA_STREAM",
        ),
    ],
    default_uri: Annotated[
        Optional[str],
        typer.Option("--default-uri", help="Default URI for web streams (e.g. https://example.com)"),
    ] = None,
    package_name: Annotated[
        Optional[str],
        typer.Option("--package-name", help="Android package name (e.g. com.example.app)"),
    ] = None,
    bundle_id: Annotated[
        Optional[str],
        typer.Option("--bundle-id", help="iOS bundle ID (e.g. com.example.app)"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Create a new data stream for a GA4 property."""
    # Validate type-specific required options
    if stream_type == "ANDROID_APP_DATA_STREAM" and not package_name:
        err_console.print(
            "[red]Error:[/red] --package-name is required for ANDROID_APP_DATA_STREAM"
        )
        raise typer.Exit(code=1)

    if stream_type == "IOS_APP_DATA_STREAM" and not bundle_id:
        err_console.print(
            "[red]Error:[/red] --bundle-id is required for IOS_APP_DATA_STREAM"
        )
        raise typer.Exit(code=1)

    client = _get_client()

    stream = admin_types.DataStream(
        display_name=display_name,
        type_=stream_type,
    )

    if stream_type == "WEB_DATA_STREAM":
        stream.web_stream_data = admin_types.DataStream.WebStreamData(
            default_uri=default_uri or ""
        )
    elif stream_type == "ANDROID_APP_DATA_STREAM":
        stream.android_app_stream_data = admin_types.DataStream.AndroidAppStreamData(
            package_name=package_name
        )
    elif stream_type == "IOS_APP_DATA_STREAM":
        stream.ios_app_stream_data = admin_types.DataStream.IosAppStreamData(
            bundle_id=bundle_id
        )

    created = client.create_data_stream(
        parent=f"properties/{property_id}",
        data_stream=stream,
    )
    _render_stream(created, output)


@data_streams_app.command("patch")
def patch_data_stream(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    stream_id: Annotated[
        str,
        typer.Option("--stream-id", help="Data Stream ID"),
    ],
    display_name: Annotated[
        Optional[str],
        typer.Option("--display-name", help="New display name for the data stream"),
    ] = None,
    default_uri: Annotated[
        Optional[str],
        typer.Option("--default-uri", help="New default URI for web streams"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Update a data stream's display name and/or default URI."""
    if not display_name and default_uri is None:
        err_console.print(
            "[red]Error:[/red] At least one of --display-name or --default-uri must be provided."
        )
        raise typer.Exit(code=1)

    client = _get_client()

    stream = admin_types.DataStream(
        name=f"properties/{property_id}/dataStreams/{stream_id}"
    )
    mask_paths: list[str] = []

    if display_name:
        stream.display_name = display_name
        mask_paths.append("display_name")

    if default_uri is not None:
        stream.web_stream_data = admin_types.DataStream.WebStreamData(
            default_uri=default_uri
        )
        mask_paths.append("web_stream_data.default_uri")

    mask = field_mask_pb2.FieldMask(paths=mask_paths)
    updated = client.update_data_stream(data_stream=stream, update_mask=mask)
    _render_stream(updated, output)


@data_streams_app.command("delete")
def delete_data_stream(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    stream_id: Annotated[
        str,
        typer.Option("--stream-id", help="Data Stream ID"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Delete a data stream (permanent — no soft delete for data streams)."""
    client = _get_client()

    if not force:
        stream = client.get_data_stream(
            name=f"properties/{property_id}/dataStreams/{stream_id}"
        )
        display_name = stream.display_name
        try:
            typer.confirm(
                f"Delete data stream {stream_id} ({display_name})?",
                abort=True,
            )
        except typer.Abort:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete_data_stream(name=f"properties/{property_id}/dataStreams/{stream_id}")
    typer.echo(f"Data stream {stream_id} deleted.")
