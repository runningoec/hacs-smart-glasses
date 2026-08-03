"""Unit tests for glasses Bearer token parsing."""

from __future__ import annotations

import secrets

import pytest

from custom_components.smart_glasses.views import (
    _extract_glasses_token,
    _lookup_glasses_token,
)

pytestmark = pytest.mark.enable_socket


def test_extract_accepts_token_urlsafe_32():
    token = secrets.token_urlsafe(32)
    assert _extract_glasses_token(f"Bearer {token}") == token


def test_extract_rejects_missing_or_wrong_scheme():
    assert _extract_glasses_token("") is None
    assert _extract_glasses_token("Basic abc") is None
    assert _extract_glasses_token("bearer " + ("a" * 43)) is None


def test_extract_rejects_short_values():
    assert _extract_glasses_token("Bearer short") is None
    assert _extract_glasses_token("Bearer " + ("a" * 42)) is None


def test_lookup_rejects_non_string_without_store():
    """Non-strings must fail closed before any store lookup."""

    class _BoomHass:
        @property
        def data(self):
            raise AssertionError("store must not be touched for bad tokens")

    hass = _BoomHass()
    assert _lookup_glasses_token(hass, None) is None  # type: ignore[arg-type]
    assert _lookup_glasses_token(hass, 123) is None  # type: ignore[arg-type]
    assert _lookup_glasses_token(hass, ["x"]) is None  # type: ignore[arg-type]
