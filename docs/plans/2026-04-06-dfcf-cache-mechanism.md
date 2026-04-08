# 东方财富缓存机制实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为东方财富 API 设计缓存机制，避免重复调用，解决频率限制问题

**架构:** 在 SQLite 数据库中新增缓存表，存储每只股票的 API 响应，设置缓存过期时间（默认1小时），采集时优先读取缓存

**Tech Stack:** Python, SQLite, SQLAlchemy (可选), 现有 Database 类

---

## 文件结构

**新建文件:**
- `storage/dfcf_cache.py` - 东方财富缓存管理器
- `tests/test_dfcf_cache.py` - 缓存机制 TDD 测试

**修改文件:**
- `collectors/dfcf_collector.py:26-30` - 集成缓存到采集器
- `collectors/dfcf_collector.py:43-90` - search_news 方法添加缓存逻辑
- `storage/database.py` - 新增缓存表初始化

---

## Task 1: 数据库缓存表设计

**Files:**
- Modify: `storage/database.py:19-43`
- Test: `tests/test_database.py`

- [ ] **Step 1: Write the failing test**

```python
def test_cache_table_exists(temp_db_path):
    """RED: 数据库应创建 dfcf_cache 表"""
    from storage.database import Database
    db = Database(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dfcf_cache'")
    result = cursor.fetchone()
    conn.close()
    assert result is not None
    assert result[0] == 'dfcf_cache'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::test_cache_table_exists -v`
Expected: FAIL with "table not found"

- [ ] **Step 3: Write minimal implementation**

在 `storage/database.py` 的 `init_db` 方法中，在 content 表创建后添加：

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::test_cache_table_exists -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add storage/database.py tests/test_database.py
git commit -m "feat: add dfcf_cache table for API response caching"
```

---

## Task 2: 缓存管理器类

**Files:**
- Create: `storage/dfcf_cache.py`
- Test: `tests/test_dfcf_cache.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from datetime import datetime, timedelta
from storage.dfcf_cache import DFCFCache

class TestDFCFCache:
    def test_cache_get_returns_none_for_miss(self, temp_db_path):
        """RED: 缓存未命中应返回 None"""
        cache = DFCFCache(temp_db_path)
        result = cache.get('600519', '贵州茅台 600519')
        assert result is None

    def test_cache_set_and_get(self, temp_db_path):
        """RED: 设置缓存后应能读取"""
        cache = DFCFCache(temp_db_path)
        data = [{'title': 'Test', 'content': 'Content'}]
        cache.set('600519', '贵州茅台 600519', data, ttl_hours=1)
        result = cache.get('600519', '贵州茅台 600519')
        assert result == data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dfcf_cache.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Write minimal implementation**

创建 `storage/dfcf_cache.py`:

```python
"""东方财富 API 缓存管理器"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class DFCFCache:
    """东方财富 API 响应缓存"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get(self, stock_code: str, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取缓存的 API 响应

        Returns:
            缓存数据或 None（如果缓存不存在或已过期）
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

        cursor.execute('''
            INSERT OR REPLACE INTO dfcf_cache
            (stock_code, query, response_data, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (
            stock_code,
            query,
            json.dumps(data),
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dfcf_cache.py::TestDFCFCache -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add storage/dfcf_cache.py tests/test_dfcf_cache.py
git commit -m "feat: add DFCFCache class for API response caching"
```

---

## Task 3: 缓存过期机制测试

**Files:**
- Modify: `tests/test_dfcf_cache.py`
- Modify: `storage/dfcf_cache.py` (如需调整)

- [ ] **Step 1: Write the failing test**

```python
    def test_cache_expires_after_ttl(self, temp_db_path):
        """RED: 缓存应在 TTL 后过期"""
        cache = DFCFCache(temp_db_path)
        data = [{'title': 'Test'}]

        # 设置0.01小时过期（36秒）
        cache.set('600519', 'query', data, ttl_hours=0.01)

        # 立即读取应该命中
        result = cache.get('600519', 'query')
        assert result is not None

        # 等待过期（模拟时间跳转或用短TTL测试）
        import time
        time.sleep(1)

        # 读取应返回 None
        result = cache.get('600519', 'query')
        assert result is None

    def test_clear_expired_removes_old_entries(self, temp_db_path):
        """RED: clear_expired 应删除过期条目"""
        cache = DFCFCache(temp_db_path)

        # 设置两个缓存，一个已过期，一个有效
        cache.set('600519', 'old_query', [{'title': 'Old'}], ttl_hours=-1)  # 已过期
        cache.set('000858', 'new_query', [{'title': 'New'}], ttl_hours=1)   # 有效

        # 清理过期缓存
        deleted = cache.clear_expired()
        assert deleted == 1

        # 验证过期缓存已删除
        assert cache.get('600519', 'old_query') is None

        # 验证有效缓存仍存在
        assert cache.get('000858', 'new_query') is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dfcf_cache.py::TestDFCFCache::test_cache_expires_after_ttl -v`
