"""BaseCollector 单元测试 - TDD"""
import pytest
from datetime import datetime
from collectors.base_collector import BaseCollector


class TestBaseCollector:
    """测试 BaseCollector 基类"""

    def test_base_collector_is_abstract(self):
        """RED: BaseCollector 应该是抽象类，不能直接实例化"""
        config = {'name': 'Test', 'enabled': True}
        with pytest.raises(TypeError):
            BaseCollector(config)

    def test_concrete_collector_can_be_created(self):
        """RED: 具体采集器应该可以实例化"""
        class ConcreteCollector(BaseCollector):
            def collect(self, hours=24):
                return []

        config = {
            'name': 'TestCollector',
            'enabled': True,
            'priority': 'high'
        }
        collector = ConcreteCollector(config)
        assert collector.name == 'TestCollector'
        assert collector.is_enabled() is True
        assert collector.priority == 'high'

    def test_collector_disabled_when_enabled_false(self):
        """RED: 当 enabled=False 时，is_enabled() 应该返回 False"""
        class ConcreteCollector(BaseCollector):
            def collect(self, hours=24):
                return []

        config = {'name': 'DisabledCollector', 'enabled': False}
        collector = ConcreteCollector(config)
        assert collector.is_enabled() is False

    def test_collector_default_priority_is_medium(self):
        """RED: 默认优先级应该是 medium"""
        class ConcreteCollector(BaseCollector):
            def collect(self, hours=24):
                return []

        config = {'name': 'TestCollector', 'enabled': True}
        collector = ConcreteCollector(config)
        assert collector.priority == 'medium'

    def test_normalize_item_adds_required_fields(self, mock_content_item):
        """RED: normalize_item 应该添加必需字段"""
        class ConcreteCollector(BaseCollector):
            def collect(self, hours=24):
                return []

        config = {'name': 'TestCollector', 'enabled': True}
        collector = ConcreteCollector(config)

        # 只提供基本字段
        basic_item = {
            'title': 'Test Title',
            'content': 'Test Content',
            'url': 'https://example.com/test',
        }

        normalized = collector.normalize_item(basic_item)

        assert normalized['title'] == 'Test Title'
        assert normalized['content'] == 'Test Content'
        assert normalized['url'] == 'https://example.com/test'
        assert normalized['source'] == 'TestCollector'
        assert normalized['source_type'] == 'ConcreteCollector'
        assert 'published_at' in normalized
        assert 'collected_at' in normalized
        assert 'metadata' in normalized
        assert 'priority' in normalized

    def test_normalize_item_uses_current_time_when_no_published_at(self):
        """RED: 当没有 published_at 时，应该使用当前时间"""
        class ConcreteCollector(BaseCollector):
            def collect(self, hours=24):
                return []

        config = {'name': 'TestCollector', 'enabled': True}
        collector = ConcreteCollector(config)

        before = datetime.now()
        normalized = collector.normalize_item({'title': 'Test'})
        after = datetime.now()

        assert before <= normalized['published_at'] <= after
        assert before <= normalized['collected_at'] <= after
