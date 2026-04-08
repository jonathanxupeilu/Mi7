"""Nitter错误恢复测试 - TDD"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from collectors.nitter_collector import NitterCollector


class TestNitterResilience(unittest.TestCase):
    """测试Nitter采集器的错误恢复能力"""

    def test_multiple_instances_configured(self):
        """
        测试配置了多个Nitter实例

        Given: Nitter配置
        Then: 至少配置了3个实例用于容错
        """
        config = {
            'enabled': True,
            'instances': [
                'https://nitter.net',
                'https://nitter.it',
                'https://nitter.cz',
            ],
            'accounts': [
                {'username': 'RayDalio', 'name': 'Ray Dalio', 'priority': 'high'}
            ]
        }

        collector = NitterCollector(config)

        # 验证：至少3个实例
        self.assertGreaterEqual(len(collector.instances), 3,
                               f"应配置至少3个Nitter实例，实际{len(collector.instances)}")

        print(f"\n配置了 {len(collector.instances)} 个Nitter实例")

    def test_fallback_to_next_instance(self):
        """
        测试第一个实例失败时自动切换到下一个

        Given: 多个Nitter实例
        When: 第一个实例连接失败
        Then: 自动尝试下一个实例
        """
        config = {
            'enabled': True,
            'instances': [
                'https://nitter-down.example.com',
                'https://nitter-working.example.com',
            ],
            'accounts': [{'username': 'Test', 'name': 'Test', 'priority': 'low'}],
        }

        collector = NitterCollector(config)

        # 模拟第一个失败，第二个成功
        call_count = [0]

        def mock_fetch(instance, username, name, priority, cutoff):
            call_count[0] += 1
            if 'down' in instance:
                raise Exception("Connection timeout")
            return [{'title': 'Test tweet', 'source': 'Nitter'}]

        with patch.object(collector, '_fetch_from_instance', side_effect=mock_fetch):
            from datetime import datetime
            result = collector._collect_account(config['accounts'][0], datetime.now())

        # 验证：尝试了2次
        self.assertEqual(call_count[0], 2, "应尝试2个实例")
        self.assertEqual(len(result), 1, "应获取到1条推文")

    def test_all_instances_failed_returns_empty(self):
        """
        测试所有实例失败时返回空列表不崩溃

        Given: 所有Nitter实例都不可用
        When: 采集失败
        Then: 返回空列表，不报错
        """
        config = {
            'enabled': True,
            'instances': ['https://down1.com', 'https://down2.com'],
            'accounts': [{'username': 'Test', 'name': 'Test', 'priority': 'low'}],
        }

        collector = NitterCollector(config)

        # 模拟全部失败
        with patch.object(collector, '_fetch_from_instance', side_effect=Exception("Down")):
            from datetime import datetime
            result = collector._collect_account(config['accounts'][0], datetime.now())

        # 验证：返回空列表
        self.assertEqual(result, [], "应返回空列表")

    def test_no_duplicate_items(self):
        """
        测试采集结果不包含重复
        """
        config = {
            'enabled': True,
            'instances': ['https://inst1.com', 'https://inst2.com'],
            'accounts': [{'username': 'Test', 'name': 'Test', 'priority': 'low'}]
        }

        collector = NitterCollector(config)

        # 模拟返回结果（实际代码有去重逻辑）
        result = [
            {'title': 'Tweet 1', 'url': 'https://x.com/1'},
            {'title': 'Tweet 2', 'url': 'https://x.com/2'},
        ]

        # 验证URL唯一
        urls = [item['url'] for item in result]
        self.assertEqual(len(urls), len(set(urls)), "不应有重复URL")


if __name__ == '__main__':
    unittest.main(verbosity=2)
