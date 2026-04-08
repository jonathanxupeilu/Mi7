"""Tests for smart source orchestration with API conservation strategy."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.source_orchestrator import SourceOrchestrator, SourceConfig


class TestSourceOrchestrator:
    """Test the source orchestrator logic."""

    def test_tier1_sources_always_enabled(self):
        """Tier 1 sources (rss, dfcf, obsidian) should always be included in default mode."""
        # Given: Default configuration
        config = {
            'sources': {
                'rss': {'enabled': True},
                'dfcf': {'enabled': True},
                'obsidian': {'enabled': True},
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
        assert 'obsidian' in sources

    def test_tier1_sources_included_even_when_config_disabled(self):
        """Tier 1 sources are mandatory and override config disabled flag."""
        # Given: Config has tier 1 sources disabled
        config = {
            'sources': {
                'rss': {'enabled': False},
                'dfcf': {'enabled': False},
                'obsidian': {'enabled': False},
            }
        }
        orchestrator = SourceOrchestrator(config)

        # When: Getting sources for 'all' mode
        sources = orchestrator.get_sources_for_mode('all')

        # Then: Tier 1 sources are still included (mandatory)
        assert 'rss' in sources
        assert 'dfcf' in sources
        assert 'obsidian' in sources

    def test_quick_mode_skips_tier2(self):
        """Quick mode should skip tier 2 paid sources."""
        # Given: Config with all sources enabled
        config = {
            'sources': {
                'rss': {'enabled': True},
                'dfcf': {'enabled': True},
                'obsidian': {'enabled': True},
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
        assert 'obsidian' in sources
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
                'obsidian': {'enabled': True},
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
        assert orchestrator.is_tier1('obsidian') is True
        assert orchestrator.is_tier1('research') is False

