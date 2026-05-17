"""Channel Groups commands: list, get, create, patch, delete."""

from __future__ import annotations

import json
from enum import Enum
from typing import Annotated, List, Literal, Optional

import typer
from google.analytics.admin_v1alpha import types as alpha_types
from google.protobuf import field_mask_pb2
from pydantic import BaseModel, Field, model_validator
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

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ChannelGroupField(str, Enum):
    """Known valid fieldName values for ChannelGroupFilter.

    These correspond to the dimension options shown in the GA4 UI when
    editing channel group conditions. Keep field_name as str in the
    Pydantic model so future or unknown fields still pass through to
    the API without validation errors.
    """

    DEFAULT_CHANNEL_GROUP = "eachScopeDefaultChannelGroup"
    SOURCE = "eachScopeSource"
    MEDIUM = "eachScopeMedium"
    SOURCE_PLATFORM = "eachScopeSourcePlatform"
    CAMPAIGN_ID = "eachScopeCampaignId"
    CAMPAIGN_NAME = "eachScopeCampaignName"


# ---------------------------------------------------------------------------
# Pydantic models for grouping rule / filter expression parsing
# ---------------------------------------------------------------------------


class StringFilterModel(BaseModel):
    """Pydantic model for a ChannelGroupFilter.StringFilter."""

    model_config = {"populate_by_name": True}
    match_type: Literal[
        "EXACT", "BEGINS_WITH", "ENDS_WITH", "CONTAINS", "FULL_REGEXP", "PARTIAL_REGEXP"
    ] = "EXACT"
    value: str

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, data: object) -> object:
        if isinstance(data, dict):
            if "match_type" not in data and "matchType" in data:
                data = {**data, "match_type": data.pop("matchType")}
        return data

    def to_proto(self) -> alpha_types.ChannelGroupFilter.StringFilter:
        """Convert to a ChannelGroupFilter.StringFilter proto."""
        return alpha_types.ChannelGroupFilter.StringFilter(
            match_type=alpha_types.ChannelGroupFilter.StringFilter.MatchType[
                self.match_type
            ],
            value=self.value,
        )


class InListFilterModel(BaseModel):
    """Pydantic model for a ChannelGroupFilter.InListFilter."""

    values: List[str]

    def to_proto(self) -> alpha_types.ChannelGroupFilter.InListFilter:
        """Convert to a ChannelGroupFilter.InListFilter proto."""
        return alpha_types.ChannelGroupFilter.InListFilter(values=self.values)


class ChannelGroupFilterModel(BaseModel):
    """Pydantic model for a ChannelGroupFilter (leaf filter node).

    field_name accepts any string so future API fields pass through, but
    the known valid values are defined in ChannelGroupField:
      eachScopeDefaultChannelGroup  — Default channel group
      eachScopeSource               — Source
      eachScopeMedium               — Medium
      eachScopeSourcePlatform       — Source platform
      eachScopeCampaignId           — Campaign ID
      eachScopeCampaignName         — Campaign name
    """

    model_config = {"populate_by_name": True}
    field_name: str = Field(alias="fieldName", default=None)
    string_filter: Optional[StringFilterModel] = Field(None, alias="stringFilter")
    in_list_filter: Optional[InListFilterModel] = Field(None, alias="inListFilter")

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, data: object) -> object:
        if isinstance(data, dict):
            if "field_name" in data and "fieldName" not in data:
                data = {**data, "fieldName": data.pop("field_name")}
            if "string_filter" in data and "stringFilter" not in data:
                data = {**data, "stringFilter": data.pop("string_filter")}
            if "in_list_filter" in data and "inListFilter" not in data:
                data = {**data, "inListFilter": data.pop("in_list_filter")}
        return data

    @model_validator(mode="after")
    def _check_filter(self) -> "ChannelGroupFilterModel":
        if self.string_filter and self.in_list_filter:
            raise ValueError("Only one of string_filter or in_list_filter may be set")
        if not self.string_filter and not self.in_list_filter:
            raise ValueError("One of string_filter or in_list_filter must be set")
        return self

    def to_proto(self) -> alpha_types.ChannelGroupFilter:
        """Convert to a ChannelGroupFilter proto."""
        kwargs: dict = {"field_name": self.field_name}
        if self.string_filter:
            kwargs["string_filter"] = self.string_filter.to_proto()
        else:
            kwargs["in_list_filter"] = self.in_list_filter.to_proto()
        return alpha_types.ChannelGroupFilter(**kwargs)


