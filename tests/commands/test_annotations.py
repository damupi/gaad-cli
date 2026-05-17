"""Tests for gaad.commands.annotations — TDD: tests written before implementation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from gaad.cli import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_annotation(
    system_generated: bool = False,
    has_range: bool = False,
) -> MagicMock:
    """Return a mock ReportingDataAnnotation resource object."""
    ann = MagicMock()
    ann.name = "properties/123/reportingDataAnnotations/456"
    ann.title = "Test Annotation"
    ann.description = "A test"
    ann.color.name = "BLUE"
    ann.system_generated = system_generated
    if has_range:
        ann.annotation_date_range.start_date.year = 2025
        ann.annotation_date_range.start_date.month = 1
        ann.annotation_date_range.start_date.day = 1
        ann.annotation_date_range.end_date.year = 2025
        ann.annotation_date_range.end_date.month = 1
        ann.annotation_date_range.end_date.day = 31
        ann.annotation_date = None
    else:
        ann.annotation_date.year = 2025
        ann.annotation_date.month = 5
        ann.annotation_date.day = 17
        ann.annotation_date_range = None
    return ann


def _patch_client():
    return patch("gaad.commands.annotations.get_client")


def _setup_config(tmp_config_dir: Path) -> None:
    """Write minimal token auth config."""
    from gaad import config as cfg

    cfg.set("auth_method", "token")
    cfg.set("access_token", "tok")


# ---------------------------------------------------------------------------
# TestAnnotationsList
# ---------------------------------------------------------------------------


class TestAnnotationsList:
    """gaad annotations list command."""

    def test_list_renders_table(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_reporting_data_annotations.return_value = [
                _make_mock_annotation()
            ]
            mock_get_client.return_value = mock_client

            result = runner.invoke(app, ["annotations", "list", "--property", "123"])

        assert result.exit_code == 0, result.output
        assert "Test Annotation" in result.output

    def test_list_calls_api_with_correct_parent(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_reporting_data_annotations.return_value = []
            mock_get_client.return_value = mock_client

            result = runner.invoke(app, ["annotations", "list", "--property", "123"])

        assert result.exit_code == 0, result.output
        mock_client.list_reporting_data_annotations.assert_called_once_with(
            parent="properties/123"
        )

    def test_list_output_json_is_list(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_reporting_data_annotations.return_value = [
                _make_mock_annotation(),
                _make_mock_annotation(),
            ]
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app, ["annotations", "list", "--property", "123", "--output", "json"]
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_output_csv_has_header(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_reporting_data_annotations.return_value = [
                _make_mock_annotation()
            ]
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app, ["annotations", "list", "--property", "123", "--output", "csv"]
            )

        assert result.exit_code == 0, result.output
        first_line = result.output.strip().splitlines()[0]
        assert "annotation_id" in first_line

    def test_list_empty_returns_exit_zero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_reporting_data_annotations.return_value = []
            mock_get_client.return_value = mock_client

            result = runner.invoke(app, ["annotations", "list", "--property", "123"])

        assert result.exit_code == 0, result.output

    def test_list_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        with patch(
            "gaad.shared.client.get_credentials",
            side_effect=AuthError("Not authenticated"),
        ):
            result = runner.invoke(app, ["annotations", "list", "--property", "123"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestAnnotationsGet
# ---------------------------------------------------------------------------


class TestAnnotationsGet:
    """gaad annotations get command."""

    def test_get_calls_api_with_correct_name(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "get",
                    "456",
                    "--property",
                    "123",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.get_reporting_data_annotation.assert_called_once_with(
            name="properties/123/reportingDataAnnotations/456"
        )

    def test_get_table_shows_title(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "get",
                    "456",
                    "--property",
                    "123",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "Test Annotation" in result.output

    def test_get_json_has_annotation_id(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "get",
                    "456",
                    "--property",
                    "123",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["annotation_id"] == "456"

    def test_get_not_found_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from google.api_core.exceptions import NotFound

        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.side_effect = NotFound(
                "Annotation not found"
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "get",
                    "999",
                    "--property",
                    "123",
                ],
            )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestAnnotationsCreate
# ---------------------------------------------------------------------------


class TestAnnotationsCreate:
    """gaad annotations create command."""

    def test_create_single_date_calls_api(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "create",
                    "--property",
                    "123",
                    "--title",
                    "Test Annotation",
                    "--color",
                    "BLUE",
                    "--date",
                    "2025-05-17",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.create_reporting_data_annotation.assert_called_once()

    def test_create_date_range_calls_api(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_reporting_data_annotation.return_value = (
                _make_mock_annotation(has_range=True)
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "create",
                    "--property",
                    "123",
                    "--title",
                    "Range Annotation",
                    "--color",
                    "GREEN",
                    "--start-date",
                    "2025-01-01",
                    "--end-date",
                    "2025-01-31",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.create_reporting_data_annotation.assert_called_once()

    def test_create_missing_date_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "create",
                    "--property",
                    "123",
                    "--title",
                    "Test",
                    "--color",
                    "BLUE",
                ],
            )

        assert result.exit_code != 0

    def test_create_both_date_and_range_exits_nonzero(
        self, tmp_config_dir: Path
    ) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "create",
                    "--property",
                    "123",
                    "--title",
                    "Test",
                    "--color",
                    "BLUE",
                    "--date",
                    "2025-05-17",
                    "--start-date",
                    "2025-01-01",
                    "--end-date",
                    "2025-01-31",
                ],
            )

        assert result.exit_code != 0

    def test_create_missing_end_date_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "create",
                    "--property",
                    "123",
                    "--title",
                    "Test",
                    "--color",
                    "BLUE",
                    "--start-date",
                    "2025-01-01",
                ],
            )

        assert result.exit_code != 0

    def test_create_output_json_has_annotation_id(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "create",
                    "--property",
                    "123",
                    "--title",
                    "Test Annotation",
                    "--color",
                    "BLUE",
                    "--date",
                    "2025-05-17",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["annotation_id"] == "456"

    def test_create_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        with patch(
            "gaad.shared.client.get_credentials",
            side_effect=AuthError("Not authenticated"),
        ):
            result = runner.invoke(
                app,
                [
                    "annotations",
                    "create",
                    "--property",
                    "123",
                    "--title",
                    "Test",
                    "--color",
                    "BLUE",
                    "--date",
                    "2025-05-17",
                ],
            )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestAnnotationsPatch
# ---------------------------------------------------------------------------


class TestAnnotationsPatch:
    """gaad annotations patch command."""

    def test_patch_title_in_mask(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_client.update_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--title",
                    "New Title",
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_reporting_data_annotation.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get(
            "update_mask"
        )
        assert "title" in mask.paths

    def test_patch_color_in_mask(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_client.update_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--color",
                    "RED",
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_reporting_data_annotation.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get(
            "update_mask"
        )
        assert "color" in mask.paths

    def test_patch_date_in_mask(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_client.update_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--date",
                    "2025-06-01",
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_reporting_data_annotation.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get(
            "update_mask"
        )
        assert "annotation_date" in mask.paths

    def test_patch_no_fields_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "patch",
                    "456",
                    "--property",
                    "123",
                ],
            )

        assert result.exit_code != 0

    def test_patch_date_and_range_conflict_exits_nonzero(
        self, tmp_config_dir: Path
    ) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--date",
                    "2025-06-01",
                    "--start-date",
                    "2025-01-01",
                    "--end-date",
                    "2025-01-31",
                ],
            )

        assert result.exit_code != 0

    def test_patch_system_generated_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation(system_generated=True)
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--title",
                    "New Title",
                ],
            )

        assert result.exit_code != 0
        mock_client.update_reporting_data_annotation.assert_not_called()

    def test_patch_output_json_has_annotation_id(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_client.update_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--title",
                    "New Title",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["annotation_id"] == "456"

    def test_patch_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        with patch(
            "gaad.shared.client.get_credentials",
            side_effect=AuthError("Not authenticated"),
        ):
            result = runner.invoke(
                app,
                [
                    "annotations",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--title",
                    "New Title",
                ],
            )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestAnnotationsDelete
# ---------------------------------------------------------------------------


class TestAnnotationsDelete:
    """gaad annotations delete command."""

    def test_delete_force_calls_delete_api(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_client.delete_reporting_data_annotation.return_value = None
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "delete",
                    "456",
                    "--property",
                    "123",
                    "--force",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.delete_reporting_data_annotation.assert_called_once_with(
            name="properties/123/reportingDataAnnotations/456"
        )

    def test_delete_force_prints_deleted(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_client.delete_reporting_data_annotation.return_value = None
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "delete",
                    "456",
                    "--property",
                    "123",
                    "--force",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "deleted" in result.output.lower()

    def test_delete_confirmation_accepted(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_client.delete_reporting_data_annotation.return_value = None
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "delete",
                    "456",
                    "--property",
                    "123",
                ],
                input="y\n",
            )

        assert result.exit_code == 0, result.output
        mock_client.delete_reporting_data_annotation.assert_called_once_with(
            name="properties/123/reportingDataAnnotations/456"
        )

    def test_delete_confirmation_aborted(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation()
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "delete",
                    "456",
                    "--property",
                    "123",
                ],
                input="n\n",
            )

        assert result.exit_code == 0, result.output
        mock_client.delete_reporting_data_annotation.assert_not_called()

    def test_delete_system_generated_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_reporting_data_annotation.return_value = (
                _make_mock_annotation(system_generated=True)
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "annotations",
                    "delete",
                    "456",
                    "--property",
                    "123",
                    "--force",
                ],
            )

        assert result.exit_code != 0
        mock_client.delete_reporting_data_annotation.assert_not_called()

    def test_delete_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        with patch(
            "gaad.shared.client.get_credentials",
            side_effect=AuthError("Not authenticated"),
        ):
            result = runner.invoke(
                app,
                [
                    "annotations",
                    "delete",
                    "456",
                    "--property",
                    "123",
                    "--force",
                ],
            )

        assert result.exit_code != 0
