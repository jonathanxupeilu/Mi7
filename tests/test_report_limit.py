"""Tests for report item limiting"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import os


class TestReportItemLimit:
    """Test report generator limits items to configured maximum"""

    def test_report_limits_to_max_60_items(self):
        """Report should contain maximum 60 items regardless of input count"""
        from output.report_generator import ReportGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)

            # Create 100 dummy items
            items = [
                {
                    'title': f'Test News {i}',
                    'source': 'Test Source',
                    'url': f'http://test.com/{i}',
                    'priority': 'high' if i < 50 else 'low',
                    'relevance_score': 80 if i < 50 else 20,
                    'impact_score': 70,
                    'summary': f'Summary {i}',
                    'collected_at': datetime.now()
                }
                for i in range(100)
            ]

            # Generate report
            result = generator.generate(
                date=datetime.now(),
                items=items,
                generate_audio=False
            )

            # Verify report was created (returns txt path)
            assert result is not None
            assert Path(result).exists()

            # Check markdown file for item count
            date_str = datetime.now().strftime('%Y-%m-%d')
            md_path = Path(tmpdir) / f'mi7_report_{date_str}.md'
            assert md_path.exists(), "Markdown report should exist"

            # Read the markdown report and count items
            content = md_path.read_text(encoding='utf-8')

            # Count how many numbered items are in the report
            import re
            # Match patterns like "### 1. 🟠 [Source] Title" or "### 15. 🔴 [Source]"
            # The items are in format: ### number. emoji [Source] Title
            md_items = len(re.findall(r'^###\s+\d+\.', content, re.MULTILINE))

            # Should be limited to 60 items max
            assert md_items <= 60, f"Report contains {md_items} items, expected max 60"

    def test_report_selects_highest_priority_items(self):
        """When limiting, should keep highest priority/relevance items"""
        from output.report_generator import ReportGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)

            # Create items with varying priorities
            items = []

            # Add 30 critical items with high relevance
            for i in range(30):
                items.append({
                    'title': f'Critical News {i}',
                    'source': 'Test Source',
                    'url': f'http://test.com/critical/{i}',
                    'priority': 'critical',
                    'relevance_score': 90,
                    'impact_score': 80,
                    'summary': f'Critical summary {i}',
                    'collected_at': datetime.now()
                })

            # Add 30 high priority items
            for i in range(30):
                items.append({
                    'title': f'High News {i}',
                    'source': 'Test Source',
                    'url': f'http://test.com/high/{i}',
                    'priority': 'high',
                    'relevance_score': 60,
                    'impact_score': 50,
                    'summary': f'High summary {i}',
                    'collected_at': datetime.now()
                })

            # Add 40 low priority items
            for i in range(40):
                items.append({
                    'title': f'Low News {i}',
                    'source': 'Test Source',
                    'url': f'http://test.com/low/{i}',
                    'priority': 'low',
                    'relevance_score': 10,
                    'impact_score': 5,
                    'summary': f'Low summary {i}',
                    'collected_at': datetime.now()
                })

            # Generate report
            result = generator.generate(
                date=datetime.now(),
                items=items,
                generate_audio=False
            )

            # Read the report
            content = Path(result).read_text(encoding='utf-8')

            # Critical and high items should be included
            assert 'Critical News' in content, "Critical priority items should be in report"
            assert 'High News' in content, "High priority items should be in report"

            # Low items may or may not be included depending on limit
            # But critical/high should definitely be there

    def test_report_uses_configured_max_items(self):
        """Report generator should read max_items from config"""
        from output.report_generator import ReportGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test config with max_items = 10
            config_content = """
report:
  max_items: 10
  time_window: 48

sources:
  rss:
    enabled: true
"""
            config_path = Path(tmpdir) / "test_config.yaml"
            config_path.write_text(config_content, encoding='utf-8')

            # Create generator with custom config
            generator = ReportGenerator(
                output_dir=tmpdir,
                config_path=str(config_path)
            )

            # Verify it loaded the config
            assert generator.max_items == 10, f"Expected max_items=10, got {generator.max_items}"

            # Create 20 items
            items = [
                {
                    'title': f'Test News {i}',
                    'source': 'Test Source',
                    'url': f'http://test.com/{i}',
                    'priority': 'high',
                    'relevance_score': 80,
                    'impact_score': 70,
                    'summary': f'Summary {i}',
                    'collected_at': datetime.now()
                }
                for i in range(20)
            ]

            # Generate report
            result = generator.generate(
                date=datetime.now(),
                items=items,
                generate_audio=False
            )

            # Check markdown file
            date_str = datetime.now().strftime('%Y-%m-%d')
            md_path = Path(tmpdir) / f'mi7_report_{date_str}.md'
            content = md_path.read_text(encoding='utf-8')

            # Count items
            import re
            md_items = len(re.findall(r'^###\s+\d+\.', content, re.MULTILINE))

            # Should be limited to 10 (from config)
            assert md_items <= 10, f"Report contains {md_items} items, expected max 10 from config"
