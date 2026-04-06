"""DFCFCollector 单元测试 - TDD"""
import pytest
import sys
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.dfcf_collector import DFCFCollector


class TestDFCFCollector:
    def test_collector_uses_cache_on_second_call(self, tmp_path):
        """RED: 第二次调用应使用缓存"""
        from collectors.dfcf_collector import DFCFCollector

        # Mock API call counter
        call_count = 0
        original_api_search = None

        def mock_api_search(self, query):
            nonlocal call_count
            call_count += 1
            return [{'title': f'News {call_count}', 'content': 'Content'}]

        # Create collector
        collector = DFCFCollector(db_path=str(tmp_path / "test.db"))

        # Replace _api_search with mock
        original_api_search = collector._api_search
        collector._api_search = lambda query: mock_api_search(collector, query)

        # First call - should hit API
        result1 = collector.search_news('贵州茅台 600519')
        assert call_count == 1

        # Second call - should use cache
        result2 = collector.search_news('贵州茅台 600519')
        assert call_count == 1  # Still 1
        assert result1 == result2
