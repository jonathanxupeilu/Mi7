"""Test text-to-audio conversion independently."""
import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestTextToAudio:
    """Test converting text report to audio independently."""

    def test_text_report_exists(self):
        """Verify text report was generated."""
        report_path = Path("reports/mi7_report_2026-04-07.txt")
        assert report_path.exists(), "Text report not found"
        assert report_path.stat().st_size > 0, "Text report is empty"

    @pytest.mark.asyncio
    async def test_convert_text_to_audio(self):
        """Convert existing text report to audio."""
        from output.audio_report_generator import AudioReportGenerator

        report_path = Path("reports/mi7_report_2026-04-07.txt")
        if not report_path.exists():
            pytest.skip("Text report not found")

        # Create audio generator
        gen = AudioReportGenerator(output_dir="reports")

        # Convert to markdown first (audio generator expects markdown)
        md_path = Path("reports/mi7_report_2026-04-07.md")
        if md_path.exists():
            # Generate audio from markdown
            result = await gen.generate_from_markdown(str(md_path))

            # Then: Should generate audio file
            assert result is not None, "Audio generation failed"
            assert Path(result).exists(), "Audio file not created"
            assert Path(result).stat().st_size > 0, "Audio file is empty"
