"""Tests for gaad.shared.client."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from gaad.errors import AuthError


class TestGetClient:
    def test_returns_v1beta_client_by_default(self, tmp_config_dir):
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")
        mock_creds = MagicMock()
        mock_client = MagicMock()
        with patch("gaad.shared.client.get_credentials", return_value=mock_creds):
            with patch("gaad.shared.client.build_admin_client", return_value=mock_client) as mock_build:
                from gaad.shared.client import get_client

                result = get_client()
                mock_build.assert_called_once_with(mock_creds, version="v1beta")
                assert result is mock_client

    def test_returns_v1alpha_client_when_specified(self, tmp_config_dir):
        from gaad import config as cfg

        cfg.set("auth_method", "token")
        cfg.set("access_token", "tok")
        mock_creds = MagicMock()
        mock_client = MagicMock()
        with patch("gaad.shared.client.get_credentials", return_value=mock_creds):
            with patch("gaad.shared.client.build_admin_client", return_value=mock_client) as mock_build:
                from gaad.shared.client import get_client

                result = get_client(version="v1alpha")
                mock_build.assert_called_once_with(mock_creds, version="v1alpha")
                assert result is mock_client

    def test_auth_error_causes_exit(self, tmp_config_dir):
        import click

        from gaad import config as cfg

        cfg.set("auth_method", "token")
        with patch("gaad.shared.client.get_credentials", side_effect=AuthError("not authed")):
            from gaad.shared.client import get_client

            with pytest.raises((SystemExit, click.exceptions.Exit)):
                get_client()
