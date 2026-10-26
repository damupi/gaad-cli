"""Tests for GA4 BigQuery link management commands."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from google.analytics.admin_v1alpha import types as alpha_types
from google.api_core.exceptions import AlreadyExists, InvalidArgument, PermissionDenied
from google.protobuf.timestamp_pb2 import Timestamp
from typer.testing import CliRunner

from gaad.cli import app


runner = CliRunner()


def _make_link(
    link_id: str = "abc567",
    *,
    property_id: str = "123",
    export_streams: list[str] | None = None,
    excluded_events: list[str] | None = None,
) -> alpha_types.BigQueryLink:
    """Build a real BigQueryLink proto for tests."""
    return alpha_types.BigQueryLink(
        name=f"properties/{property_id}/bigQueryLinks/{link_id}",
        project="projects/987654321",
        create_time=Timestamp(seconds=1704067200),
        dataset_location="US",
        daily_export_enabled=True,
        streaming_export_enabled=False,
        fresh_daily_export_enabled=True,
        include_advertising_id=False,
        export_streams=export_streams
        if export_streams is not None
        else [f"properties/{property_id}/dataStreams/456"],
        excluded_events=excluded_events
        if excluded_events is not None
        else ["internal_event"],
    )


def _patch_client(mock_client: MagicMock):
    return patch(
        "gaad.commands.bigquery_links.get_client", return_value=mock_client
    )


def _setup_config(tmp_config_dir: Path) -> None:
    from gaad import config as cfg

    cfg.set("auth_method", "token")
    cfg.set("access_token", "tok")


class TestRegistration:
    def test_top_level_help_lists_group(self) -> None:
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0, result.output
        assert "bigquery-links" in result.output

    def test_group_help_lists_commands(self) -> None:
        result = runner.invoke(app, ["bigquery-links", "--help"])

        assert result.exit_code == 0, result.output
        for command in ["list", "get", "create", "patch", "delete"]:
            assert command in result.output


class TestNormalization:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("123", "properties/123"), ("properties/123", "properties/123")],
    )
    def test_property_normalization(self, value: str, expected: str) -> None:
        from gaad.commands.bigquery_links import _normalize_property

        assert _normalize_property(value) == expected

    @pytest.mark.parametrize("value", ["", "properties/", "accounts/123", "abc"])
    def test_property_rejects_invalid_values(self, value: str) -> None:
        from gaad.commands.bigquery_links import _normalize_property

        with pytest.raises(Exception):
            _normalize_property(value)

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("123456", "projects/123456"),
            ("my-project", "projects/my-project"),
            ("projects/my-project", "projects/my-project"),
        ],
    )
    def test_project_normalization(self, value: str, expected: str) -> None:
        from gaad.commands.bigquery_links import _normalize_project

        assert _normalize_project(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("abc567", "properties/123/bigQueryLinks/abc567"),
            (
                "properties/123/bigQueryLinks/abc567",
                "properties/123/bigQueryLinks/abc567",
            ),
        ],
    )
    def test_link_normalization(self, value: str, expected: str) -> None:
        from gaad.commands.bigquery_links import _normalize_link

        assert _normalize_link(value, "properties/123") == expected

    @pytest.mark.parametrize(
        "value",
        ["link with spaces", "properties/123/bigQueryLinks/link with spaces"],
    )
    def test_link_rejects_malformed_values(self, value: str) -> None:
        from gaad.commands.bigquery_links import _normalize_link

        with pytest.raises(Exception):
            _normalize_link(value, "properties/123")

    def test_link_rejects_property_mismatch(self) -> None:
        from gaad.commands.bigquery_links import _normalize_link

        with pytest.raises(Exception):
            _normalize_link(
                "properties/999/bigQueryLinks/abc567", "properties/123"
            )

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("456", "properties/123/dataStreams/456"),
            (
                "properties/123/dataStreams/456",
                "properties/123/dataStreams/456",
            ),
        ],
    )
    def test_stream_normalization(self, value: str, expected: str) -> None:
        from gaad.commands.bigquery_links import _normalize_export_stream

        assert _normalize_export_stream(value, "properties/123") == expected

    def test_stream_rejects_property_mismatch(self) -> None:
        from gaad.commands.bigquery_links import _normalize_export_stream

        with pytest.raises(Exception):
            _normalize_export_stream(
                "properties/999/dataStreams/456", "properties/123"
            )


class TestList:
    def test_list_uses_alpha_client_and_normalized_parent(
        self, tmp_config_dir: Path
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_big_query_links.return_value = [_make_link()]

        with patch("gaad.commands.bigquery_links.get_client") as mock_get_client:
            mock_get_client.return_value = mock_client
            result = runner.invoke(
                app,
                ["bigquery-links", "list", "--property-id", "properties/123"],
            )

        assert result.exit_code == 0, result.output
        mock_get_client.assert_called_once_with("v1alpha")
        mock_client.list_big_query_links.assert_called_once_with(
            parent="properties/123"
        )

    def test_list_json_preserves_false_and_lists(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_big_query_links.return_value = [_make_link()]

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "list",
                    "--property-id",
                    "123",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data[0]["bigquery_link_id"] == "abc567"
        assert data[0]["streaming_export_enabled"] is False
        assert data[0]["export_streams"] == ["properties/123/dataStreams/456"]

    def test_list_csv_empty_has_stable_header(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_big_query_links.return_value = []

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "list",
                    "--property-id",
                    "123",
                    "--output",
                    "csv",
                ],
            )

        assert result.exit_code == 0, result.output
        header = result.output.strip().splitlines()[0]
        assert header.startswith("bigquery_link_id,name,project,create_time")
        assert "export_streams" in header
        assert "excluded_events" in header

    def test_list_csv_encodes_repeated_fields_as_json(
        self, tmp_config_dir: Path
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_big_query_links.return_value = [_make_link()]

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "list",
                    "--property-id",
                    "123",
                    "--output",
                    "csv",
                ],
            )

        assert result.exit_code == 0, result.output
        row = next(csv.DictReader(io.StringIO(result.output)))
        assert json.loads(row["export_streams"]) == [
            "properties/123/dataStreams/456"
        ]
        assert json.loads(row["excluded_events"]) == ["internal_event"]


class TestGet:
    @pytest.mark.parametrize("output", ["table", "json", "csv"])
    def test_get_supports_all_output_formats(
        self, tmp_config_dir: Path, output: str
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_big_query_link.return_value = _make_link()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "get",
                    "--property-id",
                    "123",
                    "--link-id",
                    "abc567",
                    "--output",
                    output,
                ],
            )

        assert result.exit_code == 0, result.output
        assert "abc567" in result.output
        mock_client.get_big_query_link.assert_called_once_with(
            name="properties/123/bigQueryLinks/abc567"
        )

    def test_get_accepts_full_link_name(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_big_query_link.return_value = _make_link()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "get",
                    "--property-id",
                    "properties/123",
                    "--link-id",
                    "properties/123/bigQueryLinks/abc567",
                ],
            )

        assert result.exit_code == 0, result.output


class TestCreate:
    def test_create_normalizes_payload_and_calls_api(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_big_query_link.return_value = _make_link()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "create",
                    "--property-id",
                    "properties/123",
                    "--project",
                    "my-project",
                    "--dataset-location",
                    "EU",
                    "--daily-export",
                    "--no-streaming-export",
                    "--fresh-daily-export",
                    "--include-advertising-id",
                    "--export-stream",
                    "456",
                    "--export-stream",
                    "properties/123/dataStreams/789",
                    "--exclude-event",
                    "internal_event",
                    "--exclude-event",
                    "debug_event",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_client.create_big_query_link.call_args.kwargs
        assert kwargs["parent"] == "properties/123"
        link = kwargs["bigquery_link"]
        assert link.project == "projects/my-project"
        assert link.dataset_location == "EU"
        assert link.daily_export_enabled is True
        assert link.streaming_export_enabled is False
        assert link.fresh_daily_export_enabled is True
        assert link.include_advertising_id is True
        assert list(link.export_streams) == [
            "properties/123/dataStreams/456",
            "properties/123/dataStreams/789",
        ]
        assert list(link.excluded_events) == ["internal_event", "debug_event"]
        assert link.name == ""

    @pytest.mark.parametrize("output", ["table", "json", "csv"])
    def test_create_supports_all_output_formats(
        self, tmp_config_dir: Path, output: str
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_big_query_link.return_value = _make_link()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "create",
                    "--property-id",
                    "123",
                    "--project",
                    "my-project",
                    "--dataset-location",
                    "US",
                    "--output",
                    output,
                ],
            )

        assert result.exit_code == 0, result.output
        assert "abc567" in result.output

    def test_create_defaults_optional_fields_to_false_and_empty(
        self, tmp_config_dir: Path
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_big_query_link.return_value = _make_link(
            export_streams=[], excluded_events=[]
        )

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "create",
                    "--property-id",
                    "123",
                    "--project",
                    "123456",
                    "--dataset-location",
                    "US",
                ],
            )

        assert result.exit_code == 0, result.output
        link = mock_client.create_big_query_link.call_args.kwargs["bigquery_link"]
        assert link.daily_export_enabled is False
        assert link.streaming_export_enabled is False
        assert link.fresh_daily_export_enabled is False
        assert link.include_advertising_id is False
        assert list(link.export_streams) == []
        assert list(link.excluded_events) == []

    @pytest.mark.parametrize(
        "args",
        [
            ["--property-id", "accounts/123", "--project", "my-project", "--dataset-location", "US"],
            ["--property-id", "123", "--project", "projects/", "--dataset-location", "US"],
            ["--property-id", "123", "--project", "my-project", "--dataset-location", ""],
            ["--property-id", "123", "--project", "my-project", "--dataset-location", "US", "--export-stream", "properties/999/dataStreams/1"],
            ["--property-id", "123", "--project", "my-project", "--dataset-location", "US", "--exclude-event", ""],
        ],
    )
    def test_create_validation_happens_before_authentication(
        self, tmp_config_dir: Path, args: list[str]
    ) -> None:
        _setup_config(tmp_config_dir)
        with patch("gaad.commands.bigquery_links.get_client") as mock_get_client:
            result = runner.invoke(app, ["bigquery-links", "create", *args])

        assert result.exit_code != 0
        mock_get_client.assert_not_called()

    @pytest.mark.parametrize(
        "missing_args",
        [
            ["--property-id", "123", "--dataset-location", "US"],
            ["--property-id", "123", "--project", "my-project"],
        ],
    )
    def test_create_requires_project_and_dataset_location(
        self, tmp_config_dir: Path, missing_args: list[str]
    ) -> None:
        _setup_config(tmp_config_dir)
        with patch("gaad.commands.bigquery_links.get_client") as mock_get_client:
            result = runner.invoke(
                app, ["bigquery-links", "create", *missing_args]
            )

        assert result.exit_code != 0
        mock_get_client.assert_not_called()

    def test_create_already_exists_has_actionable_error(
        self, tmp_config_dir: Path
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_big_query_link.side_effect = AlreadyExists("exists")

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "create",
                    "--property-id",
                    "123",
                    "--project",
                    "my-project",
                    "--dataset-location",
                    "US",
                ],
            )

        assert result.exit_code == 1
        assert "already" in result.output.lower()
        assert "one" in result.output.lower()

    def test_create_invalid_argument_mentions_project_and_location(
        self, tmp_config_dir: Path
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        backend_reason = "Dataset region ANTARCTICA is unsupported"
        mock_client.create_big_query_link.side_effect = InvalidArgument(backend_reason)

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "create",
                    "--property-id",
                    "123",
                    "--project",
                    "my-project",
                    "--dataset-location",
                    "US",
                ],
            )

        assert result.exit_code == 1
        assert "project" in result.output.lower()
        assert "dataset" in result.output.lower()
        assert "location" in result.output.lower()
        assert backend_reason in result.stderr


class TestPatch:
    def test_patch_false_booleans_create_exact_mask(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_big_query_link.return_value = _make_link()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "patch",
                    "--property-id",
                    "123",
                    "--link-id",
                    "abc567",
                    "--no-daily-export",
                    "--no-include-advertising-id",
                ],
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_client.update_big_query_link.call_args.kwargs
        assert kwargs["bigquery_link"].name == "properties/123/bigQueryLinks/abc567"
        assert kwargs["bigquery_link"].daily_export_enabled is False
        assert kwargs["bigquery_link"].include_advertising_id is False
        assert list(kwargs["update_mask"].paths) == [
            "daily_export_enabled",
            "include_advertising_id",
        ]

    @pytest.mark.parametrize("output", ["table", "json", "csv"])
    def test_patch_supports_all_output_formats(
        self, tmp_config_dir: Path, output: str
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_big_query_link.return_value = _make_link()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "patch",
                    "--property-id",
                    "123",
                    "--link-id",
                    "abc567",
                    "--daily-export",
                    "--output",
                    output,
                ],
            )

        assert result.exit_code == 0, result.output
        assert "abc567" in result.output

    def test_patch_replaces_lists_with_normalized_values(
        self, tmp_config_dir: Path
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_big_query_link.return_value = _make_link()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "patch",
                    "--property-id",
                    "123",
                    "--link-id",
                    "abc567",
                    "--export-stream",
                    "456",
                    "--exclude-event",
                    "purchase",
                ],
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_client.update_big_query_link.call_args.kwargs
        assert list(kwargs["bigquery_link"].export_streams) == [
            "properties/123/dataStreams/456"
        ]
        assert list(kwargs["bigquery_link"].excluded_events) == ["purchase"]
        assert list(kwargs["update_mask"].paths) == [
            "export_streams",
            "excluded_events",
        ]

    @pytest.mark.parametrize(
        ("clear_flag", "field"),
        [
            ("--clear-export-streams", "export_streams"),
            ("--clear-excluded-events", "excluded_events"),
        ],
    )
    def test_patch_can_clear_repeated_fields(
        self, tmp_config_dir: Path, clear_flag: str, field: str
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_big_query_link.return_value = _make_link(
            export_streams=[], excluded_events=[]
        )

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "patch",
                    "--property-id",
                    "123",
                    "--link-id",
                    "abc567",
                    clear_flag,
                ],
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_client.update_big_query_link.call_args.kwargs
        assert list(kwargs["update_mask"].paths) == [field]
        assert list(getattr(kwargs["bigquery_link"], field)) == []

    @pytest.mark.parametrize(
        "args",
        [
            [],
            ["--clear-export-streams", "--export-stream", "456"],
            ["--clear-excluded-events", "--exclude-event", "purchase"],
        ],
    )
    def test_patch_rejects_noop_and_conflicting_list_options_before_auth(
        self, tmp_config_dir: Path, args: list[str]
    ) -> None:
        _setup_config(tmp_config_dir)
        with patch("gaad.commands.bigquery_links.get_client") as mock_get_client:
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "patch",
                    "--property-id",
                    "123",
                    "--link-id",
                    "abc567",
                    *args,
                ],
            )

        assert result.exit_code != 0
        mock_get_client.assert_not_called()


class TestDelete:
    def test_delete_force_bypasses_get_and_confirmation(
        self, tmp_config_dir: Path
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "delete",
                    "--property-id",
                    "123",
                    "--link-id",
                    "abc567",
                    "--force",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.get_big_query_link.assert_not_called()
        mock_client.delete_big_query_link.assert_called_once_with(
            name="properties/123/bigQueryLinks/abc567"
        )

    def test_delete_confirmation_accepted(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_big_query_link.return_value = _make_link()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "delete",
                    "--property-id",
                    "123",
                    "--link-id",
                    "abc567",
                ],
                input="y\n",
            )

        assert result.exit_code == 0, result.output
        assert "projects/987654321" in result.output
        mock_client.delete_big_query_link.assert_called_once()

    @pytest.mark.parametrize("input_text", ["n\n", ""])
    def test_delete_refusal_or_eof_aborts_cleanly(
        self, tmp_config_dir: Path, input_text: str
    ) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_big_query_link.return_value = _make_link()

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "delete",
                    "--property-id",
                    "123",
                    "--link-id",
                    "abc567",
                ],
                input=input_text,
            )

        assert result.exit_code == 0, result.output
        assert "Aborted." in result.output
        mock_client.delete_big_query_link.assert_not_called()


class TestErrors:
    def test_permission_error_is_clear(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        backend_reason = "Caller lacks analytics.properties.get permission"
        mock_client.get_big_query_link.side_effect = PermissionDenied(backend_reason)

        with _patch_client(mock_client):
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "get",
                    "--property-id",
                    "123",
                    "--link-id",
                    "abc567",
                ],
            )

        assert result.exit_code == 1
        assert "permission" in result.output.lower()
        assert "analytics.edit" in result.output
        assert backend_reason in result.stderr

    def test_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        with patch(
            "gaad.shared.client.get_credentials",
            side_effect=AuthError("Not authenticated"),
        ):
            result = runner.invoke(
                app, ["bigquery-links", "list", "--property-id", "123"]
            )

        assert result.exit_code != 0

    def test_invalid_output_format_is_rejected(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with patch("gaad.commands.bigquery_links.get_client") as mock_get_client:
            result = runner.invoke(
                app,
                [
                    "bigquery-links",
                    "list",
                    "--property-id",
                    "123",
                    "--output",
                    "xml",
                ],
            )

        assert result.exit_code != 0
        mock_get_client.assert_not_called()
