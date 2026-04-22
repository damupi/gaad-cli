"""Tests for gaad.commands.properties — written before implementation (TDD)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from typer.testing import CliRunner

from gaad.cli import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_mock_property(pid="456", name="Test Property"):
    """Build a fully-populated mock GA4 Property object."""
    prop = MagicMock()
    prop.name = f"properties/{pid}"
    prop.display_name = name
    prop.property_type = MagicMock(name_="PROPERTY_TYPE_ORDINARY")
    prop.property_type.name = "PROPERTY_TYPE_ORDINARY"
    prop.parent = "accounts/123"
    prop.create_time = MagicMock(__str__=lambda self: "2024-01-01")
    prop.update_time = MagicMock(__str__=lambda self: "2024-06-01")
    prop.time_zone = "Europe/Dublin"
    prop.currency_code = "EUR"
    prop.industry_category = MagicMock()
    prop.industry_category.name = "ARTS_AND_ENTERTAINMENT"
    prop.service_level = MagicMock()
    prop.service_level.name = "GOOGLE_ANALYTICS_STANDARD"
    prop.deleted = False
    return prop


def _make_mock_retention():
    """Build a mock DataRetentionSettings object."""
    s = MagicMock()
    s.event_data_retention = MagicMock()
    s.event_data_retention.name = "FOURTEEN_MONTHS"
    s.user_data_retention = MagicMock()
    s.user_data_retention.name = "TWO_MONTHS"
    s.reset_user_data_on_new_activity = False
    return s


def _patch_client(mock_client):
    """Return a context manager stack that patches both auth helpers."""
    return (
        patch("gaad.commands.properties.get_credentials", return_value=MagicMock()),
        patch("gaad.commands.properties.build_admin_client", return_value=mock_client),
    )


# ---------------------------------------------------------------------------
# Existing tests (unchanged)
# ---------------------------------------------------------------------------

class TestPropertiesList:
    """gaad properties list command."""

    def test_list_calls_list_properties_with_correct_filter(
        self, tmp_config_dir: Path, sample_properties: list[MagicMock]
    ) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            with patch("gaad.commands.properties.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_properties.return_value = sample_properties
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(app, ["properties", "list", "--account-id", "123"])

        assert result.exit_code == 0, result.output
        mock_client.list_properties.assert_called_once()
        call_args = mock_client.list_properties.call_args
        # Check the request has the correct filter
        request_arg = call_args[0][0] if call_args[0] else call_args[1].get("request")
        assert request_arg is not None
        assert "parent:accounts/123" in str(request_arg.filter)

    def test_list_show_deleted_passes_flag(
        self, tmp_config_dir: Path, sample_properties: list[MagicMock]
    ) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            with patch("gaad.commands.properties.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_properties.return_value = sample_properties
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(
                    app,
                    ["properties", "list", "--account-id", "123", "--show-deleted"],
                )

        assert result.exit_code == 0, result.output
        call_args = mock_client.list_properties.call_args
        request_arg = call_args[0][0] if call_args[0] else call_args[1].get("request")
        assert request_arg.show_deleted is True

    def test_list_output_json_is_valid(
        self, tmp_config_dir: Path, sample_properties: list[MagicMock]
    ) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            with patch("gaad.commands.properties.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_properties.return_value = sample_properties
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(
                    app,
                    ["properties", "list", "--account-id", "123", "--output", "json"],
                )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["display_name"] == "Main Site"

    def test_list_missing_account_id_shows_error(self, tmp_config_dir: Path) -> None:
        result = runner.invoke(app, ["properties", "list"])
        assert result.exit_code != 0

    def test_list_both_flags_exits_nonzero(self, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            app, ["properties", "list", "--account-id", "123", "--property-id", "456"]
        )
        assert result.exit_code != 0

    def test_list_with_property_id_builds_parent_properties_filter(
        self, tmp_config_dir: Path, sample_properties: list[MagicMock]
    ) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            with patch("gaad.commands.properties.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_properties.return_value = sample_properties
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(app, ["properties", "list", "--property-id", "789"])

        assert result.exit_code == 0, result.output
        call_args = mock_client.list_properties.call_args
        request_arg = call_args[0][0] if call_args[0] else call_args[1].get("request")
        assert "parent:properties/789" in str(request_arg.filter)

    def test_list_with_no_auth_shows_error_and_exits_nonzero(
        self, tmp_config_dir: Path
    ) -> None:
        from gaad.errors import AuthError

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            mock_creds.side_effect = AuthError("Not authenticated. Run: gaad auth login")
            result = runner.invoke(
                app, ["properties", "list", "--account-id", "123"]
            )

        assert result.exit_code != 0

    def test_list_output_csv_has_header_and_rows(
        self, tmp_config_dir: Path, sample_properties: list[MagicMock]
    ) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            with patch("gaad.commands.properties.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_properties.return_value = sample_properties
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(
                    app,
                    ["properties", "list", "--account-id", "123", "--output", "csv"],
                )

        assert result.exit_code == 0, result.output
        lines = result.output.strip().splitlines()
        assert len(lines) >= 4  # header + 3 properties
        assert "property_id" in lines[0].lower() or "id" in lines[0].lower()
        assert "Main Site" in result.output

    def test_list_extracts_property_id_from_name(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        prop = MagicMock()
        prop.name = "properties/99887766"
        prop.display_name = "My Property"

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            with patch("gaad.commands.properties.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.list_properties.return_value = [prop]
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(app, ["properties", "list", "--account-id", "123"])

        assert result.exit_code == 0
        assert "99887766" in result.output


class TestPropertiesGet:
    """gaad properties get command."""

    def test_get_calls_get_property_with_correct_name(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        prop = MagicMock()
        prop.name = "properties/456"
        prop.display_name = "My Property"
        prop.create_time = MagicMock()
        prop.create_time.__str__ = lambda self: "2024-01-01T00:00:00Z"
        prop.update_time = MagicMock()
        prop.update_time.__str__ = lambda self: "2024-06-01T00:00:00Z"
        prop.currency_code = "USD"
        prop.time_zone = "America/Chicago"
        prop.industry_category = "FINANCE"

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            with patch("gaad.commands.properties.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.get_property.return_value = prop
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(app, ["properties", "get", "--property-id", "456"])

        assert result.exit_code == 0, result.output
        mock_client.get_property.assert_called_once_with(name="properties/456")
        assert "My Property" in result.output
        assert "456" in result.output

    def test_get_output_json_contains_all_fields(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        prop = MagicMock()
        prop.name = "properties/789"
        prop.display_name = "JSON Property"
        prop.create_time = MagicMock()
        prop.create_time.__str__ = lambda self: "2024-01-01T00:00:00Z"
        prop.update_time = MagicMock()
        prop.update_time.__str__ = lambda self: "2024-06-01T00:00:00Z"
        prop.currency_code = "EUR"
        prop.time_zone = "Europe/London"
        prop.industry_category = "RETAIL"

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            with patch("gaad.commands.properties.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.get_property.return_value = prop
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(
                    app,
                    ["properties", "get", "--property-id", "789", "--output", "json"],
                )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["property_id"] == "789"
        assert data["display_name"] == "JSON Property"
        assert data["currency_code"] == "EUR"
        assert data["time_zone"] == "Europe/London"
        assert data["industry_category"] == "RETAIL"

    def test_get_missing_property_id_shows_error(self, tmp_config_dir: Path) -> None:
        result = runner.invoke(app, ["properties", "get"])
        assert result.exit_code != 0

    def test_get_output_csv_has_header_and_row(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        prop = MagicMock()
        prop.name = "properties/321"
        prop.display_name = "CSV Property"
        prop.create_time = MagicMock()
        prop.create_time.__str__ = lambda self: "2024-01-01T00:00:00Z"
        prop.update_time = MagicMock()
        prop.update_time.__str__ = lambda self: "2024-06-01T00:00:00Z"
        prop.currency_code = "GBP"
        prop.time_zone = "Europe/Paris"
        prop.industry_category = "EDUCATION"

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            with patch("gaad.commands.properties.build_admin_client") as mock_build:
                mock_client = MagicMock()
                mock_client.get_property.return_value = prop
                mock_build.return_value = mock_client
                mock_creds.return_value = MagicMock()

                result = runner.invoke(
                    app,
                    ["properties", "get", "--property-id", "321", "--output", "csv"],
                )

        assert result.exit_code == 0, result.output
        lines = result.output.strip().splitlines()
        assert len(lines) == 2  # header + 1 data row
        assert "property_id" in lines[0]
        assert "321" in lines[1]

    def test_get_with_no_auth_shows_error_and_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            mock_creds.side_effect = AuthError("Not authenticated. Run: gaad auth login")
            result = runner.invoke(app, ["properties", "get", "--property-id", "999"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# New tests — Step 3 (TDD: written before implementation)
# ---------------------------------------------------------------------------

class TestPropertiesCreate:
    """gaad properties create command."""

    def test_create_calls_api_with_required_fields(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.create_property.return_value = _make_mock_property()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                [
                    "properties", "create",
                    "--account-id", "123",
                    "--display-name", "Test Property",
                    "--time-zone", "Europe/Dublin",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.create_property.assert_called_once()
        assert "Test Property" in result.output or "456" in result.output

    def test_create_output_json_has_property_id(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.create_property.return_value = _make_mock_property(pid="456")

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                [
                    "properties", "create",
                    "--account-id", "123",
                    "--display-name", "Test Property",
                    "--time-zone", "Europe/Dublin",
                    "--output", "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["property_id"] == "456"

    def test_create_missing_account_id_exits_nonzero(self, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "properties", "create",
                "--display-name", "Test",
                "--time-zone", "UTC",
            ],
        )
        assert result.exit_code != 0

    def test_create_missing_display_name_exits_nonzero(self, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "properties", "create",
                "--account-id", "123",
                "--time-zone", "UTC",
            ],
        )
        assert result.exit_code != 0

    def test_create_missing_time_zone_exits_nonzero(self, tmp_config_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "properties", "create",
                "--account-id", "123",
                "--display-name", "Test",
            ],
        )
        assert result.exit_code != 0


class TestPropertiesDelete:
    """gaad properties delete command."""

    def test_delete_force_calls_delete_property(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.delete_property.return_value = _make_mock_property()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                ["properties", "delete", "--property-id", "456", "--force"],
            )

        assert result.exit_code == 0, result.output
        mock_client.delete_property.assert_called_once_with(name="properties/456")

    def test_delete_force_prints_trash_message(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.delete_property.return_value = _make_mock_property()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                ["properties", "delete", "--property-id", "456", "--force"],
            )

        assert result.exit_code == 0, result.output
        assert "trash" in result.output.lower() or "recovered" in result.output.lower()

    def test_delete_confirms_before_deleting(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.get_property.return_value = _make_mock_property()
        mock_client.delete_property.return_value = _make_mock_property()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                ["properties", "delete", "--property-id", "456"],
                input="y\n",
            )

        assert result.exit_code == 0, result.output
        mock_client.delete_property.assert_called_once_with(name="properties/456")

    def test_delete_aborts_on_no(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.get_property.return_value = _make_mock_property()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                ["properties", "delete", "--property-id", "456"],
                input="n\n",
            )

        assert result.exit_code == 0
        mock_client.delete_property.assert_not_called()

    def test_delete_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        with patch("gaad.commands.properties.get_credentials") as mock_creds:
            mock_creds.side_effect = AuthError("Not authenticated")
            result = runner.invoke(
                app,
                ["properties", "delete", "--property-id", "456", "--force"],
            )

        assert result.exit_code != 0


class TestPropertiesGetDataRetentionSettings:
    """gaad properties get-data-retention-settings command."""

    def test_get_retention_calls_correct_api(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.get_data_retention_settings.return_value = _make_mock_retention()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                ["properties", "get-data-retention-settings", "--property-id", "456"],
            )

        assert result.exit_code == 0, result.output
        mock_client.get_data_retention_settings.assert_called_once_with(
            name="properties/456/dataRetentionSettings"
        )

    def test_get_retention_table_shows_fields(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.get_data_retention_settings.return_value = _make_mock_retention()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                ["properties", "get-data-retention-settings", "--property-id", "456"],
            )

        assert result.exit_code == 0, result.output
        assert "FOURTEEN_MONTHS" in result.output or "TWO_MONTHS" in result.output

    def test_get_retention_json_has_expected_keys(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.get_data_retention_settings.return_value = _make_mock_retention()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                [
                    "properties", "get-data-retention-settings",
                    "--property-id", "456",
                    "--output", "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "event_data_retention" in data
        assert data["event_data_retention"] == "FOURTEEN_MONTHS"


class TestPropertiesPatch:
    """gaad properties patch command."""

    def test_patch_calls_update_property(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.update_property.return_value = _make_mock_property()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                [
                    "properties", "patch",
                    "--property-id", "456",
                    "--display-name", "New Name",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.update_property.assert_called_once()

    def test_patch_mask_contains_display_name(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.update_property.return_value = _make_mock_property()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                [
                    "properties", "patch",
                    "--property-id", "456",
                    "--display-name", "New Name",
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_property.call_args.kwargs
        mask = call_kwargs.get("update_mask") or mock_client.update_property.call_args[1].get("update_mask")
        assert "display_name" in mask.paths

    def test_patch_multiple_fields_all_in_mask(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.update_property.return_value = _make_mock_property()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                [
                    "properties", "patch",
                    "--property-id", "456",
                    "--display-name", "New Name",
                    "--time-zone", "America/New_York",
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_property.call_args.kwargs
        mask = call_kwargs.get("update_mask")
        assert "display_name" in mask.paths
        assert "time_zone" in mask.paths

    def test_patch_no_fields_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                ["properties", "patch", "--property-id", "456"],
            )

        assert result.exit_code != 0

    def test_patch_output_json_has_property_id(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.update_property.return_value = _make_mock_property(pid="456")

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                [
                    "properties", "patch",
                    "--property-id", "456",
                    "--display-name", "New Name",
                    "--output", "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["property_id"] == "456"


class TestPropertiesUpdateDataRetentionSettings:
    """gaad properties update-data-retention-settings command."""

    def test_update_retention_calls_update_api(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.update_data_retention_settings.return_value = _make_mock_retention()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                [
                    "properties", "update-data-retention-settings",
                    "--property-id", "456",
                    "--event-data-retention", "FOURTEEN_MONTHS",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.update_data_retention_settings.assert_called_once()

    def test_update_retention_mask_contains_event_duration(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.update_data_retention_settings.return_value = _make_mock_retention()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                [
                    "properties", "update-data-retention-settings",
                    "--property-id", "456",
                    "--event-data-retention", "FOURTEEN_MONTHS",
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_data_retention_settings.call_args.kwargs
        mask = call_kwargs.get("update_mask")
        assert "event_data_retention" in mask.paths

    def test_update_retention_reset_flag_included_in_mask(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()
        mock_client.update_data_retention_settings.return_value = _make_mock_retention()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                [
                    "properties", "update-data-retention-settings",
                    "--property-id", "456",
                    "--reset-user-data",
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_data_retention_settings.call_args.kwargs
        mask = call_kwargs.get("update_mask")
        assert "reset_user_data_on_new_activity" in mask.paths

    def test_update_retention_no_fields_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")

        mock_client = MagicMock()

        p1, p2 = _patch_client(mock_client)
        with p1, p2:
            result = runner.invoke(
                app,
                ["properties", "update-data-retention-settings", "--property-id", "456"],
            )

        assert result.exit_code != 0
