"""Annotations commands: list, get, create, patch, delete."""

from __future__ import annotations

from typing import Annotated, Optional
from enum import Enum

import typer
from google.analytics.admin_v1alpha import types as alpha_types
from google.protobuf import field_mask_pb2
from google.type.date_pb2 import Date
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

annotations_app = typer.Typer(help="Manage Reporting Data Annotations (v1alpha).")


class AnnotationColor(str, Enum):
    """Supported annotation colors."""

    PURPLE = "PURPLE"
    BROWN = "BROWN"
    BLUE = "BLUE"
    GREEN = "GREEN"
    RED = "RED"
    CYAN = "CYAN"


def _parse_date(date_str: str) -> Date:
    """Parse a YYYY-MM-DD string into a google.type.date_pb2.Date proto.

    Args:
        date_str: Date string in YYYY-MM-DD format.

    Returns:
        A populated Date proto.

    Raises:
        typer.BadParameter: If the string is not in the expected format.
    """
    try:
        parts = date_str.split("-")
        if len(parts) != 3:
            raise ValueError("wrong number of parts")
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        return Date(year=year, month=month, day=day)
    except (ValueError, AttributeError) as exc:
        raise typer.BadParameter(
            f"Date '{date_str}' is not in YYYY-MM-DD format."
        ) from exc


def _format_date(d) -> str:
    """Format a Date proto as YYYY-MM-DD string.

    Args:
        d: A Date proto with year, month, day attributes.

    Returns:
        Formatted date string.
    """
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"


def _annotation_to_dict(annotation) -> dict:
    """Convert a ReportingDataAnnotation resource to a flat dict for JSON/CSV output.

    Args:
        annotation: A GA4 ReportingDataAnnotation resource object.

    Returns:
        A flat dictionary with all annotation fields.
    """
    annotation_id = extract_id(annotation.name)

    if annotation.annotation_date_range is not None and annotation.annotation_date is None:
        date_type = "range"
        start = annotation.annotation_date_range.start_date
        end = annotation.annotation_date_range.end_date
        date_value = f"{_format_date(start)} - {_format_date(end)}"
    elif annotation.annotation_date is not None:
        date_type = "single"
        date_value = _format_date(annotation.annotation_date)
    else:
        date_type = "unknown"
        date_value = ""

    return {
        "annotation_id": annotation_id,
        "title": annotation.title,
        "description": annotation.description,
        "color": enum_name(annotation.color),
        "system_generated": annotation.system_generated,
        "date_type": date_type,
        "date_value": date_value,
    }


