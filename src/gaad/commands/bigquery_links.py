"""BigQuery link commands: list, get, create, patch, delete."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Annotated, Any, Optional

import typer
from google.analytics.admin_v1alpha import types as alpha_types
from google.api_core.exceptions import (
    AlreadyExists,
    GoogleAPICallError,
    InvalidArgument,
    PermissionDenied,
)
from google.protobuf import field_mask_pb2
from rich.table import Table

from gaad.shared import (
    OutputFormat,
    console,
    err_console,
    extract_id,
    get_client,
    render_csv,
    render_json,
)

bigquery_links_app = typer.Typer(
    name="bigquery-links", help="Manage GA4 BigQuery links (v1alpha)."
)

_PROPERTY_RE = re.compile(r"^properties/(?P<id>\d+)$")
_PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_LINK_ID_RE = re.compile(r"^[^/\s]+$")
_LINK_RE = re.compile(
    r"^properties/(?P<property_id>\d+)/bigQueryLinks/(?P<link_id>[^/\s]+)$"
)
_STREAM_RE = re.compile(
    r"^properties/(?P<property_id>\d+)/dataStreams/(?P<stream_id>\d+)$"
)

BIGQUERY_LINK_FIELDS = [
    "bigquery_link_id",
    "name",
    "project",
    "create_time",
    "dataset_location",
    "daily_export_enabled",
    "streaming_export_enabled",
    "fresh_daily_export_enabled",
    "include_advertising_id",
    "export_streams",
    "excluded_events",
]


def _bad_parameter(message: str) -> typer.BadParameter:
    return typer.BadParameter(message)


def _normalize_property(value: str) -> str:
    """Return a canonical ``properties/{id}`` resource name."""
    value = value.strip()
    if value.isdigit():
        return f"properties/{value}"
    if _PROPERTY_RE.fullmatch(value):
        return value
    raise _bad_parameter(
        "Property must be a numeric ID or a resource name like 'properties/123'."
    )


def _normalize_project(value: str) -> str:
    """Return a canonical ``projects/{id-or-number}`` resource name."""
    value = value.strip()
    if value.startswith("projects/"):
        value = value.removeprefix("projects/")
    if value.isdigit() or _PROJECT_ID_RE.fullmatch(value):
        return f"projects/{value}"
    raise _bad_parameter(
        "Project must be a project number, project ID, or resource name like "
        "'projects/my-project'."
    )


def _normalize_link(value: str, parent: str) -> str:
    """Return a canonical BigQuery link name under *parent*."""
    value = value.strip()
    if not value:
        raise _bad_parameter("BigQuery link ID cannot be empty.")

    if "/" not in value:
        if not _LINK_ID_RE.fullmatch(value):
            raise _bad_parameter("BigQuery link ID cannot contain whitespace.")
        return f"{parent}/bigQueryLinks/{value}"

    match = _LINK_RE.fullmatch(value)
    if not match:
        raise _bad_parameter(
            "BigQuery link must be a bare ID or a resource name like "
            "'properties/123/bigQueryLinks/abc567'."
        )
    if f"properties/{match.group('property_id')}" != parent:
        raise _bad_parameter("BigQuery link belongs to a different property.")
    return value


def _normalize_export_stream(value: str, parent: str) -> str:
    """Return a canonical data-stream resource name under *parent*."""
    value = value.strip()
    if value.isdigit():
        return f"{parent}/dataStreams/{value}"

    match = _STREAM_RE.fullmatch(value)
    if not match:
        raise _bad_parameter(
            "Export stream must be a numeric stream ID or a resource name like "
            "'properties/123/dataStreams/456'."
        )
    if f"properties/{match.group('property_id')}" != parent:
        raise _bad_parameter("Export stream belongs to a different property.")
    return value


def _normalize_event(value: str) -> str:
    value = value.strip()
    if not value:
        raise _bad_parameter("Excluded event names cannot be empty.")
    return value


def _normalize_dataset_location(value: str) -> str:
    value = value.strip()
    if not value:
        raise _bad_parameter("Dataset location cannot be empty.")
    return value


def _call_api(operation: str, call: Callable[[], Any]) -> Any:
    """Execute an API call and turn common failures into actionable CLI errors."""
    try:
        return call()
    except PermissionDenied as exc:
        err_console.print(
            "[red]Error:[/red] Permission denied while trying to "
            f"{operation}. Write operations require the analytics.edit OAuth scope, "
            "permission on the GA4 property, and access to the Google Cloud project."
        )
        err_console.print(f"Google API: {exc}", markup=False)
        raise typer.Exit(code=1) from exc
    except AlreadyExists as exc:
        err_console.print(
            "[red]Error:[/red] A BigQuery link already exists for this property. "
            "Standard GA4 properties generally support one BigQuery link; inspect or "
            "delete the existing link before creating another."
        )
        raise typer.Exit(code=1) from exc
    except InvalidArgument as exc:
        err_console.print(
            "[red]Error:[/red] Invalid BigQuery link request. Check the Google Cloud "
            "project, dataset location, data streams, and event names."
        )
        err_console.print(f"Google API: {exc}", markup=False)
        raise typer.Exit(code=1) from exc
    except GoogleAPICallError as exc:
        err_console.print(f"[red]Error:[/red] Could not {operation}: {exc}")
        raise typer.Exit(code=1) from exc


def _bigquery_link_to_dict(link: alpha_types.BigQueryLink) -> dict:
    """Convert a BigQueryLink resource to JSON/CSV-friendly values."""
    return {
        "bigquery_link_id": extract_id(link.name),
        "name": link.name,
        "project": link.project,
        "create_time": str(link.create_time),
        "dataset_location": link.dataset_location,
        "daily_export_enabled": link.daily_export_enabled,
        "streaming_export_enabled": link.streaming_export_enabled,
        "fresh_daily_export_enabled": link.fresh_daily_export_enabled,
        "include_advertising_id": link.include_advertising_id,
        "export_streams": list(link.export_streams),
        "excluded_events": list(link.excluded_events),
    }


def _csv_row(data: dict) -> dict:
    """Encode repeated fields as JSON arrays inside CSV cells."""
    row = dict(data)
    row["export_streams"] = json.dumps(row["export_streams"])
    row["excluded_events"] = json.dumps(row["excluded_events"])
    return row


def _render_bigquery_link(
    link: alpha_types.BigQueryLink, output: OutputFormat
) -> None:
    """Render a BigQueryLink in table, JSON, or CSV format."""
    data = _bigquery_link_to_dict(link)

    if output == OutputFormat.json:
        render_json(data)
        return
    if output == OutputFormat.csv:
        render_csv([_csv_row(data)], fieldnames=BIGQUERY_LINK_FIELDS)
        return

    table = Table(
        title=f"BigQuery Link {data['bigquery_link_id']}", show_header=True
    )
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    for field in BIGQUERY_LINK_FIELDS:
        value = data[field]
        if isinstance(value, list):
            value = json.dumps(value)
        table.add_row(field, str(value))
    console.print(table)


def _property_option() -> Any:
    return typer.Option(
        "--property-id",
        "--property",
        help="GA4 property ID or properties/{id} resource name",
    )


@bigquery_links_app.command("list")
def list_bigquery_links(
    property_id: Annotated[str, _property_option()],
    output: Annotated[
        OutputFormat, typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.table,
) -> None:
    """List BigQuery links for a GA4 property."""
    parent = _normalize_property(property_id)
    client = get_client("v1alpha")
    links = _call_api(
        "list BigQuery links",
        lambda: list(client.list_big_query_links(parent=parent)),
    )
    rows = [_bigquery_link_to_dict(link) for link in links]

    if output == OutputFormat.json:
        render_json(rows)
        return
    if output == OutputFormat.csv:
        render_csv([_csv_row(row) for row in rows], fieldnames=BIGQUERY_LINK_FIELDS)
        return

    table = Table(
        title=f"BigQuery Links — Property {extract_id(parent)}", show_header=True
    )
    table.add_column("Link ID", style="cyan")
    table.add_column("Project", style="white")
    table.add_column("Location", style="magenta")
    table.add_column("Daily", style="green")
    table.add_column("Streaming", style="yellow")
    table.add_column("Fresh Daily", style="blue")
    for row in rows:
        table.add_row(
            str(row["bigquery_link_id"]),
            str(row["project"]),
            str(row["dataset_location"]),
            str(row["daily_export_enabled"]),
            str(row["streaming_export_enabled"]),
            str(row["fresh_daily_export_enabled"]),
        )
    console.print(table)


@bigquery_links_app.command("get")
def get_bigquery_link(
    property_id: Annotated[str, _property_option()],
    link_id: Annotated[
        str,
        typer.Option(
            "--link-id",
            help="BigQuery link ID or full BigQuery link resource name",
        ),
    ],
    output: Annotated[
        OutputFormat, typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.table,
) -> None:
    """Get a BigQuery link."""
    parent = _normalize_property(property_id)
    name = _normalize_link(link_id, parent)
    client = get_client("v1alpha")
    link = _call_api(
        "get the BigQuery link", lambda: client.get_big_query_link(name=name)
    )
    _render_bigquery_link(link, output)


@bigquery_links_app.command("create")
def create_bigquery_link(
    property_id: Annotated[str, _property_option()],
    project: Annotated[
        str,
        typer.Option(
            "--project", help="Google Cloud project ID, number, or projects/{id}"
        ),
    ],
    dataset_location: Annotated[
        str,
        typer.Option(
            "--dataset-location", help="BigQuery dataset location, such as US or EU"
        ),
    ],
    daily_export: Annotated[
        bool,
        typer.Option(
            "--daily-export/--no-daily-export",
            help="Enable or disable daily export (default: disabled)",
        ),
    ] = False,
    streaming_export: Annotated[
        bool,
        typer.Option(
            "--streaming-export/--no-streaming-export",
            help="Enable or disable streaming export (default: disabled)",
        ),
    ] = False,
    fresh_daily_export: Annotated[
        bool,
        typer.Option(
            "--fresh-daily-export/--no-fresh-daily-export",
            help="Enable or disable fresh daily export (default: disabled)",
        ),
    ] = False,
    include_advertising_id: Annotated[
        bool,
        typer.Option(
            "--include-advertising-id/--no-include-advertising-id",
            help="Include or omit mobile advertising identifiers (default: omitted)",
        ),
    ] = False,
    export_stream: Annotated[
        Optional[list[str]],
        typer.Option(
            "--export-stream",
            help="Data stream ID or full resource name; repeat to export multiple streams",
        ),
    ] = None,
    exclude_event: Annotated[
        Optional[list[str]],
        typer.Option(
            "--exclude-event",
            help="Event name to exclude; repeat to exclude multiple events",
        ),
    ] = None,
    output: Annotated[
        OutputFormat, typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.table,
) -> None:
    """Create a BigQuery link for a GA4 property."""
    parent = _normalize_property(property_id)
    normalized_project = _normalize_project(project)
    location = _normalize_dataset_location(dataset_location)
    streams = [
        _normalize_export_stream(value, parent) for value in (export_stream or [])
    ]
    events = [_normalize_event(value) for value in (exclude_event or [])]

    link = alpha_types.BigQueryLink(
        project=normalized_project,
        dataset_location=location,
        daily_export_enabled=daily_export,
        streaming_export_enabled=streaming_export,
        fresh_daily_export_enabled=fresh_daily_export,
        include_advertising_id=include_advertising_id,
        export_streams=streams,
        excluded_events=events,
    )
    client = get_client("v1alpha")
    created = _call_api(
        "create the BigQuery link",
        lambda: client.create_big_query_link(
            parent=parent, bigquery_link=link
        ),
    )
    _render_bigquery_link(created, output)


@bigquery_links_app.command("patch")
def patch_bigquery_link(
    property_id: Annotated[str, _property_option()],
    link_id: Annotated[
        str,
        typer.Option(
            "--link-id",
            help="BigQuery link ID or full BigQuery link resource name",
        ),
    ],
    daily_export: Annotated[
        Optional[bool],
        typer.Option(
            "--daily-export/--no-daily-export", help="Enable or disable daily export"
        ),
    ] = None,
    streaming_export: Annotated[
        Optional[bool],
        typer.Option(
            "--streaming-export/--no-streaming-export",
            help="Enable or disable streaming export",
        ),
    ] = None,
    fresh_daily_export: Annotated[
        Optional[bool],
        typer.Option(
            "--fresh-daily-export/--no-fresh-daily-export",
            help="Enable or disable fresh daily export",
        ),
    ] = None,
    include_advertising_id: Annotated[
        Optional[bool],
        typer.Option(
            "--include-advertising-id/--no-include-advertising-id",
            help="Include or omit mobile advertising identifiers",
        ),
    ] = None,
    export_stream: Annotated[
        Optional[list[str]],
        typer.Option(
            "--export-stream",
            help="Replacement data stream; repeat to provide the complete new list",
        ),
    ] = None,
    exclude_event: Annotated[
        Optional[list[str]],
        typer.Option(
            "--exclude-event",
            help="Replacement excluded event; repeat to provide the complete new list",
        ),
    ] = None,
    clear_export_streams: Annotated[
        bool,
        typer.Option(
            "--clear-export-streams", help="Replace export streams with an empty list"
        ),
    ] = False,
    clear_excluded_events: Annotated[
        bool,
        typer.Option(
            "--clear-excluded-events",
            help="Replace excluded events with an empty list",
        ),
    ] = False,
    output: Annotated[
        OutputFormat, typer.Option("--output", "-o", help="Output format")
    ] = OutputFormat.table,
) -> None:
    """Update mutable fields on a BigQuery link."""
    if clear_export_streams and export_stream:
        raise _bad_parameter(
            "--clear-export-streams cannot be combined with --export-stream."
        )
    if clear_excluded_events and exclude_event:
        raise _bad_parameter(
            "--clear-excluded-events cannot be combined with --exclude-event."
        )
    if not any(
        [
            daily_export is not None,
            streaming_export is not None,
            fresh_daily_export is not None,
            include_advertising_id is not None,
            export_stream is not None,
            exclude_event is not None,
            clear_export_streams,
            clear_excluded_events,
        ]
    ):
        raise _bad_parameter("At least one mutable field must be provided to patch.")

    parent = _normalize_property(property_id)
    name = _normalize_link(link_id, parent)
    kwargs: dict[str, Any] = {"name": name}
    mask_paths: list[str] = []

    boolean_fields = [
        ("daily_export_enabled", daily_export),
        ("streaming_export_enabled", streaming_export),
        ("fresh_daily_export_enabled", fresh_daily_export),
        ("include_advertising_id", include_advertising_id),
    ]
    for field, value in boolean_fields:
        if value is not None:
            kwargs[field] = value
            mask_paths.append(field)

    if export_stream is not None or clear_export_streams:
        kwargs["export_streams"] = (
            []
            if clear_export_streams
            else [_normalize_export_stream(value, parent) for value in export_stream]
        )
        mask_paths.append("export_streams")

    if exclude_event is not None or clear_excluded_events:
        kwargs["excluded_events"] = (
            []
            if clear_excluded_events
            else [_normalize_event(value) for value in exclude_event]
        )
        mask_paths.append("excluded_events")

    link = alpha_types.BigQueryLink(**kwargs)
    mask = field_mask_pb2.FieldMask(paths=mask_paths)
    client = get_client("v1alpha")
    updated = _call_api(
        "update the BigQuery link",
        lambda: client.update_big_query_link(
            bigquery_link=link, update_mask=mask
        ),
    )
    _render_bigquery_link(updated, output)


@bigquery_links_app.command("delete")
def delete_bigquery_link(
    property_id: Annotated[str, _property_option()],
    link_id: Annotated[
        str,
        typer.Option(
            "--link-id",
            help="BigQuery link ID or full BigQuery link resource name",
        ),
    ],
    force: Annotated[
        bool, typer.Option("--force", help="Skip confirmation prompt")
    ] = False,
) -> None:
    """Permanently delete a BigQuery link."""
    parent = _normalize_property(property_id)
    name = _normalize_link(link_id, parent)
    client = get_client("v1alpha")

    if not force:
        link = _call_api(
            "get the BigQuery link", lambda: client.get_big_query_link(name=name)
        )
        try:
            typer.confirm(
                f"Delete BigQuery link {extract_id(name)} to {link.project}?",
                abort=True,
            )
        except typer.Abort:
            typer.echo("Aborted.")
            raise typer.Exit(code=0)

    _call_api(
        "delete the BigQuery link", lambda: client.delete_big_query_link(name=name)
    )
    typer.echo(f"BigQuery link {extract_id(name)} deleted.")
