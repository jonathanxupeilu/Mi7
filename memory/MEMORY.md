---
status: active
summary: MI7 项目记忆索引
created: '2026-04-06'
updated: '2026-04-06'
artifacts: []
next_actions: []
---
# MI7 项目记忆索引

---
status: active
summary: MI7 投资情报系统项目记忆索引，包含经验、反馈和项目状态
created: 2026-04-03
updated: 2026-04-06
artifacts:
  - memory/episodic/2026-04-03-mi7-session.md
  - memory/episodic/2026-04-05-mi7-notebooklm-success.md
  - memory/episodic/2026-04-05-session-end.md
  - memory/episodic/2026-04-06-tts-implementation.md
next_actions:
  - 继续 NotebookLM 集成测试
  - 验证音频报告生成功能
  - 监控 edge-tts SSL 稳定性
---

## 经验记录
- [2026-04-06 TTS实现完成](episodic/2026-04-06-tts-implementation.md) — 音频报告生成、多提供商支持、TDD实践、测试修复
- [2026-04-05 NotebookLM集成完成](episodic/2026-04-05-session-end.md) — TDD开发、Windows编码修复、Louis Gave分析获取
- [2026-04-05 NotebookLM技能成功经验](episodic/2026-04-05-mi7-notebooklm-success.md) — YouTube技能失败教训、Windows编码修复
- [2026-04-03 完整会话经验](episodic/2026-04-03-mi7-session.md) — RSS扩展(17源)、TDD实践、免费渠道集成测试

## 反馈
- [阿里云百炼API调用反馈](feedback_ailiyun_api.md) — 用户指出API调用错误及正确做法
- [API频率限制处理方案](feedback_api_rate_limit.md) — 遇到API调用频率限制时的标准处理方案

## 关键模式 (Semantic Patterns)

### TTS 实现模式
**Pattern ID**: tts-multi-provider
**Source**: 2026-04-06 TTS实现
**Confidence**: 0.95
**Applications**: 1

**Problem**: 单一TTS服务不可靠，网络问题导致失败
**Solution**:
1. 实现多提供商支持 (edge-tts → gTTS → ElevenLabs)
2. 添加指数退避重试机制 (2^attempt seconds)
3. 支持部分结果保存（失败时保存已生成片段）
4. 文本分块处理（5000字符限制）

**Implementation**:
```python
# 重试逻辑
for attempt in range(max_retries):
    try:
        result = await generate_chunk(chunk)
        if success: return result
    except Exception as e:
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)
```

### TDD 工作流程
**Pattern ID**: tdd-audio-generation
**Source**: 2026-04-06 TTS实现
**Confidence**: 0.95
**Applications**: 2

**流程**:
1. 先写测试（验证会失败）
2. 运行测试确认失败原因正确
3. 写最小实现代码
4. 运行测试确认通过
5. 重构优化

**Files**: 
- `tests/test_audio_report_generator.py` (6 tests)
- `tests/test_elevenlabs_audio_generator.py` (8 tests)

### 网络服务容错
**Pattern ID**: network-service-resilience
**Source**: 2026-04-06 edge-tts SSL错误
**Confidence**: 0.90
**Applications**: 1

**Anti-pattern**: 直接调用外部API，失败即崩溃
**Best Practice**:
- 始终实现重试机制
- 提供降级/备用方案
- 保存部分结果优于完全失败
- 给用户清晰的错误信息

## 项目状态

### 当前测试状态
- **总计**: 138 tests
- **通过**: 138 ✅
- **失败**: 0 ❌
- **跳过**: 11 ⏭️

### 最近提交
```
f12acfd test: add DFCF cache integration tests
... (audio generation commits)
```

### 新增功能
1. **音频报告生成** — 将Markdown报告转为MP3
   - 提供商: edge-tts (免费), ElevenLabs (高质量)
   - 语音: 中文女声/男声, 22+英文语音
   - 特性: 自动重试、降级、分块处理

2. **CLI增强** — 新增 `--audio`, `--audio-provider` 参数

3. **测试修复** — 修复13个失败测试，全部通过

## 注意事项
- edge-tts在某些环境有SSL连接问题，已添加gTTS降级
- ElevenLabs需要infsh CLI和登录
- 音频文件较大（~20MB/报告），注意磁盘空间
