"""Main CLI entry point for gaad."""

from __future__ import annotations

import typer

from gaad.commands.annotations import annotations_app
from gaad.commands.auth import auth_app
from gaad.commands.accounts import accounts_app
from gaad.commands.channel_groups import channel_groups_app
from gaad.commands.custom_dimensions import custom_dimensions_app
from gaad.commands.custom_metrics import custom_metrics_app
from gaad.commands.data_streams import data_streams_app
from gaad.commands.key_events import key_events_app
from gaad.commands.properties import properties_app

app = typer.Typer(name="gaad", help="Google Analytics 4 Admin CLI")
app.add_typer(auth_app, name="auth")
app.add_typer(accounts_app, name="accounts")
app.add_typer(properties_app, name="properties")
app.add_typer(data_streams_app, name="data-streams")
app.add_typer(key_events_app, name="key-events")
app.add_typer(custom_dimensions_app, name="custom-dimensions")
app.add_typer(custom_metrics_app, name="custom-metrics")
app.add_typer(annotations_app, name="annotations")
app.add_typer(channel_groups_app, name="channel-groups")

if __name__ == "__main__":
    app()
