"""Tests for gaad.commands.auth — written before implementation (TDD)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from gaad.cli import app


runner = CliRunner()


class TestAuthLogin:
    """gaad auth login commands."""

    def test_login_service_account_stores_key_file(self, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            app,
            ["auth", "login", "--method", "service-account", "--key-file", "/fake/key.json"],
        )
        assert result.exit_code == 0, result.output

        from gaad import config as cfg

        assert cfg.get("auth_method") == "service-account"
        assert cfg.get("key_file") == "/fake/key.json"

    def test_login_token_stores_token(self, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            app,
            ["auth", "login", "--method", "token", "--token", "mytoken123"],
        )
        assert result.exit_code == 0, result.output

        from gaad import config as cfg

        assert cfg.get("auth_method") == "token"
        assert cfg.get("access_token") == "mytoken123"

    def test_login_oauth2_runs_flow(self, tmp_config_dir: Path) -> None:
        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.token = "oauth-token"
        mock_creds.refresh_token = "r-token"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "cid"
        mock_creds.client_secret = "csecret"
        mock_creds.scopes = ["https://www.googleapis.com/auth/analytics.readonly"]
        mock_creds.expiry = None
        mock_flow.run_local_server.return_value = mock_creds

        with patch(
            "gaad.commands.auth.InstalledAppFlow.from_client_secrets_file",
            return_value=mock_flow,
        ):
            result = runner.invoke(
                app,
                [
                    "auth",
                    "login",
                    "--method",
                    "oauth2",
                    "--client-secrets",
                    "/fake/client_secret.json",
                ],
            )
        assert result.exit_code == 0, result.output

        from gaad import config as cfg

        assert cfg.get("auth_method") == "oauth2"
        assert cfg.get("oauth2_credentials") is not None


class TestAuthLoginEdgeCases:
    """Edge cases for auth login."""

    def test_login_service_account_without_key_file_exits_nonzero(
        self, tmp_config_dir: Path
    ) -> None:
        result = runner.invoke(
            app,
            ["auth", "login", "--method", "service-account"],
        )
        assert result.exit_code != 0

    def test_login_oauth2_without_client_secrets_exits_nonzero(
        self, tmp_config_dir: Path
    ) -> None:
        result = runner.invoke(
            app,
            ["auth", "login", "--method", "oauth2"],
        )
        assert result.exit_code != 0

    def test_login_token_via_prompt(self, tmp_config_dir: Path) -> None:
        """Token can be provided interactively when --token is omitted."""
        result = runner.invoke(
            app,
            ["auth", "login", "--method", "token"],
            input="promptedtoken\n",
        )
        assert result.exit_code == 0, result.output
        from gaad import config as cfg

        assert cfg.get("access_token") == "promptedtoken"

    def test_status_shows_oauth2_expiry(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "oauth2")
        cfg.set(
            "oauth2_credentials",
            {
                "token": "tok",
                "refresh_token": "rtok",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "cid",
                "client_secret": "csecret",
                "scopes": [],
                "expiry": "2025-12-31T23:59:59+00:00",
            },
        )

        with patch("gaad.commands.auth.get_credentials") as mock_get_creds:
            with patch("gaad.commands.auth.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_accounts.return_value = []
                mock_build.return_value = mock_client
                mock_get_creds.return_value = MagicMock()
                result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "2025-12-31" in result.output


class TestAuthStatus:
    """gaad auth status command."""

    def test_status_shows_not_authenticated_when_no_config(self, tmp_config_dir: Path) -> None:
        result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "Not authenticated" in result.output

    def test_status_shows_method_and_path_for_service_account(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "service-account")
        cfg.set("key_file", "/path/to/key.json")

        with patch("gaad.commands.auth.get_credentials") as mock_get_creds:
            with patch("gaad.commands.auth.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_accounts.return_value = []
                mock_build.return_value = mock_client
                mock_get_creds.return_value = MagicMock()
                result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "service-account" in result.output
        assert "/path/to/key.json" in result.output

    def test_status_shows_connected_on_successful_api_call(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok123")

        with patch("gaad.commands.auth.get_credentials") as mock_get_creds:
            with patch("gaad.commands.auth.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_accounts.return_value = []
                mock_build.return_value = mock_client
                mock_get_creds.return_value = MagicMock()
                result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "Connected" in result.output

    def test_status_shows_failed_on_api_error(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "bad-token")

        with patch("gaad.commands.auth.get_credentials") as mock_get_creds:
            with patch("gaad.commands.auth.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_accounts.side_effect = Exception("permission denied")
                mock_build.return_value = mock_client
                mock_get_creds.return_value = MagicMock()
                result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "Failed" in result.output

    def test_status_shows_token_prefix_for_token_method(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "abcdefghijklmnop")

        with patch("gaad.commands.auth.get_credentials") as mock_get_creds:
            with patch("gaad.commands.auth.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_accounts.return_value = []
                mock_build.return_value = mock_client
                mock_get_creds.return_value = MagicMock()
                result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "abcdefgh..." in result.output


class TestAuthLogout:
    """gaad auth logout command."""

    def test_logout_clears_auth_keys(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "mytoken")
        cfg.set("key_file", "/some/key.json")
        cfg.set("oauth2_credentials", {"token": "x"})

        result = runner.invoke(app, ["auth", "logout"])
        assert result.exit_code == 0

        assert cfg.get("auth_method") is None
        assert cfg.get("access_token") is None
        assert cfg.get("key_file") is None
        assert cfg.get("oauth2_credentials") is None

    def test_logout_prints_confirmation(self, tmp_config_dir: Path) -> None:
        result = runner.invoke(app, ["auth", "logout"])
        assert result.exit_code == 0
        assert "logged out" in result.output.lower() or "cleared" in result.output.lower()
