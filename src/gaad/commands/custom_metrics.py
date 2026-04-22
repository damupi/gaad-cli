"""Custom Metrics commands: list, get, create, patch, archive."""

from __future__ import annotations

import csv
import io
import json
from enum import Enum
from typing import Annotated, List, Optional

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

custom_metrics_app = typer.Typer(
    name="custom-metrics", help="Custom Metrics management commands"
)


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


def _metric_to_dict(metric) -> dict:
    """Convert a CustomMetric resource to a flat dict.

    Args:
        metric: A GA4 CustomMetric resource object.

    Returns:
        A flat dictionary with all custom metric fields.
    """
    metric_id = metric.name.split("/")[-1]
    measurement_unit = (
        metric.measurement_unit.name
        if hasattr(metric.measurement_unit, "name")
        else str(metric.measurement_unit)
    )
    scope = metric.scope.name if hasattr(metric.scope, "name") else str(metric.scope)
    restricted = ",".join(
        [str(r.name) if hasattr(r, "name") else str(r) for r in metric.restricted_metric_type]
    )
    return {
        "metric_id": metric_id,
        "parameter_name": metric.parameter_name,
        "display_name": metric.display_name,
        "measurement_unit": measurement_unit,
        "scope": scope,
        "description": metric.description,
        "restricted_metric_type": restricted,
    }


