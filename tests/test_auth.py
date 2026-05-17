"""Tests for gaad.auth module — written before implementation (TDD)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gaad.errors import AuthError


class TestGetCredentials:
    """get_credentials() behaviour."""

    def test_raises_auth_error_when_config_empty(self, tmp_config_dir: Path) -> None:
        from gaad.auth import get_credentials

        with pytest.raises(AuthError, match="Not authenticated"):
            get_credentials({})

    def test_raises_auth_error_when_auth_method_missing(self, tmp_config_dir: Path) -> None:
        from gaad.auth import get_credentials

        with pytest.raises(AuthError):
            get_credentials({"some_key": "some_value"})

    def test_service_account_calls_from_service_account_file(self, tmp_config_dir: Path) -> None:
        from gaad.auth import get_credentials

        mock_creds = MagicMock()
        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_file",
            return_value=mock_creds,
        ) as mock_factory:
            result = get_credentials(
                {"auth_method": "service-account", "key_file": "/fake/key.json"}
            )
            mock_factory.assert_called_once_with(
                "/fake/key.json",
                scopes=pytest.approx(
                    [
                        "https://www.googleapis.com/auth/analytics.readonly",
                        "https://www.googleapis.com/auth/analytics.edit",
                    ],
                    abs=0,
                ),
            )
            assert result is mock_creds

    def test_token_method_returns_credentials_with_token(self, tmp_config_dir: Path) -> None:
        from gaad.auth import get_credentials

        result = get_credentials({"auth_method": "token", "access_token": "my-secret-token"})
        assert result.token == "my-secret-token"

    def test_token_from_env_var_when_not_in_config(
        self, tmp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from gaad.auth import get_credentials

        monkeypatch.setenv("GA4_ACCESS_TOKEN", "env-token-value")
        result = get_credentials({"auth_method": "token"})
        assert result.token == "env-token-value"

    def test_token_raises_if_no_token_anywhere(
        self, tmp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from gaad.auth import get_credentials

        monkeypatch.delenv("GA4_ACCESS_TOKEN", raising=False)
        with pytest.raises(AuthError, match="No access token"):
            get_credentials({"auth_method": "token"})

    def test_oauth2_deserializes_stored_credentials(self, tmp_config_dir: Path) -> None:
        from gaad.auth import get_credentials, serialize_oauth2_credentials

        mock_creds = MagicMock()
        mock_creds.token = "stored-token"
        mock_creds.refresh_token = "refresh-tok"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "client-id"
        mock_creds.client_secret = "client-secret"
        mock_creds.scopes = ["https://www.googleapis.com/auth/analytics.readonly"]
        mock_creds.expiry = None

        serialized = serialize_oauth2_credentials(mock_creds)
        config = {"auth_method": "oauth2", "oauth2_credentials": serialized}

        with patch("gaad.auth.google.auth.transport.requests.Request"):
            with patch("gaad.auth.google.oauth2.credentials.Credentials") as mock_cls:
                fake_instance = MagicMock()
                fake_instance.expired = False
                mock_cls.return_value = fake_instance
                result = get_credentials(config)
                assert result is fake_instance


    def test_oauth2_refreshes_expired_credentials(self, tmp_config_dir: Path) -> None:
        from gaad.auth import get_credentials, serialize_oauth2_credentials

        mock_creds = MagicMock()
        mock_creds.token = "expired-token"
        mock_creds.refresh_token = "refresh-tok"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "cid"
        mock_creds.client_secret = "csecret"
        mock_creds.scopes = []
        mock_creds.expiry = None

        serialized = serialize_oauth2_credentials(mock_creds)
        config = {"auth_method": "oauth2", "oauth2_credentials": serialized}

        with patch("gaad.auth.google.auth.transport.requests.Request") as mock_request_cls:
            with patch("gaad.auth.google.oauth2.credentials.Credentials") as mock_cls:
                fake_instance = MagicMock()
                fake_instance.expired = True
                fake_instance.refresh_token = "refresh-tok"
                mock_cls.return_value = fake_instance
                result = get_credentials(config)
                # refresh should have been called
                fake_instance.refresh.assert_called_once()
                assert result is fake_instance

    def test_get_credentials_raises_for_unknown_method(self) -> None:
        from gaad.auth import get_credentials

        with pytest.raises(AuthError, match="Unknown auth method"):
            get_credentials({"auth_method": "magic-beans"})


class TestSerializeDeserialize:
    """serialize/deserialize oauth2 credentials roundtrip."""

    def test_roundtrip_preserves_token_fields(self) -> None:
        from gaad.auth import deserialize_oauth2_credentials, serialize_oauth2_credentials

        mock_creds = MagicMock()
        mock_creds.token = "access-tok"
        mock_creds.refresh_token = "refresh-tok"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "cid"
        mock_creds.client_secret = "csecret"
        mock_creds.scopes = ["https://www.googleapis.com/auth/analytics.readonly"]
        mock_creds.expiry = None

        data = serialize_oauth2_credentials(mock_creds)
        assert isinstance(data, dict)
        assert data["token"] == "access-tok"
        assert data["refresh_token"] == "refresh-tok"
        assert data["client_id"] == "cid"

        reconstructed = deserialize_oauth2_credentials(data)
        assert reconstructed.token == "access-tok"
        assert reconstructed.refresh_token == "refresh-tok"
        assert reconstructed.client_id == "cid"
        assert reconstructed.client_secret == "csecret"

    def test_serialize_handles_expiry_datetime(self) -> None:
        from datetime import datetime, timezone

        from gaad.auth import serialize_oauth2_credentials

        mock_creds = MagicMock()
        mock_creds.token = "tok"
        mock_creds.refresh_token = "rtok"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "cid"
        mock_creds.client_secret = "csecret"
        mock_creds.scopes = []
        mock_creds.expiry = datetime(2025, 1, 1, tzinfo=timezone.utc)

        data = serialize_oauth2_credentials(mock_creds)
        assert data["expiry"] == "2025-01-01T00:00:00+00:00"

    def test_serialize_handles_naive_datetime_expiry(self) -> None:
        """Naive datetime expiry should be treated as UTC."""
        from datetime import datetime

        from gaad.auth import serialize_oauth2_credentials

        mock_creds = MagicMock()
        mock_creds.token = "tok"
        mock_creds.refresh_token = "rtok"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "cid"
        mock_creds.client_secret = "csecret"
        mock_creds.scopes = []
        # Naive datetime (no tzinfo)
        mock_creds.expiry = datetime(2025, 6, 15, 12, 0, 0)

        data = serialize_oauth2_credentials(mock_creds)
        assert "+00:00" in data["expiry"]

    def test_deserialize_handles_expiry_string(self) -> None:
        """Expiry string in stored data should be parsed back to datetime."""
        from gaad.auth import deserialize_oauth2_credentials

        data = {
            "token": "tok",
            "refresh_token": "rtok",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "cid",
            "client_secret": "csecret",
            "scopes": [],
            "expiry": "2025-06-15T12:00:00+00:00",
        }
        creds = deserialize_oauth2_credentials(data)
        assert creds.expiry is not None


class TestBuildAdminClient:
    """build_admin_client() behaviour."""

    def test_returns_admin_service_client(self) -> None:
        from gaad.auth import build_admin_client

        mock_creds = MagicMock()
        with patch(
            "gaad.auth.admin_v1beta.AnalyticsAdminServiceClient",
        ) as mock_cls:
            fake_client = MagicMock()
            mock_cls.return_value = fake_client
            result = build_admin_client(mock_creds)
            assert result is fake_client
            mock_cls.assert_called_once()

    def test_build_admin_client_returns_v1beta_by_default(self) -> None:
        mock_creds = MagicMock()
        with patch("gaad.auth.admin_v1beta.AnalyticsAdminServiceClient") as mock_cls:
            from gaad.auth import build_admin_client

            build_admin_client(mock_creds)
            mock_cls.assert_called_once_with(credentials=mock_creds)

    def test_build_admin_client_returns_v1alpha_when_specified(self) -> None:
        mock_creds = MagicMock()
        with patch("gaad.auth.admin_v1alpha.AnalyticsAdminServiceClient") as mock_cls:
            from gaad.auth import build_admin_client

            build_admin_client(mock_creds, version="v1alpha")
            mock_cls.assert_called_once_with(credentials=mock_creds)
