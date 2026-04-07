"""Audio report generator using edge-tts with fallback to gTTS"""
import asyncio
import re
import ssl
import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime

try:
    import edge_tts
    import aiohttp
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


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

        if not EDGE_TTS_AVAILABLE and not GTTS_AVAILABLE:
            raise ImportError(
                "No TTS library available. Install one of:\n"
                "  pip install edge-tts  # Recommended, higher quality\n"
                "  pip install gtts      # Fallback option"
            )

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

            # Try edge-tts first (better quality)
            if EDGE_TTS_AVAILABLE:
                result = await self._try_edge_tts(full_text, str(output_path))
                if result:
                    return result
                print("  Edge-TTS failed, trying fallback...")

            # Fallback to gTTS
            if GTTS_AVAILABLE:
                result = self._try_gtts(full_text, str(output_path))
                if result:
                    return result

            print("  All TTS providers failed")
            return None

        except Exception as e:
            print(f"Error generating audio report: {e}")
            return None

    async def _try_edge_tts(self, text: str, output_path: str, max_retries: int = 3) -> Optional[str]:
        """Try edge-tts with retry logic"""
        # Chunk if too long
        chunks = self._chunk_text(text, max_chars=5000)

        temp_files = []

        # Monkey-patch aiohttp TCPConnector to bypass SSL verification
        # This works around corporate/VPN SSL inspection
        original_init = aiohttp.TCPConnector.__init__

        def patched_init(self, *args, **kwargs):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            kwargs['ssl'] = ssl_context
            original_init(self, *args, **kwargs)

        aiohttp.TCPConnector.__init__ = patched_init

        try:
            for attempt in range(max_retries):
                try:
                    for i, chunk in enumerate(chunks):
                        temp_path = self.output_dir / f"temp_{i}_{attempt}.mp3"

                        # Skip if already generated
                        if temp_path.exists() and temp_path.stat().st_size > 0:
                            temp_files.append(temp_path)
                            continue

                        communicate = edge_tts.Communicate(chunk, self.voice)
                        await communicate.save(str(temp_path))

                        if temp_path.exists() and temp_path.stat().st_size > 0:
                            temp_files.append(temp_path)
                        else:
                            raise Exception(f"Empty output for chunk {i}")

                    # Combine all chunks
                    await self._combine_mp3_files(temp_files, output_path)

                    # Cleanup temp files
                    for temp_file in temp_files:
                        temp_file.unlink(missing_ok=True)

                    print(f"Audio report saved: {output_path}")
                    return output_path

                except Exception as e:
                    print(f"  Edge-TTS attempt {attempt + 1}/{max_retries} failed: {e}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        print(f"  Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        # Save partial results
                        if temp_files:
                            print(f"  Saving partial result ({len(temp_files)} chunks)")
                            await self._combine_mp3_files(temp_files, output_path)
                            # Don't cleanup - keep partial results
                            return output_path

            return None

        finally:
            # Restore original
            aiohttp.TCPConnector.__init__ = original_init

    def _try_gtts(self, text: str, output_path: str, max_chars: int = 5000) -> Optional[str]:
        """Try gTTS (Google TTS) as fallback"""
        try:
            # gTTS has limits, so we chunk
            chunks = self._chunk_text(text, max_chars=max_chars)

            temp_files = []
            for i, chunk in enumerate(chunks):
                temp_path = self.output_dir / f"gtts_temp_{i}.mp3"

                tts = gTTS(text=chunk, lang='zh-cn', slow=False)
                tts.save(str(temp_path))

                if temp_path.exists() and temp_path.stat().st_size > 0:
                    temp_files.append(temp_path)

            # Combine chunks
            if temp_files:
                self._combine_mp3_files_sync(temp_files, output_path)

                # Cleanup
                for temp_file in temp_files:
                    temp_file.unlink(missing_ok=True)

                print(f"Audio report saved (via gTTS): {output_path}")
                return output_path

        except Exception as e:
            print(f"  gTTS failed: {e}")

        return None

    async def _combine_mp3_files(self, input_paths: List[Path], output_path: str):
        """Combine multiple MP3 files into one (async)"""
        # Simple concatenation for MP3 files
        with open(output_path, 'wb') as outfile:
            for input_path in input_paths:
                with open(input_path, 'rb') as infile:
                    outfile.write(infile.read())

    def _combine_mp3_files_sync(self, input_paths: List[Path], output_path: str):
        """Combine multiple MP3 files into one (sync version)"""
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
        text = re.sub(r'[🔴🟠🟡🟢⚪⚠️🔥📈📉⭐]', '', text)

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

        # Split by paragraphs first
        paragraphs = text.split('\n\n')

        for para in paragraphs:
            para_length = len(para) + 2  # +2 for newlines

            # If a single paragraph is too long, split it by sentences
            if para_length > max_chars:
                # Save current chunk first
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Split long paragraph by sentences
                sentences = re.split(r'(?<=[.!?。！？])\s+', para)
                for sentence in sentences:
                    sent_length = len(sentence) + 1
                    if sent_length > max_chars:
                        # Even a single sentence is too long - split by max_chars
                        for i in range(0, len(sentence), max_chars):
                            chunk = sentence[i:i + max_chars]
                            if current_length + len(chunk) + 1 > max_chars:
                                if current_chunk:
                                    chunks.append('\n\n'.join(current_chunk))
                                current_chunk = [chunk]
                                current_length = len(chunk)
                            else:
                                current_chunk.append(chunk)
                                current_length += len(chunk) + 1
                    elif current_length + sent_length > max_chars:
                        if current_chunk:
                            chunks.append('\n\n'.join(current_chunk))
                        current_chunk = [sentence]
                        current_length = sent_length
                    else:
                        current_chunk.append(sentence)
                        current_length += sent_length
            elif current_length + para_length > max_chars:
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

        # If still only one chunk and text is too long, force split by max_chars
        if len(chunks) == 1 and len(chunks[0]) > max_chars:
            forced_chunks = []
            for i in range(0, len(text), max_chars):
                forced_chunks.append(text[i:i + max_chars])
            return forced_chunks

        return chunks

    def generate(self, markdown_path: str) -> Optional[str]:
        """Synchronous wrapper for generate_from_markdown"""
        return asyncio.run(self.generate_from_markdown(markdown_path))
