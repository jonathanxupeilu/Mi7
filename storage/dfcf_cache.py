"""东方财富 API 缓存管理器"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class DFCFCache:
    """东方财富 API 响应缓存"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        # Ensure database is initialized
        from storage.database import Database
        Database(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get(self, stock_code: str, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取缓存的 API 响应
        Returns: 缓存数据或 None（如果缓存不存在或已过期）
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT response_data FROM dfcf_cache
            WHERE stock_code = ? AND query = ?
            AND expires_at > ?
        ''', (stock_code, query, datetime.now()))

        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row[0])
        return None

    def set(self, stock_code: str, query: str,
            data: List[Dict[str, Any]], ttl_hours: int = 1):
        """
        设置缓存
        Args:
            stock_code: 股票代码
            query: 查询关键词
            data: API 响应数据
            ttl_hours: 缓存有效期（小时），默认1小时
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        expires_at = datetime.now() + timedelta(hours=ttl_hours)

        # 转换 datetime 对象为 ISO 格式字符串
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f'Object of type {type(obj)} is not JSON serializable')

        cursor.execute('''
            INSERT OR REPLACE INTO dfcf_cache
            (stock_code, query, response_data, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (
            stock_code,
            query,
            json.dumps(data, default=serialize_datetime),
            expires_at
        ))

        conn.commit()
        conn.close()

    def clear_expired(self) -> int:
        """清理过期缓存，返回删除条数"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM dfcf_cache WHERE expires_at < ?
        ''', (datetime.now(),))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM dfcf_cache')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM dfcf_cache WHERE expires_at > ?',
                       (datetime.now(),))
        valid = cursor.fetchone()[0]

        conn.close()

        return {
            'total': total,
            'valid': valid,
            'expired': total - valid
        }