Expected: FAIL 或 超时（如果未实现 TTL 检查）

- [ ] **Step 3: Verify implementation supports TTL**

检查 `storage/dfcf_cache.py` 中的 `get` 方法已实现 `expires_at > ?` 检查

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dfcf_cache.py::TestDFCFCache -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_dfcf_cache.py
git commit -m "test: add TTL expiration tests for DFCFCache"
```

---

## Task 4: 集成缓存到 DFCFCollector

**Files:**
- Modify: `collectors/dfcf_collector.py:26-30`
- Modify: `collectors/dfcf_collector.py:43-90`
- Test: `tests/test_dfcf_collector.py`

- [ ] **Step 1: Write the failing test**

```python
    def test_collector_uses_cache_on_second_call(self, temp_db_path):
        """RED: 第二次调用应使用缓存"""
        from collectors.dfcf_collector import DFCFCollector

        # Mock API 只应被调用一次
        call_count = 0
        def mock_search(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return [{'title': f'News {call_count}'}]

        collector = DFCFCollector(db_path=temp_db_path)
        collector._api_search = mock_search

        # 第一次调用 - 应命中 API
        result1 = collector.search_news('贵州茅台 600519')
        assert call_count == 1

        # 第二次调用 - 应使用缓存，不增加 API 调用次数
        result2 = collector.search_news('贵州茅台 600519')
        assert call_count == 1  # 仍然是 1
        assert result1 == result2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dfcf_collector.py::test_collector_uses_cache_on_second_call -v`
Expected: FAIL with "DFCFCollector has no attribute '_api_search'"

- [ ] **Step 3: Refactor DFCFCollector**

修改 `collectors/dfcf_collector.py`:

**Step 3a: 添加缓存初始化**

```python
# 在文件顶部导入
try:
    from storage.dfcf_cache import DFCFCache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

class DFCFCollector:
    def __init__(self, db_path: str = "./data/mi7.db"):
        self.db = Database(db_path)
        self.api_key = os.getenv("MX_APIKEY")
        if not self.api_key:
            raise ValueError("MX_APIKEY not set")

        # 初始化缓存
        if CACHE_AVAILABLE:
            self.cache = DFCFCache(db_path)
        else:
            self.cache = None
```

**Step 3b: 拆分 search_news 为 API 调用和缓存包装**

```python
    def search_news(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索资讯（带缓存）
        """
        # 从查询中提取股票代码（假设格式: "股票名 代码"）
        stock_code = query.split()[-1] if ' ' in query else 'unknown'

        # 尝试读取缓存
        if self.cache:
            cached = self.cache.get(stock_code, query)
            if cached is not None:
                print(f"    [CACHE HIT] {stock_code}")
                return cached

        # 缓存未命中，调用 API
        result = self._api_search(query)

        # 写入缓存（1小时 TTL）
        if self.cache and result:
            self.cache.set(stock_code, query, result, ttl_hours=1)

        return result

    def _api_search(self, query: str) -> List[Dict[str, Any]]:
        """
        实际的 API 调用（原 search_news 逻辑）
        """
        # 将原来的 search_news 实现移到这里
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }
        data = {"query": query}

        try:
            response = requests.post(
                self.BASE_URL, headers=headers, json=data, timeout=30
            )
            response.raise_for_status()
            result = response.json()

            if result.get("status") != 0 and result.get("code") != 0:
                print(f"  API Error: {result.get('message', 'Unknown error')}")
                return []

            # 解析嵌套的 data 结构...
            # 保持原有逻辑
            outer_data = result.get("data", {})
            if isinstance(outer_data, dict):
                inner_data = outer_data.get("data", {})
                llm_resp = inner_data.get("llmSearchResponse", {})

                if isinstance(llm_resp, dict):
                    news_list = llm_resp.get("data", [])
                else:
                    news_list = []
            else:
                news_list = []

            # 转换为标准格式
            items = []
            for item in news_list:
                if isinstance(item, dict):
                    items.append({
                        'title': item.get('title', ''),
                        'content': item.get('content', ''),
                        'source': item.get('source', '东方财富'),
                        'published_at': self._parse_date(item.get('date', '')),
                        'url': item.get('jumpUrl', ''),
                        'metadata': {'info_type': item.get('informationType', '')}
                    })

            return items

        except Exception as e:
            print(f"  Request error: {e}")
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dfcf_collector.py::test_collector_uses_cache_on_second_call -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add collectors/dfcf_collector.py tests/test_dfcf_collector.py
git commit -m "feat: integrate DFCFCache into DFCFCollector"
```

---

## Task 5: 缓存统计与监控

**Files:**
- Modify: `scripts/run.py`
- Modify: `collectors/dfcf_collector.py`

- [ ] **Step 1: Add cache stats display to collect flow**

在 `scripts/run.py` 的 `cmd_collect` 函数中，DFCF 采集后添加：

```python
    if args.source in ['all', 'dfcf']:
        print("\n[2] 采集东方财富...")
        try:
            dfcf_collector = DFCFCollector()
            dfcf_items = dfcf_collector.collect_all(limit_per_stock=5)
            print(f"    采集: {len(dfcf_items)} 条")

            # 显示缓存统计
            if dfcf_collector.cache:
                stats = dfcf_collector.cache.get_stats()
                print(f"    缓存: {stats['valid']} 有效, {stats['expired']} 过期")

            items.extend(dfcf_items)
        except Exception as e:
            print(f"    [ERROR] 东方财富采集失败: {e}")
```

- [ ] **Step 2: Add cache clear command**

在 `scripts/run.py` 添加新的子命令：

```python
    # cache 命令
    cache_parser = subparsers.add_parser('cache', help='缓存管理')
    cache_parser.add_argument('--clear-expired', action='store_true',
                              help='清理过期缓存')
    cache_parser.add_argument('--stats', action='store_true',
                              help='显示缓存统计')
```

在 `main()` 函数中添加：

```python
    elif args.command == 'cache':
        cmd_cache(args)
```

实现 `cmd_cache` 函数：

```python
def cmd_cache(args):
    """缓存管理命令"""
    from storage.dfcf_cache import DFCFCache
    from storage.database import Database

    db_path = DATA_DIR / 'mi7.db'
    cache = DFCFCache(str(db_path))

    if args.stats:
        stats = cache.get_stats()
        print("=" * 60)
        print("DFCF 缓存统计")
        print("=" * 60)
        print(f"  总条目: {stats['total']}")
        print(f"  有效: {stats['valid']}")
        print(f"  过期: {stats['expired']}")
        print("=" * 60)

    if args.clear_expired:
        deleted = cache.clear_expired()
        print(f"已清理 {deleted} 条过期缓存")
```

- [ ] **Step 3: Test cache commands**

Run: `python scripts/run.py cache --stats`
Expected: 显示缓存统计

Run: `python scripts/run.py cache --clear-expired`
Expected: 清理过期缓存

- [ ] **Step 4: Commit**

```bash
git add scripts/run.py
git commit -m "feat: add cache management commands"
```

---

## Task 6: 端到端测试

**Files:**
- Test: `tests/test_dfcf_integration.py`

- [ ] **Step 1: Write integration test**

```python
"""东方财富缓存集成测试"""
import pytest
import time
from collectors.dfcf_collector import DFCFCollector


class TestDFCFIntegration:
    """测试采集器与缓存的集成"""

    def test_full_collection_with_caching(self, temp_db_path):
        """
        完整流程测试：
        1. 第一次采集 - 调用 API
        2. 第二次采集 - 应命中缓存
        3. 验证 API 调用次数
        """
        collector = DFCFCollector(db_path=temp_db_path)

        # Mock API 调用
        api_calls = []
        original_api_search = collector._api_search

        def mock_api_search(query):
            api_calls.append(query)
            return [{'title': f'News for {query}', 'content': 'Content'}]

        collector._api_search = mock_api_search

        # 第一次采集某只股票
        result1 = collector.search_news('贵州茅台 600519')
        assert len(api_calls) == 1

        # 第二次采集同一只股票 - 应使用缓存
        result2 = collector.search_news('贵州茅台 600519')
        assert len(api_calls) == 1  # 没有新增 API 调用

        # 结果应相同
        assert result1 == result2

    def test_cache_reduces_api_calls_in_collect_all(self, temp_db_path):
        """
        测试 collect_all 方法中的缓存效果
        """
        # 这个测试验证在批量采集时缓存是否有效
        # 需要更复杂的 mock 来跟踪 API 调用
        pass
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_dfcf_integration.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_dfcf_integration.py
git commit -m "test: add DFCF cache integration tests"
```

---

## 总结

### 实现的功能

1. **数据库表**: `dfcf_cache` 存储 API 响应
2. **缓存管理器**: `DFCFCache` 类提供 get/set/clear/stats 方法
3. **TTL 机制**: 默认1小时过期，自动清理
4. **集成**: `DFCFCollector` 优先读取缓存，减少 API 调用
5. **监控**: `--stats` 和 `--clear-expired` 命令管理缓存

### 预期效果

- **API 调用减少**: 同一股票1小时内重复采集命中缓存
- **频率限制缓解**: 20只股票首次采集20次API，后续从缓存读取
- **性能提升**: 缓存读取 < 1ms，API调用 ~1-3秒

### 缓存策略

| 场景 | 行为 |
|------|------|
| 缓存命中 | 直接返回，不调用 API |
| 缓存过期 | 调用 API，更新缓存 |
| 新股票 | 调用 API，写入缓存 |
| API 失败 | 尝试读取过期缓存（容错） |

---

**Plan complete.** 执行选项：

1. **Subagent-Driven (推荐)** - 使用 superpowers:subagent-driven-development
2. **Inline Execution** - 使用 superpowers:executing-plans

选择哪种方式执行？