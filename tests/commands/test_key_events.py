"""Tests for gaad.commands.key_events — TDD: tests written before implementation."""

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


def _make_mock_key_event(pid: str = "123", kid: str = "456", event_name: str = "purchase") -> MagicMock:
    """Return a mock KeyEvent resource object."""
    ke = MagicMock()
    ke.name = f"properties/{pid}/keyEvents/{kid}"
    ke.event_name = event_name
    ke.counting_method = MagicMock()
    ke.counting_method.name = "ONCE_PER_EVENT"
    ke.deletable = True
    ke.custom = True
    ke.create_time = MagicMock(__str__=lambda self: "2024-01-01")
    ke.default_value = None
    return ke


def _patch_client(mocker, mock_client: MagicMock) -> None:
    """Patch get_credentials and build_admin_client in the key_events module."""
    mocker.patch("gaad.commands.key_events.get_credentials", return_value=MagicMock())
    mocker.patch("gaad.commands.key_events.build_admin_client", return_value=mock_client)


def _setup_config(tmp_config_dir: Path) -> None:
    """Write minimal token auth config so _get_client does not fail on missing config."""
    from gaad import config as cfg

    cfg.set("auth_method", "token")
    cfg.set("access_token", "tok")


# ---------------------------------------------------------------------------
# TestKeyEventsList
# ---------------------------------------------------------------------------


