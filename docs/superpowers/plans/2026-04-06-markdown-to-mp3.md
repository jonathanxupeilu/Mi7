# Markdown to MP3 Audio Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the generated markdown reports to MP3 audio files using text-to-speech (TTS) technology.

**Architecture:** Create a new `AudioReportGenerator` class that reads the markdown report, converts text to speech using a TTS library (edge-tts for Chinese support), and outputs an MP3 file. Integrate with existing `ReportGenerator` as an optional output format.

**Tech Stack:** Python, edge-tts (Microsoft Edge TTS, free, supports Chinese), asyncio, pathlib

---

## File Structure

| File | Purpose |
|------|---------|
| `output/audio_report_generator.py` | New module for TTS conversion and MP3 generation |
| `output/report_generator.py` | Modify to optionally trigger audio generation |
| `tests/test_audio_report_generator.py` | Unit tests for audio generation |
| `requirements.txt` | Add edge-tts dependency |
| `mi7.py` | Add CLI flag for audio report generation |

---

## Task 1: Add edge-tts Dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add edge-tts to requirements**

```txt
# Existing dependencies
pyyaml>=6.0
requests>=2.28.0
feedparser>=6.0.10
python-dotenv>=0.19.0
pytest>=7.0.0

# New: Text-to-speech for audio reports
edge-tts>=6.1.0
```

- [ ] **Step 2: Commit dependency update**

```bash
git add requirements.txt
git commit -m "deps: add edge-tts for audio report generation"
```

---

## Task 2: Create AudioReportGenerator Class

**Files:**
- Create: `output/audio_report_generator.py`

- [ ] **Step 1: Write the failing test**

**Create:** `tests/test_audio_report_generator.py`
```python
"""Audio report generator tests"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock

from output.audio_report_generator import AudioReportGenerator


class TestAudioReportGenerator:
    """Test audio report generation"""

    def test_initialization(self):
        """Test AudioReportGenerator initializes correctly"""
        generator = AudioReportGenerator(output_dir="./test_audio")
        assert generator.output_dir == Path("./test_audio")
        assert generator.voice == "zh-CN-XiaoxiaoNeural"

    def test_text_cleaning(self):
        """Test markdown text cleaning for TTS"""
        generator = AudioReportGenerator()
        
        # Test markdown removal
        dirty_text = "## Header\n\n**Bold** text and [link](http://example.com)"
        clean = generator._clean_text_for_tts(dirty_text)
        
        assert "##" not in clean
        assert "**" not in clean
        assert "http://example.com" not in clean
        assert "link" in clean

    def test_text_chunking(self):
        """Test long text is chunked properly"""
        generator = AudioReportGenerator()
        
        # Create text longer than max_chars
        long_text = "A" * 10000
        chunks = generator._chunk_text(long_text, max_chars=5000)
        
        assert len(chunks) > 1
        assert all(len(c) <= 5000 for c in chunks)

    @pytest.mark.asyncio
    async def test_generate_audio_report(self, tmp_path):
        """Test generating audio from markdown file"""
        generator = AudioReportGenerator(output_dir=str(tmp_path))
        
        # Create a test markdown file
        test_md = tmp_path / "test_report.md"
        test_md.write_text("# Test Report\n\nThis is a test summary.", encoding='utf-8')
        
        # Mock the TTS communication
        with patch('edge_tts.Communicate') as mock_communicate:
            mock_communicate_instance = AsyncMock()
            mock_communicate_instance.save = AsyncMock()
            mock_communicate.return_value = mock_communicate_instance
            
            result = await generator.generate_from_markdown(str(test_md))
            
            assert result is not None
            assert result.endswith('.mp3')
            mock_communicate.assert_called_once()

    def test_split_report_sections(self):
        """Test parsing markdown into speakable sections"""
        generator = AudioReportGenerator()
        
        md_content = """# Report Title

## Section One
Content for section one.

## Section Two
Content for section two.
"""
        sections = generator._parse_markdown_sections(md_content)
        
        assert len(sections) >= 2
        assert any("Section One" in s for s in sections)
        assert any("Section Two" in s for s in sections)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_audio_report_generator.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'output.audio_report_generator'"

- [ ] **Step 3: Implement AudioReportGenerator**

**Create:** `output/audio_report_generator.py`
```python
"""Audio report generator using edge-tts"""
import asyncio
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