class FilterExpressionModel(BaseModel):
    """Pydantic model for a ChannelGroupFilterExpression (recursive)."""

    model_config = {"populate_by_name": True}
    filter: Optional[ChannelGroupFilterModel] = None
    and_group: Optional["FilterExpressionListModel"] = Field(None, alias="andGroup")
    or_group: Optional["FilterExpressionListModel"] = Field(None, alias="orGroup")
    not_expression: Optional["FilterExpressionModel"] = Field(
        None, alias="notExpression"
    )

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, data: object) -> object:
        if isinstance(data, dict):
            mapping = {
                "and_group": "andGroup",
                "or_group": "orGroup",
                "not_expression": "notExpression",
            }
            for snake, camel in mapping.items():
                if snake in data and camel not in data:
                    data = {**data, camel: data.pop(snake)}
        return data

    @model_validator(mode="after")
    def _check_exactly_one(self) -> "FilterExpressionModel":
        n = sum(
            [
                self.filter is not None,
                self.and_group is not None,
                self.or_group is not None,
                self.not_expression is not None,
            ]
        )
        if n != 1:
            raise ValueError(
                f"Exactly one of filter/and_group/or_group/not_expression must be set,"
                f" got {n}"
            )
        return self

    def to_proto(self) -> alpha_types.ChannelGroupFilterExpression:
        """Convert to a ChannelGroupFilterExpression proto."""
        if self.and_group:
            return alpha_types.ChannelGroupFilterExpression(
                and_group=self.and_group.to_proto()
            )
        if self.or_group:
            return alpha_types.ChannelGroupFilterExpression(
                or_group=self.or_group.to_proto()
            )
        if self.not_expression:
            return alpha_types.ChannelGroupFilterExpression(
                not_expression=self.not_expression.to_proto()
            )
        return alpha_types.ChannelGroupFilterExpression(filter=self.filter.to_proto())


class FilterExpressionListModel(BaseModel):
    """Pydantic model for a ChannelGroupFilterExpressionList."""

    model_config = {"populate_by_name": True}
    filter_expressions: List[FilterExpressionModel] = Field(
        alias="filterExpressions", default_factory=list
    )

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, data: object) -> object:
        if isinstance(data, dict):
            if "expressions" in data and "filterExpressions" not in data:
                data = {**data, "filterExpressions": data.pop("expressions")}
            if "filter_expressions" in data and "filterExpressions" not in data:
                data = {**data, "filterExpressions": data.pop("filter_expressions")}
        return data

    def to_proto(self) -> alpha_types.ChannelGroupFilterExpressionList:
        """Convert to a ChannelGroupFilterExpressionList proto."""
        return alpha_types.ChannelGroupFilterExpressionList(
            filter_expressions=[e.to_proto() for e in self.filter_expressions]
        )


# Resolve forward references after all models are defined.
FilterExpressionModel.model_rebuild()


class GroupingRuleModel(BaseModel):
    """Pydantic model for a GroupingRule."""

    model_config = {"populate_by_name": True}
    display_name: str = Field(alias="displayName", default=None)
    expression: FilterExpressionModel

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, data: object) -> object:
        if isinstance(data, dict):
            if "display_name" in data and "displayName" not in data:
                data = {**data, "displayName": data.pop("display_name")}
        return data

    def to_proto(self) -> alpha_types.GroupingRule:
        """Convert to a GroupingRule proto."""
        return alpha_types.GroupingRule(
            display_name=self.display_name,
            expression=self.expression.to_proto(),
        )


# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

channel_groups_app = typer.Typer(help="Manage Channel Groups (v1alpha).")


