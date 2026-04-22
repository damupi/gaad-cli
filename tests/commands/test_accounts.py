"""Tests for gaad.commands.accounts — written before implementation (TDD)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from typer.testing import CliRunner

from gaad.cli import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_account() -> MagicMock:
    """Return a standard mock account object."""
    mock_account = MagicMock()
    mock_account.name = "accounts/123"
    mock_account.display_name = "Test Account"
    mock_account.create_time = MagicMock(__str__=lambda self: "2024-01-01")
    mock_account.update_time = MagicMock(__str__=lambda self: "2024-06-01")
    mock_account.region_code = "IE"
    mock_account.deleted = False
    return mock_account


def _make_mock_settings() -> MagicMock:
    """Return a standard mock data sharing settings object."""
    mock_settings = MagicMock()
    mock_settings.sharing_with_google_support_enabled = True
    mock_settings.sharing_with_google_assigned_sales_enabled = False
    mock_settings.sharing_with_google_any_sales_enabled = False
    mock_settings.sharing_with_google_products_enabled = True
    mock_settings.sharing_with_others_enabled = False
    return mock_settings


def _patch_client(mock_client: MagicMock):
    """Return a context manager tuple that patches creds + client builder."""
    return (
        patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()),
        patch("gaad.commands.accounts.build_admin_client", return_value=mock_client),
    )


# ---------------------------------------------------------------------------
# Existing tests
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# TestAccountsGet
# ---------------------------------------------------------------------------

class TestAccountsGet:
    """gaad accounts get command."""

    def test_get_calls_api_with_correct_name(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_account.return_value = _make_mock_account()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(app, ["accounts", "get", "--account-id", "123"])

        assert result.exit_code == 0, result.output
        mock_client.get_account.assert_called_once_with(name="accounts/123")

    def test_get_table_shows_display_name(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_account.return_value = _make_mock_account()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(app, ["accounts", "get", "--account-id", "123"])

        assert result.exit_code == 0, result.output
        assert "Test Account" in result.output

    def test_get_output_json_is_dict_with_account_id(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_account.return_value = _make_mock_account()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app, ["accounts", "get", "--account-id", "123", "--output", "json"]
                )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert data["account_id"] == "123"

    def test_get_output_csv_has_header_and_row(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_account.return_value = _make_mock_account()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app, ["accounts", "get", "--account-id", "123", "--output", "csv"]
                )

        assert result.exit_code == 0, result.output
        lines = result.output.strip().splitlines()
        assert len(lines) >= 2  # header + data row
        assert "account_id" in lines[0]

    def test_get_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        with patch(
            "gaad.commands.accounts.get_credentials",
            side_effect=AuthError("Not authenticated"),
        ):
            result = runner.invoke(app, ["accounts", "get", "--account-id", "123"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestAccountsDelete
# ---------------------------------------------------------------------------

class TestAccountsDelete:
    """gaad accounts delete command."""

    def test_delete_force_calls_delete_account(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_account.return_value = _make_mock_account()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app, ["accounts", "delete", "--account-id", "123", "--force"]
                )

        assert result.exit_code == 0, result.output
        mock_client.delete_account.assert_called_once_with(name="accounts/123")

    def test_delete_force_prints_trash_message(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_account.return_value = _make_mock_account()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app, ["accounts", "delete", "--account-id", "123", "--force"]
                )

        assert result.exit_code == 0, result.output
        assert "trash" in result.output.lower() or "30 days" in result.output.lower()

    def test_delete_confirms_before_deleting(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_account.return_value = _make_mock_account()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app, ["accounts", "delete", "--account-id", "123"], input="y\n"
                )

        assert result.exit_code == 0, result.output
        mock_client.delete_account.assert_called_once_with(name="accounts/123")

    def test_delete_aborts_on_no(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_account.return_value = _make_mock_account()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app, ["accounts", "delete", "--account-id", "123"], input="n\n"
                )

        assert result.exit_code == 0, result.output
        mock_client.delete_account.assert_not_called()

    def test_delete_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        with patch(
            "gaad.commands.accounts.get_credentials",
            side_effect=AuthError("Not authenticated"),
        ):
            result = runner.invoke(
                app, ["accounts", "delete", "--account-id", "123", "--force"]
            )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestAccountsGetDataSharingSettings
# ---------------------------------------------------------------------------

class TestAccountsGetDataSharingSettings:
    """gaad accounts get-data-sharing-settings command."""

    def test_get_data_sharing_calls_correct_api(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_data_sharing_settings.return_value = _make_mock_settings()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app,
                    ["accounts", "get-data-sharing-settings", "--account-id", "123"],
                )

        assert result.exit_code == 0, result.output
        mock_client.get_data_sharing_settings.assert_called_once_with(
            name="accounts/123/dataSharingSettings"
        )

    def test_get_data_sharing_table_shows_yes_no(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_data_sharing_settings.return_value = _make_mock_settings()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app,
                    ["accounts", "get-data-sharing-settings", "--account-id", "123"],
                )

        assert result.exit_code == 0, result.output
        assert "Yes" in result.output
        assert "No" in result.output

    def test_get_data_sharing_json_has_boolean_values(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_data_sharing_settings.return_value = _make_mock_settings()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app,
                    [
                        "accounts",
                        "get-data-sharing-settings",
                        "--account-id",
                        "123",
                        "--output",
                        "json",
                    ],
                )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["sharing_with_google_support_enabled"] is True

    def test_get_data_sharing_csv_has_rows(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.get_data_sharing_settings.return_value = _make_mock_settings()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app,
                    [
                        "accounts",
                        "get-data-sharing-settings",
                        "--account-id",
                        "123",
                        "--output",
                        "csv",
                    ],
                )

        assert result.exit_code == 0, result.output
        lines = result.output.strip().splitlines()
        # header + 5 settings rows
        assert len(lines) >= 6


# ---------------------------------------------------------------------------
# TestAccountsPatch
# ---------------------------------------------------------------------------

class TestAccountsPatch:
    """gaad accounts patch command."""

    def test_patch_calls_update_account(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.update_account.return_value = _make_mock_account()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app,
                    [
                        "accounts",
                        "patch",
                        "--account-id",
                        "123",
                        "--display-name",
                        "New Name",
                    ],
                )

        assert result.exit_code == 0, result.output
        mock_client.update_account.assert_called_once()

    def test_patch_mask_contains_display_name(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.update_account.return_value = _make_mock_account()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app,
                    [
                        "accounts",
                        "patch",
                        "--account-id",
                        "123",
                        "--display-name",
                        "New Name",
                    ],
                )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_account.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get("update_mask")
        assert "display_name" in mask.paths

    def test_patch_with_region_code_adds_to_mask(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        mock_client.update_account.return_value = _make_mock_account()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app,
                    [
                        "accounts",
                        "patch",
                        "--account-id",
                        "123",
                        "--display-name",
                        "New Name",
                        "--region-code",
                        "US",
                    ],
                )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_account.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get("update_mask")
        assert "region_code" in mask.paths

    def test_patch_output_shows_updated_account(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()
        updated = _make_mock_account()
        updated.display_name = "New Name"
        mock_client.update_account.return_value = updated

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app,
                    [
                        "accounts",
                        "patch",
                        "--account-id",
                        "123",
                        "--display-name",
                        "New Name",
                    ],
                )

        assert result.exit_code == 0, result.output
        assert "New Name" in result.output

    def test_patch_missing_display_name_exits_nonzero(self, tmp_config_dir: Path) -> None:
        mock_client = MagicMock()

        with patch("gaad.commands.accounts.get_credentials", return_value=MagicMock()):
            with patch("gaad.commands.accounts.build_admin_client", return_value=mock_client):
                result = runner.invoke(
                    app,
                    ["accounts", "patch", "--account-id", "123"],
                )

        assert result.exit_code != 0