def _render_metric(metric, output: OutputFormat) -> None:
    """Render a CustomMetric resource in the requested format.

    Args:
        metric: A GA4 CustomMetric resource object.
        output: The desired output format.
    """
    metric_id = metric.name.split("/")[-1]
    data = _metric_to_dict(metric)
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
    table = Table(title=f"Custom Metric {metric_id}", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    for field in fields:
        table.add_row(field, str(data[field]))
    console.print(table)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@custom_metrics_app.command("list")
def list_custom_metrics(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """List all custom metrics for a GA4 property."""
    client = _get_client()
    metrics = list(client.list_custom_metrics(parent=f"properties/{property_id}"))

    rows: list[dict] = [
        {
            "metric_id": m.name.split("/")[-1],
            "parameter_name": m.parameter_name,
            "display_name": m.display_name,
            "measurement_unit": (
                m.measurement_unit.name
                if hasattr(m.measurement_unit, "name")
                else str(m.measurement_unit)
            ),
            "scope": m.scope.name if hasattr(m.scope, "name") else str(m.scope),
        }
        for m in metrics
    ]

    if output == OutputFormat.json:
        typer.echo(json.dumps(rows, indent=2, default=str))
        return

    if output == OutputFormat.csv:
        buf = io.StringIO()
        fieldnames = ["metric_id", "parameter_name", "display_name", "measurement_unit", "scope"]
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        typer.echo(buf.getvalue().rstrip())
        return

    # Default: rich table
    table = Table(title=f"Custom Metrics — Property {property_id}", show_header=True)
    table.add_column("Metric ID", style="cyan")
    table.add_column("Parameter Name", style="white")
    table.add_column("Display Name", style="white")
    table.add_column("Measurement Unit", style="green")
    table.add_column("Scope", style="magenta")
    for row in rows:
        table.add_row(
            str(row["metric_id"]),
            str(row["parameter_name"]),
            str(row["display_name"]),
            str(row["measurement_unit"]),
            str(row["scope"]),
        )
    console.print(table)


@custom_metrics_app.command("get")
def get_custom_metric(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    metric_id: Annotated[
        str,
        typer.Option("--metric-id", help="Custom Metric ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Get details for a specific custom metric."""
    client = _get_client()
    metric = client.get_custom_metric(
        name=f"properties/{property_id}/customMetrics/{metric_id}"
    )
    _render_metric(metric, output)


@custom_metrics_app.command("create")
def create_custom_metric(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    parameter_name: Annotated[
        str,
        typer.Option("--parameter-name", help="Parameter name (immutable after creation)"),
    ],
    display_name: Annotated[
        str,
        typer.Option("--display-name", help="Display name"),
    ],
    measurement_unit: Annotated[
        str,
        typer.Option(
            "--measurement-unit",
            help="Measurement unit: STANDARD, CURRENCY, FEET, METERS, KILOMETERS, MILES, "
            "MILLISECONDS, SECONDS, MINUTES, HOURS",
        ),
    ],
    scope: Annotated[
        Optional[str],
        typer.Option("--scope", help="Metric scope (default: EVENT)"),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", help="Optional description"),
    ] = None,
    restricted_metric_type: Annotated[
        Optional[List[str]],
        typer.Option("--restricted-metric-type", help="Restricted metric type: COST_DATA, REVENUE_DATA"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Create a new custom metric for a GA4 property."""
    # Validate CURRENCY + restricted_metric_type rules
    is_currency = measurement_unit.upper() == "CURRENCY"
    has_restricted = bool(restricted_metric_type)

    if is_currency and not has_restricted:
        err_console.print(
            "[red]Error:[/red] --restricted-metric-type is required when "
            "--measurement-unit is CURRENCY."
        )
        raise typer.Exit(code=1)

    if not is_currency and has_restricted:
        err_console.print(
            "[red]Error:[/red] --restricted-metric-type must be empty when "
            "--measurement-unit is not CURRENCY."
        )
        raise typer.Exit(code=1)

    client = _get_client()

    metric = admin_types.CustomMetric(
        parameter_name=parameter_name,
        display_name=display_name,
        measurement_unit=measurement_unit,
        scope=scope or "EVENT",
    )
    if description:
        metric.description = description
    if restricted_metric_type:
        metric.restricted_metric_type = list(restricted_metric_type)

    created = client.create_custom_metric(
        parent=f"properties/{property_id}",
        custom_metric=metric,
    )
    _render_metric(created, output)


@custom_metrics_app.command("patch")
def patch_custom_metric(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    metric_id: Annotated[
        str,
        typer.Option("--metric-id", help="Custom Metric ID"),
    ],
    display_name: Annotated[
        Optional[str],
        typer.Option("--display-name", help="New display name"),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", help="New description"),
    ] = None,
    measurement_unit: Annotated[
        Optional[str],
        typer.Option("--measurement-unit", help="New measurement unit"),
    ] = None,
    restricted_metric_type: Annotated[
        Optional[List[str]],
        typer.Option("--restricted-metric-type", help="Restricted metric type: COST_DATA, REVENUE_DATA"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Update a custom metric's patchable fields."""
    if (
        display_name is None
        and description is None
        and measurement_unit is None
        and restricted_metric_type is None
    ):
        err_console.print(
            "[red]Error:[/red] At least one of --display-name, --description, "
            "--measurement-unit, or --restricted-metric-type must be provided."
        )
        raise typer.Exit(code=1)

    # Validate CURRENCY + restricted_metric_type when both provided
    if measurement_unit and restricted_metric_type is not None:
        is_currency = measurement_unit.upper() == "CURRENCY"
        has_restricted = bool(restricted_metric_type)
        if is_currency and not has_restricted:
            err_console.print(
                "[red]Error:[/red] --restricted-metric-type is required when "
                "--measurement-unit is CURRENCY."
            )
            raise typer.Exit(code=1)
        if not is_currency and has_restricted:
            err_console.print(
                "[red]Error:[/red] --restricted-metric-type must be empty when "
                "--measurement-unit is not CURRENCY."
            )
            raise typer.Exit(code=1)

    client = _get_client()

    metric = admin_types.CustomMetric(
        name=f"properties/{property_id}/customMetrics/{metric_id}"
    )
    mask_paths: list[str] = []

    if display_name:
        metric.display_name = display_name
        mask_paths.append("display_name")
    if description is not None:
        metric.description = description
        mask_paths.append("description")
    if measurement_unit:
        metric.measurement_unit = measurement_unit
        mask_paths.append("measurement_unit")
    if restricted_metric_type is not None:
        metric.restricted_metric_type = list(restricted_metric_type)
        mask_paths.append("restricted_metric_type")

    mask = field_mask_pb2.FieldMask(paths=mask_paths)
    updated = client.update_custom_metric(custom_metric=metric, update_mask=mask)
    _render_metric(updated, output)


@custom_metrics_app.command("archive")
def archive_custom_metric(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    metric_id: Annotated[
        str,
        typer.Option("--metric-id", help="Custom Metric ID"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Archive a custom metric (soft-removes it from reports)."""
    client = _get_client()

    if not force:
        metric = client.get_custom_metric(
            name=f"properties/{property_id}/customMetrics/{metric_id}"
        )
        display_name = metric.display_name
        try:
            typer.confirm(
                f"Archive custom metric {metric_id} ({display_name})? "
                "This will hide it from reports but not delete it.",
                abort=True,
            )
        except typer.Abort:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.archive_custom_metric(
        name=f"properties/{property_id}/customMetrics/{metric_id}"
    )

    # Fetch parameter_name for the success message (or reuse if already fetched)
    if force:
        metric = client.get_custom_metric(
            name=f"properties/{property_id}/customMetrics/{metric_id}"
        )

    typer.echo(
        f"Custom metric '{metric.parameter_name}' ({metric_id}) archived."
    )