def _rules_from_json(json_str: str) -> list:
    """Parse a JSON string into a list of GroupingRule protos via Pydantic models.

    Args:
        json_str: JSON string representing a list of grouping rules.

    Returns:
        List of GroupingRule proto objects.
    """
    from pydantic import ValidationError

    try:
        rules_data = json.loads(json_str)
        if not isinstance(rules_data, list):
            raise ValueError("Rules JSON must be a list")
        rules = [GroupingRuleModel.model_validate(r) for r in rules_data]
        return [r.to_proto() for r in rules]
    except json.JSONDecodeError as exc:
        err_console.print(f"[red]Error:[/red] Invalid JSON: {exc}")
        raise typer.Exit(code=1) from exc
    except ValidationError as exc:
        err_console.print(f"[red]Error:[/red] Invalid rules structure:\n{exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        err_console.print(f"[red]Error:[/red] Failed to parse grouping rules: {exc}")
        raise typer.Exit(code=1) from exc


def _channel_group_to_dict(cg) -> dict:
    """Convert a ChannelGroup resource to a flat dict for JSON/CSV output.

    Args:
        cg: A GA4 ChannelGroup resource object.

    Returns:
        A flat dictionary with all channel group fields.
    """
    return {
        "channel_group_id": extract_id(cg.name),
        "display_name": cg.display_name,
        "description": cg.description,
        "system_defined": cg.system_defined,
        "primary": cg.primary,
        "rule_count": len(cg.grouping_rule),
    }


def _render_channel_group(cg, output: OutputFormat) -> None:
    """Render a ChannelGroup in the requested format.

    Args:
        cg: A GA4 ChannelGroup resource object.
        output: The desired output format.
    """
    channel_group_id = extract_id(cg.name)
    data = _channel_group_to_dict(cg)
    fields = list(data.keys())

    if output == OutputFormat.json:
        render_json(data)
        return

    if output == OutputFormat.csv:
        render_csv([data], fieldnames=fields)
        return

    table = Table(title=f"Channel Group {channel_group_id}", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    for field in fields:
        table.add_row(field, str(data[field]))
    console.print(table)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@channel_groups_app.command("list")
def list_channel_groups(
    property_id: Annotated[
        str,
        typer.Option("--property", help="GA4 Property ID"),
    ],
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """List all channel groups for a GA4 property."""
    client = get_client("v1alpha")
    items = list(client.list_channel_groups(parent=f"properties/{property_id}"))

    rows: list[dict] = []
    for cg in items:
        rows.append(
            {
                "channel_group_id": extract_id(cg.name),
                "display_name": cg.display_name,
                "system_defined": cg.system_defined,
                "primary": cg.primary,
                "rule_count": len(cg.grouping_rule),
            }
        )

    if output == OutputFormat.json:
        render_json(rows)
        return

    if output == OutputFormat.csv:
        fieldnames = [
            "channel_group_id",
            "display_name",
            "system_defined",
            "primary",
            "rule_count",
        ]
        render_csv(rows, fieldnames=fieldnames)
        return

    table = Table(
        title=f"Channel Groups — Property {property_id}", show_header=True
    )
    table.add_column("Channel Group ID", style="cyan")
    table.add_column("Display Name", style="white")
    table.add_column("System Defined", style="yellow")
    table.add_column("Primary", style="green")
    table.add_column("Rules", style="magenta")
    for row in rows:
        table.add_row(
            str(row["channel_group_id"]),
            str(row["display_name"]),
            str(row["system_defined"]),
            str(row["primary"]),
            str(row["rule_count"]),
        )
    console.print(table)


@channel_groups_app.command("get")
def get_channel_group(
    channel_group_id: Annotated[
        str,
        typer.Argument(help="Channel Group ID"),
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
    """Get details for a specific channel group."""
    client = get_client("v1alpha")
    cg = client.get_channel_group(
        name=f"properties/{property_id}/channelGroups/{channel_group_id}"
    )
    _render_channel_group(cg, output)


@channel_groups_app.command("create")
def create_channel_group(
    property_id: Annotated[
        str,
        typer.Option("--property", help="GA4 Property ID"),
    ],
    display_name: Annotated[
        str,
        typer.Option("--display-name", help="Display name (max 80 chars)"),
    ],
    rules_json: Annotated[
        str,
        typer.Option(
            "--rules-json",
            help=(
                "JSON array of grouping rules. "
                "Each rule needs display_name and expression (and_group → or_group → filter). "
                "Known fieldName values: eachScopeSource, eachScopeMedium, eachScopeDefaultChannelGroup, "
                "eachScopeSourcePlatform, eachScopeCampaignId, eachScopeCampaignName. "
                "Run 'gaad channel-groups create --help' for a full example."
            ),
        ),
    ],
    description: Annotated[
        Optional[str],
        typer.Option("--description", help="Optional description (max 256 chars)"),
    ] = None,
    primary: Annotated[
        bool,
        typer.Option("--primary/--no-primary", help="Mark as primary channel group"),
    ] = False,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Create a new channel group for a GA4 property.

    Rules are passed as a JSON array via --rules-json. The GA4 API requires
    expressions to follow a strict and_group → or_group → filter nesting.
    Both snake_case and camelCase keys are accepted.

    Known fieldName values (see ChannelGroupField enum):
      eachScopeDefaultChannelGroup  Default channel group
      eachScopeSource               Source
      eachScopeMedium               Medium
      eachScopeSourcePlatform       Source platform
      eachScopeCampaignId           Campaign ID
      eachScopeCampaignName         Campaign name

    Supported match types: EXACT, BEGINS_WITH, ENDS_WITH, CONTAINS,
    FULL_REGEXP, PARTIAL_REGEXP.

    Example — match sessions where Source contains twitter:

    \b
    gaad channel-groups create \\
      --property 123456789 \\
      --display-name "Social Traffic" \\
      --rules-json '[
        {
          "display_name": "Twitter",
          "expression": {
            "and_group": {
              "expressions": [{
                "or_group": {
                  "expressions": [{
                    "filter": {
                      "field_name": "eachScopeSource",
                      "string_filter": {
                        "match_type": "FULL_REGEXP",
                        "value": ".*\\\\.twitter\\\\.com"
                      }
                    }
                  }]
                }
              }]
            }
          }
        }
      ]'
    """
    rules = _rules_from_json(rules_json)

    kwargs: dict = {
        "display_name": display_name,
        "grouping_rule": rules,
        "primary": primary,
    }
    if description is not None:
        kwargs["description"] = description

    channel_group = alpha_types.ChannelGroup(**kwargs)

    client = get_client("v1alpha")
    created = client.create_channel_group(
        parent=f"properties/{property_id}",
        channel_group=channel_group,
    )
    _render_channel_group(created, output)


@channel_groups_app.command("patch")
def patch_channel_group(
    channel_group_id: Annotated[
        str,
        typer.Argument(help="Channel Group ID"),
    ],
    property_id: Annotated[
        str,
        typer.Option("--property", help="GA4 Property ID"),
    ],
    display_name: Annotated[
        Optional[str],
        typer.Option("--display-name", help="New display name"),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", help="New description"),
    ] = None,
    primary: Annotated[
        Optional[bool],
        typer.Option("--primary/--no-primary", help="Set or unset primary flag"),
    ] = None,
    rules_json: Annotated[
        Optional[str],
        typer.Option(
            "--rules-json",
            help=(
                "Replacement JSON array of grouping rules (replaces all existing rules). "
                "Same format as create — see 'gaad channel-groups create --help'."
            ),
        ),
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="Output format"),
    ] = OutputFormat.table,
) -> None:
    """Update a channel group.

    Only the fields you provide are updated. Passing --rules-json replaces
    the entire grouping_rule array — include all rules you want to keep.
    System-defined channel groups cannot be patched.

    See 'gaad channel-groups create --help' for the --rules-json format
    and the list of valid fieldName values.
    """
    if not any([display_name, description, primary is not None, rules_json]):
        err_console.print(
            "[red]Error:[/red] At least one field must be provided to patch."
        )
        raise typer.Exit(code=1)

    client = get_client("v1alpha")

    existing = client.get_channel_group(
        name=f"properties/{property_id}/channelGroups/{channel_group_id}"
    )
    if existing.system_defined:
        err_console.print(
            "[red]Error:[/red] System-defined channel groups cannot be patched."
        )
        raise typer.Exit(code=1)

    cg_kwargs: dict = {
        "name": f"properties/{property_id}/channelGroups/{channel_group_id}"
    }
    mask_paths: list[str] = []

    if display_name is not None:
        cg_kwargs["display_name"] = display_name
        mask_paths.append("display_name")

    if description is not None:
        cg_kwargs["description"] = description
        mask_paths.append("description")

    if primary is not None:
        cg_kwargs["primary"] = primary
        mask_paths.append("primary")

    if rules_json is not None:
        cg_kwargs["grouping_rule"] = _rules_from_json(rules_json)
        mask_paths.append("grouping_rule")

    channel_group = alpha_types.ChannelGroup(**cg_kwargs)
    mask = field_mask_pb2.FieldMask(paths=mask_paths)

    updated = client.update_channel_group(
        channel_group=channel_group,
        update_mask=mask,
    )
    _render_channel_group(updated, output)


@channel_groups_app.command("delete")
def delete_channel_group(
    channel_group_id: Annotated[
        str,
        typer.Argument(help="Channel Group ID"),
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
    """Delete a channel group (permanent)."""
    client = get_client("v1alpha")

    cg = client.get_channel_group(
        name=f"properties/{property_id}/channelGroups/{channel_group_id}"
    )

    if cg.system_defined:
        err_console.print(
            "[red]Error:[/red] System-defined channel groups cannot be deleted."
        )
        raise typer.Exit(code=1)

    if not force:
        try:
            typer.confirm(
                f"Delete channel group '{cg.display_name}' ({channel_group_id})?",
                abort=True,
            )
        except typer.Abort:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete_channel_group(
        name=f"properties/{property_id}/channelGroups/{channel_group_id}"
    )
    typer.echo(
        f"Channel group '{cg.display_name}' ({channel_group_id}) deleted."
    )
