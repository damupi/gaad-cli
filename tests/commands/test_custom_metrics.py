"""Tests for gaad.commands.custom_metrics — TDD: tests written before implementation."""

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


def _make_mock_metric(pid: str = "123", mid: str = "789") -> MagicMock:
    """Return a mock CustomMetric resource object."""
    m = MagicMock()
    m.name = f"properties/{pid}/customMetrics/{mid}"
    m.parameter_name = "my_metric"
    m.display_name = "My Metric"
    m.measurement_unit = MagicMock()
    m.measurement_unit.name = "STANDARD"
    m.scope = MagicMock()
    m.scope.name = "EVENT"
    m.description = "A test metric"
    m.restricted_metric_type = []
    return m


def _patch_client(mocker, mock_client: MagicMock) -> None:
    """Patch get_credentials and build_admin_client in the custom_metrics module."""
    mocker.patch("gaad.commands.custom_metrics.get_credentials", return_value=MagicMock())
    mocker.patch("gaad.commands.custom_metrics.build_admin_client", return_value=mock_client)


def _setup_config(tmp_config_dir: Path) -> None:
    """Write minimal token auth config so _get_client does not fail on missing config."""
    from gaad import config as cfg

    cfg.set("auth_method", "token")
    cfg.set("access_token", "tok")


# ---------------------------------------------------------------------------
# TestCustomMetricsList
# ---------------------------------------------------------------------------


