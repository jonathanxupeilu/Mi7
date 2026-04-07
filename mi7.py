#!/usr/bin/env python3
"""MI7 - Main Entry"""
import sys
import io
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

import yaml
import ssl
from datetime import datetime, timedelta
from storage.database import Database
from output.report_generator import ReportGenerator
from core.source_orchestrator import SourceOrchestrator

ssl._create_default_https_context = ssl._create_unverified_context


class MI7:
    def __init__(self):
        with open('config/sources.yaml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.db = Database()

    def run(self, hours=48, skip_analysis=False, source='all', generate_audio=False, audio_provider='edge'):
        """运行完整流程：采集 → 存储 → AI分析 → 生成报告"""
        print("="*60)
        print("MI7 - Intelligence Report Generation")
        print("="*60)
        print(f"\nTime window: last {hours} hours")
        print(f"Source mode: {source}\n")

        # Initialize orchestrator for smart source selection
        orchestrator = SourceOrchestrator(self.config)
        sources_to_use = orchestrator.get_sources_for_mode(source)

        print(f"Active sources: {', '.join(sources_to_use)}")
        print("-"*60)

        items = []

        # 1. 采集数据 - Tier 1 sources (always on, with caching)
        if 'rss' in sources_to_use:
            from collectors.rss_collector import RSSCollector
            rss_config = self.config['sources']['rss']['native']
            collector = RSSCollector(rss_config)
            print("[1/4] Collecting data from RSS sources...")
            rss_items = collector.collect(hours=hours)
            print(f"  RSS collected: {len(rss_items)} items")
            items.extend(rss_items)

        if 'dfcf' in sources_to_use:
            from collectors.dfcf_collector import DFCFCollector
            print("\n  Collecting from 东方财富...")
            dfcf_collector = DFCFCollector()
            dfcf_items = dfcf_collector.collect_all(limit_per_stock=5)
            print(f"  东方财富 collected: {dfcf_items} items")

        if 'notebooklm' in sources_to_use:
            try:
                from collectors.notebooklm_collector import NotebookLMCollector
                print("\n  Collecting from NotebookLM...")
                notebooklm_config = self.config['sources']['notebooklm']
                notebooklm_collector = NotebookLMCollector(notebooklm_config)
                notebooklm_items = notebooklm_collector.collect(hours=hours)
                print(f"  NotebookLM: {len(notebooklm_items)} items")
                items.extend(notebooklm_items)
            except Exception as e:
                print(f"  NotebookLM error: {e}")

        # Tier 2 sources (conditional/paid)
        if 'research' in sources_to_use:
            try:
                from collectors.research_collector import ResearchCollector
                print("\n  Collecting research reports...")
                research_collector = ResearchCollector()
                research_items = research_collector.collect_all(limit_per_stock=5)
                print(f"  Research reports: {research_items} items")
            except Exception as e:
                print(f"  Research error: {e}")

        if 'announcement' in sources_to_use:
            try:
                from collectors.announcement_collector import AnnouncementCollector
                print("\n  Collecting announcements...")
                announcement_collector = AnnouncementCollector()
                announcement_items = announcement_collector.collect_all(limit_per_stock=5)
                print(f"  Announcements: {announcement_items} items")
            except Exception as e:
                print(f"  Announcement error: {e}")

        if 'snowball' in sources_to_use:
            try:
                # Snowball collector would be imported here
                print("\n  Collecting from Snowball...")
                print("  Snowball: not yet implemented")
            except Exception as e:
                print(f"  Snowball error: {e}")

        # 2. 保存到数据库
        print("\n[2/4] Saving to database...")
        saved = 0
        duplicates = 0
        for item in items:
            if not self.db.check_duplicate(item['url']):
                if self.db.insert_content(item):
                    saved += 1
            else:
                duplicates += 1
        print(f"  New items: {saved}")
        print(f"  Duplicates: {duplicates}")

        # 3. AI 分析
        if not skip_analysis and saved > 0:
            print("\n[3/4] AI analysis (Claude API)...")
            try:
                from processors.ai_analyzer import AIAnalyzer
                analyzer = AIAnalyzer()
                processed = analyzer.process_unprocessed_content(limit=50)
                print(f"  Analyzed: {processed} items")
            except Exception as e:
                print(f"  Warning: AI analysis failed: {e}")
                print("  Continuing without analysis...")

        # 4. 生成报告
        print("\n[4/4] Generating report...")
        try:
            report_gen = ReportGenerator()
            analyzed_items = self.db.get_analyzed_content(hours=hours)

            if analyzed_items:
                report_path = report_gen.generate(datetime.now(), analyzed_items,
                                                    generate_audio=generate_audio,
                                                    audio_provider=audio_provider)
                print(f"  Report saved: {report_path}")

                # 显示摘要
                print(f"\n  Report summary:")
                critical = len([i for i in analyzed_items if i.get('priority') == 'critical'])
                high = len([i for i in analyzed_items if i.get('priority') == 'high'])
                medium = len([i for i in analyzed_items if i.get('priority') == 'medium'])
                low = len([i for i in analyzed_items if i.get('priority') == 'low'])
                print(f"    Critical: {critical}")
                print(f"    High: {high}")
                print(f"    Medium: {medium}")
                print(f"    Low: {low}")
            else:
                print("  No analyzed content available for report")

        except Exception as e:
            print(f"  Error generating report: {e}")

        print("\n" + "="*60)
        print("Done!")
        print("="*60)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='MI7 - 军情七处情报报告生成')
    parser.add_argument('--hours', type=int, default=48, help='采集最近多少小时的内容')
    parser.add_argument('--skip-analysis', action='store_true', help='跳过AI分析')
    parser.add_argument('--source', type=str, default='quick',
                        choices=['all', 'quick', 'rss', 'dfcf', 'nitter', 'gmail', 'research', 'announcement', 'snowball', 'notebooklm'],
                        help='选择采集来源：all(全部), quick(仅Tier 1: RSS+DFCF+NotebookLM), rss, dfcf(东方财富), nitter, gmail, research(研报), announcement(公告), snowball(雪球), notebooklm')
    parser.add_argument('--audio', action='store_true', help='同时生成MP3音频报告（默认已启用）')
    parser.add_argument('--audio-provider', type=str, default='edge',
                        choices=['edge', 'elevenlabs'],
                        help='音频提供商: edge (免费) 或 elevenlabs (高质量)')
    args = parser.parse_args()

    mi7 = MI7()
    mi7.run(args.hours, skip_analysis=args.skip_analysis, source=args.source,
            generate_audio=True, audio_provider=args.audio_provider)
