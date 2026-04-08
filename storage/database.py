"""数据库层"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path


class Database:
    """SQLite数据库管理"""
    
    def __init__(self, db_path: str = "./data/mi7.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
        
    def get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
        
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                summary TEXT,
                url TEXT UNIQUE,
                source TEXT,
                source_type TEXT,
                published_at TIMESTAMP,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                relevance_score REAL DEFAULT 0,
                impact_score REAL DEFAULT 0,
                priority TEXT DEFAULT 'low',
                metadata TEXT,
                is_processed BOOLEAN DEFAULT FALSE
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_url ON content(url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_date ON content(published_at)')

        # DFCF缓存表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dfcf_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                query TEXT NOT NULL,
                response_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                UNIQUE(stock_code, query)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_stock ON dfcf_cache(stock_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_expires ON dfcf_cache(expires_at)')

        conn.commit()
        conn.close()
        
    def insert_content(self, item: Dict[str, Any]) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO content 
                (title, content, url, source, source_type, published_at, collected_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.get('title', ''),
                item.get('content', ''),
                item.get('url', ''),
                item.get('source', ''),
                item.get('source_type', ''),
                item.get('published_at', datetime.now()),
                item.get('collected_at', datetime.now()),
                str(item.get('metadata', {}))
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting content: {e}")
            return False
        finally:
            conn.close()
            
    def get_unprocessed_content(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM content 
            WHERE is_processed = FALSE 
            ORDER BY published_at DESC 
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
        
    def get_analyzed_content(self, hours: int = 48, min_relevance: int = 0) -> List[Dict[str, Any]]:
        """
        获取已分析的内容

        Args:
            hours: 最近多少小时内的内容
            min_relevance: 最小相关性分数 (0-100)

        Returns:
            已分析的内容列表
        """
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(hours=hours)

        cursor.execute('''
            SELECT * FROM content
            WHERE is_processed = TRUE
              AND relevance_score >= ?
              AND collected_at >= ?
            ORDER BY relevance_score DESC, impact_score DESC
        ''', (min_relevance, cutoff))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def check_duplicate(self, url: str) -> bool:
        """检查 URL 是否已存在"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM content WHERE url = ?', (url,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
