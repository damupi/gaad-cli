"""Tests for gaad.commands.data_streams — TDD: tests written before implementation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from typer.testing import CliRunner

from gaad.cli import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _make_mock_web_stream(pid: str = "123", sid: str = "456") -> MagicMock:
    """Return a mock web data stream object."""
    s = MagicMock()
    s.name = f"properties/{pid}/dataStreams/{sid}"
    s.display_name = "My Website"
    s.type_ = MagicMock()
    s.type_.name = "WEB_DATA_STREAM"
    s.create_time = MagicMock(__str__=lambda self: "2024-01-01")
    s.update_time = MagicMock(__str__=lambda self: "2024-06-01")
    s.web_stream_data = MagicMock()
    s.web_stream_data.measurement_id = "G-ABC123"
    s.web_stream_data.default_uri = "https://example.com"
    s.web_stream_data.firebase_app_id = ""
    s.android_app_stream_data = None
    s.ios_app_stream_data = None
    return s


def _make_mock_android_stream(pid: str = "123", sid: str = "789") -> MagicMock:
    """Return a mock Android app data stream object."""
    s = MagicMock()
    s.name = f"properties/{pid}/dataStreams/{sid}"
    s.display_name = "My Android App"
    s.type_ = MagicMock()
    s.type_.name = "ANDROID_APP_DATA_STREAM"
    s.create_time = MagicMock(__str__=lambda self: "2024-01-01")
    s.update_time = MagicMock(__str__=lambda self: "2024-06-01")
    s.web_stream_data = None
    s.android_app_stream_data = MagicMock()
    s.android_app_stream_data.package_name = "com.example.app"
    s.android_app_stream_data.firebase_app_id = ""
    s.ios_app_stream_data = None
    return s


def _make_mock_ios_stream(pid: str = "123", sid: str = "999") -> MagicMock:
    """Return a mock iOS app data stream object."""
    s = MagicMock()
    s.name = f"properties/{pid}/dataStreams/{sid}"
    s.display_name = "My iOS App"
    s.type_ = MagicMock()
    s.type_.name = "IOS_APP_DATA_STREAM"
    s.create_time = MagicMock(__str__=lambda self: "2024-01-01")
    s.update_time = MagicMock(__str__=lambda self: "2024-06-01")
    s.web_stream_data = None
    s.android_app_stream_data = None
    s.ios_app_stream_data = MagicMock()
    s.ios_app_stream_data.bundle_id = "com.example.app"
    s.ios_app_stream_data.firebase_app_id = ""
    return s


def _patch_client(mock_client: MagicMock):
    """Return a patch context manager for get_client in shared.client."""
    return patch("gaad.commands.data_streams.get_client", return_value=mock_client)


def _setup_config(tmp_config_dir: Path) -> None:
    """Write minimal token auth config so _get_client does not fail on missing config."""
    from gaad import config as cfg

    cfg.set("auth_method", "token")
    cfg.set("access_token", "tok")


# ---------------------------------------------------------------------------
# TestDataStreamsList
# ---------------------------------------------------------------------------


class TestDataStreamsList:
    """gaad data-streams list command."""

    def test_list_calls_api_with_correct_parent(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_data_streams.return_value = [_make_mock_web_stream()]

        with _patch_client(mock_client):
            result = runner.invoke(
                app, ["data-streams", "list", "--property-id", "123"]
            )

        assert result.exit_code == 0, result.output
        mock_client.list_data_streams.assert_called_once_with(parent="properties/123")

    def test_list_renders_table_with_streams(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_data_streams.return_value = [
            _make_mock_web_stream(),
            _make_mock_android_stream(),
        ]

        with _patch_client(mock_client):
            result = runner.invoke(
                app, ["data-streams", "list", "--property-id", "123"]
            )

        assert result.exit_code == 0, result.output
        assert "My Website" in result.output
        assert "My Android App" in result.output

    def test_list_output_json_is_list(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_data_streams.return_value = [
            _make_mock_web_stream(),
            _make_mock_android_stream(),
        ]

        with _patch_client(mock_client):
            result = runner.invoke(
                app, ["data-streams", "list", "--property-id", "123", "--output", "json"]
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_output_csv_has_header(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_data_streams.return_value = [_make_mock_web_stream()]

        with _patch_client(mock_client):
            result = runner.invoke(
                app, ["data-streams", "list", "--property-id", "123", "--output", "csv"]
            )

        assert result.exit_code == 0, result.output
        first_line = result.output.strip().splitlines()[0]
        assert "stream_id" in first_line

    def test_list_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        with patch(
            "gaad.shared.client.get_credentials",
            side_effect=AuthError("Not authenticated"),
        ):
            result = runner.invoke(
                app, ["data-streams", "list", "--property-id", "123"]
            )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestDataStreamsGet
# ---------------------------------------------------------------------------


class TestDataStreamsGet:
    """gaad data-streams get command."""

    def test_get_calls_api_with_correct_name(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "get",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.get_data_stream.assert_called_once_with(
            name="properties/123/dataStreams/456"
        )

    def test_get_table_shows_display_name(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "get",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "My Website" in result.output

    def test_get_json_has_stream_id(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "get",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["stream_id"] == "456"

    def test_get_json_web_stream_includes_measurement_id(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "get",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["measurement_id"] == "G-ABC123"

    def test_get_output_csv_has_header_and_row(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "get",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                    "--output",
                    "csv",
                ],
            )

        assert result.exit_code == 0, result.output
        lines = result.output.strip().splitlines()
        assert len(lines) >= 2
        assert "stream_id" in lines[0]

    def test_get_missing_stream_id_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                ["data-streams", "get", "--property-id", "123"],
            )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestDataStreamsCreate
# ---------------------------------------------------------------------------


class TestDataStreamsCreate:
    """gaad data-streams create command."""

    def test_create_web_stream_calls_api(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "create",
                    "--property-id",
                    "123",
                    "--display-name",
                    "My Website",
                    "--type",
                    "WEB_DATA_STREAM",
                    "--default-uri",
                    "https://example.com",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.create_data_stream.assert_called_once()
        assert "456" in result.output

    def test_create_android_stream_calls_api(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_data_stream.return_value = _make_mock_android_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "create",
                    "--property-id",
                    "123",
                    "--display-name",
                    "My Android App",
                    "--type",
                    "ANDROID_APP_DATA_STREAM",
                    "--package-name",
                    "com.x",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.create_data_stream.assert_called_once()

    def test_create_ios_stream_calls_api(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_data_stream.return_value = _make_mock_ios_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "create",
                    "--property-id",
                    "123",
                    "--display-name",
                    "My iOS App",
                    "--type",
                    "IOS_APP_DATA_STREAM",
                    "--bundle-id",
                    "com.x",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.create_data_stream.assert_called_once()

    def test_create_android_missing_package_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "create",
                    "--property-id",
                    "123",
                    "--display-name",
                    "My Android App",
                    "--type",
                    "ANDROID_APP_DATA_STREAM",
                ],
            )

        assert result.exit_code != 0

    def test_create_ios_missing_bundle_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "create",
                    "--property-id",
                    "123",
                    "--display-name",
                    "My iOS App",
                    "--type",
                    "IOS_APP_DATA_STREAM",
                ],
            )

        assert result.exit_code != 0

    def test_create_output_json_has_stream_id(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "create",
                    "--property-id",
                    "123",
                    "--display-name",
                    "My Website",
                    "--type",
                    "WEB_DATA_STREAM",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "stream_id" in data
        assert data["stream_id"] == "456"


# ---------------------------------------------------------------------------
# TestDataStreamsPatch
# ---------------------------------------------------------------------------


class TestDataStreamsPatch:
    """gaad data-streams patch command."""

    def test_patch_calls_update_data_stream(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "patch",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                    "--display-name",
                    "Updated Name",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.update_data_stream.assert_called_once()

    def test_patch_display_name_in_mask(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "patch",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                    "--display-name",
                    "Updated Name",
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_data_stream.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get("update_mask")
        assert "display_name" in mask.paths

    def test_patch_default_uri_in_mask(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "patch",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                    "--default-uri",
                    "https://updated.com",
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_data_stream.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get("update_mask")
        assert "web_stream_data.default_uri" in mask.paths

    def test_patch_no_fields_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "patch",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                ],
            )

        assert result.exit_code != 0

    def test_patch_output_json_has_stream_id(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "patch",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                    "--display-name",
                    "Updated Name",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["stream_id"] == "456"


# ---------------------------------------------------------------------------
# TestDataStreamsDelete
# ---------------------------------------------------------------------------


class TestDataStreamsDelete:
    """gaad data-streams delete command."""

    def test_delete_force_calls_delete_api(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.delete_data_stream.return_value = None

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "delete",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                    "--force",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.delete_data_stream.assert_called_once_with(
            name="properties/123/dataStreams/456"
        )

    def test_delete_force_prints_success(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.delete_data_stream.return_value = None

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "delete",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                    "--force",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "deleted" in result.output.lower()

    def test_delete_confirms_before_deleting(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_data_stream.return_value = _make_mock_web_stream()
        mock_client.delete_data_stream.return_value = None

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "delete",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                ],
                input="y\n",
            )

        assert result.exit_code == 0, result.output
        mock_client.delete_data_stream.assert_called_once_with(
            name="properties/123/dataStreams/456"
        )

    def test_delete_aborts_on_no(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_data_stream.return_value = _make_mock_web_stream()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "delete",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                ],
                input="n\n",
            )

        assert result.exit_code == 0, result.output
        mock_client.delete_data_stream.assert_not_called()

    def test_delete_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        with patch(
            "gaad.shared.client.get_credentials",
            side_effect=AuthError("Not authenticated"),
        ):
            result = runner.invoke(
                app,
                [
                    "data-streams",
                    "delete",
                    "--property-id",
                    "123",
                    "--stream-id",
                    "456",
                    "--force",
                ],
            )

        assert result.exit_code != 0
