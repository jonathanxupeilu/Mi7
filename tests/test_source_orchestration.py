"""Tests for smart source orchestration with API conservation strategy."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.source_orchestrator import SourceOrchestrator, SourceConfig, NotebookLMCache


class TestSourceOrchestrator:
    """Test the source orchestrator logic."""

    def test_tier1_sources_always_enabled(self):
        """Tier 1 sources (rss, dfcf, notebooklm) should always be included in default mode."""
        # Given: Default configuration
        config = {
            'sources': {
                'rss': {'enabled': True},
                'dfcf': {'enabled': True},
                'notebooklm': {'enabled': True},
                'research': {'enabled': True},
                'announcement': {'enabled': True},
                'snowball': {'enabled': True}
            }
        }
        orchestrator = SourceOrchestrator(config)

        # When: Getting sources for 'all' mode
        sources = orchestrator.get_sources_for_mode('all')

        # Then: Tier 1 sources are always included
        assert 'rss' in sources
        assert 'dfcf' in sources
        assert 'notebooklm' in sources

    def test_tier1_sources_included_even_when_config_disabled(self):
        """Tier 1 sources are mandatory and override config disabled flag."""
        # Given: Config has tier 1 sources disabled
        config = {
            'sources': {
                'rss': {'enabled': False},
                'dfcf': {'enabled': False},
                'notebooklm': {'enabled': False},
            }
        }
        orchestrator = SourceOrchestrator(config)

        # When: Getting sources for 'all' mode
        sources = orchestrator.get_sources_for_mode('all')

        # Then: Tier 1 sources are still included (mandatory)
        assert 'rss' in sources
        assert 'dfcf' in sources
        assert 'notebooklm' in sources

    def test_quick_mode_skips_tier2(self):
        """Quick mode should skip tier 2 paid sources."""
        # Given: Config with all sources enabled
        config = {
            'sources': {
                'rss': {'enabled': True},
                'dfcf': {'enabled': True},
                'notebooklm': {'enabled': True},
                'research': {'enabled': True},
                'announcement': {'enabled': True},
                'snowball': {'enabled': True}
            }
        }
        orchestrator = SourceOrchestrator(config)

        # When: Getting sources for quick mode
        sources = orchestrator.get_sources_for_mode('quick')

        # Then: Only tier 1 sources
        assert 'rss' in sources
        assert 'dfcf' in sources
        assert 'notebooklm' in sources
        assert 'research' not in sources
        assert 'announcement' not in sources
        assert 'snowball' not in sources

    def test_specific_source_overrides_default(self):
        """Explicit --source should override default 'all' behavior."""
        # Given: Config
        config = {
            'sources': {
                'rss': {'enabled': True},
                'dfcf': {'enabled': True},
                'notebooklm': {'enabled': True},
            }
        }
        orchestrator = SourceOrchestrator(config)

        # When: Getting specific source
        sources = orchestrator.get_sources_for_mode('rss')

        # Then: Only that source is used
        assert sources == ['rss']

    def test_is_tier1_method(self):
        """Test tier 1 source detection."""
        config = {'sources': {}}
        orchestrator = SourceOrchestrator(config)

        assert orchestrator.is_tier1('rss') is True
        assert orchestrator.is_tier1('dfcf') is True
        assert orchestrator.is_tier1('notebooklm') is True
        assert orchestrator.is_tier1('research') is False


class TestNotebookLMCache:
    """Test NotebookLM cache functionality."""

    def test_cache_set_and_get(self, tmp_path):
        """Test storing and retrieving from cache."""
        # Given: Cache instance with temp db
        db_path = str(tmp_path / "test_cache.db")
        cache = NotebookLMCache(db_path)

        # When: Setting cache entry
        test_data = {'analysis': 'Test analysis result', 'sources': ['doc1', 'doc2']}
        cache.set('test_query', test_data, ttl_hours=1)

        # Then: Can retrieve it
        result = cache.get('test_query')
        assert result == test_data

    def test_cache_expires(self, tmp_path):
        """Test cache entries expire correctly."""
        # Given: Cache with entry that expires immediately
        db_path = str(tmp_path / "test_cache.db")
        cache = NotebookLMCache(db_path)

        # When: Setting cache with 0 TTL (already expired)
        test_data = {'analysis': 'Expired data'}
        cache.set('test_query', test_data, ttl_hours=0)

        # Then: Should not be retrievable
        result = cache.get('test_query')
        assert result is None

    def test_is_fresh_method(self, tmp_path):
        """Test is_fresh cache check."""
        # Given: Cache with fresh entry
        db_path = str(tmp_path / "test_cache.db")
        cache = NotebookLMCache(db_path)

        # When: Setting fresh cache
        cache.set('fresh_query', {'data': 'test'}, ttl_hours=1)

        # Then: Should be fresh
        assert cache.is_fresh('fresh_query') is True
        assert cache.is_fresh('nonexistent_query') is False

    def test_clear_expired(self, tmp_path):
        """Test clearing expired entries."""
        # Given: Cache with expired and fresh entries
        db_path = str(tmp_path / "test_cache.db")
        cache = NotebookLMCache(db_path)

        cache.set('expired', {'data': 'old'}, ttl_hours=0)
        cache.set('fresh', {'data': 'new'}, ttl_hours=1)

        # When: Clearing expired
        deleted = cache.clear_expired()

        # Then: One entry deleted
        assert deleted == 1
        assert cache.get('expired') is None
        assert cache.get('fresh') is not None

