"""Tests for src/models/cache_entry.py."""

import json

import pytest

from src.models.cache_entry import CacheEntry


class TestCacheEntry:
    """Tests for the CacheEntry class."""

    def test_construction_with_value_only(self):
        entry = CacheEntry(value="test-value")
        assert entry.value == "test-value"
        assert entry.ttl is None

    def test_construction_with_value_and_ttl(self):
        entry = CacheEntry(value="test-value", ttl=300)
        assert entry.value == "test-value"
        assert entry.ttl == 300

    def test_get_ttl_returns_ttl(self):
        entry = CacheEntry(value="test", ttl=600)
        assert entry.get_ttl() == 600

    def test_get_ttl_returns_none_when_not_set(self):
        entry = CacheEntry(value="test")
        assert entry.get_ttl() is None

    def test_get_json_value_decodes_dict(self):
        data = {"key": "value", "number": 42}
        entry = CacheEntry(value=json.dumps(data))
        decoded = entry.get_json_value()
        assert decoded == data

    def test_get_json_value_decodes_list(self):
        data = ["item1", "item2", "item3"]
        entry = CacheEntry(value=json.dumps(data))
        decoded = entry.get_json_value()
        assert decoded == data

    def test_get_json_value_invalid_json_raises(self):
        entry = CacheEntry(value="not valid json")
        with pytest.raises(json.JSONDecodeError):
            entry.get_json_value()

    def test_value_can_be_any_type(self):
        entry = CacheEntry(value=b"binary data")
        assert entry.value == b"binary data"

    def test_ttl_zero_is_valid(self):
        entry = CacheEntry(value="test", ttl=0)
        assert entry.ttl == 0

    def test_ttl_negative_is_valid(self):
        entry = CacheEntry(value="test", ttl=-1)
        assert entry.ttl == -1
