"""DFCFCache 单元测试 - TDD"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.dfcf_cache import DFCFCache


class TestDFCFCache:
    def test_cache_get_returns_none_for_miss(self, tmp_path):
        """RED: 缓存未命中应返回 None"""
        db_path = tmp_path / "test_cache.db"
        cache = DFCFCache(str(db_path))
        result = cache.get('600519', '贵州茅台 600519')
        assert result is None

    def test_cache_set_and_get(self, tmp_path):
        """RED: 设置缓存后应能读取"""
        db_path = tmp_path / "test_cache.db"
        cache = DFCFCache(str(db_path))
        data = [{'title': 'Test', 'content': 'Content'}]
        cache.set('600519', '贵州茅台 600519', data, ttl_hours=1)
        result = cache.get('600519', '贵州茅台 600519')
        assert result == data
