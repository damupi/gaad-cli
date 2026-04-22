"""Tests for gaad.commands.properties — written before implementation (TDD)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from typer.testing import CliRunner

from gaad.cli import app


runner = CliRunner()


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
