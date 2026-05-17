"""Custom Dimensions commands: list, get, create, patch, archive."""

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

custom_dimensions_app = typer.Typer(
    name="custom-dimensions", help="Custom Dimensions management commands"
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _dim_to_dict(dim) -> dict:
    """Convert a CustomDimension resource to a flat dict.

    Args:
        dim: A GA4 CustomDimension resource object.

    Returns:
        A flat dictionary with all custom dimension fields.
    """
    dim_id = extract_id(dim.name)
    scope = enum_name(dim.scope)
    return {
        "dim_id": dim_id,
        "parameter_name": dim.parameter_name,
        "display_name": dim.display_name,
        "scope": scope,
        "description": dim.description,
        "disallow_ads_personalization": dim.disallow_ads_personalization,
    }


def _render_dim(dim, output: OutputFormat) -> None:
    """Render a CustomDimension resource in the requested format.

    Args:
        dim: A GA4 CustomDimension resource object.
        output: The desired output format.
    """
    dim_id = extract_id(dim.name)
    data = _dim_to_dict(dim)
    fields = list(data.keys())

    if output == OutputFormat.json:
        render_json(data)
        return

    if output == OutputFormat.csv:
        render_csv([data], fieldnames=fields)
        return

    # Default: rich key/value table
    table = Table(title=f"Custom Dimension {dim_id}", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    for field in fields:
        table.add_row(field, str(data[field]))
    console.print(table)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@custom_dimensions_app.command("list")
def list_custom_dimensions(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """List all custom dimensions for a GA4 property."""
    client = get_client()
    dims = list(client.list_custom_dimensions(parent=f"properties/{property_id}"))

    rows: list[dict] = [
        {
            "dim_id": extract_id(d.name),
            "parameter_name": d.parameter_name,
            "display_name": d.display_name,
            "scope": enum_name(d.scope),
        }
        for d in dims
    ]

    if output == OutputFormat.json:
        render_json(rows)
        return

    if output == OutputFormat.csv:
        fieldnames = ["dim_id", "parameter_name", "display_name", "scope"]
        render_csv(rows, fieldnames=fieldnames)
        return

    # Default: rich table
    table = Table(
        title=f"Custom Dimensions — Property {property_id}", show_header=True
    )
    table.add_column("Dim ID", style="cyan")
    table.add_column("Parameter Name", style="white")
    table.add_column("Display Name", style="white")
    table.add_column("Scope", style="green")
    for row in rows:
        table.add_row(
            str(row["dim_id"]),
            str(row["parameter_name"]),
            str(row["display_name"]),
            str(row["scope"]),
        )
    console.print(table)


@custom_dimensions_app.command("get")
def get_custom_dimension(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    dimension_id: Annotated[
        str,
        typer.Option("--dimension-id", help="Custom Dimension ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Get details for a specific custom dimension."""
    client = get_client()
    dim = client.get_custom_dimension(
        name=f"properties/{property_id}/customDimensions/{dimension_id}"
    )
    _render_dim(dim, output)


@custom_dimensions_app.command("create")
def create_custom_dimension(
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
    scope: Annotated[
        str,
        typer.Option("--scope", help="Dimension scope: EVENT, USER, or ITEM"),
    ],
    description: Annotated[
        Optional[str],
        typer.Option("--description", help="Optional description"),
    ] = None,
    disallow_ads_personalization: Annotated[
        Optional[bool],
        typer.Option(
            "--disallow-ads-personalization/--no-disallow-ads-personalization",
            help="Disallow ads personalization (USER scope only)",
        ),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Create a new custom dimension for a GA4 property."""
    client = get_client()

    dim = admin_types.CustomDimension(
        parameter_name=parameter_name,
        display_name=display_name,
        scope=scope,
    )
    if description:
        dim.description = description
    if disallow_ads_personalization is not None:
        dim.disallow_ads_personalization = disallow_ads_personalization

    created = client.create_custom_dimension(
        parent=f"properties/{property_id}",
        custom_dimension=dim,
    )
    _render_dim(created, output)


@custom_dimensions_app.command("patch")
def patch_custom_dimension(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    dimension_id: Annotated[
        str,
        typer.Option("--dimension-id", help="Custom Dimension ID"),
    ],
    display_name: Annotated[
        Optional[str],
        typer.Option("--display-name", help="New display name"),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", help="New description"),
    ] = None,
    disallow_ads_personalization: Annotated[
        Optional[bool],
        typer.Option(
            "--disallow-ads-personalization/--no-disallow-ads-personalization",
            help="Disallow ads personalization (USER scope only)",
        ),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Update a custom dimension's patchable fields."""
    if display_name is None and description is None and disallow_ads_personalization is None:
        err_console.print(
            "[red]Error:[/red] At least one of --display-name, --description, or "
            "--disallow-ads-personalization must be provided."
        )
        raise typer.Exit(code=1)

    client = get_client()

    dim = admin_types.CustomDimension(
        name=f"properties/{property_id}/customDimensions/{dimension_id}"
    )
    mask_paths: list[str] = []

    if display_name:
        dim.display_name = display_name
        mask_paths.append("display_name")
    if description is not None:
        dim.description = description
        mask_paths.append("description")
    if disallow_ads_personalization is not None:
        dim.disallow_ads_personalization = disallow_ads_personalization
        mask_paths.append("disallow_ads_personalization")

    mask = field_mask_pb2.FieldMask(paths=mask_paths)
    updated = client.update_custom_dimension(custom_dimension=dim, update_mask=mask)
    _render_dim(updated, output)


@custom_dimensions_app.command("archive")
def archive_custom_dimension(
    property_id: Annotated[
        str,
        typer.Option("--property-id", help="GA4 Property ID"),
    ],
    dimension_id: Annotated[
        str,
        typer.Option("--dimension-id", help="Custom Dimension ID"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Archive a custom dimension (soft-removes it from reports)."""
    client = get_client()

    if not force:
        dim = client.get_custom_dimension(
            name=f"properties/{property_id}/customDimensions/{dimension_id}"
        )
        display_name = dim.display_name
        try:
            typer.confirm(
                f"Archive custom dimension {dimension_id} ({display_name})? "
                "This will hide it from reports but not delete it.",
                abort=True,
            )
        except typer.Abort:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.archive_custom_dimension(
        name=f"properties/{property_id}/customDimensions/{dimension_id}"
    )

    # Fetch parameter_name for the success message (or reuse if already fetched)
    if force:
        dim = client.get_custom_dimension(
            name=f"properties/{property_id}/customDimensions/{dimension_id}"
        )

    typer.echo(
        f"Custom dimension '{dim.parameter_name}' ({dimension_id}) archived."
    )
