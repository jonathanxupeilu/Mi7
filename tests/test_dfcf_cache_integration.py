"""东方财富采集器缓存集成测试"""
import pytest
from datetime import datetime
from collectors.dfcf_collector import DFCFCollector


class TestDFCFCacheIntegration:
    """测试 DFCFCollector 与 DFCFCache 的集成"""

    def test_collector_initializes_cache(self, tmp_path):
        """RED: DFCFCollector 应初始化缓存"""
        db_path = tmp_path / "test.db"
        collector = DFCFCollector(db_path=str(db_path))
        assert collector.cache is not None

    def test_search_news_uses_cache(self, tmp_path):
        """RED: search_news 应使用缓存"""
        db_path = tmp_path / "test.db"
        collector = DFCFCollector(db_path=str(db_path))

        # Mock API 调用
        api_calls = []
        original_api = collector._api_search

        def mock_api_search(query):
            api_calls.append(query)
            return [{'title': f'News for {query}', 'content': 'Content'}]

        collector._api_search = mock_api_search

        # 第一次调用 - 应命中 API
        result1 = collector.search_news('贵州茅台 600519')
        assert len(api_calls) == 1

        # 第二次调用相同股票 - 应使用缓存
        result2 = collector.search_news('贵州茅台 600519')
        assert len(api_calls) == 1  # 没有新增 API 调用
        assert result1 == result2

    def test_cache_different_stocks_isolated(self, tmp_path):
        """RED: 不同股票应有独立缓存"""
        db_path = tmp_path / "test.db"
        collector = DFCFCollector(db_path=str(db_path))

        api_calls = []
        def mock_api_search(query):
            api_calls.append(query)
            return [{'title': f'News {len(api_calls)}'}]

        collector._api_search = mock_api_search

        # 查询股票 A
        collector.search_news('贵州茅台 600519')
        assert len(api_calls) == 1

        # 查询股票 B - 应调用 API
        collector.search_news('五粮液 000858')
        assert len(api_calls) == 2

        # 再次查询股票 A - 应使用缓存
        collector.search_news('贵州茅台 600519')
        assert len(api_calls) == 2  # 没有新增调用

    def test_cache_stats_after_collection(self, tmp_path):
        """RED: 采集后应能看到缓存统计"""
        db_path = tmp_path / "test.db"
        collector = DFCFCollector(db_path=str(db_path))

        # 设置一些缓存
        collector.cache.set('600519', 'query1', [{'title': 'Test'}], ttl_hours=1)
        collector.cache.set('000858', 'query2', [{'title': 'Test'}], ttl_hours=-1)

        stats = collector.cache.get_stats()
        assert stats['total'] == 2
        assert stats['valid'] == 1
        assert stats['expired'] == 1
