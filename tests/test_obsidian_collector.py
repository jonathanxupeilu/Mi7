"""Tests for Obsidian vault collector"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import os

from collectors.obsidian_collector import ObsidianCollector


class TestObsidianCollectorInit:
    """Test ObsidianCollector initialization"""

    def test_initializes_with_valid_config(self):
        """Should initialize with valid vault path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                'vault_path': tmpdir,
                'folders': ['notes'],
                'keywords': ['investment'],
                'tags': ['finance']
            }

            collector = ObsidianCollector(config)

            assert collector.vault_path == Path(tmpdir)
            assert collector.folders == ['notes']
            assert collector.keywords == ['investment']
            assert collector.tags == ['finance']
            assert collector.enabled is True

    def test_disabled_if_vault_not_found(self):
        """Should disable collector if vault path doesn't exist"""
        config = {
            'vault_path': '/nonexistent/path',
            'folders': [],
            'keywords': []
        }

        collector = ObsidianCollector(config)

        assert collector.enabled is False


class TestFrontmatterParsing:
    """Test YAML frontmatter parsing"""

    def test_parses_simple_frontmatter(self):
        """Should parse basic YAML frontmatter"""
        collector = ObsidianCollector({'vault_path': '.'})
        content = """---
title: Test Note
date: 2026-04-08
tags: [finance, investment]
---
# Content here
"""
        frontmatter = collector._parse_frontmatter(content)

        assert frontmatter.get('title') == 'Test Note'
        assert frontmatter.get('tags') == ['finance', 'investment']

    def test_returns_empty_dict_if_no_frontmatter(self):
        """Should return empty dict if no frontmatter present"""
        collector = ObsidianCollector({'vault_path': '.'})
        content = "# Just a note\n\nNo frontmatter here."

        frontmatter = collector._parse_frontmatter(content)

        assert frontmatter == {}

    def test_handles_invalid_yaml(self):
        """Should handle malformed YAML gracefully"""
        collector = ObsidianCollector({'vault_path': '.'})
        content = """---
title: Test
invalid yaml content: [unclosed
---
# Content
"""
        frontmatter = collector._parse_frontmatter(content)

        assert frontmatter == {}


class TestTagExtraction:
    """Test tag extraction from notes"""

    def test_extracts_hash_tags_from_content(self):
        """Should extract #tag format from content"""
        collector = ObsidianCollector({'vault_path': '.'})
        content = "# Note\n\nThis has #finance and #investment tags\nAlso #stock/analysis nested"

        tags = collector._extract_tags(content)

        assert 'finance' in tags
        assert 'investment' in tags
        assert 'stock/analysis' in tags

    def test_extracts_tags_from_frontmatter(self):
        """Should extract tags from YAML frontmatter"""
        collector = ObsidianCollector({'vault_path': '.'})
        content = """---
tags: [finance, macro]
---
# Content
"""
        tags = collector._extract_tags(content)

        assert 'finance' in tags
        assert 'macro' in tags

    def test_extracts_single_tag_from_frontmatter(self):
        """Should handle single tag string in frontmatter"""
        collector = ObsidianCollector({'vault_path': '.'})
        content = """---
tags: finance
---
# Content
"""
        tags = collector._extract_tags(content)

        assert 'finance' in tags


class TestWikilinkExtraction:
    """Test [[wikilink]] extraction"""

    def test_extracts_basic_wikilinks(self):
        """Should extract [[note]] format links"""
        collector = ObsidianCollector({'vault_path': '.'})
        content = "This links to [[Investment Analysis]] and [[Stock Research]]"

        links = collector._extract_wikilinks(content)

        assert 'Investment Analysis' in links
        assert 'Stock Research' in links

    def test_extracts_wikilinks_with_display_text(self):
        """Should extract [[note|display]] format"""
        collector = ObsidianCollector({'vault_path': '.'})
        content = "See [[Investment Analysis|my analysis]] for details"

        links = collector._extract_wikilinks(content)

        assert 'Investment Analysis' in links

    def test_returns_empty_list_if_no_wikilinks(self):
        """Should return empty list when no wikilinks"""
        collector = ObsidianCollector({'vault_path': '.'})
        content = "Just regular text with no links"

        links = collector._extract_wikilinks(content)

        assert links == []