class AudioReportGenerator:
    """Generate MP3 audio reports from markdown files"""
    
    # Chinese voices from edge-tts
    CHINESE_VOICES = {
        'xiaoxiao': 'zh-CN-XiaoxiaoNeural',      # 女声，新闻风格
        'xiaoyi': 'zh-CN-XiaoyiNeural',          # 女声，温柔
        'yunjian': 'zh-CN-YunjianNeural',        # 男声，新闻风格
        'yunxi': 'zh-CN-YunxiNeural',            # 男声，轻松
    }
    
    def __init__(self, output_dir: str = "./reports", voice: str = "xiaoxiao"):
        """
        Initialize audio report generator
        
        Args:
            output_dir: Directory to save MP3 files
            voice: Voice name (xiaoxiao, xiaoyi, yunjian, yunxi)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.voice = self.CHINESE_VOICES.get(voice, self.CHINESE_VOICES['xiaoxiao'])
        
        if not EDGE_TTS_AVAILABLE:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts")
    
    async def generate_from_markdown(self, markdown_path: str) -> Optional[str]:
        """
        Convert markdown report to MP3 audio file
        
        Args:
            markdown_path: Path to markdown file
            
        Returns:
            Path to generated MP3 file or None if failed
        """
        md_path = Path(markdown_path)
        if not md_path.exists():
            print(f"Error: Markdown file not found: {markdown_path}")
            return None
        
        # Read markdown content
        content = md_path.read_text(encoding='utf-8')
        
        # Parse into sections
        sections = self._parse_markdown_sections(content)
        
        if not sections:
            print("Error: No speakable content found in markdown")
            return None
        
        # Clean text for TTS
        cleaned_sections = [self._clean_text_for_tts(s) for s in sections]
        
        # Generate output filename
        stem = md_path.stem
        output_path = self.output_dir / f"{stem}.mp3"
        
        try:
            # Combine all text
            full_text = "\n\n".join(cleaned_sections)
            
            # Chunk if too long (edge-tts has limits)
            chunks = self._chunk_text(full_text, max_chars=5000)
            
            if len(chunks) == 1:
                # Single chunk - direct conversion
                await self._text_to_mp3(chunks[0], str(output_path))
            else:
                # Multiple chunks - convert each and combine
                temp_files = []
                for i, chunk in enumerate(chunks):
                    temp_path = self.output_dir / f"{stem}_temp_{i}.mp3"
                    await self._text_to_mp3(chunk, str(temp_path))
                    temp_files.append(temp_path)
                
                # Combine audio files
                await self._combine_mp3_files(temp_files, str(output_path))
                
                # Cleanup temp files
                for temp_file in temp_files:
                    temp_file.unlink(missing_ok=True)
            
            print(f"Audio report saved: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"Error generating audio report: {e}")
            return None
    
    async def _text_to_mp3(self, text: str, output_path: str):
        """Convert text to MP3 using edge-tts"""
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_path)
    
    async def _combine_mp3_files(self, input_paths: List[Path], output_path: str):
        """Combine multiple MP3 files into one"""
        # Simple concatenation for MP3 files
        with open(output_path, 'wb') as outfile:
            for input_path in input_paths:
                with open(input_path, 'rb') as infile:
                    outfile.write(infile.read())
    
    def _parse_markdown_sections(self, content: str) -> List[str]:
        """Parse markdown into speakable sections"""
        sections = []
        
        # Split by headers
        lines = content.split('\n')
        current_section = []
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                if current_section:
                    sections.append('\n'.join(current_section))
                    current_section = []
                continue
            
            # Add line to current section
            current_section.append(line)
        
        # Add remaining content
        if current_section:
            sections.append('\n'.join(current_section))
        
        # Filter out empty sections and metadata
        sections = [s for s in sections if len(s.strip()) > 10]
        
        return sections
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean markdown formatting for text-to-speech"""
        # Remove markdown headers
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        
        # Remove bold/italic markers
        text = re.sub(r'\*\*', '', text)
        text = re.sub(r'\*', '', text)
        text = re.sub(r'__', '', text)
        text = re.sub(r'_', '', text)
        
        # Remove links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Remove bare URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove markdown tables (keep content)
        text = re.sub(r'\|', ' ', text)
        text = re.sub(r'---+', ' ', text)
        
        # Remove emojis and special symbols that don't translate well to speech
        text = re.sub(r'[🔴🟠🟡🟢⚪⚠️🔥📈📉]', '', text)
        
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Clean up empty lines
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        return '\n'.join(lines)
    
    def _chunk_text(self, text: str, max_chars: int = 5000) -> List[str]:
        """Split text into chunks for TTS processing"""
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Split by paragraphs
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            para_length = len(para) + 2  # +2 for newlines
            
            if current_length + para_length > max_chars:
                # Save current chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
        
        # Add remaining
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def generate(self, markdown_path: str) -> Optional[str]:
        """Synchronous wrapper for generate_from_markdown"""
        return asyncio.run(self.generate_from_markdown(markdown_path))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pip install edge-tts
