"""Tests for edge-tts retry with fallback mechanism."""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestEdgeTTSRetry:
    """Test edge-tts connection retry and fallback."""

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self, tmp_path):
        """Should retry on connection timeout and eventually succeed."""
        from output.audio_report_generator import AudioReportGenerator

        gen = AudioReportGenerator(output_dir=str(tmp_path))

        # Mock edge_tts.Communicate to fail twice then succeed
        call_count = 0

        class MockCommunicate:
            def __init__(self, text, voice):
                self.text = text
                self.voice = voice

            async def save(self, path):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Connection timeout")
                # Success on 3rd try
                with open(path, 'w') as f:
                    f.write("mock audio data")

        with patch('output.audio_report_generator.edge_tts') as mock_edge:
            mock_edge.Communicate = MockCommunicate

            # Mock chunk text and combine
            with patch.object(gen, '_chunk_text', return_value=['test text']):
                # When: Generating audio with max 3 retries
                result = await gen._try_edge_tts('test text', str(tmp_path / 'output.mp3'), max_retries=3)

        # Then: Should have retried and succeeded
        assert call_count == 3
        assert result is not None

    @pytest.mark.asyncio
    async def test_returns_none_after_all_retries_fail(self, tmp_path):
        """Should return None if all retries fail."""
        from output.audio_report_generator import AudioReportGenerator

        gen = AudioReportGenerator(output_dir=str(tmp_path))

        class MockCommunicate:
            def __init__(self, text, voice):
                pass

            async def save(self, path):
                raise Exception("Connection failed")

        with patch('output.audio_report_generator.edge_tts') as mock_edge:
            mock_edge.Communicate = MockCommunicate

            with patch.object(gen, '_chunk_text', return_value=['test text']):
                # When: Generating audio
                result = await gen._try_edge_tts('test text', str(tmp_path / 'output.mp3'), max_retries=3)

        # Then: Should return None after all retries
        assert result is None