class TestCriteriaMatching:
    """Test keyword and tag matching"""

    def test_matches_keyword_in_content(self):
        """Should match keywords in content"""
        collector = ObsidianCollector({
            'vault_path': '.',
            'keywords': ['investment', 'stock']
        })
        content = "# Note\n\nThis is about investment strategies."
        frontmatter = {}
        tags = []

        matches = collector._matches_criteria(content, frontmatter, tags)

        assert matches is True

    def test_matches_tag_in_tags_list(self):
        """Should match tags in note tags"""
        collector = ObsidianCollector({
            'vault_path': '.',
            'tags': ['finance', 'macro']
        })
        content = "# Note"
        frontmatter = {}
        tags = ['finance', 'analysis']

        matches = collector._matches_criteria(content, frontmatter, tags)

        assert matches is True

    def test_returns_true_if_no_criteria(self):
        """Should return all notes if no criteria set"""
        collector = ObsidianCollector({
            'vault_path': '.',
            'keywords': [],
            'tags': []
        })
        content = "# Random note"
        frontmatter = {}
        tags = []

        matches = collector._matches_criteria(content, frontmatter, tags)

        assert matches is True

    def test_case_insensitive_keyword_match(self):
        """Should match keywords case-insensitively"""
        collector = ObsidianCollector({
            'vault_path': '.',
            'keywords': ['INVESTMENT']
        })
        content = "This is about investment strategies."
        frontmatter = {}
        tags = []

        matches = collector._matches_criteria(content, frontmatter, tags)

        assert matches is True


class TestRelevanceScoring:
    """Test relevance score calculation"""

    def test_base_score_is_50(self):
        """Should start with base score of 50"""
        collector = ObsidianCollector({
            'vault_path': '.',
            'keywords': [],
            'tags': []
        })
        content = "Some content"
        frontmatter = {}
        tags = []

        score = collector._calculate_relevance(content, frontmatter, tags)

        assert score == 50

    def test_keyword_match_increases_score(self):
        """Should add 10 points per keyword match"""
        collector = ObsidianCollector({
            'vault_path': '.',
            'keywords': ['investment', 'stock']
        })
        content = "This covers investment and stock topics."
        frontmatter = {}
        tags = []

        score = collector._calculate_relevance(content, frontmatter, tags)

        assert score >= 70  # 50 base + 10*2 keywords

    def test_tag_match_increases_score(self):
        """Should add 15 points per tag match"""
        collector = ObsidianCollector({
            'vault_path': '.',
            'tags': ['finance']
        })
        content = "Content"
        frontmatter = {}
        tags = ['finance', 'analysis']

        score = collector._calculate_relevance(content, frontmatter, tags)

        assert score >= 65  # 50 base + 15 for tag match

    def test_priority_in_frontmatter_increases_score(self):
        """Should add points for priority field"""
        collector = ObsidianCollector({'vault_path': '.'})
        content = "Content"
        frontmatter = {'priority': 'critical'}
        tags = []

        score = collector._calculate_relevance(content, frontmatter, tags)

        assert score >= 80  # 50 base + 30 for critical

    def test_score_capped_at_100(self):
        """Should cap score at 100"""
        collector = ObsidianCollector({
            'vault_path': '.',
            'keywords': ['a', 'b', 'c', 'd', 'e', 'f'],
            'tags': ['x', 'y', 'z']
        })
        content = "a b c d e f"
        frontmatter = {'priority': 'critical'}
        tags = ['x', 'y', 'z']

        score = collector._calculate_relevance(content, frontmatter, tags)

        assert score <= 100


class TestCollect:
    """Test the main collect method"""

    def test_collects_matching_notes_from_vault(self):
        """Should find and return matching notes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)

            # Create test note
            note_path = vault / "investment_note.md"
            note_path.write_text("""---
