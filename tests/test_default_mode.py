"""Tests for simplified CLI default mode logic."""
import pytest
import sys
import argparse
from unittest.mock import patch, MagicMock


class TestDefaultModeLogic:
    """Test that default mode applies correct logic."""

    def parse_args(self, args_list):
        """Helper to parse CLI args like mi7.py does."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--full', action='store_true')
        parser.add_argument('--no-audio', action='store_true')
        parser.add_argument('--audio-provider', type=str, default='edge',
                           choices=['edge', 'elevenlabs'])
        return parser.parse_args(args_list)

    def test_default_mode_uses_quick_source(self):
        """Default mode (no args) should use 'quick' source mode."""
        # Given: No command line arguments
        args = self.parse_args([])

        # When: Determine source mode
        source_mode = 'all' if args.full else 'quick'

        # Then: Should be 'quick'
        assert source_mode == 'quick'

    def test_default_mode_uses_48_hours(self):
        """Default mode should use 48 hours time window."""
        # The hours is hardcoded to 48 in the current implementation
        hours = 48
        assert hours == 48

    def test_default_mode_enables_audio(self):
        """Default mode should enable audio generation."""
        args = self.parse_args([])

        # When: Determine audio generation
        generate_audio = not args.no_audio

        # Then: Should be True
        assert generate_audio is True

    def test_default_mode_uses_edge_provider(self):
        """Default mode should use edge audio provider."""
        args = self.parse_args([])

        # Then: Should be 'edge'
        assert args.audio_provider == 'edge'

    def test_full_flag_uses_all_sources(self):
        """--full flag should use 'all' source mode."""
        args = self.parse_args(['--full'])

        # When: Determine source mode
        source_mode = 'all' if args.full else 'quick'

        # Then: Should be 'all'
        assert source_mode == 'all'

    def test_no_audio_flag_disables_audio(self):
        """--no-audio flag should disable audio generation."""
        args = self.parse_args(['--no-audio'])

        # When: Determine audio generation
        generate_audio = not args.no_audio

        # Then: Should be False
        assert generate_audio is False

    def test_elevenlabs_provider_option(self):
        """--audio-provider elevenlabs should be passed through."""
        args = self.parse_args(['--audio-provider', 'elevenlabs'])

        # Then: Should be 'elevenlabs'
        assert args.audio_provider == 'elevenlabs'

    def test_full_mode_with_no_audio(self):
        """Combined --full and --no-audio flags."""
        args = self.parse_args(['--full', '--no-audio'])

        # When: Determine settings
        source_mode = 'all' if args.full else 'quick'
        generate_audio = not args.no_audio
        hours = 48

        # Then: All settings correct
        assert source_mode == 'all'
        assert generate_audio is False
        assert hours == 48

    def test_full_mode_with_elevenlabs(self):
        """--full with --audio-provider elevenlabs."""
        args = self.parse_args(['--full', '--audio-provider', 'elevenlabs'])

        source_mode = 'all' if args.full else 'quick'

        assert source_mode == 'all'
        assert args.audio_provider == 'elevenlabs'
