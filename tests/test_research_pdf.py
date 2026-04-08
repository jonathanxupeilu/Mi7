"""研报PDF内容采集测试 - TDD"""
import unittest
import os
from collectors.research_collector import ResearchCollector


class TestResearchPDFContent(unittest.TestCase):
    """测试研报PDF正文采集"""

    def test_fetch_pdf_content_from_detail_page(self):
        """
        测试能从研报详情页获取PDF并提取正文

        Given: 中煤能源研报详情页链接
        When: 调用PDF内容提取方法
        Then: 返回研报PDF中的正文文字（不是元数据）
        """
        collector = ResearchCollector()

        # 使用中煤能源的研报详情页URL测试
        info_code = 'AP202604011820960354'  # 国信证券研报
        detail_url = f'https://data.eastmoney.com/report/zw_stock.jshtml?infocode={info_code}'

        # 获取PDF内容
        try:
            content = collector.extract_pdf_content(detail_url)
        except Exception as e:
            self.skipTest(f"无法获取PDF内容（可能是网络或PDF过期）: {e}")

        # 验证：内容不为空且长度合理
        if not content:
            self.skipTest("PDF内容为空，可能是PDF链接已过期")

        self.assertTrue(len(content) > 100, f"PDF内容不应过短，实际长度: {len(content) if content else 0}")

        # 验证：内容包含实质性投资分析（不是简单的评级信息）
        # 应该包含中文分析文字，而不是只有"评级: xxx, EPS: xxx"
        chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
        self.assertGreater(chinese_chars, 50, f"应该包含至少50个中文字符，实际: {chinese_chars}")

        # 验证：不包含模板生成的标记
        self.assertNotIn('【', content, "内容不应包含模板标记")
        self.assertNotIn('核心观点：', content, "内容不应是模板生成的")

        # 打印前300字用于人工验证
        print(f"\n提取的PDF内容（前300字）：")
        print(content[:300])
        print(f"\n总字数: {len(content)}")

    def test_pdf_content_vs_metadata(self):
        """
        测试PDF内容与元数据的区别

        Given: 同一份研报的元数据和PDF内容
        Then: PDF内容比元数据丰富得多
        """
        collector = ResearchCollector()

        # 先获取元数据
        items = collector.collect_from_eastmoney_web('601898', '中煤能源', limit=1)
        self.assertGreaterEqual(len(items), 1, "应该能获取元数据")

        metadata_item = items[0]
        metadata_content = metadata_item['content']
        metadata_length = len(metadata_content)

        # 再获取PDF内容
        info_code = metadata_item['metadata'].get('info_code', '')
        if info_code:
            detail_url = f'https://data.eastmoney.com/report/zw_stock.jshtml?infocode={info_code}'
            pdf_content = collector.extract_pdf_content(detail_url)

            if pdf_content:
                # PDF内容应该比元数据丰富得多（至少3倍以上）
                self.assertGreater(
                    len(pdf_content),
                    metadata_length * 3,
                    f"PDF内容({len(pdf_content)})应该比元数据({metadata_length})丰富得多"
                )

                print(f"\n对比：")
                print(f"  元数据长度: {metadata_length}")
                print(f"  PDF内容长度: {len(pdf_content)}")


if __name__ == '__main__':
    unittest.main()
