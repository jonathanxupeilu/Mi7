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

        # Mock the TTS communication to succeed on first try
        with patch('edge_tts.Communicate') as mock_communicate:
            mock_communicate_instance = AsyncMock()
            mock_communicate_instance.save = AsyncMock()
            mock_communicate.return_value = mock_communicate_instance

            result = await generator.generate_from_markdown(str(test_md))

            assert result is not None
            assert result.endswith('.mp3')
            # Should be called at least once (may retry on failure)
            assert mock_communicate.call_count >= 1

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

    @pytest.mark.asyncio
    async def test_gtts_fallback(self, tmp_path):
        """Test gTTS fallback when edge-tts fails"""
        generator = AudioReportGenerator(output_dir=str(tmp_path))

        # Create a test markdown file
        test_md = tmp_path / "test_report.md"
        test_md.write_text("# Test Report\n\nThis is a test summary.", encoding='utf-8')

        # Mock edge-tts to always fail
        with patch('edge_tts.Communicate') as mock_edge:
            mock_edge.side_effect = Exception("SSL Error")

            result = await generator.generate_from_markdown(str(test_md))

            # Should succeed via gTTS fallback
            assert result is not None
            assert result.endswith('.mp3')