class TestKeyEventsList:
    """gaad key-events list command."""

    def test_list_calls_api_with_correct_parent(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_key_events.return_value = [_make_mock_key_event()]
        _patch_client(mocker, mock_client)

        result = runner.invoke(app, ["key-events", "list", "--property-id", "123"])

        assert result.exit_code == 0, result.output
        mock_client.list_key_events.assert_called_once_with(parent="properties/123")

    def test_list_renders_table_with_events(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_key_events.return_value = [
            _make_mock_key_event(kid="456", event_name="purchase"),
            _make_mock_key_event(kid="789", event_name="sign_up"),
        ]
        _patch_client(mocker, mock_client)

        result = runner.invoke(app, ["key-events", "list", "--property-id", "123"])

        assert result.exit_code == 0, result.output
        assert "purchase" in result.output
        assert "sign_up" in result.output

    def test_list_output_json_is_list(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_key_events.return_value = [
            _make_mock_key_event(kid="456", event_name="purchase"),
            _make_mock_key_event(kid="789", event_name="sign_up"),
        ]
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app, ["key-events", "list", "--property-id", "123", "--output", "json"]
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_output_csv_has_header(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.list_key_events.return_value = [_make_mock_key_event()]
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app, ["key-events", "list", "--property-id", "123", "--output", "csv"]
        )

        assert result.exit_code == 0, result.output
        first_line = result.output.strip().splitlines()[0]
        assert "key_event_id" in first_line

    def test_list_auth_error_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        mocker.patch(
            "gaad.commands.key_events.get_credentials",
            side_effect=AuthError("Not authenticated"),
        )

        result = runner.invoke(app, ["key-events", "list", "--property-id", "123"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestKeyEventsGet
# ---------------------------------------------------------------------------


class TestKeyEventsGet:
    """gaad key-events get command."""

    def test_get_calls_api_with_correct_name(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_key_event.return_value = _make_mock_key_event()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            ["key-events", "get", "--property-id", "123", "--key-event-id", "456"],
        )

        assert result.exit_code == 0, result.output
        mock_client.get_key_event.assert_called_once_with(
            name="properties/123/keyEvents/456"
        )

    def test_get_table_shows_event_name(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_key_event.return_value = _make_mock_key_event()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            ["key-events", "get", "--property-id", "123", "--key-event-id", "456"],
        )

        assert result.exit_code == 0, result.output
        assert "purchase" in result.output

    def test_get_json_has_key_event_id(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_key_event.return_value = _make_mock_key_event()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "get",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["key_event_id"] == "456"

    def test_get_missing_key_event_id_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            ["key-events", "get", "--property-id", "123"],
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestKeyEventsCreate
# ---------------------------------------------------------------------------


class TestKeyEventsCreate:
    """gaad key-events create command."""

    def test_create_calls_api(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_key_event.return_value = _make_mock_key_event()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "create",
                "--property-id",
                "123",
                "--event-name",
                "purchase",
                "--counting-method",
                "ONCE_PER_EVENT",
            ],
        )

        assert result.exit_code == 0, result.output
        mock_client.create_key_event.assert_called_once()

    def test_create_output_json_has_key_event_id(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.create_key_event.return_value = _make_mock_key_event()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "create",
                "--property-id",
                "123",
                "--event-name",
                "purchase",
                "--counting-method",
                "ONCE_PER_EVENT",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["key_event_id"] == "456"

    def test_create_with_default_value_sets_both_fields(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        ke = _make_mock_key_event()
        ke.default_value = MagicMock()
        ke.default_value.numeric_value = 9.99
        ke.default_value.currency_code = "USD"
        mock_client.create_key_event.return_value = ke
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "create",
                "--property-id",
                "123",
                "--event-name",
                "purchase",
                "--counting-method",
                "ONCE_PER_EVENT",
                "--default-numeric-value",
                "9.99",
                "--default-currency-code",
                "USD",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "default_numeric_value" in data

    def test_create_missing_event_name_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "create",
                "--property-id",
                "123",
                "--counting-method",
                "ONCE_PER_EVENT",
            ],
        )

        assert result.exit_code != 0

    def test_create_missing_counting_method_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "create",
                "--property-id",
                "123",
                "--event-name",
                "purchase",
            ],
        )

        assert result.exit_code != 0

    def test_create_default_value_partial_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        """Only --default-numeric-value without --default-currency-code should fail."""
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "create",
                "--property-id",
                "123",
                "--event-name",
                "purchase",
                "--counting-method",
                "ONCE_PER_EVENT",
                "--default-numeric-value",
                "9.99",
            ],
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestKeyEventsPatch
# ---------------------------------------------------------------------------


class TestKeyEventsPatch:
    """gaad key-events patch command."""

    def test_patch_counting_method_in_mask(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_key_event.return_value = _make_mock_key_event()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "patch",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
                "--counting-method",
                "ONCE_PER_SESSION",
            ],
        )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_key_event.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get("update_mask")
        assert "counting_method" in mask.paths

    def test_patch_default_value_in_mask(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_key_event.return_value = _make_mock_key_event()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "patch",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
                "--default-numeric-value",
                "5.00",
                "--default-currency-code",
                "EUR",
            ],
        )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_key_event.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get("update_mask")
        assert "default_value" in mask.paths

    def test_patch_no_fields_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "patch",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
            ],
        )

        assert result.exit_code != 0

    def test_patch_default_value_partial_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        """Only --default-currency-code without --default-numeric-value should fail."""
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "patch",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
                "--default-currency-code",
                "EUR",
            ],
        )

        assert result.exit_code != 0

    def test_patch_output_json_has_key_event_id(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.update_key_event.return_value = _make_mock_key_event()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "patch",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
                "--counting-method",
                "ONCE_PER_SESSION",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["key_event_id"] == "456"


# ---------------------------------------------------------------------------
# TestKeyEventsDelete
# ---------------------------------------------------------------------------


class TestKeyEventsDelete:
    """gaad key-events delete command."""

    def test_delete_force_calls_delete_api(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.delete_key_event.return_value = None
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "delete",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
                "--force",
            ],
        )

        assert result.exit_code == 0, result.output
        mock_client.delete_key_event.assert_called_once_with(
            name="properties/123/keyEvents/456"
        )

    def test_delete_force_prints_success(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.delete_key_event.return_value = None
        # get is called to retrieve event_name even with --force to compose the message
        mock_client.get_key_event.return_value = _make_mock_key_event()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "delete",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
                "--force",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "deleted" in result.output.lower()

    def test_delete_confirms_before_deleting(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_key_event.return_value = _make_mock_key_event()
        mock_client.delete_key_event.return_value = None
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "delete",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
            ],
            input="y\n",
        )

        assert result.exit_code == 0, result.output
        mock_client.delete_key_event.assert_called_once_with(
            name="properties/123/keyEvents/456"
        )

    def test_delete_aborts_on_no(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        mock_client.get_key_event.return_value = _make_mock_key_event()
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "delete",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
            ],
            input="n\n",
        )

        assert result.exit_code == 0, result.output
        mock_client.delete_key_event.assert_not_called()

    def test_delete_non_deletable_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        _setup_config(tmp_config_dir)
        mock_client = MagicMock()
        ke = _make_mock_key_event()
        ke.deletable = False
        mock_client.get_key_event.return_value = ke
        _patch_client(mocker, mock_client)

        result = runner.invoke(
            app,
            [
                "key-events",
                "delete",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
                "--force",
            ],
        )

        assert result.exit_code != 0
        mock_client.delete_key_event.assert_not_called()

    def test_delete_auth_error_exits_nonzero(self, tmp_config_dir: Path, mocker) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        mocker.patch(
            "gaad.commands.key_events.get_credentials",
            side_effect=AuthError("Not authenticated"),
        )

        result = runner.invoke(
            app,
            [
                "key-events",
                "delete",
                "--property-id",
                "123",
                "--key-event-id",
                "456",
                "--force",
            ],
        )

        assert result.exit_code != 0
