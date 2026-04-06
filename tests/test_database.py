"""Database 单元测试 - TDD"""
import pytest
import sqlite3
from datetime import datetime
from storage.database import Database


class TestDatabase:
    """测试 Database 类"""

    def test_database_creates_file_on_init(self, temp_db_path):
        """RED: Database 初始化应该创建数据库文件"""
        import os
        assert not os.path.exists(temp_db_path)
        db = Database(temp_db_path)
        assert os.path.exists(temp_db_path)

    def test_database_creates_content_table(self, temp_db_path):
        """RED: Database 应该创建 content 表"""
        db = Database(temp_db_path)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='content'")
        result = cursor.fetchone()
        conn.close()
        assert result is not None
        assert result[0] == 'content'

    def test_database_creates_indexes(self, temp_db_path):
        """RED: Database 应该创建索引"""
        db = Database(temp_db_path)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert 'idx_content_url' in indexes
        assert 'idx_content_date' in indexes

    def test_database_creates_dfcf_cache_table(self, temp_db_path):
        """RED: Database 应该创建 dfcf_cache 表"""
        db = Database(temp_db_path)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dfcf_cache'")
        result = cursor.fetchone()
        conn.close()
        assert result is not None
        assert result[0] == 'dfcf_cache'

    def test_dfcf_cache_has_correct_indexes(self, temp_db_path):
        """RED: dfcf_cache 应该有正确的索引"""
        db = Database(temp_db_path)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert 'idx_cache_stock' in indexes
        assert 'idx_cache_expires' in indexes

    def test_insert_content_returns_true_on_success(self, temp_db_path, mock_content_item):
        """RED: insert_content 成功时应该返回 True"""
        db = Database(temp_db_path)
        result = db.insert_content(mock_content_item)
        assert result is True

    def test_insert_content_stores_data_correctly(self, temp_db_path, mock_content_item):
        """RED: insert_content 应该正确存储数据"""
        db = Database(temp_db_path)
        db.insert_content(mock_content_item)

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT title, content, url, source FROM content WHERE url = ?",
                      (mock_content_item['url'],))
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == mock_content_item['title']
        assert result[1] == mock_content_item['content']
        assert result[2] == mock_content_item['url']
        assert result[3] == mock_content_item['source']

    def test_check_duplicate_returns_true_for_existing_url(self, temp_db_path, mock_content_item):
        """RED: check_duplicate 对存在的 URL 应该返回 True"""
        db = Database(temp_db_path)
        db.insert_content(mock_content_item)
        result = db.check_duplicate(mock_content_item['url'])
        assert result is True

    def test_check_duplicate_returns_false_for_new_url(self, temp_db_path):
        """RED: check_duplicate 对新 URL 应该返回 False"""
        db = Database(temp_db_path)
        result = db.check_duplicate('https://new-url.com')
        assert result is False

    def test_get_unprocessed_content_returns_unprocessed_items(self, temp_db_path):
        """RED: get_unprocessed_content 应该返回未处理的内容"""
        db = Database(temp_db_path)

        # 插入两条内容
        item1 = {
            'title': 'Processed Item',
            'content': 'Content 1',
            'url': 'https://test.com/1',
            'source': 'Test',
            'source_type': 'Test',
            'published_at': datetime.now(),
            'collected_at': datetime.now(),
            'metadata': {}
        }
        item2 = {
            'title': 'Unprocessed Item',
            'content': 'Content 2',
            'url': 'https://test.com/2',
            'source': 'Test',
            'source_type': 'Test',
            'published_at': datetime.now(),
            'collected_at': datetime.now(),
            'metadata': {}
        }

        db.insert_content(item1)
        db.insert_content(item2)

        # 将第一条标记为已处理
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE content SET is_processed = TRUE WHERE url = ?", (item1['url'],))
        conn.commit()
        conn.close()

        # 应该只返回未处理的内容
        unprocessed = db.get_unprocessed_content(limit=100)
        assert len(unprocessed) == 1
        assert unprocessed[0]['title'] == 'Unprocessed Item'

    def test_insert_content_updates_existing_record(self, temp_db_path, mock_content_item):
        """RED: insert_content 应该更新已存在的记录（UPSERT）"""
        db = Database(temp_db_path)

        # 插入第一次
        db.insert_content(mock_content_item)

        # 修改内容后再次插入（相同 URL）
        updated_item = mock_content_item.copy()
        updated_item['title'] = 'Updated Title'
        updated_item['content'] = 'Updated content'

        result = db.insert_content(updated_item)
        assert result is True

        # 验证只有一条记录，且内容已更新
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT title, content FROM content WHERE url = ?", (mock_content_item['url'],))
        result = cursor.fetchone()
        conn.close()

        assert result[0] == 'Updated Title'
        assert result[1] == 'Updated content'
