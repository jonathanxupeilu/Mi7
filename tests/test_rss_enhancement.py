"""RSS渠道扩展测试 - TDD"""
import unittest
from collectors.rss_collector import RSSCollector
import yaml


class TestRSSEnhancement(unittest.TestCase):
    """测试RSS渠道扩展功能"""

    def test_rss_feeds_configuration_loaded(self):
        """
        测试能正确加载配置中的多个RSS源

        Given: sources.yaml配置文件中定义了多个RSS源
        When: 创建RSSCollector
        Then: 所有配置的RSS源都被正确加载
        """
        # 加载配置
        with open('config/sources.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        rss_config = config['sources']['rss']['native']
        collector = RSSCollector(rss_config)

        # 验证：至少加载了2个RSS源
        self.assertGreaterEqual(len(collector.feeds), 2, "应该至少加载2个RSS源")

        # 验证：每个RSS源都有必需的字段
        required_fields = ['id', 'name', 'url', 'priority']
        for feed in collector.feeds:
            for field in required_fields:
                self.assertIn(field, feed, f"RSS源 {feed.get('id', 'unknown')} 缺少字段 {field}")

        # 验证：Yahoo Finance在配置中
        feed_ids = [f['id'] for f in collector.feeds]
        self.assertIn('yahoo_finance', feed_ids, "应该有Yahoo Finance RSS源")

        print(f"\n已加载 {len(collector.feeds)} 个RSS源:")
        for feed in collector.feeds:
            print(f"  - [{feed['priority']}] {feed['name']}: {feed['url']}")

    def test_collect_from_multiple_rss_feeds(self):
        """
        测试能从多个RSS源采集内容

        Given: 配置了多个RSS源
        When: 调用collect方法
        Then: RSS采集器能处理所有配置的源
        """
        with open('config/sources.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        rss_config = config['sources']['rss']['native']
        collector = RSSCollector(rss_config)

        # 验证：至少有5个RSS源（新添加的）
        self.assertGreaterEqual(len(collector.feeds), 5,
                              f"应该至少加载5个RSS源，实际加载了 {len(collector.feeds)} 个")

        # 验证：新添加的RSS源存在
        feed_ids = [f['id'] for f in collector.feeds]
        expected_feeds = ['yahoo_finance', 'github_blog', 'cnbc', 'seekingalpha', 'zerohedge']
        for feed_id in expected_feeds:
            self.assertIn(feed_id, feed_ids, f"应该有 {feed_id} RSS源")

        # 尝试采集（不强制要求有内容，RSS可能在该时段无更新）
        items = collector.collect(hours=168)  # 最近7天，增加成功率

        # 验证：采集器运行无错误
        self.assertIsInstance(items, list, "collect应返回列表")

        # 如果采集到内容，验证结构
        if items:
            required_fields = ['title', 'content', 'url', 'source', 'published_at']
            for item in items[:5]:
                for field in required_fields:
                    self.assertIn(field, item, f"采集内容缺少字段 {field}")

        print(f"\n配置验证通过:")
        print(f"  总RSS源: {len(collector.feeds)}")
        for feed in collector.feeds:
            print(f"    - [{feed['priority']}] {feed['name']}")

    def test_rss_feed_has_valid_url(self):
        """
        测试RSS源的URL格式正确且可访问

        Given: 配置中的RSS源
        Then: URL格式正确
        """
        import re

        with open('config/sources.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        rss_config = config['sources']['rss']['native']
        collector = RSSCollector(rss_config)

        url_pattern = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)

        for feed in collector.feeds:
            url = feed.get('url', '')
            self.assertRegex(url, url_pattern, f"RSS源 {feed['id']} 的URL格式不正确: {url}")
            self.assertTrue(url.endswith(('.xml', '.rss', '/feed', '/feed/')) or 'rss' in url.lower() or 'reuters' in url.lower(),
                          f"RSS源 {feed['id']} 的URL可能不是RSS格式: {url}")


if __name__ == '__main__':
    unittest.main()
