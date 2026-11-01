"""Check for newer gaad-cli releases (vX.Y.Z git tags) and suggest how to upgrade."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from importlib import metadata
from pathlib import Path

from gaad.config import get_config_path

REPO_URL = "https://github.com/damupi/gaad-cli.git"
REPO_INSTALL_URL = "git+https://github.com/damupi/gaad-cli"
RELEASES_URL = "https://github.com/damupi/gaad-cli/releases/tag"
CHECK_INTERVAL = 24 * 3600
DISABLE_ENV = "GAAD_NO_UPDATE_CHECK"

_TAG = re.compile(r"refs/tags/v(\d+)\.(\d+)\.(\d+)$")
_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def _version_tuple(version: str) -> tuple[int, int, int] | None:
    match = _VERSION.match(version)
    return tuple(int(part) for part in match.groups()) if match else None


def installed_version() -> str | None:
    try:
        return metadata.version("gaad-cli")
    except metadata.PackageNotFoundError:
        return None


def latest_release(timeout: float = 5) -> str | None:
    """Return the highest vX.Y.Z tag on GitHub (without the "v"), or None.

    The repository is public, so this reads tags over HTTPS without
    credentials. GIT_TERMINAL_PROMPT=0 makes git fail instead of prompting.
    """
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "--refs", REPO_URL, "v*"],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    versions = []
    for line in result.stdout.splitlines():
        match = _TAG.search(line)
        if match:
            versions.append(tuple(int(part) for part in match.groups()))
    if not versions:
        return None
    return ".".join(str(part) for part in max(versions))


def is_newer(latest: str | None, current: str | None) -> bool:
    latest_t = _version_tuple(latest or "")
    current_t = _version_tuple(current or "")
    return latest_t is not None and current_t is not None and latest_t > current_t


def _install_info() -> dict:
    """Describe how gaad-cli was installed: editable checkout, uv tool, or pip."""
    # A source checkout on sys.path can expose a bare egg-info first; the
    # installed distribution is the one that records direct_url.json.
    direct_url = {}
    for dist in metadata.distributions(name="gaad-cli"):
        raw = dist.read_text("direct_url.json")
        if raw:
            try:
                direct_url = json.loads(raw)
            except ValueError:
                pass
            break
    if direct_url.get("dir_info", {}).get("editable"):
        path = urllib.parse.unquote(urllib.parse.urlparse(direct_url.get("url", "")).path)
        return {"kind": "editable", "path": path}
    # `uv tool install` leaves a receipt in the tool's environment.
    if (Path(sys.prefix) / "uv-receipt.toml").exists():
        return {"kind": "uv"}
    return {"kind": "pip"}


def upgrade_command(version: str) -> str:
    """The command that installs release `version` the same way gaad is installed now."""
    info = _install_info()
    if info["kind"] == "editable":
        path = info["path"] or "<your gaad-cli checkout>"
        return f"git -C {path} pull  (editable install: update your checkout)"
    target = f"{REPO_INSTALL_URL}@v{version}"
    if info["kind"] == "uv":
        return f"uv tool install --force {target}"
    return f'pip install --upgrade "{target}"'


def upgrade_notice(latest: str, current: str) -> str:
    return (
        f"A new release of gaad is available: {current} → {latest}\n"
        f"To upgrade, run: {upgrade_command(latest)}\n"
        f"Release notes: {RELEASES_URL}/v{latest}"
    )


def _cache_path() -> Path:
    return get_config_path().parent / "update-check.json"


def _read_cache() -> dict:
    try:
        data = json.loads(_cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_cache(latest: str | None) -> None:
    try:
        path = _cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"checked_at": int(time.time()), "latest": latest}) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def cached_latest_release() -> str | None:
    """Latest release, refreshed from GitHub at most once per CHECK_INTERVAL."""
    cache = _read_cache()
    checked_at = cache.get("checked_at")
    if isinstance(checked_at, (int, float)) and time.time() - checked_at < CHECK_INTERVAL:
        return cache.get("latest")
    latest = latest_release()
    _write_cache(latest)
    return latest


def should_check() -> bool:
    """Only notify interactive users: not when disabled, in CI, or when stderr is piped."""
    if os.environ.get(DISABLE_ENV) or os.environ.get("CI"):
        return False
    return sys.stderr.isatty()


def pending_notice() -> str | None:
    """The upgrade notice to show after a command, or None. Never raises."""
    try:
        if not should_check():
            return None
        current = installed_version()
        latest = cached_latest_release()
        if is_newer(latest, current):
            return upgrade_notice(latest, current)
    except Exception:
        return None
    return None
