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

    def test_cache_expires_after_ttl(self, tmp_path):
        """RED: 缓存应在 TTL 后过期"""
        db_path = tmp_path / "test_cache.db"
        cache = DFCFCache(str(db_path))
        data = [{'title': 'Test'}]

        # 使用负值TTL使缓存立即过期
        cache.set('600519', 'query', data, ttl_hours=-1)

        # 读取应返回 None (已过期)
        result = cache.get('600519', 'query')
        assert result is None

    def test_clear_expired_removes_old_entries(self, tmp_path):
        """RED: clear_expired 应删除过期条目"""
        db_path = tmp_path / "test_cache.db"
        cache = DFCFCache(str(db_path))

        # 设置两个缓存，一个已过期，一个有效
        cache.set('600519', 'old_query', [{'title': 'Old'}], ttl_hours=-1)
        cache.set('000858', 'new_query', [{'title': 'New'}], ttl_hours=1)

        # 清理过期缓存
        deleted = cache.clear_expired()
        assert deleted == 1

        # 验证过期缓存已删除，有效缓存仍存在
        assert cache.get('600519', 'old_query') is None
        assert cache.get('000858', 'new_query') is not None

    def test_get_stats_returns_correct_counts(self, tmp_path):
        """RED: get_stats 应返回正确的统计信息"""
        db_path = tmp_path / "test_cache.db"
        cache = DFCFCache(str(db_path))

        # 初始状态
        stats = cache.get_stats()
        assert stats['total'] == 0
        assert stats['valid'] == 0
        assert stats['expired'] == 0

        # 添加有效缓存
        cache.set('600519', 'query1', [{'title': 'Test'}], ttl_hours=1)
        stats = cache.get_stats()
        assert stats['total'] == 1
        assert stats['valid'] == 1
        assert stats['expired'] == 0

        # 添加过期缓存
        cache.set('000858', 'query2', [{'title': 'Old'}], ttl_hours=-1)
        stats = cache.get_stats()
        assert stats['total'] == 2
        assert stats['valid'] == 1
        assert stats['expired'] == 1
