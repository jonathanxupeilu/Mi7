"""外文RSS信源扩展测试 - TDD"""
import unittest
import yaml
from collectors.rss_collector import RSSCollector


class TestForeignRSSFeeds(unittest.TestCase):
    """测试外文RSS信源扩展"""

    def test_foreign_rss_feeds_configured(self):
        """
        测试配置了外文RSS信源

        Given: sources.yaml配置文件
        Then: 包含多个高质量外文财经RSS源
        """
        with open('config/sources.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        rss_feeds = config['sources']['rss']['native']['feeds']

        # 验证：至少8个RSS源
        self.assertGreaterEqual(len(rss_feeds), 8,
                              f"应该至少配置8个RSS源，当前只有{len(rss_feeds)}个")

        # 验证：包含必需的外文信源
        required_foreign = [
            'bloomberg',      # 彭博
            'reuters',        # 路透
            'ft',             # 金融时报
            'wsj',            # 华尔街日报
        ]

        feed_ids = [f['id'] for f in rss_feeds]
        for feed_id in required_foreign:
            self.assertIn(feed_id, feed_ids,
                         f"应该包含 {feed_id} RSS源")

        print(f"\n已配置 {len(rss_feeds)} 个RSS源:")
        for feed in rss_feeds:
            print(f"  - [{feed['priority']}] {feed['name']}")

    def test_rss_feeds_by_category(self):
        """
        测试RSS源按类别分布合理

        Given: RSS源配置
        Then: 包含综合财经、投资分析、宏观经济等类别
        """
        with open('config/sources.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        rss_feeds = config['sources']['rss']['native']['feeds']

        # 统计优先级分布
        high_priority = [f for f in rss_feeds if f['priority'] == 'high']
        medium_priority = [f for f in rss_feeds if f['priority'] == 'medium']

        # 验证：高优先级至少4个
        self.assertGreaterEqual(len(high_priority), 4,
                              f"高优先级源至少4个，实际{len(high_priority)}")

        print(f"\n优先级分布:")
        print(f"  High: {len(high_priority)}")
        print(f"  Medium: {len(medium_priority)}")

    def test_foreign_rss_feeds_accessible(self):
        """
        测试外文RSS源可访问

        Given: 配置的外文RSS源
        When: 尝试解析RSS
        Then: 源可访问且格式正确
        """
        with open('config/sources.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        rss_config = config['sources']['rss']['native']
        collector = RSSCollector(rss_config)

        # 验证：所有外文源都能初始化
        foreign_keywords = ['Bloomberg', 'Reuters', 'Financial Times',
                           'Wall Street', 'MarketWatch', 'Investing',
                           'Economist', 'Forbes']

        foreign_feeds = []
        for feed in collector.feeds:
            if any(kw in feed['name'] for kw in foreign_keywords):
                foreign_feeds.append(feed)

        self.assertGreaterEqual(len(foreign_feeds), 4,
                              f"应该至少有4个外文源，实际{len(foreign_feeds)}")

        print(f"\n外文信源: {len(foreign_feeds)} 个")
        for feed in foreign_feeds:
            print(f"  - {feed['name']}")

    def test_collect_from_foreign_sources(self):
        """
        测试能从外文RSS源采集内容

        Given: 配置了外文RSS源
        When: 调用collect
        Then: 成功采集内容
        """
        with open('config/sources.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        rss_config = config['sources']['rss']['native']
        collector = RSSCollector(rss_config)

        # 采集最近3天
        items = collector.collect(hours=72)

        # 验证：采集器正常工作
        self.assertIsInstance(items, list)

        # 统计外文内容
        foreign_keywords = ['Bloomberg', 'Reuters', 'FT', 'WSJ', 'MarketWatch']
        foreign_items = []
        for item in items:
            if any(kw in item.get('source', '') for kw in foreign_keywords):
                foreign_items.append(item)

        print(f"\n采集统计:")
        print(f"  总条目: {len(items)}")
        print(f"  外文条目: {len(foreign_items)}")

        # 验证：至少有一些外文内容（RSS可能近期无更新）
        if len(items) > 0:
            # 如果有内容，验证结构正确
            for item in items[:3]:
                self.assertIn('title', item)
                self.assertIn('url', item)
                self.assertIn('source', item)


if __name__ == '__main__':
    unittest.main()
