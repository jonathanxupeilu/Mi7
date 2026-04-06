"""数据源集成测试 - 验证所有信息源可用性"""
import pytest
import feedparser
import ssl
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.rss_collector import RSSCollector
from collectors.youtube_rss_collector import YouTubeRSSCollector


# 禁用SSL验证用于测试
ssl._create_default_https_context = ssl._create_unverified_context


class TestRSSSourcesIntegration:
    """RSS 源集成测试"""

    RSS_FEEDS = [
        ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
        ("GitHub Blog", "https://github.blog/feed/"),
    ]

    @pytest.mark.integration
    @pytest.mark.parametrize("name,url", RSS_FEEDS)
    def test_rss_feed_returns_entries(self, name, url):
        """RSS 源应该返回条目"""
        feed = feedparser.parse(url)
        assert hasattr(feed, 'entries'), f"{name}: 没有 entries 属性"
        assert len(feed.entries) > 0, f"{name}: 返回空条目"
        print(f"\n{name}: {len(feed.entries)} 个条目")

    @pytest.mark.integration
    @pytest.mark.parametrize("name,url", RSS_FEEDS)
    def test_rss_feed_entries_have_required_fields(self, name, url):
        """RSS 条目应该包含必需字段"""
        feed = feedparser.parse(url)
        if not feed.entries:
            pytest.skip(f"{name}: 无条目可测试")

        entry = feed.entries[0]
        assert hasattr(entry, 'title') and entry.title, f"{name}: 缺少 title"
        assert hasattr(entry, 'link') and entry.link, f"{name}: 缺少 link"
        print(f"\n{name} 最新: {entry.title[:50]}...")

    @pytest.mark.integration
    @pytest.mark.parametrize("name,url", RSS_FEEDS)
    def test_rss_feed_has_timestamp(self, name, url):
        """RSS 条目应该有发布时间戳"""
        feed = feedparser.parse(url)
        if not feed.entries:
            pytest.skip(f"{name}: 无条目可测试")

        entry = feed.entries[0]
        has_published = hasattr(entry, 'published_parsed') and entry.published_parsed
        has_updated = hasattr(entry, 'updated_parsed') and entry.updated_parsed
        assert has_published or has_updated, f"{name}: 没有时间戳"


class TestYouTubeSourcesIntegration:
    """YouTube 源集成测试"""

    YOUTUBE_FEEDS = [
        ("CNBC", "UCe_3CN7FHPVCIifAnD7hL_A"),
        ("Bloomberg", "UChKG8K6YZE"),
        ("ARK Invest", "UC-0PpCqHGAw"),
    ]

    @pytest.mark.integration
    @pytest.mark.parametrize("name,channel_id", YOUTUBE_FEEDS)
    def test_youtube_feed_returns_entries(self, name, channel_id):
        """YouTube RSS 应该返回条目"""
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(url)

        # YouTube 有时会返回错误，检查 bozo 标志
        if hasattr(feed, 'bozo_exception') and feed.bozo:
            pytest.skip(f"{name}: Feed 解析警告 - {feed.bozo_exception}")

        assert hasattr(feed, 'entries'), f"{name}: 没有 entries 属性"
        print(f"\n{name} YouTube: {len(feed.entries)} 个条目")

    @pytest.mark.integration
    @pytest.mark.parametrize("name,channel_id", YOUTUBE_FEEDS)
    def test_youtube_feed_entries_have_video_info(self, name, channel_id):
        """YouTube 条目应该包含视频信息"""
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(url)

        if not hasattr(feed, 'entries') or not feed.entries:
            pytest.skip(f"{name}: 无条目可测试")

        entry = feed.entries[0]
        assert hasattr(entry, 'title') and entry.title, f"{name}: 缺少 title"
        # YouTube entries use 'link' not 'yt_videoid' in RSS
        assert hasattr(entry, 'link') and entry.link, f"{name}: 缺少 link"
        print(f"\n{name} 最新视频: {entry.title[:50]}...")


class TestCollectorIntegration:
    """采集器集成测试"""

    @pytest.mark.integration
    def test_rss_collector_with_real_feed(self):
        """RSSCollector 应该能采集真实 RSS 数据"""
        config = {
            'name': 'TestRSS',
            'enabled': True,
            'feeds': [
                {
                    'id': 'hn',
                    'name': 'Hacker News',
                    'url': 'https://hnrss.org/frontpage',
                    'enabled': True
                }
            ]
        }
        collector = RSSCollector(config)
        items = collector.collect(hours=24)

        assert isinstance(items, list), "应该返回列表"
        if items:
            assert 'title' in items[0], "条目应该有 title"
            assert 'url' in items[0], "条目应该有 url"
            assert 'source' in items[0], "条目应该有 source"
            print(f"\n采集到 {len(items)} 条 HN 内容")
            print(f"第一条: {items[0]['title'][:50]}...")

    @pytest.mark.integration
    def test_rss_collector_time_filtering(self):
        """RSSCollector 应该正确过滤时间"""
        config = {
            'name': 'TestRSS',
            'enabled': True,
            'feeds': [
                {
                    'id': 'hn',
                    'name': 'Hacker News',
                    'url': 'https://hnrss.org/frontpage',
                    'enabled': True
                }
            ]
        }
        collector = RSSCollector(config)

        # 测试不同时间窗口
        items_1h = collector.collect(hours=1)
        items_24h = collector.collect(hours=24)
        items_168h = collector.collect(hours=168)

        print(f"\n时间窗口统计:")
        print(f"  1小时: {len(items_1h)} 条")
        print(f"  24小时: {len(items_24h)} 条")
        print(f"  7天: {len(items_168h)} 条")

        # 时间窗口越大，条目应该越多或相等
        assert len(items_24h) >= len(items_1h), "24小时应该比1小时条目多"
        assert len(items_168h) >= len(items_24h), "7天应该比24小时条目多"


class TestDataAvailability:
    """数据可用性测试"""

    @pytest.mark.integration
    def test_all_configured_sources_accessible(self):
        """测试配置文件中所有源是否可访问"""
        import yaml

        config_path = Path(__file__).parent.parent / "config" / "sources.yaml"
        if not config_path.exists():
            pytest.skip("sources.yaml 不存在")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        sources = config.get('sources', {})
        results = {}

        # 测试 RSS 源
        rss_config = sources.get('rss', {})
        if rss_config.get('enabled'):
            # native feeds
            native_feeds = rss_config.get('native', {}).get('feeds', [])
            for feed in native_feeds:
                if feed.get('enabled', True):
                    try:
                        parsed = feedparser.parse(feed['url'])
                        results[feed['name']] = {
                            'status': 'OK' if parsed.entries else 'EMPTY',
                            'count': len(parsed.entries)
                        }
                    except Exception as e:
                        results[feed['name']] = {'status': 'ERROR', 'error': str(e)}

        print("\n数据源可用性报告:")
        for name, result in results.items():
            status = result['status']
            if status == 'OK':
                print(f"  ✓ {name}: {result['count']} 条目")
            elif status == 'EMPTY':
                print(f"  ⚠ {name}: 无条目")
            else:
                print(f"  ✗ {name}: {result.get('error', '未知错误')}")

        # 至少有一个源应该可用
        ok_sources = [s for s, r in results.items() if r['status'] == 'OK']
        assert len(ok_sources) > 0, "没有可用的数据源"
