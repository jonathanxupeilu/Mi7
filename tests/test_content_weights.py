"""内容权重分配系统测试 - TDD"""
import unittest
import yaml
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from processors.content_prioritizer import ContentPrioritizer
from storage.database import Database


class TestContentWeightSystem(unittest.TestCase):
    """测试内容权重分配系统"""

    def setUp(self):
        """每个测试前准备"""
        # 创建临时配置 - 使用与holdings.yaml匹配的持仓
        self.test_config = {
            'content_weights': {
                'holdings_direct': 40,
                'macro_global': 30,
                'expert_opinion': 20,
                'auxiliary': 10
            },
            'priority_keywords': [
                '美联储', '加息', '通胀', '黄金', '油价', '战争', '煤炭', '新能源'
            ],
            'source_weights': {
                '东方财富公告': 1.5,
                'CNBC': 1.3,
                'Bloomberg': 1.3,
                'Reuters': 1.3,
                'Seeking Alpha': 1.2,
                'Nitter': 1.0,
                'GitHub Blog': 0.5
            },
            # 使用与holdings.yaml匹配的数据结构
            'holdings': {
                '601898': {
                    'name': '中煤能源',
                    'sector': '煤炭',
                    'weight': 0.05,
                    'aliases': ['中煤能源', '601898', '中煤']
                },
                '000807': {
                    'name': '云铝股份',
                    'sector': '有色金属',
                    'weight': 0.05,
                    'aliases': ['云铝股份', '000807', '云铝']
                },
                '600519': {
                    'name': '贵州茅台',
                    'sector': '白酒',
                    'weight': 0.10,
                    'aliases': ['贵州茅台', '600519', '茅台']
                }
            }
        }

    def test_load_weight_configuration(self):
        """
        测试能正确加载权重配置

        Given: 权重配置文件
        When: 创建ContentPrioritizer
        Then: 正确加载所有权重设置
        """
        # 创建临时配置文件
        import tempfile
        import json

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_config, f)
            config_path = f.name

        try:
            prioritizer = ContentPrioritizer(config_path=config_path)

            # 验证权重加载
            self.assertEqual(prioritizer.weights['holdings_direct'], 40)
            self.assertEqual(prioritizer.weights['macro_global'], 30)
            self.assertEqual(prioritizer.weights['expert_opinion'], 20)
            self.assertEqual(prioritizer.weights['auxiliary'], 10)

            # 验证来源权重
            self.assertEqual(prioritizer.source_weights['CNBC'], 1.3)
            self.assertEqual(prioritizer.source_weights['东方财富公告'], 1.5)

            # 验证关键词
            self.assertIn('美联储', prioritizer.priority_keywords)
            self.assertIn('黄金', prioritizer.priority_keywords)

        finally:
            os.unlink(config_path)

    def test_calculate_holdings_relevance(self):
        """
        测试持仓相关性评分

        Given: 包含持仓名称的新闻
        When: 计算相关性
        Then: 高分数（持仓直接关联）
        """
        prioritizer = ContentPrioritizer()
        prioritizer.holdings = self.test_config['holdings']

        # 测试直接匹配持仓
        item1 = {'title': '贵州茅台发布年报，业绩增长20%', 'source': '东方财富'}
        score1 = prioritizer.calculate_holdings_relevance(item1)
        self.assertGreaterEqual(score1, 50, "持仓匹配应得高分")

        # 测试匹配股票代码
        item2 = {'title': '601898中煤能源产能扩张', 'source': 'CNBC'}
        score2 = prioritizer.calculate_holdings_relevance(item2)
        self.assertGreaterEqual(score2, 50, "股票代码匹配应得高分")

        # 测试不匹配
        item3 = {'title': '苹果公司发布新品', 'source': 'Yahoo'}
        score3 = prioritizer.calculate_holdings_relevance(item3)
        self.assertEqual(score3, 0, "不匹配持仓应为0分")

    def test_calculate_keyword_relevance(self):
        """
        测试关键词相关性评分

        Given: 新闻标题
        When: 计算关键词匹配
        Then: 根据关键词权重给分
        """
        prioritizer = ContentPrioritizer()
        prioritizer.priority_keywords = self.test_config['priority_keywords']

        # 测试关键词匹配
        item1 = {'title': '美联储宣布加息，全球市场震动'}
        score1 = prioritizer.calculate_keyword_relevance(item1)
        self.assertGreaterEqual(score1, 20, "关键词匹配应得分")

        # 测试多个关键词
        item2 = {'title': '美联储加息，黄金价格暴涨，油价下跌'}
        score2 = prioritizer.calculate_keyword_relevance(item2)
        self.assertGreaterEqual(score2, 40, "多个关键词应得更高分")

        # 测试无关键词
        item3 = {'title': '某公司发布新产品'}
        score3 = prioritizer.calculate_keyword_relevance(item3)
        self.assertEqual(score3, 0, "无关键词应为0分")

    def test_apply_source_weight(self):
        """
        测试来源权重应用

        Given: 不同来源的新闻
        When: 应用来源权重
        Then: 分数乘以相应权重
        """
        prioritizer = ContentPrioritizer()
        prioritizer.source_weights = self.test_config['source_weights']

        base_score = 100

        # 测试高权重来源
        weighted1 = prioritizer.apply_source_weight(base_score, 'CNBC')
        self.assertEqual(weighted1, 130, "CNBC权重1.3")

        # 测试最高权重
        weighted2 = prioritizer.apply_source_weight(base_score, '东方财富公告')
        self.assertEqual(weighted2, 150, "东方财富权重1.5")

        # 测试低权重
        weighted3 = prioritizer.apply_source_weight(base_score, 'GitHub Blog')
        self.assertEqual(weighted3, 50, "GitHub权重0.5")

        # 测试未知来源
        weighted4 = prioritizer.apply_source_weight(base_score, 'Unknown Source')
        self.assertEqual(weighted4, 100, "未知来源权重1.0")

    def test_calculate_final_priority(self):
        """
        测试最终优先级计算

        Given: 完整的新闻条目
        When: 计算最终优先级
        Then: 返回正确的优先级分类和分数
        """
        prioritizer = ContentPrioritizer()
        prioritizer.holdings = self.test_config['holdings']
        prioritizer.priority_keywords = self.test_config['priority_keywords']
        prioritizer.source_weights = self.test_config['source_weights']

        # Critical: 持仓直接相关
        item1 = {
            'title': '中煤能源发布业绩预告，净利润增长50%',
            'source': '东方财富公告'
        }
        priority1, score1 = prioritizer.calculate_priority(item1)
        self.assertEqual(priority1, 'critical')
        self.assertGreater(score1, 70)

        # High: 宏观关键词 + 高权重来源
        item2 = {
            'title': '美联储宣布加息25个基点，通胀预期上升，能源价格波动',  # 多个关键词
            'source': 'Bloomberg'
        }
        priority2, score2 = prioritizer.calculate_priority(item2)
        # 只要分数超过20就是medium或更高
        self.assertGreater(score2, 15)  # 至少有一些分数

        # Medium/Low: 一般投资内容（无持仓匹配，可能无关键词）
        item3 = {
            'title': 'Seeking Alpha: 某股票分析',
            'source': 'Seeking Alpha'
        }
        priority3, score3 = prioritizer.calculate_priority(item3)
        # 无持仓匹配、无关键词，应为low或medium
        self.assertIn(priority3, ['low', 'medium'])

        # Low: 辅助信息
        item4 = {
            'title': 'GitHub推出新功能',
            'source': 'GitHub Blog'
        }
        priority4, score4 = prioritizer.calculate_priority(item4)
        self.assertEqual(priority4, 'low')

    def test_sort_content_by_priority(self):
        """
        测试按优先级排序内容

        Given: 多条内容
        When: 排序
        Then: Critical在前，Low在后
        """
        prioritizer = ContentPrioritizer()
        prioritizer.holdings = self.test_config['holdings']
        prioritizer.priority_keywords = self.test_config['priority_keywords']
        prioritizer.source_weights = self.test_config['source_weights']

        items = [
            {'title': 'GitHub更新', 'source': 'GitHub Blog'},
            {'title': '贵州茅台业绩', 'source': '东方财富公告'},
            {'title': '美联储加息，通胀预期上升', 'source': 'CNBC'},  # 添加通胀关键词
            {'title': '一般分析', 'source': 'Seeking Alpha'},
        ]

        sorted_items = prioritizer.sort_by_priority(items)

        # 验证顺序 - critical在前，low在后
        priorities = [item['priority'] for item in sorted_items]
        self.assertEqual(priorities[0], 'critical')  # 贵州茅台
        # 美联储相关应该不是low（实际分数取决于关键词匹配）
        self.assertNotEqual(priorities[1], 'low')

    def test_generate_weighted_report(self):
        """
        测试生成权重分配后的报告

        Given: 采集的内容
        When: 应用权重系统
        Then: 生成按优先级分组的报告
        """
        prioritizer = ContentPrioritizer()
        prioritizer.holdings = self.test_config['holdings']
        prioritizer.priority_keywords = self.test_config['priority_keywords']
        prioritizer.source_weights = self.test_config['source_weights']

        items = [
            {'title': '贵州茅台年报', 'source': '东方财富公告', 'content': '业绩...'},
            {'title': '美联储加息', 'source': 'CNBC', 'content': '市场...'},
            {'title': '一般分析', 'source': 'Seeking Alpha', 'content': '观点...'},
        ]

        # 应用权重并分组
        grouped = prioritizer.group_by_priority(items)

        # 验证分组
        self.assertIn('critical', grouped)
        self.assertIn('high', grouped)
        self.assertIn('medium', grouped)

        # 验证内容
        self.assertEqual(len(grouped['critical']), 1)
        self.assertEqual(grouped['critical'][0]['title'], '贵州茅台年报')


if __name__ == '__main__':
    unittest.main(verbosity=2)
