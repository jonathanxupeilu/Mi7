"""Source orchestrator for MI7 - manages smart source selection and API conservation."""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json


@dataclass
class SourceConfig:
    """Configuration for a data source."""
    name: str
    tier: int  # 1 = always on, 2 = conditional/paid
    enabled: bool
    supports_caching: bool = False
    cache_ttl_hours: int = 4


class SourceOrchestrator:
    """Orchestrates data sources with smart API conservation strategy."""

    # Tier 1: Always on, proactive caching
    TIER1_SOURCES = ['rss', 'dfcf', 'obsidian']

    # Tier 2: Conditional/paid sources
    TIER2_SOURCES = ['research', 'announcement', 'snowball']

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sources = self._initialize_sources()

    def _initialize_sources(self) -> Dict[str, SourceConfig]:
        """Initialize source configurations."""
        sources = {}

        # Tier 1 sources - always enabled, mandatory
        for source_name in self.TIER1_SOURCES:
            source_config = self.config.get('sources', {}).get(source_name, {})
            sources[source_name] = SourceConfig(
                name=source_name,
                tier=1,
                enabled=True,  # Mandatory - always enabled
                supports_caching=source_name in ['dfcf', 'obsidian'],
                cache_ttl_hours=4 if source_name == 'dfcf' else 24
            )

        # Tier 2 sources - respect config enabled flag
        for source_name in self.TIER2_SOURCES:
            source_config = self.config.get('sources', {}).get(source_name, {})
            sources[source_name] = SourceConfig(
                name=source_name,
                tier=2,
                enabled=source_config.get('enabled', False),
                supports_caching=False,
                cache_ttl_hours=24
            )

        return sources

    def get_sources_for_mode(self, mode: str) -> List[str]:
        """Get list of sources to use for given mode."""
        if mode == 'all':
            # All enabled sources
            return [
                name for name, config in self.sources.items()
                if config.enabled
            ]
        elif mode == 'quick':
            # Only tier 1 sources (RSS, DFCF, NotebookLM)
            return self.TIER1_SOURCES
        elif mode in self.sources:
            # Specific single source
            return [mode]
        else:
            # Unknown mode - return tier 1 as safe default
            return self.TIER1_SOURCES

    def is_tier1(self, source_name: str) -> bool:
        """Check if source is tier 1 (always on)."""
        return source_name in self.TIER1_SOURCES

    def should_use_cache(self, source_name: str) -> bool:
        """Check if source supports caching."""
        source = self.sources.get(source_name)
        return source.supports_caching if source else False

    def get_cache_ttl(self, source_name: str) -> int:
        """Get cache TTL in hours for source."""
        source = self.sources.get(source_name)
        return source.cache_ttl_hours if source else 4