pytest tests/test_audio_report_generator.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit the implementation**

```bash
git add output/audio_report_generator.py tests/test_audio_report_generator.py
git commit -m "feat: add AudioReportGenerator for MP3 report conversion"
```

---

## Task 3: Integrate Audio Generation into ReportGenerator

**Files:**
- Modify: `output/report_generator.py:14-35`

- [ ] **Step 1: Modify ReportGenerator to support audio output**

```python
# Add to imports at top of report_generator.py
from typing import Optional

# In generate() method, add audio parameter
def generate(self, date: datetime, items: List[Dict[str, Any]], 
             generate_audio: bool = False) -> Optional[str]:
    """Generate report (TXT, Markdown, and optionally MP3)"""
    if not items:
        return None

    priority_groups = self._group_by_priority(items)

    # Generate TXT report
    txt_content = self._build_report(date, priority_groups, items)
    txt_filename = f"mi7_report_{date.strftime('%Y-%m-%d')}.txt"
    txt_filepath = self.output_dir / txt_filename
    with open(txt_filepath, 'w', encoding='utf-8') as f:
        f.write(txt_content)

    # Generate Markdown report
    md_content = self._build_markdown_report(date, priority_groups, items)
    md_filename = f"mi7_report_{date.strftime('%Y-%m-%d')}.md"
    md_filepath = self.output_dir / md_filename
    with open(md_filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    # Generate Audio report if requested
    if generate_audio:
        try:
            from output.audio_report_generator import AudioReportGenerator
            audio_gen = AudioReportGenerator(output_dir=str(self.output_dir))
            audio_path = audio_gen.generate(str(md_filepath))
            if audio_path:
                print(f"  Audio report: {audio_path}")
        except Exception as e:
            print(f"  Audio generation skipped: {e}")

    return str(txt_filepath)
```

- [ ] **Step 2: Run existing tests to ensure no regression**

```bash
pytest tests/test_report_generator.py -v 2>&1 || echo "No existing tests"
pytest tests/ -k "report" -v
```
Expected: No failures in existing tests

- [ ] **Step 3: Commit integration**

```bash
git add output/report_generator.py
git commit -m "feat: integrate audio report generation into ReportGenerator"
```

---

## Task 4: Add CLI Flag for Audio Generation

**Files:**
- Modify: `mi7.py:170-180`

- [ ] **Step 1: Add --audio flag to CLI**

```python
# In the main block, add argument:
parser.add_argument('--audio', action='store_true', 
                    help='同时生成MP3音频报告（需要edge-tts）')

# Pass audio flag to report generation
report_gen = ReportGenerator()
analyzed_items = self.db.get_analyzed_content(hours=hours)

if analyzed_items:
    report_path = report_gen.generate(datetime.now(), analyzed_items, 
                                      generate_audio=args.audio)
```

- [ ] **Step 2: Test the CLI**

```bash
python mi7.py --help | grep -A1 audio
```
Expected: Shows `--audio` flag in help

- [ ] **Step 3: Commit CLI update**

```bash
git add mi7.py
git commit -m "feat: add --audio CLI flag for MP3 report generation"
```

