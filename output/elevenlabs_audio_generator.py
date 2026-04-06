"""ElevenLabs Audio report generator using infsh CLI"""
import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import List, Optional


class ElevenLabsAudioGenerator:
    """Generate MP3 audio reports from markdown files using ElevenLabs TTS"""

    # Available voices
    VALID_VOICES = {
        'aria', 'alice', 'bella', 'jessica', 'laura', 'lily', 'sarah',  # Female
        'george', 'adam', 'bill', 'brian', 'callum', 'charlie', 'chris',
        'daniel', 'eric', 'harry', 'liam', 'matilda', 'river', 'roger', 'will'  # Male
    }

    # Available models
    VALID_MODELS = {
        'eleven_multilingual_v2',
        'eleven_turbo_v2_5',
        'eleven_flash_v2_5'
    }

    def __init__(self, output_dir: str = "./reports", voice: str = "aria",
                 model: str = "eleven_multilingual_v2"):
        """
        Initialize ElevenLabs audio report generator

        Args:
            output_dir: Directory to save MP3 files
            voice: Voice ID (e.g., 'aria', 'george')
            model: Model ID (eleven_multilingual_v2, eleven_turbo_v2_5, eleven_flash_v2_5)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.voice = voice if voice in self.VALID_VOICES else 'aria'
        self.model = model if model in self.VALID_MODELS else 'eleven_multilingual_v2'

    def generate(self, markdown_path: str, max_retries: int = 3) -> Optional[str]:
        """
        Convert markdown report to MP3 audio file using ElevenLabs TTS

        Args:
            markdown_path: Path to markdown file
            max_retries: Number of retries on failure

        Returns:
            Path to generated MP3 file or None if failed
        """
        md_path = Path(markdown_path)
        if not md_path.exists():
            print(f"Error: Markdown file not found: {markdown_path}")
            return None

        # Read and clean content
        content = md_path.read_text(encoding='utf-8')
        cleaned_text = self._clean_text_for_tts(content)

        if not cleaned_text or len(cleaned_text.strip()) < 10:
            print("Error: No speakable content found in markdown")
            return None

        # Generate output filename
        stem = md_path.stem
        output_path = self.output_dir / f"{stem}.mp3"

        # ElevenLabs has a 5000 character limit per request
        chunks = self._chunk_text(cleaned_text, max_chars=5000)

        if len(chunks) == 1:
            # Single chunk - generate directly
            return self._generate_single_audio(chunks[0], str(output_path), max_retries)
        else:
            # Multiple chunks - generate each and combine
            return self._generate_multi_chunk(chunks, str(output_path), max_retries)

    def _generate_single_audio(self, text: str, output_path: str,
                               max_retries: int = 3) -> Optional[str]:
        """Generate audio for single text chunk"""
        for attempt in range(max_retries):
            try:
                # Build infsh command
                cmd = [
                    'infsh', 'app', 'run', 'elevenlabs/tts',
                    '--input', json.dumps({
                        'text': text,
                        'voice': self.voice,
                        'model': self.model,
                        'output_format': 'mp3_44100_192'
                    })
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if result.returncode != 0:
                    print(f"  Attempt {attempt + 1}/{max_retries} failed: {result.stderr}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"  Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    continue

                # Parse response and download audio
                try:
                    response = json.loads(result.stdout)
                    audio_url = response.get('audio_url')
                    if audio_url:
                        self._download_audio(audio_url, output_path)
                        print(f"Audio report saved: {output_path}")
                        return output_path
                except json.JSONDecodeError:
                    # Response might be direct URL or binary
                    if result.stdout.startswith('http'):
                        self._download_audio(result.stdout.strip(), output_path)
                        print(f"Audio report saved: {output_path}")
                        return output_path

            except subprocess.TimeoutExpired:
                print(f"  Attempt {attempt + 1}/{max_retries} timed out")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                print(f"  Attempt {attempt + 1}/{max_retries} error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        return None

    def _generate_multi_chunk(self, chunks: List[str], output_path: str,
                              max_retries: int = 3) -> Optional[str]:
        """Generate audio for multiple chunks and combine"""
        temp_files = []
        success_count = 0

        for i, chunk in enumerate(chunks):
            temp_path = self.output_dir / f"temp_elevenlabs_{i}.mp3"

            # Skip if already exists and has content
            if temp_path.exists() and temp_path.stat().st_size > 0:
                temp_files.append(temp_path)
                success_count += 1
                continue

            result = self._generate_single_audio(chunk, str(temp_path), max_retries)
            if result:
                temp_files.append(Path(result))
                success_count += 1
            else:
                print(f"  Warning: Failed to generate chunk {i + 1}/{len(chunks)}")

        if not temp_files:
            print("Error: All chunks failed to generate")
            return None

        # Combine audio files
        self._combine_mp3_files(temp_files, output_path)

        # Cleanup temp files
        for temp_file in temp_files:
            temp_file.unlink(missing_ok=True)

        print(f"Audio report saved: {output_path} ({success_count}/{len(chunks)} chunks)")
        return output_path

    def _download_audio(self, url: str, output_path: str):
        """Download audio from URL"""
        urllib.request.urlretrieve(url, output_path)

    def _combine_mp3_files(self, input_paths: List[Path], output_path: str):
        """Combine multiple MP3 files into one"""
        with open(output_path, 'wb') as outfile:
            for input_path in input_paths:
                with open(input_path, 'rb') as infile:
                    outfile.write(infile.read())

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

        # Remove emojis and special symbols
        text = re.sub(r'[🔴🟠🟡🟢⚪⚠️🔥📈📉⭐]', '', text)

        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)

        # Clean up empty lines but preserve paragraph breaks
        lines = [l.strip() for l in text.split('\n')]
        paragraphs = []
        current_para = []

        for line in lines:
            if line:
                current_para.append(line)
            else:
                if current_para:
                    paragraphs.append(' '.join(current_para))
                    current_para = []

        if current_para:
            paragraphs.append(' '.join(current_para))

        return '\n\n'.join(paragraphs)

    def _chunk_text(self, text: str, max_chars: int = 5000) -> List[str]:
        """Split text into chunks for API limits"""
        if len(text) <= max_chars:
            return [text]

        chunks = []
        paragraphs = text.split('\n\n')
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para_length = len(para) + 2

            if para_length > max_chars:
                # Single paragraph too long - split by sentences
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0

                sentences = re.split(r'(?<=[.!?。！？])\s+', para)
                current_sentences = []
                sent_length = 0

                for sent in sentences:
                    if sent_length + len(sent) > max_chars:
                        if current_sentences:
                            chunks.append(' '.join(current_sentences))
                        current_sentences = [sent]
                        sent_length = len(sent)
                    else:
                        current_sentences.append(sent)
                        sent_length += len(sent) + 1

                if current_sentences:
                    chunks.append(' '.join(current_sentences))

            elif current_length + para_length > max_chars:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        # If still only one chunk and text is too long, force split by max_chars
        if len(chunks) == 1 and len(chunks[0]) > max_chars:
            forced_chunks = []
            for i in range(0, len(text), max_chars):
                forced_chunks.append(text[i:i + max_chars])
            return forced_chunks

        return chunks
