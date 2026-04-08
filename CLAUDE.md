# MI7 Source Orchestration

## Overview

The MI7 pipeline now uses a **smart source orchestration** strategy that optimizes API usage while ensuring critical data sources are always available.

## Source Tiers

### Tier 1: Always On (Must-Have)
These sources are **mandatory** and always included in default mode:

| Source | Cost | Caching | TTL |
|--------|------|---------|-----|
| RSS | Free | No | N/A |
| DFCF (东方财富) | Free tier | Yes | 4 hours |
| Obsidian | Free (local) | Yes | 24 hours |

### Tier 2: Conditional (Paid APIs)
These sources respect the `enabled` flag in `config/sources.yaml`:

| Source | Cost | Default |
|--------|------|---------|
| Research | Paid | Config-dependent |
| Announcement | Paid | Config-dependent |
| Snowball | Paid | Config-dependent |

## Usage Modes

### Default Mode (`python mi7.py`)
```bash
python mi7.py
```
- **Tier 1 sources only** (RSS + DFCF + Obsidian)
- **Audio enabled** (pyttsx3, local)
- Excludes Tier 2 paid sources

### Quick Mode (`--source quick`)
```bash
python mi7.py --source quick
```
- Only Tier 1 sources (RSS + DFCF + Obsidian)
- Skips all paid Tier 2 sources
- Fastest execution, minimal API costs

### Single Source Mode
```bash
python mi7.py --source rss      # RSS only
python mi7.py --source dfcf     # DFCF only
python mi7.py --source obsidian # Obsidian Vault only
```

## Caching Strategy

### DFCF Cache
- Location: `data/mi7.db` (dfcf_cache table)
- TTL: **48 hours**
- Automatically refreshes when stale
- Respects 50 calls/day free tier limit

### Obsidian Cache
- Location: Local file system
- TTL: 24 hours
- Scans markdown files from configured vault
- Parses frontmatter, tags, and wikilinks

## Implementation

The source orchestration is implemented in `core/source_orchestrator.py`:

```python
from core.source_orchestrator import SourceOrchestrator

orchestrator = SourceOrchestrator(config)
sources = orchestrator.get_sources_for_mode('all')  # or 'quick'
```

## API Cost Optimization

1. **Cache-First**: Check cache before API calls
2. **Tier 1 Priority**: Free/cheap sources always enabled
3. **Graceful Degradation**: Skip failing sources, don't fail pipeline
4. **Quick Mode**: For rapid testing without paid APIs

## Configuration

See `config/sources.yaml`:

```yaml
sources:
  rss:
    enabled: true
  dfcf:
    enabled: true
  obsidian:
    enabled: true
  research:
    enabled: false  # Tier 2: respects this flag
  announcement:
    enabled: false
  snowball:
    enabled: false
```
