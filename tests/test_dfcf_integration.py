"""东方财富缓存集成测试"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.dfcf_collector import DFCFCollector


class TestDFCFIntegration:
    """测试采集器与缓存的集成"""

    def test_full_collection_with_caching(self, tmp_path):
        """
        完整流程测试：
        1. 第一次采集某只股票 - 应调用 API
        2. 第二次采集同一只股票 - 应命中缓存
        3. 验证 API 调用次数
        """
        db_path = tmp_path / "test.db"
        collector = DFCFCollector(db_path=str(db_path))

        # Mock API 调用计数器
        api_call_count = 0

        def mock_api_search(query):
            nonlocal api_call_count
            api_call_count += 1
            return [{'title': f'News {api_call_count}', 'content': 'Test content'}]

        # 替换 _api_search 方法
        original_api_search = collector._api_search
        collector._api_search = mock_api_search

        try:
            # 第一次调用 - 应命中 API
            result1 = collector.search_news('贵州茅台 600519')
            assert api_call_count == 1
            assert len(result1) > 0

            # 第二次调用同一只股票 - 应使用缓存
            result2 = collector.search_news('贵州茅台 600519')
            assert api_call_count == 1  # 没有新增 API 调用
            assert result1 == result2  # 结果相同

            # 调用不同股票 - 应命中 API
            result3 = collector.search_news('五粮液 000858')
            assert api_call_count == 2  # 新增一次 API 调用
            assert len(result3) > 0

        finally:
            # 恢复原始方法
            collector._api_search = original_api_search

    def test_cache_stats_increases_with_new_entries(self, tmp_path):
        """
        测试缓存统计是否正确更新
        """
        db_path = tmp_path / "test.db"
        collector = DFCFCollector(db_path=str(db_path))

        # 初始状态
        if collector.cache:
            stats = collector.cache.get_stats()
            initial_total = stats['total']

            # Mock API 返回数据
            def mock_api_search(query):
                return [{'title': 'Test', 'content': 'Content'}]

            original = collector._api_search
            collector._api_search = mock_api_search

            try:
                # 采集一只股票
                collector.search_news('测试 000001')

                # 验证缓存统计增加
                stats = collector.cache.get_stats()
                assert stats['total'] == initial_total + 1
                assert stats['valid'] == initial_total + 1

            finally:
                collector._api_search = original