---

## Task 5: Create Standalone Audio Conversion Script

**Files:**
- Create: `scripts/convert_report_to_audio.py`

- [ ] **Step 1: Create standalone conversion script**

```python
#!/usr/bin/env python3
"""Standalone script to convert existing markdown reports to MP3"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from output.audio_report_generator import AudioReportGenerator


def main():
    parser = argparse.ArgumentParser(description='Convert MI7 markdown report to MP3 audio')
    parser.add_argument('markdown_file', help='Path to markdown report file')
    parser.add_argument('-o', '--output', help='Output MP3 file path (optional)')
    parser.add_argument('-v', '--voice', default='xiaoxiao',
                        choices=['xiaoxiao', 'xiaoyi', 'yunjian', 'yunxi'],
                        help='Voice for TTS (default: xiaoxiao)')
    parser.add_argument('--output-dir', default='./reports',
                        help='Output directory for MP3 file')
    
    args = parser.parse_args()
    
    # Validate input file
    md_path = Path(args.markdown_file)
    if not md_path.exists():
        print(f"Error: File not found: {args.markdown_file}")
        sys.exit(1)
    
    # Generate audio
    print(f"Converting {md_path.name} to MP3...")
    print(f"Using voice: {args.voice}")
    
    generator = AudioReportGenerator(
        output_dir=args.output_dir,
        voice=args.voice
    )
    
    mp3_path = generator.generate(str(md_path))
    
    if mp3_path:
        print(f"\nSuccess! Audio saved to: {mp3_path}")
        
        # Get file size
        size_mb = Path(mp3_path).stat().st_size / (1024 * 1024)
        print(f"File size: {size_mb:.1f} MB")
    else:
        print("\nFailed to generate audio report")
        sys.exit(1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Make script executable and test**

```bash
chmod +x scripts/convert_report_to_audio.py
python scripts/convert_report_to_audio.py --help
```
Expected: Shows usage help

- [ ] **Step 3: Test with a sample file**

```bash
python scripts/convert_report_to_audio.py reports/mi7_report_2026-04-06.md --voice xiaoxiao
```
Expected: Generates MP3 file in reports/

- [ ] **Step 4: Commit standalone script**

```bash
git add scripts/convert_report_to_audio.py
git commit -m "feat: add standalone script to convert markdown reports to MP3"
```

---

## Task 6: Update Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add audio generation section to README**

```markdown
## Audio Reports (MP3)

Convert reports to MP3 audio for listening on-the-go:

```bash
# Generate report with audio (during pipeline run)
python mi7.py --hours 48 --audio

# Convert existing markdown report to MP3
python scripts/convert_report_to_audio.py reports/mi7_report_2026-04-06.md

# Choose different voice
python scripts/convert_report_to_audio.py report.md --voice yunjian
```

**Available Voices:**
- `xiaoxiao` (默认): 女声，新闻播报风格
- `xiaoyi`: 女声，温柔风格
- `yunjian`: 男声，新闻播报风格
- `yunxi`: 男声，轻松风格

**Requirements:**
```bash
pip install edge-tts
```

**Note:** First run may download voice model (~50MB).
```

- [ ] **Step 2: Commit documentation**

```bash
git add README.md
git commit -m "docs: add audio report generation instructions"
```

---

## Self-Review Checklist

**1. Spec Coverage:**
- [x] Convert markdown to MP3 - Task 2, 3, 5
- [x] Chinese TTS support - edge-tts with zh-CN voices
- [x] CLI integration - Task 4
- [x] Standalone script - Task 5
- [x] Documentation - Task 6

**2. Placeholder Scan:**
- [x] No "TBD" or "TODO" found
- [x] All code is complete and copy-paste ready
- [x] All commands have expected output defined
- [x] Exact file paths used throughout

**3. Type Consistency:**
- [x] `AudioReportGenerator` class defined in Task 2
- [x] `generate_from_markdown()` async method
- [x] `generate()` synchronous wrapper
- [x] Voice names consistent: xiaoxiao, xiaoyi, yunjian, yunxi

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-06-markdown-to-mp3.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** - Fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session, batch execution with checkpoints

**Which approach would you prefer?**
