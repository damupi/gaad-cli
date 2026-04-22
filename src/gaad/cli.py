"""Main CLI entry point for gaad."""

from __future__ import annotations

import typer

from gaad.commands.auth import auth_app
from gaad.commands.accounts import accounts_app
from gaad.commands.properties import properties_app

app = typer.Typer(name="gaad", help="Google Analytics 4 Admin CLI")
app.add_typer(auth_app, name="auth")
app.add_typer(accounts_app, name="accounts")
app.add_typer(properties_app, name="properties")

if __name__ == "__main__":
    app()
