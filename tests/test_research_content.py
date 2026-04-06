"""研报内容采集测试 - TDD"""
import unittest
from datetime import datetime
from collectors.research_collector import ResearchCollector


class TestResearchContent(unittest.TestCase):
    """测试研报内容采集"""

    def test_fetch_full_research_content(self):
        """
        测试能获取研报的完整内容（不仅是标题）

        Given: 中煤能源(601898)的股票代码
        When: 调用内容采集方法
        Then: 返回的研报包含完整内容摘要
        """
        collector = ResearchCollector()

        # 采集中煤能源研报
        items = collector.collect_from_eastmoney_web('601898', '中煤能源', limit=1)

        # 验证：至少采集到1条
        self.assertGreaterEqual(len(items), 1, "应该至少采集到1条研报")

        # 验证：内容字段不为空
        item = items[0]
        self.assertIn('title', item, "研报应有标题")
        self.assertIn('content', item, "研报应有内容")
        self.assertIn('url', item, "研报应有原文链接")

        # 验证：内容包含关键信息（评级、预测等）
        content = item['content']
        self.assertTrue(
            len(content) > 10,
            f"研报内容不应过短，实际内容: {content}"
        )

        # 验证：metadata包含评级信息
        metadata = item.get('metadata', {})
        self.assertIn('rating', metadata, "metadata应包含评级信息")
        self.assertIn('eps_forecast', metadata, "metadata应包含EPS预测")

        # 打印采集到的内容（用于人工验证）
        print(f"\n采集到研报:")
        print(f"  标题: {item['title']}")
        print(f"  券商: {item['source']}")
        print(f"  评级: {metadata.get('rating', 'N/A')}")
        print(f"  内容预览: {content[:100]}...")
        print(f"  原文链接: {item['url']}")

    def test_research_content_structure(self):
        """
        测试研报内容的数据结构完整性

        Given: 采集研报数据
        Then: 所有必需字段都存在且格式正确
        """
        collector = ResearchCollector()
        items = collector.collect_from_eastmoney_web('601898', '中煤能源', limit=2)

        for item in items:
            # 必需字段检查
            required_fields = ['title', 'content', 'source', 'published_at', 'url', 'metadata']
            for field in required_fields:
                self.assertIn(field, item, f"研报数据缺少字段: {field}")

            # metadata必需字段
            metadata = item['metadata']
            metadata_fields = ['stock_code', 'stock_name', 'info_type', 'broker', 'channel']
            for field in metadata_fields:
                self.assertIn(field, metadata, f"metadata缺少字段: {field}")

            # 类型检查
            self.assertIsInstance(item['title'], str)
            self.assertIsInstance(item['content'], str)
            self.assertIsInstance(item['published_at'], datetime)


if __name__ == '__main__':
    unittest.main()
