"""Tests for gaad.commands.channel_groups."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from gaad.cli import app


runner = CliRunner()

SAMPLE_RULES_JSON = json.dumps(
    [
        {
            "display_name": "Direct",
            "expression": {
                "and_group": {
                    "expressions": [
                        {
                            "or_group": {
                                "expressions": [
                                    {
                                        "filter": {
                                            "field_name": "eachScopeSource",
                                            "string_filter": {
                                                "match_type": "EXACT",
                                                "value": "direct",
                                            },
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
        }
    ]
)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_channel_group(
    system_defined: bool = False,
    primary: bool = False,
    rule_count: int = 2,
) -> MagicMock:
    """Return a mock ChannelGroup resource object."""
    cg = MagicMock()
    cg.name = "properties/123/channelGroups/456"
    cg.display_name = "Test Channel Group"
    cg.description = "A test channel group"
    cg.system_defined = system_defined
    cg.primary = primary
    cg.grouping_rule = [MagicMock() for _ in range(rule_count)]
    return cg


def _patch_client():
    return patch("gaad.commands.channel_groups.get_client")


def _setup_config(tmp_config_dir: Path) -> None:
    """Write minimal token auth config."""
    from gaad import config as cfg

    cfg.set("auth_method", "token")
    cfg.set("access_token", "tok")


# ---------------------------------------------------------------------------
# TestChannelGroupsList
# ---------------------------------------------------------------------------


class TestChannelGroupsList:
    """gaad channel-groups list command."""

    def test_list_renders_table(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_channel_groups.return_value = [
                _make_mock_channel_group()
            ]
            mock_get_client.return_value = mock_client

            result = runner.invoke(app, ["channel-groups", "list", "--property", "123"])

        assert result.exit_code == 0, result.output
        assert "Test Channel Group" in result.output

    def test_list_calls_api_with_correct_parent(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_channel_groups.return_value = []
            mock_get_client.return_value = mock_client

            result = runner.invoke(app, ["channel-groups", "list", "--property", "123"])

        assert result.exit_code == 0, result.output
        mock_client.list_channel_groups.assert_called_once_with(
            parent="properties/123"
        )

    def test_list_output_json_is_list(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_channel_groups.return_value = [
                _make_mock_channel_group(),
                _make_mock_channel_group(),
            ]
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                ["channel-groups", "list", "--property", "123", "--output", "json"],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_output_csv_has_header(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_channel_groups.return_value = [
                _make_mock_channel_group()
            ]
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                ["channel-groups", "list", "--property", "123", "--output", "csv"],
            )

        assert result.exit_code == 0, result.output
        first_line = result.output.strip().splitlines()[0]
        assert "channel_group_id" in first_line

    def test_list_empty_returns_exit_zero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_channel_groups.return_value = []
            mock_get_client.return_value = mock_client

            result = runner.invoke(app, ["channel-groups", "list", "--property", "123"])

        assert result.exit_code == 0, result.output

    def test_list_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        with patch(
            "gaad.shared.client.get_credentials",
            side_effect=AuthError("Not authenticated"),
        ):
            result = runner.invoke(app, ["channel-groups", "list", "--property", "123"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestChannelGroupsGet
# ---------------------------------------------------------------------------


class TestChannelGroupsGet:
    """gaad channel-groups get command."""

    def test_get_calls_api_with_correct_name(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app, ["channel-groups", "get", "456", "--property", "123"]
            )

        assert result.exit_code == 0, result.output
        mock_client.get_channel_group.assert_called_once_with(
            name="properties/123/channelGroups/456"
        )

    def test_get_table_shows_display_name(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app, ["channel-groups", "get", "456", "--property", "123"]
            )

        assert result.exit_code == 0, result.output
        assert "Test Channel Group" in result.output

    def test_get_json_has_channel_group_id(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "channel-groups",
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
        assert data["channel_group_id"] == "456"


# ---------------------------------------------------------------------------
# TestChannelGroupsCreate
# ---------------------------------------------------------------------------


class TestChannelGroupsCreate:
    """gaad channel-groups create command."""

    def test_create_with_rules_json_calls_api(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_channel_group.return_value = _make_mock_channel_group()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "channel-groups",
                    "create",
                    "--property",
                    "123",
                    "--display-name",
                    "Test Channel Group",
                    "--rules-json",
                    SAMPLE_RULES_JSON,
                ],
            )

        assert result.exit_code == 0, result.output
        mock_client.create_channel_group.assert_called_once()

    def test_create_output_json_has_channel_group_id(
        self, tmp_config_dir: Path
    ) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_channel_group.return_value = _make_mock_channel_group()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "channel-groups",
                    "create",
                    "--property",
                    "123",
                    "--display-name",
                    "Test Channel Group",
                    "--rules-json",
                    SAMPLE_RULES_JSON,
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["channel_group_id"] == "456"

    def test_create_invalid_json_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "channel-groups",
                    "create",
                    "--property",
                    "123",
                    "--display-name",
                    "Test",
                    "--rules-json",
                    "not-valid-json",
                ],
            )

        assert result.exit_code != 0
        mock_client.create_channel_group.assert_not_called()

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
                    "channel-groups",
                    "create",
                    "--property",
                    "123",
                    "--display-name",
                    "Test",
                    "--rules-json",
                    SAMPLE_RULES_JSON,
                ],
            )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestChannelGroupsPatch
# ---------------------------------------------------------------------------


class TestChannelGroupsPatch:
    """gaad channel-groups patch command."""

    def test_patch_display_name_in_mask(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group()
            mock_client.update_channel_group.return_value = _make_mock_channel_group()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "channel-groups",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--display-name",
                    "New Name",
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_channel_group.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get(
            "update_mask"
        )
        assert "display_name" in mask.paths

    def test_patch_rules_json_in_mask(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group()
            mock_client.update_channel_group.return_value = _make_mock_channel_group()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "channel-groups",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--rules-json",
                    SAMPLE_RULES_JSON,
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_client.update_channel_group.call_args
        mask = call_kwargs.kwargs.get("update_mask") or call_kwargs[1].get(
            "update_mask"
        )
        assert "grouping_rule" in mask.paths

    def test_patch_no_fields_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                ["channel-groups", "patch", "456", "--property", "123"],
            )

        assert result.exit_code != 0
        mock_client.update_channel_group.assert_not_called()

    def test_patch_system_defined_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group(
                system_defined=True
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "channel-groups",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--display-name",
                    "New Name",
                ],
            )

        assert result.exit_code != 0
        mock_client.update_channel_group.assert_not_called()

    def test_patch_output_json_has_channel_group_id(
        self, tmp_config_dir: Path
    ) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group()
            mock_client.update_channel_group.return_value = _make_mock_channel_group()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "channel-groups",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--display-name",
                    "New Name",
                    "--output",
                    "json",
                ],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["channel_group_id"] == "456"

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
                    "channel-groups",
                    "patch",
                    "456",
                    "--property",
                    "123",
                    "--display-name",
                    "New Name",
                ],
            )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestChannelGroupsDelete
# ---------------------------------------------------------------------------


class TestChannelGroupsDelete:
    """gaad channel-groups delete command."""

    def test_delete_force_calls_delete_api(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group()
            mock_client.delete_channel_group.return_value = None
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                ["channel-groups", "delete", "456", "--property", "123", "--force"],
            )

        assert result.exit_code == 0, result.output
        mock_client.delete_channel_group.assert_called_once_with(
            name="properties/123/channelGroups/456"
        )

    def test_delete_force_prints_deleted(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group()
            mock_client.delete_channel_group.return_value = None
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                ["channel-groups", "delete", "456", "--property", "123", "--force"],
            )

        assert result.exit_code == 0, result.output
        assert "deleted" in result.output.lower()

    def test_delete_confirmation_accepted(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group()
            mock_client.delete_channel_group.return_value = None
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                ["channel-groups", "delete", "456", "--property", "123"],
                input="y\n",
            )

        assert result.exit_code == 0, result.output
        mock_client.delete_channel_group.assert_called_once_with(
            name="properties/123/channelGroups/456"
        )

    def test_delete_confirmation_aborted(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group()
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                ["channel-groups", "delete", "456", "--property", "123"],
                input="n\n",
            )

        assert result.exit_code == 0, result.output
        mock_client.delete_channel_group.assert_not_called()

    def test_delete_system_defined_exits_nonzero(self, tmp_config_dir: Path) -> None:
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_channel_group.return_value = _make_mock_channel_group(
                system_defined=True
            )
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                app,
                ["channel-groups", "delete", "456", "--property", "123", "--force"],
            )

        assert result.exit_code != 0
        mock_client.delete_channel_group.assert_not_called()

    def test_delete_auth_error_exits_nonzero(self, tmp_config_dir: Path) -> None:
        from gaad.errors import AuthError

        _setup_config(tmp_config_dir)
        with patch(
            "gaad.shared.client.get_credentials",
            side_effect=AuthError("Not authenticated"),
        ):
            result = runner.invoke(
                app,
                ["channel-groups", "delete", "456", "--property", "123", "--force"],
            )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestRulesFromJson
# ---------------------------------------------------------------------------


class TestRulesFromJson:
    """Unit tests for the _rules_from_json Pydantic-backed parser."""

    def test_valid_snake_case_rules(self):
        from gaad.commands.channel_groups import _rules_from_json

        rules_json = json.dumps([{
            "display_name": "Direct",
            "expression": {
                "and_group": {"expressions": [
                    {"or_group": {"expressions": [
                        {"filter": {"field_name": "eachScopeDefaultChannelGroup",
                                    "string_filter": {"match_type": "EXACT", "value": "Direct"}}}
                    ]}}
                ]}
            }
        }])
        result = _rules_from_json(rules_json)
        assert len(result) == 1

    def test_valid_camel_case_rules(self):
        from gaad.commands.channel_groups import _rules_from_json

        rules_json = json.dumps([{
            "displayName": "Direct",
            "expression": {
                "andGroup": {"filterExpressions": [
                    {"orGroup": {"filterExpressions": [
                        {"filter": {"fieldName": "eachScopeDefaultChannelGroup",
                                    "stringFilter": {"matchType": "EXACT", "value": "Direct"}}}
                    ]}}
                ]}
            }
        }])
        result = _rules_from_json(rules_json)
        assert len(result) == 1

    def test_invalid_json_exits(self, tmp_config_dir: Path):
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_get_client.return_value = MagicMock()
            result = runner.invoke(app, [
                "channel-groups", "create",
                "--property", "123",
                "--display-name", "Test",
                "--rules-json", "not-valid-json",
            ])
        assert result.exit_code != 0

    def test_missing_filter_field_exits(self, tmp_config_dir: Path):
        _setup_config(tmp_config_dir)
        with _patch_client() as mock_get_client:
            mock_get_client.return_value = MagicMock()
            result = runner.invoke(app, [
                "channel-groups", "create",
                "--property", "123",
                "--display-name", "Test",
                "--rules-json", json.dumps([{
                    "display_name": "Bad",
                    "expression": {"filter": {"field_name": "x"}}  # missing string_filter/in_list_filter
                }]),
            ])
        assert result.exit_code != 0

    def test_channel_group_field_enum_values(self):
        from gaad.commands.channel_groups import ChannelGroupField

        assert ChannelGroupField.SOURCE == "eachScopeSource"
        assert ChannelGroupField.MEDIUM == "eachScopeMedium"
        assert ChannelGroupField.DEFAULT_CHANNEL_GROUP == "eachScopeDefaultChannelGroup"
        assert ChannelGroupField.SOURCE_PLATFORM == "eachScopeSourcePlatform"
        assert ChannelGroupField.CAMPAIGN_ID == "eachScopeCampaignId"
        assert ChannelGroupField.CAMPAIGN_NAME == "eachScopeCampaignName"
