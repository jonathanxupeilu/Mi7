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
    TIER1_SOURCES = ['rss', 'dfcf', 'notebooklm']

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
                supports_caching=source_name in ['dfcf', 'notebooklm'],
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


class NotebookLMCache:
    """Cache for NotebookLM analysis results."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self):
        """Ensure cache table exists."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notebooklm_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT UNIQUE NOT NULL,
                response_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis if fresh."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Use ISO format string for datetime comparison
        now_str = datetime.now().isoformat()
        cursor.execute('''
            SELECT response_data FROM notebooklm_cache
            WHERE query = ? AND expires_at > ?
        ''', (query, now_str))

        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row[0])
        return None

    def set(self, query: str, data: Dict[str, Any], ttl_hours: int = 24):
        """Cache analysis result."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()

        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f'Object of type {type(obj)} is not JSON serializable')

        cursor.execute('''
            INSERT OR REPLACE INTO notebooklm_cache
            (query, response_data, expires_at)
            VALUES (?, ?, ?)
        ''', (query, json.dumps(data, default=serialize_datetime), expires_at))

        conn.commit()
        conn.close()

    def is_fresh(self, query: str) -> bool:
        """Check if cache entry is fresh."""
        return self.get(query) is not None

    def clear_expired(self) -> int:
        """Clear expired cache entries."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now_str = datetime.now().isoformat()
        cursor.execute('DELETE FROM notebooklm_cache WHERE expires_at < ?',
                       (now_str,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted
