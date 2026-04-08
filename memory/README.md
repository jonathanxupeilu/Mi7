---
status: active
summary: Memory 系统使用文档
created: '2026-04-06'
updated: '2026-04-06'
artifacts: []
next_actions: []
---
# Memory 系统使用文档

符合 Agent Harness 规范的 Memory 系统

---
status: active
summary: Memory 系统使用说明和最佳实践
created: 2026-04-05
updated: 2026-04-05
artifacts:
  - memory/memory_validator.py
  - memory/MEMORY.md
next_actions:
  - 定期运行验证工具检查 memory 健康
  - 维护 artifacts 和 next_actions
---

## 概述

Memory 系统采用 **YAML Frontmatter + Markdown** 格式，符合 Agent Harness 规范：

- **状态追踪** (status)
- **摘要索引** (summary)
- **工件引用** (artifacts)
- **后续行动** (next_actions)

## 文件格式

```markdown
---
status: active
summary: 一句话摘要
created: 2026-04-05
updated: 2026-04-05
artifacts:
  - path/to/file1
  - path/to/file2
next_actions:
  - 行动1
  - 行动2
---

# 标题

正文内容...
```

## Frontmatter 字段

| 字段 | 必需 | 说明 | 示例 |
|------|------|------|------|
| status | ✅ | 状态 | `active`, `archived`, `deprecated`, `draft` |
| summary | ✅ | 一句话摘要 | "NotebookLM 集成完成" |
| created | ❌ | 创建日期 | `2026-04-05` |
| updated | ❌ | 更新日期 | `2026-04-05` |
| artifacts | ❌ | 相关文件列表 | `['collectors/xxx.py']` |
| next_actions | ❌ | 后续行动 | `['测试集成']` |

## 验证工具

### 使用方法

```bash
# 验证所有 memory 文件
cd memory
python memory_validator.py

# 自动修复问题
python memory_validator.py --fix

# 验证单个文件
python memory_validator.py --file episodic/2026-04-05-session.md

# 指定目录
python memory_validator.py --dir /path/to/memory
```

### 验证规则

- ✅ **必填字段**: status, summary
- ✅ **状态值**: active, archived, deprecated, draft
- ⚠️ **建议**: created/updated 使用 YYYY-MM-DD 格式
- ⚠️ **警告**: artifacts 引用的文件不存在时会警告

## 最佳实践

### DO
- ✅ 使用清晰的摘要（50字以内）
- ✅ 维护 artifacts 列表（代码文件、配置等）
- ✅ 更新 next_actions（下一步计划）
- ✅ 定期运行验证工具
- ✅ 使用 UTF-8 编码

### DON'T
- ❌ 缺少 frontmatter
- ❌ frontmatter 格式错误
- ❌ 无效的状态值
- ❌ 过时的 artifacts 引用

## 目录结构

```
memory/
├── MEMORY.md              # 主索引（必须）
├── memory_validator.py    # 验证工具
├── feedback_*.md          # 反馈记录
├── episodic/              # 经验记录
│   ├── 2026-04-03-session.md
│   └── 2026-04-05-session.md
└── semantic/              # 模式/规则（可选）
    └── patterns.json
```

## 集成到工作流

### 会话结束时
```bash
# 自动验证和修复
python memory/memory_validator.py --fix
```

### 提交前
```bash
# 检查是否有无效文件
python memory/memory_validator.py
```

## 状态说明

| 状态 | 含义 | 使用场景 |
|------|------|----------|
| **active** | 活跃 | 当前项目、有效的经验 |
| **archived** | 归档 | 已完成的项目、历史记录 |
| **deprecated** | 废弃 | 过时的信息、不再使用 |
| **draft** | 草稿 | 未完成、待编辑的内容 |

## 示例

### 经验记录 (episodic)
```markdown
---
status: active
summary: NotebookLM 集成完成，8/9 测试通过
created: 2026-04-05
updated: 2026-04-05
artifacts:
  - collectors/notebooklm_collector.py
  - tests/test_notebooklm_source.py
next_actions:
  - 运行集成测试
  - 验证报告生成
---

# NotebookLM 集成

## 完成内容
...
```

### 反馈记录 (feedback)
```markdown
---
status: active
summary: API 调用错误及正确做法
created: 2026-04-03
---

# 阿里云百炼API调用反馈

...
```

## 故障排除

### 编码问题
如果遇到 GBK 编码错误，使用：
```bash
python -X utf8 memory_validator.py
```

### 修复失败
手动添加 frontmatter：
```markdown
---
status: active
summary: 摘要内容
---

# 标题
```

## 相关资源

- [Agent Harness 规范](../references/agent-harness-spec.md)
- [Memory 研究论文](../references/memory-research.md)
