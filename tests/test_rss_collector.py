"""RSSCollector 单元测试 - TDD"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from collectors.rss_collector import RSSCollector


class TestRSSCollector:
    """测试 RSSCollector"""

    def test_rss_collector_inherits_from_base(self):
        """RED: RSSCollector 应该继承自 BaseCollector"""
        config = {'name': 'RSS', 'enabled': True, 'feeds': []}
        collector = RSSCollector(config)
        from collectors.base_collector import BaseCollector
        assert isinstance(collector, BaseCollector)

    def test_rss_collector_stores_feeds_config(self):
        """RED: RSSCollector 应该存储 feeds 配置"""
        feeds = [
            {'id': 'feed1', 'name': 'Feed 1', 'url': 'https://feed1.com', 'enabled': True},
            {'id': 'feed2', 'name': 'Feed 2', 'url': 'https://feed2.com', 'enabled': False}
        ]
        config = {'name': 'RSS', 'enabled': True, 'feeds': feeds}
        collector = RSSCollector(config)
        assert len(collector.feeds) == 2
        assert collector.feeds[0]['id'] == 'feed1'

    def test_collect_skips_disabled_feeds(self):
        """RED: collect() 应该跳过禁用的 feeds"""
        feeds = [
            {'id': 'feed1', 'name': 'Feed 1', 'url': 'https://feed1.com', 'enabled': False},
        ]
        config = {'name': 'RSS', 'enabled': True, 'feeds': feeds}
        collector = RSSCollector(config)

        # Mock feedparser 避免网络请求
        with patch('collectors.rss_collector.feedparser') as mock_feedparser:
            items = collector.collect(hours=24)
            # 禁用 feed 不应该被解析
            mock_feedparser.parse.assert_not_called()
            assert items == []

    def test_parse_feed_filters_by_time(self):
        """RED: _parse_feed 应该根据时间过滤条目"""
        feeds = [{'id': 'feed1', 'name': 'Test Feed', 'url': 'https://test.com', 'enabled': True}]
        config = {'name': 'RSS', 'enabled': True, 'feeds': feeds}
        collector = RSSCollector(config)

        # 创建模拟条目类
        class MockEntry:
            def __init__(self, title, summary, link, published_parsed):
                self.title = title
                self.summary = summary
                self.link = link
                self.published_parsed = published_parsed

            def get(self, key, default=None):
                return getattr(self, key, default)

        # 一个在 cutoff 之前，一个在之后
        old_time = datetime.now() - timedelta(hours=48)
        recent_time = datetime.now() - timedelta(hours=12)

        mock_entry_old = MockEntry('Old Entry', 'Old content', 'https://test.com/old', old_time.timetuple())
        mock_entry_recent = MockEntry('Recent Entry', 'Recent content', 'https://test.com/recent', recent_time.timetuple())

        mock_feed = Mock()
        mock_feed.entries = [mock_entry_old, mock_entry_recent]

        with patch('collectors.rss_collector.feedparser.parse', return_value=mock_feed):
            cutoff_time = datetime.now() - timedelta(hours=24)
            items = collector._parse_feed(feeds[0], cutoff_time)

            # 应该只返回最近的条目
            assert len(items) == 1
            assert items[0]['title'] == 'Recent Entry'

    def test_parse_feed_handles_missing_published_time(self):
        """RED: _parse_feed 应该处理缺少 published_parsed 的情况"""
        feeds = [{'id': 'feed1', 'name': 'Test Feed', 'url': 'https://test.com', 'enabled': True}]
        config = {'name': 'RSS', 'enabled': True, 'feeds': feeds}
        collector = RSSCollector(config)

        mock_entry = {
            'title': 'No Date Entry',
            'summary': 'Content',
            'link': 'https://test.com/no-date',
            # 没有 published_parsed 字段
        }

        mock_feed = Mock()
        mock_feed.entries = [mock_entry]

        with patch('collectors.rss_collector.feedparser.parse', return_value=mock_feed):
            cutoff_time = datetime.now() - timedelta(hours=24)
            items = collector._parse_feed(feeds[0], cutoff_time)

            # 应该返回条目，使用当前时间作为 published_at
            assert len(items) == 1
            assert items[0]['title'] == 'No Date Entry'

    def test_get_published_time_prefers_published_over_updated(self):
        """RED: _get_published_time 应该优先使用 published_parsed"""
        config = {'name': 'RSS', 'enabled': True, 'feeds': []}
        collector = RSSCollector(config)

        published_time = datetime(2024, 1, 1, 12, 0, 0)
        updated_time = datetime(2024, 1, 2, 12, 0, 0)

        mock_entry = Mock()
        mock_entry.published_parsed = published_time.timetuple()
        mock_entry.updated_parsed = updated_time.timetuple()

        result = collector._get_published_time(mock_entry)
        assert result == published_time

    def test_get_published_time_falls_back_to_updated(self):
        """RED: 没有 published_parsed 时应该回退到 updated_parsed"""
        config = {'name': 'RSS', 'enabled': True, 'feeds': []}
        collector = RSSCollector(config)

        updated_time = datetime(2024, 1, 2, 12, 0, 0)

        mock_entry = Mock()
        del mock_entry.published_parsed
        mock_entry.updated_parsed = updated_time.timetuple()

        result = collector._get_published_time(mock_entry)
        assert result == updated_time

    def test_collect_returns_normalized_items(self):
        """RED: collect() 应该返回规范化的条目"""
        feeds = [{'id': 'feed1', 'name': 'Test Feed', 'url': 'https://test.com', 'enabled': True}]
        config = {'name': 'RSS', 'enabled': True, 'feeds': feeds, 'priority': 'high'}
        collector = RSSCollector(config)

        mock_entry = {
            'title': 'Test Entry',
            'summary': 'Test summary',
            'link': 'https://test.com/entry',
            'published_parsed': datetime.now().timetuple(),
        }

        mock_feed = Mock()
        mock_feed.entries = [mock_entry]

        with patch('collectors.rss_collector.feedparser.parse', return_value=mock_feed):
            items = collector.collect(hours=24)

            assert len(items) == 1
            assert items[0]['title'] == 'Test Entry'
            assert items[0]['content'] == 'Test summary'
            assert items[0]['url'] == 'https://test.com/entry'
            assert items[0]['source'] == 'Test Feed'
            assert items[0]['source_type'] == 'RSSCollector'
            assert items[0]['priority'] == 'high'