title: Investment Analysis
---
# Investment Analysis

This note discusses stock market strategies.
#finance #investment
""", encoding='utf-8')

            collector = ObsidianCollector({
                'vault_path': str(vault),
                'folders': [],
                'keywords': ['investment'],
                'tags': []
            })

            items = collector.collect(hours=0)

            assert len(items) >= 1
            assert any('Investment' in item['title'] for item in items)

    def test_filters_by_time_window(self):
        """Should filter notes by modification time"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)

            # Create note
            note_path = vault / "old_note.md"
            note_path.write_text("# Old Note\n\nContent about investment.")

            # Set old modification time
            old_time = datetime.now() - timedelta(hours=72)
            import os
            os.utime(note_path, (old_time.timestamp(), old_time.timestamp()))

            collector = ObsidianCollector({
                'vault_path': str(vault),
                'folders': [],
                'keywords': ['investment']
            })

            # 48 hour window should exclude 72 hour old note
            items = collector.collect(hours=48)

            assert len(items) == 0

    def test_skips_hidden_files(self):
        """Should skip .hidden files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)

            # Create hidden file
            hidden_path = vault / ".hidden_note.md"
            hidden_path.write_text("# Investment", encoding='utf-8')

            # Create regular file
            note_path = vault / "visible_note.md"
            note_path.write_text("# Investment", encoding='utf-8')

            collector = ObsidianCollector({
                'vault_path': str(vault),
                'folders': [],
                'keywords': ['investment']
            })

            items = collector.collect(hours=0)

            assert len(items) == 1
            # Title comes from heading, not filename
            assert items[0]['title'] == 'Investment'

    def test_scans_specific_folders(self):
        """Should only scan specified folders"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)

            # Create folder structure
            folder_a = vault / "04-资源"
            folder_a.mkdir()
            folder_b = vault / "99-附件"
            folder_b.mkdir()

            # Create notes in different folders
            (folder_a / "note_a.md").write_text("# Investment analysis", encoding='utf-8')
            (folder_b / "note_b.md").write_text("# Investment data", encoding='utf-8')

            collector = ObsidianCollector({
                'vault_path': str(vault),
                'folders': ['04-资源'],
                'keywords': ['investment']
            })

            items = collector.collect(hours=0)

            assert len(items) == 1
            assert 'note_a' in items[0]['file_path']


class TestItemFormatting:
    """Test item formatting for MI7 pipeline"""

    def test_formats_item_with_all_fields(self):
        """Should format item with expected fields"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            note_path = vault / "test_note.md"
            note_path.write_text("""---
title: Test Note
priority: high
---
# Test Note
Content about investment.
[[Related Note]]
#finance
""", encoding='utf-8')

            collector = ObsidianCollector({
                'vault_path': str(vault),
                'keywords': [],
                'tags': []
            })

            content = note_path.read_text(encoding='utf-8')
            frontmatter = collector._parse_frontmatter(content)
            tags = collector._extract_tags(content)
            item = collector._format_item(note_path, content, frontmatter, tags)

            assert item['title'] == 'Test Note'
            assert item['source'] == 'Obsidian'
            assert 'obsidian://' in item['url']  # obsidian://open?vault=...
            assert 'finance' in item['tags']
            assert 'Related Note' in item['wikilinks']
            assert item['priority'] == 'high'

    def test_uses_filename_if_no_title(self):
        """Should use filename as title if no title in frontmatter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir)
            note_path = vault / "my_analysis.md"
            note_path.write_text("# Some Heading\n\nContent.", encoding='utf-8')

            collector = ObsidianCollector({'vault_path': str(vault)})
            content = note_path.read_text(encoding='utf-8')
            frontmatter = collector._parse_frontmatter(content)
            tags = collector._extract_tags(content)
            item = collector._format_item(note_path, content, frontmatter, tags)

            # Should use heading from content
            assert 'Some Heading' in item['title'] or item['title'] == 'my_analysis'