def _render_annotation(annotation, output: OutputFormat) -> None:
    """Render a ReportingDataAnnotation in the requested format.

    Args:
        annotation: A GA4 ReportingDataAnnotation resource object.
        output: The desired output format.
    """
    annotation_id = extract_id(annotation.name)
    data = _annotation_to_dict(annotation)
    fields = list(data.keys())

    if output == OutputFormat.json:
        render_json(data)
        return

    if output == OutputFormat.csv:
        render_csv([data], fieldnames=fields)
        return

    table = Table(title=f"Annotation {annotation_id}", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    for field in fields:
        table.add_row(field, str(data[field]))
    console.print(table)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@annotations_app.command("list")
def list_annotations(
    property_id: Annotated[
        str,
        typer.Option("--property", help="GA4 Property ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """List all reporting data annotations for a GA4 property."""
    client = get_client("v1alpha")
    items = list(
        client.list_reporting_data_annotations(parent=f"properties/{property_id}")
    )

    rows: list[dict] = []
    for ann in items:
        annotation_id = extract_id(ann.name)
        if ann.annotation_date_range is not None and ann.annotation_date is None:
            start = ann.annotation_date_range.start_date
            end = ann.annotation_date_range.end_date
            date_str = f"{_format_date(start)} - {_format_date(end)}"
        elif ann.annotation_date is not None:
            date_str = _format_date(ann.annotation_date)
        else:
            date_str = ""

        rows.append(
            {
                "annotation_id": annotation_id,
                "title": ann.title,
                "color": enum_name(ann.color),
                "system_generated": ann.system_generated,
                "date": date_str,
            }
        )

    if output == OutputFormat.json:
        render_json(rows)
        return

    if output == OutputFormat.csv:
        fieldnames = ["annotation_id", "title", "color", "system_generated", "date"]
        render_csv(rows, fieldnames=fieldnames)
        return

    table = Table(
        title=f"Annotations — Property {property_id}", show_header=True
    )
    table.add_column("Annotation ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Color", style="green")
    table.add_column("System Generated", style="yellow")
    table.add_column("Date", style="magenta")
    for row in rows:
        table.add_row(
            str(row["annotation_id"]),
            str(row["title"]),
            str(row["color"]),
            str(row["system_generated"]),
            str(row["date"]),
        )
    console.print(table)


@annotations_app.command("get")
def get_annotation(
    annotation_id: Annotated[
        str,
        typer.Argument(help="Annotation ID"),
    ],
    property_id: Annotated[
        str,
        typer.Option("--property", help="GA4 Property ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Get details for a specific reporting data annotation."""
    client = get_client("v1alpha")
    annotation = client.get_reporting_data_annotation(
        name=f"properties/{property_id}/reportingDataAnnotations/{annotation_id}"
    )
    _render_annotation(annotation, output)


@annotations_app.command("create")
def create_annotation(
    property_id: Annotated[
        str,
        typer.Option("--property", help="GA4 Property ID"),
    ],
    title: Annotated[
        str,
        typer.Option("--title", help="Title for the annotation"),
    ],
    color: Annotated[
        AnnotationColor,
        typer.Option("--color", help="Color for the annotation"),
    ],
    description: Annotated[
        Optional[str],
        typer.Option("--description", help="Optional description"),
    ] = None,
    date: Annotated[
        Optional[str],
        typer.Option("--date", help="Single date in YYYY-MM-DD format"),
    ] = None,
    start_date: Annotated[
        Optional[str],
        typer.Option("--start-date", help="Start date (YYYY-MM-DD) for a date range"),
    ] = None,
    end_date: Annotated[
        Optional[str],
        typer.Option("--end-date", help="End date (YYYY-MM-DD) for a date range"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Create a new reporting data annotation for a GA4 property."""
    has_date = date is not None
    has_start = start_date is not None
    has_end = end_date is not None
    has_range = has_start or has_end

    # Validate mutual exclusivity and completeness
    if has_date and has_range:
        err_console.print(
            "[red]Error:[/red] --date and --start-date/--end-date are mutually exclusive."
        )
        raise typer.Exit(code=1)

    if not has_date and not has_range:
        err_console.print(
            "[red]Error:[/red] Provide either --date or both --start-date and --end-date."
        )
        raise typer.Exit(code=1)

    if has_range and not (has_start and has_end):
        err_console.print(
            "[red]Error:[/red] Both --start-date and --end-date must be provided together."
        )
        raise typer.Exit(code=1)

    color_enum = alpha_types.ReportingDataAnnotation.Color[color.value]

    kwargs: dict = {
        "title": title,
        "color": color_enum,
    }
    if description is not None:
        kwargs["description"] = description

    if has_date:
        kwargs["annotation_date"] = _parse_date(date)
    else:
        kwargs["annotation_date_range"] = alpha_types.ReportingDataAnnotation.DateRange(
            start_date=_parse_date(start_date),
            end_date=_parse_date(end_date),
        )

    annotation = alpha_types.ReportingDataAnnotation(**kwargs)

    client = get_client("v1alpha")
    created = client.create_reporting_data_annotation(
        parent=f"properties/{property_id}",
        reporting_data_annotation=annotation,
    )
    _render_annotation(created, output)


@annotations_app.command("patch")
def patch_annotation(
    annotation_id: Annotated[
        str,
        typer.Argument(help="Annotation ID"),
    ],
    property_id: Annotated[
        str,
        typer.Option("--property", help="GA4 Property ID"),
    ],
    title: Annotated[
        Optional[str],
        typer.Option("--title", help="New title"),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", help="New description"),
    ] = None,
    color: Annotated[
        Optional[AnnotationColor],
        typer.Option("--color", help="New color"),
    ] = None,
    date: Annotated[
        Optional[str],
        typer.Option("--date", help="New single date (YYYY-MM-DD)"),
    ] = None,
    start_date: Annotated[
        Optional[str],
        typer.Option("--start-date", help="New range start date (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        Optional[str],
        typer.Option("--end-date", help="New range end date (YYYY-MM-DD)"),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Update a reporting data annotation."""
    has_date = date is not None
    has_start = start_date is not None
    has_end = end_date is not None
    has_range_args = has_start or has_end

    # Validate mutual exclusivity
    if has_date and has_range_args:
        err_console.print(
            "[red]Error:[/red] --date and --start-date/--end-date are mutually exclusive."
        )
        raise typer.Exit(code=1)

    # Validate range args completeness
    if has_range_args and not (has_start and has_end):
        err_console.print(
            "[red]Error:[/red] Both --start-date and --end-date must be provided together."
        )
        raise typer.Exit(code=1)

    # Require at least one field
    if not any([title, description, color, has_date, has_range_args]):
        err_console.print(
            "[red]Error:[/red] At least one field must be provided to patch."
        )
        raise typer.Exit(code=1)

    client = get_client("v1alpha")

    # Check system_generated before patching
    existing = client.get_reporting_data_annotation(
        name=f"properties/{property_id}/reportingDataAnnotations/{annotation_id}"
    )
    if existing.system_generated:
        err_console.print(
            "[red]Error:[/red] System-generated annotations cannot be patched."
        )
        raise typer.Exit(code=1)

    ann_kwargs: dict = {
        "name": f"properties/{property_id}/reportingDataAnnotations/{annotation_id}"
    }
    mask_paths: list[str] = []

    if title is not None:
        ann_kwargs["title"] = title
        mask_paths.append("title")

    if description is not None:
        ann_kwargs["description"] = description
        mask_paths.append("description")

    if color is not None:
        ann_kwargs["color"] = alpha_types.ReportingDataAnnotation.Color[color.value]
        mask_paths.append("color")

    if has_date:
        ann_kwargs["annotation_date"] = _parse_date(date)
        mask_paths.append("annotation_date")
    elif has_range_args:
        ann_kwargs["annotation_date_range"] = alpha_types.ReportingDataAnnotation.DateRange(
            start_date=_parse_date(start_date),
            end_date=_parse_date(end_date),
        )
        mask_paths.append("annotation_date_range")

    annotation = alpha_types.ReportingDataAnnotation(**ann_kwargs)
    mask = field_mask_pb2.FieldMask(paths=mask_paths)

    updated = client.update_reporting_data_annotation(
        reporting_data_annotation=annotation,
        update_mask=mask,
    )
    _render_annotation(updated, output)


@annotations_app.command("delete")
def delete_annotation(
    annotation_id: Annotated[
        str,
        typer.Argument(help="Annotation ID"),
    ],
    property_id: Annotated[
        str,
        typer.Option("--property", help="GA4 Property ID"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Delete a reporting data annotation (permanent)."""
    client = get_client("v1alpha")

    annotation = client.get_reporting_data_annotation(
        name=f"properties/{property_id}/reportingDataAnnotations/{annotation_id}"
    )

    if annotation.system_generated:
        err_console.print(
            "[red]Error:[/red] System-generated annotations cannot be deleted."
        )
        raise typer.Exit(code=1)

    if not force:
        try:
            typer.confirm(
                f"Delete annotation '{annotation.title}' ({annotation_id})?",
                abort=True,
            )
        except typer.Abort:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete_reporting_data_annotation(
        name=f"properties/{property_id}/reportingDataAnnotations/{annotation_id}"
    )
    typer.echo(f"Annotation '{annotation.title}' ({annotation_id}) deleted.")
