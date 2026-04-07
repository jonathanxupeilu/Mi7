"""Tests for DFCF degradation mode - use cache when API fails."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class MockCache:
    """Mock cache that can return expired data."""
    def __init__(self, fresh_data=None, expired_data=None):
        self.fresh_data = fresh_data
        self.expired_data = expired_data

    def get(self, stock_code, query):
        """Get any cached data (fresh or expired)"""
        if self.fresh_data is not None:
            return self.fresh_data
        if self.expired_data is not None:
            return self.expired_data
        return None

    def is_fresh(self, stock_code, query):
        """Check if data is fresh"""
        return self.fresh_data is not None

    def get_expired(self, stock_code, query):
        """Get expired data only"""
        return self.expired_data

    def set(self, stock_code, query, data, ttl_hours=48):
        pass


class TestDFCFDegradation:
    """Test DFCF graceful degradation when API rate limit hit."""

    def test_returns_cached_data_when_api_fails(self, monkeypatch):
        """When API returns rate limit error, should return cached data even if expired."""
        # Given: Expired cache exists
        expired_data = [{'title': 'Cached News', 'date': '2026-04-05'}]
        mock_cache = MockCache(fresh_data=None, expired_data=expired_data)

        # Create collector with mocked cache
        from collectors.dfcf_collector import DFCFCollector

        # Mock environment
        monkeypatch.setenv('MX_APIKEY', 'test_key')

        collector = DFCFCollector.__new__(DFCFCollector)
        collector.cache = mock_cache
        collector.api_key = 'test_key'

        # And: API fails with rate limit
        with patch.object(collector, '_api_search') as mock_api:
            mock_api.return_value = []  # API returns empty due to error
            result = collector.search_news('测试股票 000001')

        # Then: Should return expired cached data
        assert result == expired_data

    def test_returns_fresh_cache_without_api_call(self, monkeypatch):
        """When cache is fresh, should not call API at all."""
        # Given: Fresh cache exists
        fresh_data = [{'title': 'Fresh News', 'date': '2026-04-07'}]
        mock_cache = MockCache(fresh_data=fresh_data, expired_data=None)

        from collectors.dfcf_collector import DFCFCollector

        monkeypatch.setenv('MX_APIKEY', 'test_key')

        collector = DFCFCollector.__new__(DFCFCollector)
        collector.cache = mock_cache
        collector.api_key = 'test_key'

        with patch.object(collector, '_api_search') as mock_api:
            result = collector.search_news('测试股票 000001')

        # Then: Should return cached data without API call
        assert result == fresh_data
        mock_api.assert_not_called()

    def test_returns_empty_when_no_cache_and_api_fails(self, monkeypatch):
        """When no cache and API fails, should return empty list gracefully."""
        # Given: No cache at all
        mock_cache = MockCache(fresh_data=None, expired_data=None)

        from collectors.dfcf_collector import DFCFCollector

        monkeypatch.setenv('MX_APIKEY', 'test_key')

        collector = DFCFCollector.__new__(DFCFCollector)
        collector.cache = mock_cache
        collector.api_key = 'test_key'

        with patch.object(collector, '_api_search') as mock_api:
            mock_api.return_value = []  # API fails
            result = collector.search_news('测试股票 000001')

        # Then: Should return empty list
        assert result == []
