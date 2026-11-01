import json
import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from gaad import update
from gaad.cli import app as cli


LS_REMOTE = (
    "aaa\trefs/tags/v0.3.0\n"
    "bbb\trefs/tags/v0.10.0\n"
    "ccc\trefs/tags/v0.4.1\n"
    "ddd\trefs/tags/v1.0.0-rc1\n"
    "eee\trefs/tags/vnext\n"
)


def _completed(stdout="", returncode=0):
    return MagicMock(stdout=stdout, returncode=returncode)


@pytest.fixture
def cache(tmp_config_dir):
    """update-check.json lives next to config.json (GAAD_CONFIG_DIR)."""
    return tmp_config_dir / "update-check.json"


# ── latest_release ────────────────────────────────────────────────────────────

def test_latest_release_picks_highest_semver_tag():
    with patch("gaad.update.subprocess.run", return_value=_completed(LS_REMOTE)) as run:
        assert update.latest_release() == "0.10.0"
    args, kwargs = run.call_args
    assert args[0] == ["git", "ls-remote", "--tags", "--refs", update.REPO_URL, "v*"]
    assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert kwargs["timeout"] == 5


def test_latest_release_without_tags_is_none():
    with patch("gaad.update.subprocess.run", return_value=_completed("")):
        assert update.latest_release() is None


@pytest.mark.parametrize("side_effect", [
    OSError("git not found"),
    subprocess.TimeoutExpired(cmd="git", timeout=5),
])
def test_latest_release_failures_are_silent(side_effect):
    with patch("gaad.update.subprocess.run", side_effect=side_effect):
        assert update.latest_release() is None


def test_latest_release_git_error_is_none():
    with patch("gaad.update.subprocess.run", return_value=_completed(LS_REMOTE, returncode=128)):
        assert update.latest_release() is None


# ── comparison and upgrade command ────────────────────────────────────────────

@pytest.mark.parametrize("latest, current, expected", [
    ("0.4.0", "0.3.0", True),
    ("0.10.0", "0.9.0", True),
    ("0.3.0", "0.3.0", False),
    ("0.3.0", "0.4.0", False),
    (None, "0.3.0", False),
    ("0.4.0", None, False),
])
def test_is_newer(latest, current, expected):
    assert update.is_newer(latest, current) is expected


@pytest.mark.parametrize("info, expected", [
    ({"kind": "uv"}, "uv tool install --force git+https://github.com/damupi/gaad-cli@v0.4.0"),
    ({"kind": "pip"}, 'pip install --upgrade "git+https://github.com/damupi/gaad-cli@v0.4.0"'),
    ({"kind": "editable", "path": "/src/gaad-cli"}, "git -C /src/gaad-cli pull  (editable install: update your checkout)"),
])
def test_upgrade_command_matches_install_kind(info, expected):
    with patch("gaad.update._install_info", return_value=info):
        assert update.upgrade_command("0.4.0") == expected


def test_upgrade_notice_mentions_versions_command_and_release_notes():
    with patch("gaad.update._install_info", return_value={"kind": "uv"}):
        notice = update.upgrade_notice("0.4.0", "0.3.0")
    assert "0.3.0 → 0.4.0" in notice
    assert "uv tool install --force" in notice
    assert "releases/tag/v0.4.0" in notice


# ── cache ─────────────────────────────────────────────────────────────────────

def test_cached_latest_release_uses_fresh_cache(cache):
    cache.write_text(json.dumps({"checked_at": int(time.time()), "latest": "0.4.0"}))
    with patch("gaad.update.latest_release") as latest:
        assert update.cached_latest_release() == "0.4.0"
    latest.assert_not_called()


def test_cached_latest_release_refreshes_stale_cache(cache):
    stale = int(time.time()) - update.CHECK_INTERVAL - 1
    cache.write_text(json.dumps({"checked_at": stale, "latest": "0.4.0"}))
    with patch("gaad.update.latest_release", return_value="0.5.0"):
        assert update.cached_latest_release() == "0.5.0"
    assert json.loads(cache.read_text())["latest"] == "0.5.0"


def test_cached_latest_release_records_failed_check(cache):
    with patch("gaad.update.latest_release", return_value=None) as latest:
        assert update.cached_latest_release() is None
        assert update.cached_latest_release() is None
    latest.assert_called_once()


