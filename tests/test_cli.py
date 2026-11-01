"""Tests for the root gaad command."""

from __future__ import annotations

from importlib import metadata

from typer.testing import CliRunner

from gaad.cli import app

runner = CliRunner()


def test_version_prints_installed_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output == f"gaad {metadata.version('gaad-cli')}\n"


def test_version_without_installed_package(mocker) -> None:
    mocker.patch("gaad.cli.metadata.version", side_effect=metadata.PackageNotFoundError)

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert "unknown" in result.output


def test_subcommands_still_work_with_root_callback() -> None:
    result = runner.invoke(app, ["custom-dimensions", "--help"])

    assert result.exit_code == 0, result.output
    assert "archive" in result.output