class TestCustomMetricsList:
    """gaad custom-metrics list command."""

    def test_list_calls_api_with_correct_parent(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_custom_metrics.return_value = [_make_mock_metric()]
        _patch_client(mocker, mock_client)

        result = runner.invoke(app, ["custom-metrics", "list", "--property-id", "123"])

        assert result.exit_code == 0, result.output
        mock_client.list_custom_metrics.assert_called_once_with(parent="properties/123")

    def test_list_renders_table(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_custom_metrics.return_value = [_make_mock_metric()]
        _patch_client(mocker, mock_client)

        result = runner.invoke(app, ["custom-metrics", "list", "--property-id", "123"])

        assert result.exit_code == 0, result.output
        assert "My Metric" in result.output

    def test_list_output_json_is_list(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_custom_metrics.return_value = [
            _make_mock_metric(mid="789"),
            _make_mock_metric(mid="101"),
        ]
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app, ["custom-metrics", "list", "--property-id", "123", "--output", "json"]
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_output_csv_has_header(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_custom_metrics.return_value = [_make_mock_metric()]
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app, ["custom-metrics", "list", "--property-id", "123", "--output", "csv"]
        )

        assert result.exit_code == 0, result.output
        first_line = result.output.strip().splitlines()[0]
        assert "metric_id" in first_line

    def test_list_auth_error_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        mocker.patch(
            "gaad.commands.custom_metrics.get_credentials",
            side_effect=AuthError("Not authenticated"),
        )

        result = runner.invoke(app, ["custom-metrics", "list", "--property-id", "123"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestCustomMetricsGet
# ---------------------------------------------------------------------------


class TestCustomMetricsGet:
    """gaad custom-metrics get command."""

    def test_get_calls_api_with_correct_name(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_metric.return_value = _make_mock_metric()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            ["custom-metrics", "get", "--property-id", "123", "--metric-id", "789"],
        )

        assert result.exit_code == 0, result.output
        mock_client.get_custom_metric.assert_called_once_with(
            name="properties/123/customMetrics/789"
        )

    def test_get_table_shows_display_name(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_metric.return_value = _make_mock_metric()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            ["custom-metrics", "get", "--property-id", "123", "--metric-id", "789"],
        )

        assert result.exit_code == 0, result.output
        assert "My Metric" in result.output

    def test_get_json_has_metric_id(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_metric.return_value = _make_mock_metric()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "get",
                "--property-id",
                "123",
                "--metric-id",
                "789",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["metric_id"] == "789"

    def test_get_missing_metric_id_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            ["custom-metrics", "get", "--property-id", "123"],
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestCustomMetricsCreate
# ---------------------------------------------------------------------------


class TestCustomMetricsCreate:
    """gaad custom-metrics create command."""

    def test_create_calls_api(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_custom_metric.return_value = _make_mock_metric()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "create",
                "--property-id",
                "123",
                "--parameter-name",
                "my_metric",
                "--display-name",
                "My Metric",
                "--measurement-unit",
                "STANDARD",
            ],
        )

        assert result.exit_code == 0, result.output
        mock_client.create_custom_metric.assert_called_once()

    def test_create_output_json_has_metric_id(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_custom_metric.return_value = _make_mock_metric()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "create",
                "--property-id",
                "123",
                "--parameter-name",
                "my_metric",
                "--display-name",
                "My Metric",
                "--measurement-unit",
                "STANDARD",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["metric_id"] == "789"

    def test_create_missing_parameter_name_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "create",
                "--property-id",
                "123",
                "--display-name",
                "My Metric",
                "--measurement-unit",
                "STANDARD",
            ],
        )

        assert result.exit_code != 0

    def test_create_currency_without_restricted_type_exits_nonzero(
        self, tmp_config_dir: Path, mocker
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "create",
                "--property-id",
                "123",
                "--parameter-name",
                "my_metric",
                "--display-name",
                "My Metric",
                "--measurement-unit",
                "CURRENCY",
            ],
        )

        assert result.exit_code != 0

    def test_create_restricted_type_on_non_currency_exits_nonzero(
        self, tmp_config_dir: Path, mocker
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "create",
                "--property-id",
                "123",
                "--parameter-name",
                "my_metric",
                "--display-name",
                "My Metric",
                "--measurement-unit",
                "STANDARD",
                "--restricted-metric-type",
                "COST_DATA",
            ],
        )

        assert result.exit_code != 0

    def test_create_currency_with_restricted_type_succeeds(
        self, tmp_config_dir: Path, mocker
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        currency_metric = _make_mock_metric()
        currency_metric.measurement_unit.name = "CURRENCY"
        rmt = MagicMock()
        rmt.name = "REVENUE_DATA"
        currency_metric.restricted_metric_type = [rmt]
        mock_client.create_custom_metric.return_value = currency_metric
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "create",
                "--property-id",
                "123",
                "--parameter-name",
                "my_metric",
                "--display-name",
                "My Metric",
                "--measurement-unit",
                "CURRENCY",
                "--restricted-metric-type",
                "REVENUE_DATA",
            ],
        )

        assert result.exit_code == 0, result.output
        mock_client.create_custom_metric.assert_called_once()


# ---------------------------------------------------------------------------
# TestCustomMetricsPatch
# ---------------------------------------------------------------------------


class TestCustomMetricsPatch:
    """gaad custom-metrics patch command."""

    def test_patch_display_name_in_mask(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_custom_metric.return_value = _make_mock_metric()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "patch",
                "--property-id",
                "123",
                "--metric-id",
                "789",
                "--display-name",
                "New Name",
            ],
        )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_custom_metric.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get("update_mask")
        assert "display_name" in mask.paths

    def test_patch_measurement_unit_in_mask(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_custom_metric.return_value = _make_mock_metric()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "patch",
                "--property-id",
                "123",
                "--metric-id",
                "789",
                "--measurement-unit",
                "SECONDS",
            ],
        )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_custom_metric.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get("update_mask")
        assert "measurement_unit" in mask.paths

    def test_patch_no_fields_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "patch",
                "--property-id",
                "123",
                "--metric-id",
                "789",
            ],
        )

        assert result.exit_code != 0

    def test_patch_output_json_has_metric_id(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_custom_metric.return_value = _make_mock_metric()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "patch",
                "--property-id",
                "123",
                "--metric-id",
                "789",
                "--display-name",
                "New Name",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["metric_id"] == "789"


# ---------------------------------------------------------------------------
# TestCustomMetricsArchive
# ---------------------------------------------------------------------------


class TestCustomMetricsArchive:
    """gaad custom-metrics archive command."""

    def test_archive_force_calls_api(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.archive_custom_metric.return_value = None
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "archive",
                "--property-id",
                "123",
                "--metric-id",
                "789",
                "--force",
            ],
        )

        assert result.exit_code == 0, result.output
        mock_client.archive_custom_metric.assert_called_once_with(
            name="properties/123/customMetrics/789"
        )

    def test_archive_force_prints_success(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_metric.return_value = _make_mock_metric()
        mock_client.archive_custom_metric.return_value = None
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "archive",
                "--property-id",
                "123",
                "--metric-id",
                "789",
                "--force",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "archived" in result.output.lower()

    def test_archive_confirms_before_archiving(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_metric.return_value = _make_mock_metric()
        mock_client.archive_custom_metric.return_value = None
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "archive",
                "--property-id",
                "123",
                "--metric-id",
                "789",
            ],
            input="y\n",
        )

        assert result.exit_code == 0, result.output
        mock_client.archive_custom_metric.assert_called_once_with(
            name="properties/123/customMetrics/789"
        )

    def test_archive_aborts_on_no(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_custom_metric.return_value = _make_mock_metric()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "archive",
                "--property-id",
                "123",
                "--metric-id",
                "789",
            ],
            input="n\n",
        )

        assert result.exit_code == 0, result.output
        mock_client.archive_custom_metric.assert_not_called()

    def test_archive_auth_error_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        mocker.patch(
            "gaad.commands.custom_metrics.get_credentials",
            side_effect=AuthError("Not authenticated"),
        )

        result = runner.invoke(
            app,
            [
                "custom-metrics",
                "archive",
                "--property-id",
                "123",
                "--metric-id",
                "789",
                "--force",
            ],
        )

        assert result.exit_code != 0
