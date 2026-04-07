"""Tests for default audio generation in pipeline"""
import pytest
import subprocess
import sys
import os


class TestDefaultAudioGeneration:
    """Test that default pipeline mode includes audio generation"""

    def test_audio_enabled_by_default(self):
        """Running mi7.py without --audio flag should still enable audio"""
        # Set encoding env var for Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        # Run mi7.py --help to check default values
        result = subprocess.run(
            [sys.executable, 'mi7.py', '--help'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            env=env
        )

        help_text = result.stdout or ""

        # The --audio flag help text should indicate it's enabled by default
        # Check if --no-audio exists (which would indicate proper default-on design)
        has_no_audio = '--no-audio' in help_text

        if not has_no_audio:
            # If there's no --no-audio flag, then audio is opt-in (default off)
            # which violates the requirement
            assert False, \
                "Audio is not enabled by default. Need --no-audio flag to allow disabling"

    def test_no_audio_flag_exists(self):
        """Should have --no-audio flag to disable audio when it's on by default"""
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        result = subprocess.run(
            [sys.executable, 'mi7.py', '--help'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            env=env
        )

        help_text = result.stdout or ""
        assert '--no-audio' in help_text, \
            "Missing --no-audio flag to disable audio when it's enabled by default"
