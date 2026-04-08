"""项目数据源可用性验证测试"""
import pytest
import feedparser
import ssl
import yaml
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.rss_collector import RSSCollector
from collectors.youtube_rss_collector import YouTubeRSSCollector

ssl._create_default_https_context = ssl._create_unverified_context


def load_sources_config():
    """加载项目配置的源"""
    config_path = Path(__file__).parent.parent / "config" / "sources.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class TestProjectSources:
    """验证项目配置的数据源"""

    def test_hackernews_rss_available(self):
        """Hacker News RSS 应该可用"""
        feed = feedparser.parse("https://hnrss.org/frontpage")
        assert feed.entries, "Hacker News 返回空"
        assert len(feed.entries) > 0, "Hacker News 无条目"
        print(f"\nHacker News: {len(feed.entries)} 条")
        print(f"最新: {feed.entries[0].title[:50]}")

    def test_yahoo_finance_rss_available(self):
        """Yahoo Finance RSS 应该可用"""
        feed = feedparser.parse("https://finance.yahoo.com/news/rssindex")
        # 网络可能不稳定，跳过而非失败
        if not feed.entries:
            pytest.skip("Yahoo Finance RSS 暂时不可用（网络问题）")
        assert len(feed.entries) > 0, "Yahoo Finance 无条目"
        print(f"\nYahoo Finance: {len(feed.entries)} 条")
        print(f"最新: {feed.entries[0].title[:50]}")

    def test_youtube_cnbc_available(self):
        """CNBC YouTube RSS 应该可用（带重试）"""
        from collectors.youtube_rss_collector import YouTubeRSSCollector

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

        # 验证重试机制存在
        assert hasattr(collector, '_fetch_with_retry'), "应该有重试方法"

        # 尝试采集
        items = collector.collect(hours=168)  # 7天
        print(f"\nYouTube CNBC: {len(items)} videos")

        if items:
            print(f"最新: {items[0]['title'][:50]}...")
            assert 'source' in items[0]
            assert items[0]['source'] == 'CNBC'
        else:
            pytest.skip("YouTube CNBC 暂时不可用（可能被限制）")

    def test_rss_collector_works_with_hackernews(self):
        """RSSCollector 应该能采集 Hacker News"""
        config = {
            'name': 'HNRSS',
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

        assert isinstance(items, list)
        print(f"\n采集到 {len(items)} 条 HN 内容（24小时内）")

        if items:
            assert 'title' in items[0]
            assert 'url' in items[0]
            assert 'source' in items[0]
            print(f"第一条: {items[0]['title'][:50]}...")
            print(f"来源: {items[0]['source']}")
            print(f"URL: {items[0]['url'][:60]}...")

    def test_rss_collector_works_with_yahoo_finance(self):
        """RSSCollector 应该能采集 Yahoo Finance"""
        config = {
            'name': 'YahooFinance',
            'enabled': True,
            'feeds': [
                {
                    'id': 'yahoo',
                    'name': 'Yahoo Finance',
                    'url': 'https://finance.yahoo.com/news/rssindex',
                    'enabled': True
                }
            ]
        }
        collector = RSSCollector(config)
        items = collector.collect(hours=24)

        assert isinstance(items, list)
        print(f"\n采集到 {len(items)} 条 Yahoo Finance 内容（24小时内）")

        if items:
            print(f"第一条: {items[0]['title'][:50]}...")

    def test_collector_returns_proper_data_structure(self):
        """采集器返回的数据结构应该正确"""
        config = {
            'name': 'Test',
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

        if not items:
            pytest.skip("无数据可验证结构")

        item = items[0]
        required_fields = ['title', 'content', 'url', 'source', 'source_type',
                          'published_at', 'collected_at', 'priority']

        for field in required_fields:
            assert field in item, f"缺少字段: {field}"

        print(f"\n数据结构验证通过")
        print(f"所有必需字段: {required_fields}")


class TestDataQuality:
    """数据质量测试"""

    def test_hackernews_entries_have_url(self):
        """HN 条目应该有 URL"""
        feed = feedparser.parse("https://hnrss.org/frontpage")
        if not feed.entries:
            pytest.skip("无条目")

        for entry in feed.entries[:5]:
            assert entry.link, f"条目缺少 URL: {entry.get('title', 'N/A')}"

    def test_hackernews_entries_have_timestamp(self):
        """HN 条目应该有时间戳"""
        feed = feedparser.parse("https://hnrss.org/frontpage")
        if not feed.entries:
            pytest.skip("无条目")

        for entry in feed.entries[:5]:
            has_time = hasattr(entry, 'published_parsed') or hasattr(entry, 'updated_parsed')
            assert has_time, f"条目缺少时间戳: {entry.get('title', 'N/A')}"

    def test_data_freshness(self):
        """数据应该是最近更新的"""
        feed = feedparser.parse("https://hnrss.org/frontpage")
        if not feed.entries:
            pytest.skip("无条目")

        entry = feed.entries[0]
        if hasattr(entry, 'published_parsed'):
            pub_time = datetime(*entry.published_parsed[:6])
            age = datetime.now() - pub_time
            print(f"\n最新条目年龄: {age}")
            assert age.days < 1, f"最新条目超过1天未更新: {age}"


class TestNitterSource:
    """Nitter 源测试"""

    def test_nitter_instance_available(self):
        """Nitter 实例应该可用"""
        feed = feedparser.parse("https://nitter.net/elonmusk/rss")

        # 检查是否被限速
        if feed.get('status') == 429:
            pytest.skip("Nitter 速率限制 (429)")

        assert feed.entries, "Nitter 返回空"
        assert len(feed.entries) > 0, "Nitter 无条目"
        print(f"\nNitter: {len(feed.entries)} 条推文")
        print(f"最新: {feed.entries[0].title[:50]}...")

    def test_nitter_collector_integration(self):
        """NitterCollector 应该能采集 Twitter - 可选测试"""
        from collectors.nitter_collector import NitterCollector

        # 检查配置
        config = load_sources_config()
        if not config['sources'].get('nitter', {}).get('enabled', False):
            pytest.skip("Nitter 在配置中未启用")

        nitter_config = config['sources']['nitter']
        collector = NitterCollector(nitter_config)
        items = collector.collect(hours=24)

        assert isinstance(items, list)
        print(f"\n采集到 {len(items)} 条推文")

        if items:
            print(f"第一条: {items[0]['title'][:50]}...")
            assert 'source' in items[0]
            assert 'Twitter' in items[0]['source']
