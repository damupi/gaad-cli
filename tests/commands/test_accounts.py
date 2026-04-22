"""Tests for gaad.commands.accounts — written before implementation (TDD)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from gaad.cli import app


runner = CliRunner()


class TestAccountsList:
    """gaad accounts list command."""

    def test_list_calls_list_accounts_and_renders_table(
        self, tmp_config_dir: Path, sample_accounts: list[MagicMock]
    ) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        with patch("gaad.commands.accounts.get_credentials") as mock_creds:
            with patch("gaad.commands.accounts.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_accounts.return_value = sample_accounts
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(app, ["accounts", "list"])

        assert result.exit_code == 0, result.output
        mock_client.list_accounts.assert_called_once()
        # Check account names appear in output
        assert "Acme Corp" in result.output
        assert "Beta Inc" in result.output

    def test_list_output_json_is_valid_list(
        self, tmp_config_dir: Path, sample_accounts: list[MagicMock]
    ) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        with patch("gaad.commands.accounts.get_credentials") as mock_creds:
            with patch("gaad.commands.accounts.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_accounts.return_value = sample_accounts
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(app, ["accounts", "list", "--output", "json"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["display_name"] == "Acme Corp"

    def test_list_output_csv_has_header_and_rows(
        self, tmp_config_dir: Path, sample_accounts: list[MagicMock]
    ) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        with patch("gaad.commands.accounts.get_credentials") as mock_creds:
            with patch("gaad.commands.accounts.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_accounts.return_value = sample_accounts
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(app, ["accounts", "list", "--output", "csv"])

        assert result.exit_code == 0, result.output
        lines = result.output.strip().splitlines()
        assert len(lines) >= 4  # header + 3 accounts
        assert "account_id" in lines[0].lower() or "id" in lines[0].lower()
        assert "Acme Corp" in result.output

    def test_list_with_no_auth_shows_error_and_exits_nonzero(
        self, tmp_config_dir: Path
    ) -> None:
        from gaad.errors import AuthError

        with patch("gaad.commands.accounts.get_credentials") as mock_creds:
            mock_creds.side_effect = AuthError("Not authenticated. Run: gaad auth login")
            result = runner.invoke(app, ["accounts", "list"])

        assert result.exit_code != 0
        assert "Not authenticated" in result.output or "Error" in result.output

    def test_list_extracts_account_id_from_name(
        self, tmp_config_dir: Path
    ) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        acct = MagicMock()
        acct.name = "accounts/987654321"
        acct.display_name = "Test Account"

        with patch("gaad.commands.accounts.get_credentials") as mock_creds:
            with patch("gaad.commands.accounts.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_accounts.return_value = [acct]
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(app, ["accounts", "list"])

        assert result.exit_code == 0
        assert "987654321" in result.output
