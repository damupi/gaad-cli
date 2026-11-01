"""Main CLI entry point for gaad."""

from __future__ import annotations

import json
from importlib import metadata
from typing import Annotated

import typer

from gaad.commands.annotations import annotations_app
from gaad.commands.auth import auth_app
from gaad.commands.accounts import accounts_app
from gaad.commands.bigquery_links import bigquery_links_app
from gaad.commands.channel_groups import channel_groups_app
from gaad.commands.custom_dimensions import custom_dimensions_app
from gaad.commands.custom_metrics import custom_metrics_app
from gaad.commands.data_streams import data_streams_app
from gaad.commands.key_events import key_events_app
from gaad.commands.properties import properties_app
from gaad.update import (
    installed_version,
    is_newer,
    latest_release,
    pending_notice,
    upgrade_command,
)

app = typer.Typer(name="gaad", help="Google Analytics 4 Admin CLI")


def _version_callback(value: bool) -> None:
    if value:
        try:
            version = metadata.version("gaad-cli")
        except metadata.PackageNotFoundError:
            version = "unknown (not installed as a package)"
        typer.echo(f"gaad {version}")
        raise typer.Exit()


def _show_update_notice() -> None:
    notice = pending_notice()
    if notice:
        typer.echo(f"\n{notice}", err=True)


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the installed version and exit.",
        ),
    ] = False,
) -> None:
    """Google Analytics 4 Admin CLI

    Once a day, gaad checks GitHub for a newer release and prints an upgrade
    notice on stderr (interactive terminals only). Disable it with
    GAAD_NO_UPDATE_CHECK=1. Run 'gaad version' to check now.
    """
    # `gaad version` already reports the result of a fresh check.
    if ctx.invoked_subcommand != "version":
        ctx.call_on_close(_show_update_notice)


@app.command("version")
def version_command(
    as_json: Annotated[
        bool, typer.Option("--json", help="Output machine-readable JSON")
    ] = False,
) -> None:
    """Show the installed version and check GitHub for a newer release now."""
    current = installed_version()
    latest = latest_release()
    update_available = is_newer(latest, current)
    upgrade = upgrade_command(latest) if update_available else None

    if as_json:
        typer.echo(json.dumps({
            "installed": current,
            "latest": latest,
            "update_available": update_available,
            "upgrade_command": upgrade,
        }, indent=2))
        return

    typer.echo(f"gaad {current or 'unknown (not installed as a package)'}")
    if latest is None:
        typer.echo("Could not determine the latest release (offline, or no releases yet).")
    elif update_available:
        typer.echo(f"A new release is available: {latest}")
        typer.echo(f"To upgrade, run: {upgrade}")
    else:
        typer.echo(f"Up to date (latest release: {latest}).")


app.add_typer(auth_app, name="auth")
app.add_typer(accounts_app, name="accounts")
app.add_typer(properties_app, name="properties")
app.add_typer(data_streams_app, name="data-streams")
app.add_typer(key_events_app, name="key-events")
app.add_typer(custom_dimensions_app, name="custom-dimensions")
app.add_typer(custom_metrics_app, name="custom-metrics")
app.add_typer(annotations_app, name="annotations")
app.add_typer(channel_groups_app, name="channel-groups")
app.add_typer(bigquery_links_app, name="bigquery-links")

if __name__ == "__main__":
    app()
