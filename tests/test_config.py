"""Tests for gaad.config module — written before implementation (TDD)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from gaad import config as cfg


class TestLoadConfig:
    """load_config() behaviour."""

    def test_returns_empty_dict_when_file_missing(self, tmp_config_dir: Path) -> None:
        result = cfg.load_config()
        assert result == {}

    def test_returns_parsed_json_when_file_exists(self, tmp_config_dir: Path) -> None:
        config_file = cfg.get_config_path()
        config_file.write_text(json.dumps({"auth_method": "token"}))
        result = cfg.load_config()
        assert result == {"auth_method": "token"}


class TestSaveConfig:
    """save_config() behaviour."""

    def test_creates_file_with_correct_content(self, tmp_config_dir: Path) -> None:
        data = {"key": "value", "number": 42}
        cfg.save_config(data)
        config_file = cfg.get_config_path()
        assert config_file.exists()
        loaded = json.loads(config_file.read_text())
        assert loaded == data

    def test_uses_two_space_indent(self, tmp_config_dir: Path) -> None:
        cfg.save_config({"a": 1})
        config_file = cfg.get_config_path()
        raw = config_file.read_text()
        assert "  " in raw  # two-space indent present

    def test_creates_parent_directories(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        deep_dir = tmp_path / "deeply" / "nested" / "config"
        monkeypatch.setenv("GAAD_CONFIG_DIR", str(deep_dir))
        cfg.save_config({"x": 1})
        assert cfg.get_config_path().exists()


class TestGetAndSet:
    """get() and set() convenience helpers."""

    def test_get_returns_value_for_existing_key(self, tmp_config_dir: Path) -> None:
        cfg.save_config({"auth_method": "oauth2"})
        assert cfg.get("auth_method") == "oauth2"

    def test_get_returns_default_for_missing_key(self, tmp_config_dir: Path) -> None:
        cfg.save_config({})
        assert cfg.get("missing_key", "fallback") == "fallback"

    def test_get_returns_none_default_when_not_specified(self, tmp_config_dir: Path) -> None:
        cfg.save_config({})
        assert cfg.get("no_key") is None

    def test_set_persists_value(self, tmp_config_dir: Path) -> None:
        cfg.set("auth_method", "token")
        assert cfg.get("auth_method") == "token"

    def test_set_does_not_overwrite_other_keys(self, tmp_config_dir: Path) -> None:
        cfg.save_config({"existing": "value"})
        cfg.set("new_key", "new_value")
        assert cfg.get("existing") == "value"
        assert cfg.get("new_key") == "new_value"


class TestClear:
    """clear() behaviour."""

    def test_clear_resets_to_empty_dict(self, tmp_config_dir: Path) -> None:
        cfg.save_config({"auth_method": "token", "access_token": "abc"})
        cfg.clear()
        assert cfg.load_config() == {}

    def test_clear_writes_file(self, tmp_config_dir: Path) -> None:
        cfg.clear()
        config_file = cfg.get_config_path()
        assert config_file.exists()
        assert json.loads(config_file.read_text()) == {}


class TestConfigPath:
    """get_config_path() behaviour."""

    def test_respects_gaad_config_dir_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        custom_dir = tmp_path / "custom-config"
        monkeypatch.setenv("GAAD_CONFIG_DIR", str(custom_dir))
        path = cfg.get_config_path()
        assert str(custom_dir) in str(path)

    def test_defaults_to_home_config_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GAAD_CONFIG_DIR", raising=False)
        path = cfg.get_config_path()
        assert "gaad-cli" in str(path)
        assert "config.json" in str(path)
