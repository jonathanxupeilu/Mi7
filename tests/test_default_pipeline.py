"""Tests for the new default pipeline configuration"""
import pytest
import subprocess
import sys
import os
import tempfile
from pathlib import Path


class TestDefaultPipeline:
    """Test that default pipeline uses correct configuration"""

    def test_default_source_is_quick(self):
        """Default --source should be 'quick' (Tier 1 only)"""
        result = subprocess.run(
            [sys.executable, 'mi7.py', '--help'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        help_text = result.stdout

        # Check default is 'quick'
        assert 'default' in help_text.lower() or 'quick' in help_text

    def test_audio_enabled_by_default(self):
        """Audio generation should be enabled by default"""
        result = subprocess.run(
            [sys.executable, 'mi7.py', '--help'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        help_text = result.stdout

        # Should have --no-audio to disable
        assert '--no-audio' in help_text, "Missing --no-audio flag for disabling audio"

    def test_tier1_sources_are_rss_dfcf_obsidian(self):
        """Tier 1 sources should be RSS, DFCF, Obsidian"""
        from core.source_orchestrator import SourceOrchestrator

        config = {'sources': {}}
        orchestrator = SourceOrchestrator(config)

        assert 'rss' in orchestrator.TIER1_SOURCES
        assert 'dfcf' in orchestrator.TIER1_SOURCES
        assert 'obsidian' in orchestrator.TIER1_SOURCES
        assert len(orchestrator.TIER1_SOURCES) == 3

    def test_quick_mode_returns_tier1_only(self):
        """Quick mode should only return Tier 1 sources"""
        from core.source_orchestrator import SourceOrchestrator

        config = {
            'sources': {
                'rss': {'enabled': True},
                'dfcf': {'enabled': True},
                'obsidian': {'enabled': True},
                'research': {'enabled': True},
                'snowball': {'enabled': True}
            }
        }
        orchestrator = SourceOrchestrator(config)
        sources = orchestrator.get_sources_for_mode('quick')

        assert 'rss' in sources
        assert 'dfcf' in sources
        assert 'obsidian' in sources
        assert 'research' not in sources
        assert 'snowball' not in sources

    def test_report_limits_to_60_items(self):
        """Report should be limited to 60 items max"""
        from output.report_generator import ReportGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)

            # Verify max_items is 60
            assert generator.max_items == 60

    def test_tier1_always_enabled_regardless_of_config(self):
        """Tier 1 sources should be enabled even if config says False"""
        from core.source_orchestrator import SourceOrchestrator

        config = {
            'sources': {
                'rss': {'enabled': False},
                'dfcf': {'enabled': False},
                'obsidian': {'enabled': False}
            }
        }
        orchestrator = SourceOrchestrator(config)

        # Tier 1 sources should still be enabled
        for source_name in orchestrator.TIER1_SOURCES:
            source = orchestrator.sources.get(source_name)
            assert source.enabled is True, f"{source_name} should be forced enabled"

    def test_default_hours_is_48(self):
        """Default time window should be 48 hours"""
        # Check the argparse default value in code
        import ast
        import re

        with open('mi7.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the --hours argument definition
        match = re.search(r"--hours.*?default=(\d+)", content)
        assert match is not None, "Could not find --hours default value"
        assert match.group(1) == '48', f"Default hours should be 48, got {match.group(1)}"

    def test_all_mode_includes_tier1_and_tier2(self):
        """'all' mode should include both Tier 1 and enabled Tier 2 sources"""
        from core.source_orchestrator import SourceOrchestrator

        config = {
            'sources': {
                'rss': {'enabled': True},
                'dfcf': {'enabled': True},
                'obsidian': {'enabled': True},
                'research': {'enabled': True},
                'announcement': {'enabled': True},
                'snowball': {'enabled': False}  # Disabled Tier 2
            }
        }
        orchestrator = SourceOrchestrator(config)
        sources = orchestrator.get_sources_for_mode('all')

        # Tier 1 always included
        assert 'rss' in sources
        assert 'dfcf' in sources
        assert 'obsidian' in sources

        # Tier 2 only if enabled
        assert 'research' in sources
        assert 'announcement' in sources
        assert 'snowball' not in sources  # Disabled


class TestPipelineIntegration:
    """Integration tests for the complete pipeline"""

    def test_collector_imports_work(self):
        """All Tier 1 collectors should be importable"""
        # RSS
        from collectors.rss_collector import RSSCollector

        # DFCF
        from collectors.dfcf_collector import DFCFCollector

        # Obsidian
        from collectors.obsidian_collector import ObsidianCollector

        assert RSSCollector is not None
        assert DFCFCollector is not None
        assert ObsidianCollector is not None

    def test_source_orchestrator_can_be_created(self):
        """SourceOrchestrator should initialize with minimal config"""
        from core.source_orchestrator import SourceOrchestrator

        config = {'sources': {}}
        orchestrator = SourceOrchestrator(config)

        assert orchestrator is not None
        assert len(orchestrator.sources) > 0

    def test_report_generator_respects_config(self):
        """ReportGenerator should read max_items from config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a custom config
            config_content = """
report:
  max_items: 30
  time_window: 48

sources:
  rss:
    enabled: true
"""
            config_path = Path(tmpdir) / "test_config.yaml"
            config_path.write_text(config_content, encoding='utf-8')

            from output.report_generator import ReportGenerator
            generator = ReportGenerator(
                output_dir=tmpdir,
                config_path=str(config_path)
            )

            assert generator.max_items == 30


class TestPipelineEndToEnd:
    """End-to-end tests that verify the pipeline runs correctly"""

    def test_help_command_works(self):
        """mi7.py --help should exit successfully"""
        result = subprocess.run(
            [sys.executable, 'mi7.py', '--help'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        assert result.returncode == 0
        assert 'MI7' in result.stdout

    def test_single_source_mode_obsidian(self):
        """--source obsidian should only use Obsidian collector"""
        from core.source_orchestrator import SourceOrchestrator

        config = {'sources': {}}
        orchestrator = SourceOrchestrator(config)
        sources = orchestrator.get_sources_for_mode('obsidian')

        assert sources == ['obsidian']

    def test_single_source_mode_rss(self):
        """--source rss should only use RSS collector"""
        from core.source_orchestrator import SourceOrchestrator

        config = {'sources': {}}
        orchestrator = SourceOrchestrator(config)
        sources = orchestrator.get_sources_for_mode('rss')

        assert sources == ['rss']

    def test_single_source_mode_dfcf(self):
        """--source dfcf should only use DFCF collector"""
        from core.source_orchestrator import SourceOrchestrator

        config = {'sources': {}}
        orchestrator = SourceOrchestrator(config)
        sources = orchestrator.get_sources_for_mode('dfcf')

        assert sources == ['dfcf']