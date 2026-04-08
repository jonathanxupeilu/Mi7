"""测试配置和共享 fixtures"""
import pytest
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def temp_db_path():
    """创建临时数据库文件"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    yield db_path
    # 清理
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_feed_entry():
    """模拟 RSS feed entry"""
    return {
        'title': 'Test Article Title',
        'summary': 'Test article summary content',
        'link': 'https://example.com/article/1',
        'published_parsed': datetime.now().timetuple(),
    }


@pytest.fixture
def mock_collector_config():
    """模拟采集器配置"""
    return {
        'name': 'TestCollector',
        'enabled': True,
        'priority': 'high',
        'feeds': [
            {
                'id': 'test_feed',
                'name': 'Test Feed',
                'url': 'https://example.com/feed',
                'enabled': True
            }
        ]
    }


@pytest.fixture
def mock_content_item():
    """模拟内容项"""
    return {
        'title': 'AAPL Stock Surges 10% on Strong Earnings',
        'content': 'Apple reported strong quarterly earnings...',
        'url': 'https://example.com/aapl-news',
        'source': 'TestSource',
        'source_type': 'TestCollector',
        'published_at': datetime.now(),
        'collected_at': datetime.now(),
        'metadata': {'category': 'earnings'},
        'priority': 'high'
    }
