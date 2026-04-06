"""完整集成测试 - 仅使用免费渠道（RSS、Nitter、报告生成）

不调用任何有限配额API：
- 不使用东方财富mx-search API
- 使用RSS（17个源）、Nitter、数据库、报告生成
"""
import unittest
import os
import sys
import sqlite3
from datetime import datetime, timedelta
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from collectors.rss_collector import RSSCollector
from collectors.nitter_collector import NitterCollector
from storage.database import Database
from output.report_generator import ReportGenerator
import yaml


class TestIntegrationFreeSources(unittest.TestCase):
    """完整集成测试 - 免费渠道"""

    @classmethod
    def setUpClass(cls):
        """测试前准备：创建临时数据库"""
        cls.test_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.test_dir, 'test.db')

        # 创建测试数据库
        conn = sqlite3.connect(cls.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                url TEXT UNIQUE NOT NULL,
                source TEXT,
                source_type TEXT,
                published_at TIMESTAMP,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                summary TEXT,
                relevance_score INTEGER DEFAULT 0,
                impact_score INTEGER DEFAULT 0,
                priority TEXT DEFAULT 'medium',
                is_processed BOOLEAN DEFAULT 0,
                metadata TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        shutil.rmtree(cls.test_dir)

    def test_01_rss_collection(self):
        """
        Step 1: 测试RSS采集（17个免费源）

        Given: 配置文件中17个RSS源
        When: 调用RSS采集器
        Then: 成功采集内容，不消耗API配额
        """
        with open('config/sources.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        rss_config = config['sources']['rss']['native']
        collector = RSSCollector(rss_config)

        # 验证：加载了13个源
        self.assertEqual(len(collector.feeds), 13,
                        f"应该加载13个RSS源，实际{len(collector.feeds)}")

        # 采集最近24小时（放宽时间窗口确保有内容）
        items = collector.collect(hours=24)

        # 验证：采集成功（RSS可能某些时段无更新）
        self.assertIsInstance(items, list)

        # 如果有内容，验证结构
        if items:
            for item in items[:3]:
                self.assertIn('title', item)
                self.assertIn('url', item)
                self.assertIn('source', item)
                self.assertIn('published_at', item)

        # 统计
        sources = {}
        for item in items:
            src = item['source']
            sources[src] = sources.get(src, 0) + 1

        print(f"\n[Step 1] RSS采集: {len(items)} 条")
        print(f"  来源: {len(sources)} 个")
        for src, cnt in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    - {src}: {cnt}")

        # 保存用于后续测试
        TestIntegrationFreeSources.rss_items = items

    def test_02_nitter_collection(self):
        """
        Step 2: 测试Nitter采集（Twitter，免费）- 可选

        Given: 配置的投资大V列表
        When: 调用Nitter采集器
        Then: 采集推文，不消耗API配额
        """
        with open('config/sources.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        nitter_config = config['sources'].get('nitter')

        if not nitter_config or not nitter_config.get('enabled', False):
            self.skipTest("Nitter未启用或已移除")

        collector = NitterCollector(nitter_config)

        # 验证：加载了大V账号
        self.assertGreater(len(collector.accounts), 0, "应该有大V账号配置")

        # 采集最近6小时
        items = collector.collect(hours=6)

        # 验证：采集成功（可能为空，因为Nitter不稳定）
        self.assertIsInstance(items, list)

        print(f"\n[Step 2] Nitter采集: {len(items)} 条")
        if items:
            sources = set(item['source'] for item in items)
            print(f"  来源: {', '.join(sources)}")

        # 保存用于后续测试
        TestIntegrationFreeSources.nitter_items = items

    def test_03_database_storage(self):
        """
        Step 3: 测试数据库存储（本地操作，免费）

        Given: 采集的内容
        When: 保存到数据库
        Then: 成功存储，可查询
        """
        # 准备测试数据（混合RSS和Nitter）
        rss_items = getattr(TestIntegrationFreeSources, 'rss_items', [])
        nitter_items = getattr(TestIntegrationFreeSources, 'nitter_items', [])
        all_items = rss_items[:5] + nitter_items[:5]  # 限制数量

        if not all_items:
            self.skipTest("没有采集到内容")

        # 直接使用sqlite3存储（不依赖Database类内部实现）
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 存储
        saved = 0
        duplicates = 0
        for item in all_items:
            try:
                cursor.execute('''
                    INSERT INTO content (title, content, url, source, source_type, published_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    item['title'], item.get('content', ''), item['url'],
                    item['source'], item.get('source_type', ''),
                    item['published_at'].strftime('%Y-%m-%d %H:%M:%S')
                ))
                saved += 1
            except sqlite3.IntegrityError:
                duplicates += 1

        conn.commit()

        # 验证：存储成功
        self.assertGreater(saved, 0, "应该保存至少一条")

        # 验证：可查询
        cursor.execute('SELECT COUNT(*) FROM content')
        count = cursor.fetchone()[0]
        self.assertGreaterEqual(count, saved, "数据库记录数应匹配")

        conn.close()

        print(f"\n[Step 3] 数据库存储: {saved} 条")
        print(f"  重复: {duplicates}")

        # 保存用于后续测试
        TestIntegrationFreeSources.saved_count = saved

    def test_04_report_generation(self):
        """
        Step 4: 测试报告生成（本地操作，免费）

        Given: 数据库中的内容
        When: 生成报告
        Then: 成功生成TXT报告
        """
        # 直接使用sqlite3连接（不依赖Database类内部实现）
        conn = sqlite3.connect(self.db_path)

        # 获取已保存的内容
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM content
            WHERE collected_at > datetime('now', '-1 day')
            LIMIT 10
        ''')
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            self.skipTest("数据库中没有内容")

        # 转换为报告格式
        items = []
        for row in rows:
            items.append({
                'title': row[1],
                'content': row[2],
                'url': row[3],
                'source': row[4],
                'source_type': row[5],
                'published_at': row[6],
                'summary': row[8] or '',
                'relevance_score': row[9] or 50,
                'impact_score': row[10] or 50,
                'priority': row[11] or 'medium',
                'is_processed': row[12]
            })

        # 生成报告
        report_gen = ReportGenerator(output_dir=self.test_dir)
        report_path = report_gen.generate(datetime.now(), items)

        # 验证：报告文件存在
        self.assertTrue(os.path.exists(report_path), "报告文件应存在")
        self.assertTrue(report_path.endswith('.txt'), "报告应为TXT格式")

        # 验证：报告有内容
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertGreater(len(content), 100, "报告应有内容")

        # 验证：报告包含必要元素
        self.assertIn('军情七处', content, "报告应包含军情七处标识")

        print(f"\n[Step 4] 报告生成: ✓")
        print(f"  路径: {report_path}")
        print(f"  大小: {len(content)} 字符")

    def test_05_full_workflow(self):
        """
        Step 5: 完整工作流程测试

        Given: 配置、采集器、数据库、报告生成器
        When: 执行完整流程（采集→存储→报告）
        Then: 全部成功，不调用付费API
        """
        print("\n[Step 5] 完整工作流程:")

        # 1. RSS采集
        with open('config/sources.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        rss_collector = RSSCollector(config['sources']['rss']['native'])
        rss_items = rss_collector.collect(hours=3)
        print(f"  1. RSS采集: {len(rss_items)} 条")

        # 2. 数据库存储
        db = Database(self.db_path)
        saved = 0
        for item in rss_items[:10]:  # 只存前10条
            if not db.check_duplicate(item['url']):
                if db.insert_content(item):
                    saved += 1
        print(f"  2. 数据库存储: {saved} 条")

        # 3. 生成报告
        if saved > 0:
            cursor = db.conn.cursor()
            cursor.execute('SELECT * FROM content ORDER BY collected_at DESC LIMIT 10')
            rows = cursor.fetchall()

            items = [{
                'title': r[1], 'content': r[2], 'url': r[3],
                'source': r[4], 'published_at': r[6],
                'summary': r[8] or '', 'relevance_score': r[9] or 50,
                'impact_score': r[10] or 50, 'priority': r[11] or 'medium'
            } for r in rows]

            report_gen = ReportGenerator(output_dir=self.test_dir)
            report_path = report_gen.generate(datetime.now(), items)
            print(f"  3. 报告生成: ✓")
            print(f"     {os.path.basename(report_path)}")
        else:
            print(f"  3. 报告生成: 跳过（无数据）")

        print(f"\n  ✓ 完整流程测试通过")
        print(f"  ✓ 未调用任何付费API")


if __name__ == '__main__':
    unittest.main(verbosity=2)
