"""Auth commands: login, status, logout."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from gaad import config as cfg
from gaad.auth import (
    GA4_SCOPES,
    build_admin_client,
    deserialize_oauth2_credentials,
    get_credentials,
    serialize_oauth2_credentials,
)
from gaad.errors import AuthError

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:  # pragma: no cover
    InstalledAppFlow = None  # type: ignore[assignment,misc]

console = Console()
err_console = Console(stderr=True)

auth_app = typer.Typer(name="auth", help="Authentication commands")


class AuthMethod(str, Enum):
    """Supported authentication methods."""

    oauth2 = "oauth2"
    service_account = "service-account"
    token = "token"


@auth_app.command("login")
def login(
    method: Annotated[
        AuthMethod,
        typer.Option("--method", help="Authentication method"),
    ] = AuthMethod.oauth2,
    client_secrets: Annotated[
        Optional[str],
        typer.Option("--client-secrets", help="Path to OAuth2 client secrets JSON file"),
    ] = None,
    key_file: Annotated[
        Optional[str],
        typer.Option("--key-file", help="Path to service account key JSON file"),
    ] = None,
    token: Annotated[
        Optional[str],
        typer.Option("--token", help="Raw GA4 access token"),
    ] = None,
) -> None:
    """Authenticate with Google Analytics Admin API."""
    if method == AuthMethod.service_account:
        if not key_file:
            err_console.print("[red]Error:[/red] --key-file is required for service-account method.")
            raise typer.Exit(code=1)
        cfg.set("auth_method", "service-account")
        cfg.set("key_file", key_file)
        console.print(f"[green]Stored service account credentials:[/green] {key_file}")

    elif method == AuthMethod.token:
        if not token:
            token = typer.prompt("Enter access token", hide_input=True)
        cfg.set("auth_method", "token")
        cfg.set("access_token", token)
        console.print("[green]Access token stored.[/green]")

    elif method == AuthMethod.oauth2:
        if not client_secrets:
            err_console.print("[red]Error:[/red] --client-secrets is required for oauth2 method.")
            raise typer.Exit(code=1)
        if InstalledAppFlow is None:  # pragma: no cover
            err_console.print("[red]Error:[/red] google-auth-oauthlib is not installed.")
            raise typer.Exit(code=1)
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets, GA4_SCOPES)
        creds = flow.run_local_server(port=0)
        serialized = serialize_oauth2_credentials(creds)
        cfg.set("auth_method", "oauth2")
        cfg.set("oauth2_credentials", serialized)
        cfg.set("oauth2_client_secret_file", client_secrets)
        console.print("[green]OAuth2 credentials stored.[/green]")


@auth_app.command("status")
def status() -> None:
    """Show current authentication status and validate API connectivity."""
    config = cfg.load_config()
    auth_method: str | None = config.get("auth_method")

    if not auth_method:
        console.print("[yellow]Not authenticated.[/yellow] Run: gaad auth login")
        return

    console.print(f"Auth method: [bold]{auth_method}[/bold]")

    if auth_method == "service-account":
        key_path = config.get("key_file", "<unknown>")
        console.print(f"Key file: {key_path}")

    elif auth_method == "token":
        raw_token: str = config.get("access_token", "")
        preview = (raw_token[:8] + "...") if len(raw_token) >= 8 else raw_token
        console.print(f"Token: {preview}")

    elif auth_method == "oauth2":
        stored = config.get("oauth2_credentials", {})
        expiry = stored.get("expiry")
        if expiry:
            console.print(f"Token expiry: {expiry}")

    # Validate connectivity
    try:
        creds = get_credentials(config)
        client = build_admin_client(creds)
        list(client.list_accounts())
        console.print("[green]Connected[/green]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed:[/red] {exc}")


@auth_app.command("logout")
def logout() -> None:
    """Remove stored authentication credentials."""
    auth_keys = [
        "auth_method",
        "oauth2_credentials",
        "oauth2_client_secret_file",
        "key_file",
        "access_token",
    ]
    config = cfg.load_config()
    for key in auth_keys:
        config.pop(key, None)
    cfg.save_config(config)
    console.print("[green]Logged out.[/green] Authentication credentials cleared.")
