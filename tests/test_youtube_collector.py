"""YouTubeRSSCollector 单元测试 - TDD"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from collectors.youtube_rss_collector import YouTubeRSSCollector


class TestYouTubeRSSCollector:
    """测试 YouTubeRSSCollector"""

    def test_youtube_collector_has_retry_mechanism(self):
        """RED: YouTubeRSSCollector 应该有重试机制"""
        config = {
            'name': 'YouTube',
            'enabled': True,
            'feeds': [
                {
                    'id': 'cnbc',
                    'name': 'CNBC',
                    'channel_id': 'UCe_3CN7FHPVCIifAnD7hL_A',
                    'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCe_3CN7FHPVCIifAnD7hL_A',
                    'enabled': True
                }
            ]
        }
        collector = YouTubeRSSCollector(config)

        # 验证有重试相关的方法或属性
        assert hasattr(collector, '_fetch_with_retry'), \
            "YouTubeRSSCollector 应该有 _fetch_with_retry 方法"

    def test_retry_on_parse_failure(self):
        """RED: 解析失败时应该重试"""
        config = {
            'name': 'YouTube',
            'enabled': True,
            'feeds': [
                {
                    'id': 'test',
                    'name': 'Test',
                    'channel_id': 'TEST123',
                    'url': 'https://test.com',
                    'enabled': True
                }
            ]
        }
        collector = YouTubeRSSCollector(config)

        # 模拟 feedparser 前两次失败，第三次成功
        call_count = 0
        def mock_parse(url):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Connection error {call_count}")
            return {'entries': []}

        with patch('collectors.youtube_rss_collector.feedparser.parse', side_effect=mock_parse):
            items = collector._fetch_with_retry('https://test.com', max_retries=3)
            # 应该重试了 3 次
            assert call_count == 3, f"应该重试 3 次，实际 {call_count} 次"

    def test_retry_exhausted_raises_error(self):
        """RED: 重试耗尽后应该抛出异常"""
        config = {
            'name': 'YouTube',
            'enabled': True,
            'feeds': []
        }
        collector = YouTubeRSSCollector(config)

        # 模拟一直失败
        with patch('collectors.youtube_rss_collector.feedparser.parse',
                   side_effect=Exception("Persistent error")):
            with pytest.raises(Exception) as exc_info:
                collector._fetch_with_retry('https://test.com', max_retries=3)
            assert "Persistent error" in str(exc_info.value)

    def test_successful_parse_no_retry_needed(self):
        """RED: 成功时不应该重试"""
        config = {
            'name': 'YouTube',
            'enabled': True,
            'feeds': []
        }
        collector = YouTubeRSSCollector(config)

        # 模拟立即成功
        mock_feed = Mock()
        mock_feed.entries = []
        mock_feed.bozo = False  # 没有警告

        with patch('collectors.youtube_rss_collector.feedparser.parse', return_value=mock_feed) as mock_parse:
            items = collector._fetch_with_retry('https://test.com', max_retries=3)
            # 应该只调用一次
            assert mock_parse.call_count == 1, "成功时不应重试"

    def test_retry_with_backoff_delay(self):
        """RED: 重试应该有延迟"""
        config = {
            'name': 'YouTube',
            'enabled': True,
            'feeds': []
        }
        collector = YouTubeRSSCollector(config)

        # 模拟需要重试的情况
        call_times = []
        def mock_parse(url):
            call_times.append(datetime.now())
            if len(call_times) < 3:
                raise Exception("Network error")
            return {'entries': []}

        with patch('collectors.youtube_rss_collector.feedparser.parse', side_effect=mock_parse):
            with patch('time.sleep') as mock_sleep:  # 模拟 sleep
                collector._fetch_with_retry('https://test.com', max_retries=3, backoff=1.0)
                # 验证有调用 sleep（延迟）
                assert mock_sleep.called, "重试应该有延迟"

    def test_youtube_collector_uses_retry_in_collect(self):
        """RED: collect 方法应该使用重试机制"""
        config = {
            'name': 'YouTube',
            'enabled': True,
            'feeds': [
                {
                    'id': 'cnbc',
                    'name': 'CNBC',
                    'channel_id': 'TEST',
                    'url': 'https://test.com',
                    'enabled': True
                }
            ]
        }
        collector = YouTubeRSSCollector(config)

        # 模拟 _fetch_with_retry 被调用
        with patch.object(collector, '_fetch_with_retry', return_value={'entries': []}) as mock_retry:
            items = collector.collect(hours=24)
            # 应该使用重试机制
            assert mock_retry.called, "collect 应该调用 _fetch_with_retry"