def test_corrupt_cache_triggers_refresh(cache):
    cache.write_text("not json")
    with patch("gaad.update.latest_release", return_value="0.4.0"):
        assert update.cached_latest_release() == "0.4.0"


# ── when to notify ────────────────────────────────────────────────────────────

def test_should_check_requires_tty(monkeypatch):
    monkeypatch.delenv(update.DISABLE_ENV, raising=False)
    monkeypatch.delenv("CI", raising=False)
    with patch("gaad.update.sys.stderr.isatty", return_value=True):
        assert update.should_check() is True
    with patch("gaad.update.sys.stderr.isatty", return_value=False):
        assert update.should_check() is False


@pytest.mark.parametrize("env", [update.DISABLE_ENV, "CI"])
def test_should_check_respects_opt_out_and_ci(monkeypatch, env):
    monkeypatch.setenv(env, "1")
    with patch("gaad.update.sys.stderr.isatty", return_value=True):
        assert update.should_check() is False


def test_pending_notice_when_newer_release():
    with patch("gaad.update.should_check", return_value=True), \
         patch("gaad.update.installed_version", return_value="0.3.0"), \
         patch("gaad.update.cached_latest_release", return_value="0.4.0"), \
         patch("gaad.update._install_info", return_value={"kind": "uv"}):
        assert "0.3.0 → 0.4.0" in update.pending_notice()


def test_pending_notice_none_when_up_to_date():
    with patch("gaad.update.should_check", return_value=True), \
         patch("gaad.update.installed_version", return_value="0.4.0"), \
         patch("gaad.update.cached_latest_release", return_value="0.4.0"):
        assert update.pending_notice() is None


def test_pending_notice_never_raises():
    with patch("gaad.update.should_check", return_value=True), \
         patch("gaad.update.cached_latest_release", side_effect=RuntimeError("boom")):
        assert update.pending_notice() is None


# ── CLI integration ───────────────────────────────────────────────────────────

def test_command_prints_pending_notice_on_stderr():
    runner = CliRunner()
    with patch("gaad.cli.pending_notice", return_value="A new release of gaad is available"), \
         patch("gaad.commands.accounts.get_client") as get_client:
        get_client.return_value.list_accounts.return_value = []
        result = runner.invoke(cli, ["accounts", "list", "--output", "json"])
    assert result.exit_code == 0
    assert "A new release" in result.stderr
    assert "A new release" not in result.stdout
    json.loads(result.stdout)


def test_command_without_pending_notice_prints_nothing_extra():
    runner = CliRunner()
    with patch("gaad.cli.pending_notice", return_value=None), \
         patch("gaad.commands.accounts.get_client") as get_client:
        get_client.return_value.list_accounts.return_value = []
        result = runner.invoke(cli, ["accounts", "list", "--output", "json"])
    assert result.exit_code == 0
    assert result.stderr == ""


def test_version_command_reports_available_update():
    runner = CliRunner()
    with patch("gaad.cli.installed_version", return_value="0.3.0"), \
         patch("gaad.cli.latest_release", return_value="0.4.0"), \
         patch("gaad.cli.upgrade_command", return_value="uv tool install --force X@v0.4.0"), \
         patch("gaad.cli.pending_notice") as notice:
        result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "gaad 0.3.0" in result.output
    assert "A new release is available: 0.4.0" in result.output
    assert "uv tool install --force X@v0.4.0" in result.output
    notice.assert_not_called()


def test_version_command_json():
    runner = CliRunner()
    with patch("gaad.cli.installed_version", return_value="0.4.0"), \
         patch("gaad.cli.latest_release", return_value="0.4.0"):
        result = runner.invoke(cli, ["version", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "installed": "0.4.0",
        "latest": "0.4.0",
        "update_available": False,
        "upgrade_command": None,
    }


def test_version_command_without_latest_release():
    runner = CliRunner()
    with patch("gaad.cli.installed_version", return_value="0.3.0"), \
         patch("gaad.cli.latest_release", return_value=None):
        result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "Could not determine the latest release" in result.output


def test_version_option():
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert result.output.startswith("gaad ")
