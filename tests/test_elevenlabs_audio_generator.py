"""ElevenLabs Audio report generator tests"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from output.elevenlabs_audio_generator import ElevenLabsAudioGenerator


class TestElevenLabsAudioGenerator:
    """Test ElevenLabs audio report generation"""

    def test_initialization(self):
        """Test ElevenLabsAudioGenerator initializes correctly"""
        generator = ElevenLabsAudioGenerator(output_dir="./test_audio")
        assert generator.output_dir == Path("./test_audio")
        assert generator.voice == "aria"
        assert generator.model == "eleven_multilingual_v2"

    def test_initialization_with_custom_voice(self):
        """Test initialization with custom voice"""
        generator = ElevenLabsAudioGenerator(output_dir="./test_audio", voice="george")
        assert generator.voice == "george"

    def test_text_cleaning(self):
        """Test markdown text cleaning for TTS"""
        generator = ElevenLabsAudioGenerator()

        # Test markdown removal
        dirty_text = "## Header\n\n**Bold** text and [link](http://example.com)"
        clean = generator._clean_text_for_tts(dirty_text)

        assert "##" not in clean
        assert "**" not in clean
        assert "http://example.com" not in clean
        assert "link" in clean

    def test_text_chunking(self):
        """Test long text is chunked properly for API limits"""
        generator = ElevenLabsAudioGenerator()

        # Create text longer than max_chars (5000 for ElevenLabs)
        long_text = "A" * 10000
        chunks = generator._chunk_text(long_text, max_chars=5000)

        assert len(chunks) > 1
        assert all(len(c) <= 5000 for c in chunks)

    @patch('urllib.request.urlretrieve')
    @patch('subprocess.run')
    def test_generate_audio_success(self, mock_run, mock_download, tmp_path):
        """Test successful audio generation via infsh CLI"""
        # Mock successful subprocess run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"audio_url": "https://example.com/audio.mp3"}'
        mock_run.return_value = mock_result

        generator = ElevenLabsAudioGenerator(output_dir=str(tmp_path))

        # Create a test markdown file
        test_md = tmp_path / "test_report.md"
        test_md.write_text("# Test Report\n\nThis is a test summary.", encoding='utf-8')

        result = generator.generate(str(test_md))

        assert result is not None
        assert result.endswith('.mp3')
        mock_run.assert_called()

    @patch('urllib.request.urlretrieve')
    @patch('subprocess.run')
    def test_generate_audio_with_retry(self, mock_run, mock_download, tmp_path):
        """Test audio generation with retry on failure"""
        # First call fails, second succeeds
        mock_fail = MagicMock()
        mock_fail.returncode = 1
        mock_fail.stderr = "API Error"

        mock_success = MagicMock()
        mock_success.returncode = 0
        mock_success.stdout = '{"audio_url": "https://example.com/audio.mp3"}'

        mock_run.side_effect = [mock_fail, mock_success]

        generator = ElevenLabsAudioGenerator(output_dir=str(tmp_path))

        test_md = tmp_path / "test_report.md"
        test_md.write_text("# Test Report\n\nThis is a test.", encoding='utf-8')

        result = generator.generate(str(test_md))

        assert result is not None
        assert mock_run.call_count >= 2

    def test_voice_validation(self):
        """Test that only valid ElevenLabs voices are accepted"""
        # Valid voices
        gen1 = ElevenLabsAudioGenerator(voice="aria")
        assert gen1.voice == "aria"

        gen2 = ElevenLabsAudioGenerator(voice="george")
        assert gen2.voice == "george"

        # Invalid voice defaults to aria
        gen3 = ElevenLabsAudioGenerator(voice="invalid_voice")
        assert gen3.voice == "aria"

    def test_model_selection(self):
        """Test model selection"""
        gen1 = ElevenLabsAudioGenerator(model="eleven_multilingual_v2")
        assert gen1.model == "eleven_multilingual_v2"

        gen2 = ElevenLabsAudioGenerator(model="eleven_turbo_v2_5")
        assert gen2.model == "eleven_turbo_v2_5"

        # Invalid model defaults to multilingual_v2
        gen3 = ElevenLabsAudioGenerator(model="invalid_model")
        assert gen3.model == "eleven_multilingual_v2"
