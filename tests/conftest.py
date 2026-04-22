"""Shared pytest fixtures for gaad-cli tests."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def tmp_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a temporary config directory and override GAAD_CONFIG_DIR env var."""
    config_dir = tmp_path / "gaad-config"
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GAAD_CONFIG_DIR", str(config_dir))
    return config_dir


@pytest.fixture()
def mock_admin_client() -> MagicMock:
    """Return a MagicMock standing in for AnalyticsAdminServiceClient."""
    return MagicMock()


@pytest.fixture()
def sample_accounts() -> list[MagicMock]:
    """Return a list of mock GA4 account objects."""
    accounts = []
    for i, name in enumerate(["Acme Corp", "Beta Inc", "Gamma LLC"], start=1):
        acct = MagicMock()
        acct.name = f"accounts/{i * 111}"
        acct.display_name = name
        accounts.append(acct)
    return accounts


@pytest.fixture()
def sample_properties() -> list[MagicMock]:
    """Return a list of mock GA4 property objects."""
    properties = []
    for i, name in enumerate(["Main Site", "Mobile App", "Blog"], start=1):
        prop = MagicMock()
        prop.name = f"properties/{i * 100}"
        prop.display_name = name
        prop.create_time = MagicMock()
        prop.create_time.__str__ = lambda self: "2024-01-01T00:00:00Z"
        prop.update_time = MagicMock()
        prop.update_time.__str__ = lambda self: "2024-06-01T00:00:00Z"
        prop.currency_code = "USD"
        prop.time_zone = "America/New_York"
        prop.industry_category = "TECHNOLOGY"
        properties.append(prop)
    return properties
