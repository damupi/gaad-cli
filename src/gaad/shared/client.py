"""Shared admin client factory."""

from __future__ import annotations

from typing import Literal

import typer

from gaad import config as cfg
from gaad.auth import build_admin_client, get_credentials
from gaad.errors import AuthError
from gaad.shared.console import err_console


def get_client(version: Literal["v1beta", "v1alpha"] = "v1beta"):
    """Load config, authenticate, and return an admin API client.

    Args:
        version: API version to use — ``"v1beta"`` (default) or ``"v1alpha"``.

    Returns:
        A configured :class:`AnalyticsAdminServiceClient`.

    Raises:
        typer.Exit: with code 1 when authentication fails.
    """
    config = cfg.load_config()
    try:
        creds = get_credentials(config)
    except AuthError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    return build_admin_client(creds, version=version)
