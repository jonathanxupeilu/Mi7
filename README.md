# 军情七处 (MI7)

智能投资信息收集系统

## 核心特性

- **多源采集**: RSS、YouTube、Twitter(Nitter)、AI搜索、东方财富
- **统一摘要**: 600字中文摘要，关键术语保留英文
- **本地运行**: 完全本地化，数据隐私可控
- **费用可控**: 约¥400/月（Claude API）

## 信息源架构

- **Layer 1**: AI搜索（Jina/Tavily/Firecrawl - 免费）
- **Layer 2**: 东方财富mx-skills（5个技能 - 已安装）
- **Layer 3**: RSS新闻（Reuters、CNBC等 - 免费）
- **Layer 4**: YouTube官方RSS（CNBC、Bloomberg、ARK - 免费稳定）
- **Layer 5**: Twitter（Nitter - 免费但不稳定）
- **Layer 6**: 播客（RSS - 免费）

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python mi7.py

# 或指定采集时间范围
python mi7.py --hours 48
```

## Audio Reports (MP3)

Convert reports to MP3 audio for listening on-the-go:

```bash
# Generate report with audio (using free edge-tts)
python mi7.py --hours 48 --audio

# Generate report with premium ElevenLabs TTS
python mi7.py --hours 48 --audio --audio-provider elevenlabs

# Convert existing markdown report to MP3
python scripts/convert_report_to_audio.py reports/mi7_report_2026-04-06.md

# Choose different voice (edge-tts)
python scripts/convert_report_to_audio.py report.md --voice yunjian
```

**Audio Providers:**

| Provider | Quality | Cost | Voices |
|----------|---------|------|--------|
| `edge` (default) | Good | Free | Chinese voices: xiaoxiao, xiaoyi, yunjian, yunxi |
| `elevenlabs` | Excellent | Per-use | 22+ voices: aria, george, brian, etc. |

**Edge-TTS Voices (Free):**
- `xiaoxiao`: 女声，新闻播报风格 (默认)
- `xiaoyi`: 女声，温柔风格
- `yunjian`: 男声，新闻播报风格
- `yunxi`: 男声，轻松风格

**ElevenLabs Voices (Premium):**
- `aria`: American, conversational (female)
- `george`: British, authoritative (male)
- `brian`: American, conversational (male)
- `alice`: British, confident (female)
- See full list: [ElevenLabs Voice Library](https://elevenlabs.io/voice-library)

**Requirements:**
```bash
# For edge-tts (free)
pip install edge-tts gtts

# For ElevenLabs (requires infsh CLI)
npx skills add https://github.com/inferen-sh/skills --skill elevenlabs-tts
infsh login
```

---

## 费用说明

- **Claude API**: ~$54/月（约¥400）
- **其他服务**: 全部免费

## 配置

编辑 `.env` 文件配置API Keys：
- ANTHROPIC_API_KEY（必需）
- MX_APIKEY（已配置）
