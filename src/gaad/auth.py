"""Authentication utilities for gaad-cli.

Supports three auth methods:
- oauth2: InstalledAppFlow / stored credentials
- service-account: service account key file
- token: raw access token (or GA4_ACCESS_TOKEN env var)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import google.auth
import google.auth.credentials
import google.auth.transport.requests
import google.oauth2.credentials
import google.oauth2.service_account
from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
from google.api_core import gapic_v1

from gaad.errors import AuthError

GA4_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/analytics.edit",
]


def get_credentials(config: dict) -> google.auth.credentials.Credentials:
    """Build credentials from stored config.

    Args:
        config: Config dict (typically from :func:`gaad.config.load_config`).

    Returns:
        A valid :class:`google.auth.credentials.Credentials` instance.

    Raises:
        AuthError: If no auth method is configured or credentials cannot be built.
    """
    auth_method: str | None = config.get("auth_method")

    if not auth_method:
        raise AuthError("Not authenticated. Run: gaad auth login")

    if auth_method == "service-account":
        key_file: str = config["key_file"]
        return google.oauth2.service_account.Credentials.from_service_account_file(
            key_file,
            scopes=GA4_SCOPES,
        )

    if auth_method == "token":
        token: str | None = config.get("access_token") or os.environ.get("GA4_ACCESS_TOKEN")
        if not token:
            raise AuthError(
                "No access token found. Provide --token or set GA4_ACCESS_TOKEN env var."
            )
        return google.oauth2.credentials.Credentials(token=token)

    if auth_method == "oauth2":
        stored: dict = config["oauth2_credentials"]
        creds = deserialize_oauth2_credentials(stored)
        if creds.expired and creds.refresh_token:
            request = google.auth.transport.requests.Request()
            creds.refresh(request)
        return creds

    raise AuthError(f"Unknown auth method: {auth_method!r}. Run: gaad auth login")


def build_admin_client(credentials: google.auth.credentials.Credentials) -> AnalyticsAdminServiceClient:
    """Construct an :class:`AnalyticsAdminServiceClient` from *credentials*.

    Args:
        credentials: Valid Google credentials.

    Returns:
        Configured admin API client.
    """
    return AnalyticsAdminServiceClient(credentials=credentials)


def serialize_oauth2_credentials(creds: google.oauth2.credentials.Credentials) -> dict[str, Any]:
    """Convert an OAuth2 credentials object to a JSON-serialisable dict.

    Args:
        creds: OAuth2 credentials to serialise.

    Returns:
        Dict with token fields suitable for :func:`save_config`.
    """
    expiry_str: str | None = None
    if creds.expiry is not None:
        expiry: datetime = creds.expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        expiry_str = expiry.isoformat()

    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else [],
        "expiry": expiry_str,
    }


def deserialize_oauth2_credentials(data: dict[str, Any]) -> google.oauth2.credentials.Credentials:
    """Reconstruct OAuth2 credentials from a serialised dict.

    Args:
        data: Dict produced by :func:`serialize_oauth2_credentials`.

    Returns:
        Reconstructed :class:`google.oauth2.credentials.Credentials`.
    """
    expiry: datetime | None = None
    if data.get("expiry"):
        expiry = datetime.fromisoformat(data["expiry"])

    return google.oauth2.credentials.Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
        expiry=expiry,
    )
