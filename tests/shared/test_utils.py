"""Tests for gaad.shared.utils."""

from gaad.shared.utils import enum_name, extract_id


class TestExtractId:
    def test_returns_last_segment(self):
        assert extract_id("properties/123") == "123"
        assert extract_id("properties/123/dataStreams/456") == "456"


class TestEnumName:
    def test_returns_name_when_has_name(self):
        class FakeEnum:
            name = "MY_VALUE"

        assert enum_name(FakeEnum()) == "MY_VALUE"

    def test_falls_back_to_str(self):
        assert enum_name(42) == "42"
