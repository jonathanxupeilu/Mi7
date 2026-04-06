# MI7 测试框架

本项目使用 **pytest** 进行单元测试，遵循 **TDD（测试驱动开发）** 原则。

## TDD 原则

1. **RED**: 先写测试，确保它失败
2. **GREEN**: 编写最小代码使测试通过
3. **REFACTOR**: 重构代码，保持测试通过

## 测试结构

```
tests/
├── conftest.py              # 共享 fixtures
├── test_base_collector.py   # BaseCollector 测试
├── test_rss_collector.py    # RSSCollector 测试
├── test_database.py         # Database 测试
└── test_config.py           # 配置测试
```

## 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_rss_collector.py -v

# 运行特定测试类
python -m pytest tests/test_database.py::TestDatabase -v

# 使用测试运行器脚本
python run_tests.py
python run_tests.py --coverage
python run_tests.py --test tests/test_database.py
```

## 测试覆盖率

```bash
# 安装 coverage 工具
pip install pytest-cov

# 运行带覆盖率的测试
python -m pytest tests/ --cov=collectors --cov=storage --cov-report=term-missing
```

## 发现的 Bug 及修复

### Bug 1: source 字段被覆盖
**问题**: `BaseCollector.normalize_item()` 使用 `self.name` 覆盖了 `source` 字段。

**修复**: `collectors/base_collector.py:24`
```python
# 修复前
'source': self.name,

# 修复后
'source': item.get('source', self.name),
```

### Bug 2: 时间过滤逻辑已验证正确
**验证**: `test_parse_feed_filters_by_time` 确认了时间过滤逻辑正确工作。

## 测试统计

- **总测试数**: 25
- **通过**: 25
- **失败**: 0

### 按模块分布

| 模块 | 测试数 | 状态 |
|------|--------|------|
| BaseCollector | 6 | ✓ |
| RSSCollector | 8 | ✓ |
| Database | 9 | ✓ |
| Config | 2 | ✓ |

## 添加新测试

1. 在 `tests/` 目录创建 `test_<module>.py`
2. 使用 `conftest.py` 中的 fixtures
3. 遵循命名规范: `test_<functionality>`
4. 确保测试先失败（RED），再写代码使其通过（GREEN）

## Fixtures

常用 fixtures（在 `conftest.py` 中定义）:

- `temp_db_path`: 临时数据库文件路径
- `mock_feed_entry`: 模拟 RSS feed 条目
- `mock_collector_config`: 模拟采集器配置
- `mock_content_item`: 模拟内容项
