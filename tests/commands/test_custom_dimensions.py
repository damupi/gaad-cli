"""Tests for gaad.commands.custom_dimensions — TDD: tests written before implementation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from gaad.cli import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_dim(pid: str = "123", did: str = "456") -> MagicMock:
    """Return a mock CustomDimension resource object."""
    d = MagicMock()
    d.name = f"properties/{pid}/customDimensions/{did}"
    d.parameter_name = "my_param"
    d.display_name = "My Dimension"
    d.scope = MagicMock()
    d.scope.name = "EVENT"
    d.description = "A test dimension"
    d.disallow_ads_personalization = False
    return d


def _patch_client(mocker, mock_client: MagicMock) -> None:
    """Patch get_client in gaad.commands.custom_dimensions."""
    mocker.patch("gaad.commands.custom_dimensions.get_client", return_value=mock_client)


def _setup_config(tmp_config_dir: Path) -> None:
    """Write minimal token auth config so _get_client does not fail on missing config."""
    from gaad import config as cfg

    cfg.set("auth_method", "token")
    cfg.set("access_token", "tok")


# ---------------------------------------------------------------------------
# TestCustomDimensionsList
# ---------------------------------------------------------------------------


class TestCustomDimensionsList:
    """gaad custom-dimensions list command."""

    def test_list_calls_api_with_correct_parent(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_custom_dimensions.return_value = [_make_mock_dim()]
        _patch_client(mocker, mock_client)

        result = runner.invoke(app, ["custom-dimensions", "list", "--property-id", "123"])

        assert result.exit_code == 0, result.output
        mock_client.list_custom_dimensions.assert_called_once_with(parent="properties/123")

    def test_list_renders_table(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_custom_dimensions.return_value = [_make_mock_dim()]
        _patch_client(mocker, mock_client)

        result = runner.invoke(app, ["custom-dimensions", "list", "--property-id", "123"])

        assert result.exit_code == 0, result.output
        assert "My Dimension" in result.output

    def test_list_output_json_is_list(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_custom_dimensions.return_value = [
            _make_mock_dim(did="456"),
            _make_mock_dim(did="789"),
        ]
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app, ["custom-dimensions", "list", "--property-id", "123", "--output", "json"]
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_output_csv_has_header(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_custom_dimensions.return_value = [_make_mock_dim()]
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app, ["custom-dimensions", "list", "--property-id", "123", "--output", "csv"]
        )

        assert result.exit_code == 0, result.output
        first_line = result.output.strip().splitlines()[0]
        assert "dim_id" in first_line

    def test_list_auth_error_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        mocker.patch(
            "gaad.shared.client.get_credentials",
            side_effect=AuthError("Not authenticated"),
        )

        result = runner.invoke(app, ["custom-dimensions", "list", "--property-id", "123"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestCustomDimensionsGet
# ---------------------------------------------------------------------------


class TestCustomDimensionsGet:
    """gaad custom-dimensions get command."""

    def test_get_calls_api_with_correct_name(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_dimension.return_value = _make_mock_dim()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            ["custom-dimensions", "get", "--property-id", "123", "--dimension-id", "456"],
        )

        assert result.exit_code == 0, result.output
        mock_client.get_custom_dimension.assert_called_once_with(
            name="properties/123/customDimensions/456"
        )

    def test_get_table_shows_display_name(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_dimension.return_value = _make_mock_dim()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            ["custom-dimensions", "get", "--property-id", "123", "--dimension-id", "456"],
        )

        assert result.exit_code == 0, result.output
        assert "My Dimension" in result.output

    def test_get_json_has_dim_id(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_dimension.return_value = _make_mock_dim()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "get",
                "--property-id",
                "123",
                "--dimension-id",
                "456",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["dim_id"] == "456"

    def test_get_missing_dimension_id_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            ["custom-dimensions", "get", "--property-id", "123"],
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestCustomDimensionsCreate
# ---------------------------------------------------------------------------


class TestCustomDimensionsCreate:
    """gaad custom-dimensions create command."""

    def test_create_calls_api(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_custom_dimension.return_value = _make_mock_dim()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "create",
                "--property-id",
                "123",
                "--parameter-name",
                "my_param",
                "--display-name",
                "My Dimension",
                "--scope",
                "EVENT",
            ],
        )

        assert result.exit_code == 0, result.output
        mock_client.create_custom_dimension.assert_called_once()

    def test_create_output_json_has_dim_id(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_custom_dimension.return_value = _make_mock_dim()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "create",
                "--property-id",
                "123",
                "--parameter-name",
                "my_param",
                "--display-name",
                "My Dimension",
                "--scope",
                "EVENT",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["dim_id"] == "456"

    def test_create_missing_parameter_name_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "create",
                "--property-id",
                "123",
                "--display-name",
                "My Dimension",
                "--scope",
                "EVENT",
            ],
        )

        assert result.exit_code != 0

    def test_create_missing_display_name_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "create",
                "--property-id",
                "123",
                "--parameter-name",
                "my_param",
                "--scope",
                "EVENT",
            ],
        )

        assert result.exit_code != 0

    def test_create_missing_scope_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "create",
                "--property-id",
                "123",
                "--parameter-name",
                "my_param",
                "--display-name",
                "My Dimension",
            ],
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestCustomDimensionsPatch
# ---------------------------------------------------------------------------


class TestCustomDimensionsPatch:
    """gaad custom-dimensions patch command."""

    def test_patch_display_name_in_mask(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_custom_dimension.return_value = _make_mock_dim()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "patch",
                "--property-id",
                "123",
                "--dimension-id",
                "456",
                "--display-name",
                "New Name",
            ],
        )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_custom_dimension.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get("update_mask")
        assert "display_name" in mask.paths

    def test_patch_description_in_mask(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_custom_dimension.return_value = _make_mock_dim()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "patch",
                "--property-id",
                "123",
                "--dimension-id",
                "456",
                "--description",
                "New description",
            ],
        )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_custom_dimension.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get("update_mask")
        assert "description" in mask.paths

    def test_patch_no_fields_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "patch",
                "--property-id",
                "123",
                "--dimension-id",
                "456",
            ],
        )

        assert result.exit_code != 0

    def test_patch_output_json_has_dim_id(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_custom_dimension.return_value = _make_mock_dim()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "patch",
                "--property-id",
                "123",
                "--dimension-id",
                "456",
                "--display-name",
                "New Name",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["dim_id"] == "456"


# ---------------------------------------------------------------------------
# TestCustomDimensionsArchive
# ---------------------------------------------------------------------------


class TestCustomDimensionsArchive:
    """gaad custom-dimensions archive command."""

    def test_archive_force_calls_api(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.archive_custom_dimension.return_value = None
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "archive",
                "--property-id",
                "123",
                "--dimension-id",
                "456",
                "--force",
            ],
        )

        assert result.exit_code == 0, result.output
        mock_client.archive_custom_dimension.assert_called_once_with(
            name="properties/123/customDimensions/456"
        )

    def test_archive_force_prints_success(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_dimension.return_value = _make_mock_dim()
        mock_client.archive_custom_dimension.return_value = None
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "archive",
                "--property-id",
                "123",
                "--dimension-id",
                "456",
                "--force",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "archived" in result.output.lower()

    def test_archive_confirms_before_archiving(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_dimension.return_value = _make_mock_dim()
        mock_client.archive_custom_dimension.return_value = None
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "archive",
                "--property-id",
                "123",
                "--dimension-id",
                "456",
            ],
            input="y\n",
        )

        assert result.exit_code == 0, result.output
        mock_client.archive_custom_dimension.assert_called_once_with(
            name="properties/123/customDimensions/456"
        )

    def test_archive_aborts_on_no(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_dimension.return_value = _make_mock_dim()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "archive",
                "--property-id",
                "123",
                "--dimension-id",
                "456",
            ],
            input="n\n",
        )

        assert result.exit_code == 0, result.output
        mock_client.archive_custom_dimension.assert_not_called()

    def test_archive_auth_error_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        mocker.patch(
            "gaad.shared.client.get_credentials",
            side_effect=AuthError("Not authenticated"),
        )

        result = runner.invoke(
            app,
            [
                "custom-dimensions",
                "archive",
                "--property-id",
                "123",
                "--dimension-id",
                "456",
                "--force",
            ],
        )

        assert result.exit_code != 0
