"""Custom exception hierarchy for gaad-cli."""

from __future__ import annotations


class GaadError(Exception):
    """Base exception for all gaad-cli errors."""


class AuthError(GaadError):
    """Authentication failures.

    Exit code: 2
    """

    exit_code: int = 2


class ConfigError(GaadError):
    """Configuration file problems."""
