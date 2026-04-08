#!/usr/bin/env python3
"""MI7 项目统一入口脚本"""
import sys
import os
import io
import argparse
from pathlib import Path
from argparse import Namespace

# Fix Windows encoding (only when not testing)
if sys.platform == 'win32' and not os.getenv('PYTEST_CURRENT_TEST'):
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 获取项目根目录
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

# 数据目录
DATA_DIR = PROJECT_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)


def check_api_key():
    """检查 API Key 是否设置"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY 环境变量未设置")
        print("\n请设置环境变量：")
        print("  export ANTHROPIC_API_KEY='your_key_here'")
        print("\n或在 .env 文件中添加：")
        print("  ANTHROPIC_API_KEY=your_key_here")
        return False
    return True


def cmd_collect(args):
    """采集数据命令"""
    print("=" * 60)
    print("MI7 - 数据采集")
    print("=" * 60)

    from collectors.rss_collector import RSSCollector
    from collectors.dfcf_collector import DFCFCollector
    from collectors.nitter_collector import NitterCollector
    from collectors.obsidian_collector import ObsidianCollector
    from collectors.gmail_collector import GmailCollector
    from storage.database import Database
    import yaml

    # 加载配置
    config_path = PROJECT_DIR / 'config' / 'sources.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 数据库路径
    db_path = DATA_DIR / 'mi7.db'
    db = Database(str(db_path))

    items = []

    # 根据 source 参数选择采集源
    if args.source in ['all', 'rss']:
        print("\n[1] 采集 RSS 财经源...")
        rss_config = config['sources']['rss']['native']
        if rss_config.get('enabled', True):
            try:
                collector = RSSCollector(rss_config)
                rss_items = collector.collect(hours=args.hours)
                print(f"    采集: {len(rss_items)} 条")
                items.extend(rss_items)
            except Exception as e:
                print(f"    [ERROR] RSS 采集失败: {e}")

    if args.source in ['all', 'dfcf']:
        print("\n[2] 采集东方财富...")
        try:
            dfcf_collector = DFCFCollector()
            dfcf_items = dfcf_collector.collect_all(limit_per_stock=5)
            print(f"    采集: {len(dfcf_items)} 条")
            items.extend(dfcf_items)
        except Exception as e:
            print(f"    [ERROR] 东方财富采集失败: {e}")

    if args.source in ['all', 'nitter']:
        if config['sources'].get('nitter', {}).get('enabled', False):
            print("\n[3] 采集 Nitter (Twitter)...")
            nitter_config = config['sources']['nitter']
            nitter_collector = NitterCollector(nitter_config)
            nitter_items = nitter_collector.collect(hours=args.hours)
            print(f"    采集: {len(nitter_items)} 条")
            items.extend(nitter_items)

    if args.source in ['all', 'obsidian']:
        if config['sources'].get('obsidian', {}).get('enabled', False):
            print("\n[4] 采集 Obsidian Vault...")
            obsidian_config = config['sources']['obsidian']
            obsidian_collector = ObsidianCollector(obsidian_config)
            obsidian_items = obsidian_collector.collect(hours=args.hours)
            print(f"    采集: {len(obsidian_items)} 条")
            items.extend(obsidian_items)

    if args.source in ['all', 'gmail']:
        try:
            print("\n[5] 采集 Gmail (Google Alerts)...")
            gmail_collector = GmailCollector()
            gmail_items = gmail_collector.collect(hours=args.hours)
            print(f"    采集: {len(gmail_items)} 条")
            items.extend(gmail_items)
        except Exception as e:
            print(f"    跳过: {e}")

    # 保存到数据库
    print("\n" + "=" * 60)
    print("保存到数据库...")
    saved = 0
    duplicates = 0
    for item in items:
        if not db.check_duplicate(item['url']):
            if db.insert_content(item):
                saved += 1
        else:
            duplicates += 1

    print(f"  新增: {saved}")
    print(f"  重复: {duplicates}")
    print("=" * 60)

    return saved


def cmd_analyze(args):
    """AI 分析命令"""
    if not check_api_key():
        return 0

    print("=" * 60)
    print("MI7 - AI 分析")
    print("=" * 60)

    from processors.ai_analyzer import AIAnalyzer

    db_path = DATA_DIR / 'mi7.db'
    analyzer = AIAnalyzer(str(db_path))

    processed = analyzer.process_unprocessed_content(limit=args.limit)
    print(f"\n分析完成: {processed} 条")
    print("=" * 60)

    return processed


def cmd_report(args):
    """生成报告命令"""
    print("=" * 60)
    print("MI7 - 生成报告")
    print("=" * 60)

    from output.report_generator import ReportGenerator
    from storage.database import Database
    from datetime import datetime

    db_path = DATA_DIR / 'mi7.db'
    db = Database(str(db_path))

    # 获取已分析的内容
    analyzed_items = db.get_analyzed_content(hours=args.hours, min_relevance=args.min_relevance)

    if not analyzed_items:
        print("\n[WARNING] 没有可报告的内容")
        print("  请先运行: python scripts/run.py collect")
        print("  然后运行: python scripts/run.py analyze")
        return 0

    # 生成报告
    report_gen = ReportGenerator(str(DATA_DIR))
    report_path = report_gen.generate(datetime.now(), analyzed_items)

    print(f"\n报告已保存: {report_path}")

    # 显示统计
    critical = len([i for i in analyzed_items if i.get('priority') == 'critical'])
    high = len([i for i in analyzed_items if i.get('priority') == 'high'])
    medium = len([i for i in analyzed_items if i.get('priority') == 'medium'])
    low = len([i for i in analyzed_items if i.get('priority') == 'low'])

    print("\n报告统计:")
    print(f"  Critical: {critical}")
    print(f"  High: {high}")
    print(f"  Medium: {medium}")
    print(f"  Low: {low}")
    print("=" * 60)

    return len(analyzed_items)


def cmd_run(args):
    """完整流程命令"""
    print("=" * 60)
    print("MI7 - 完整流程")
    print("=" * 60)

    # 1. 采集
    saved = cmd_collect(args)

    # 2. 分析（除非跳过）
    if not args.skip_analysis and saved > 0:
        analyze_args = Namespace(limit=50)
        cmd_analyze(analyze_args)

    # 3. 生成报告
    report_args = Namespace(hours=48, min_relevance=0)
    cmd_report(report_args)

    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)


def cmd_config(args):
    """配置管理命令"""
    config_dir = PROJECT_DIR / 'config'

    if args.show:
        print("=" * 60)
        print("MI7 - 当前配置")
        print("=" * 60)

        import yaml

        # 显示持仓
        holdings_path = config_dir / 'holdings.yaml'
        if holdings_path.exists():
            with open(holdings_path, 'r', encoding='utf-8') as f:
                holdings = yaml.safe_load(f)
            print(f"\n持仓股票: {len(holdings.get('portfolio', {}))} 只")
            for code, info in list(holdings.get('portfolio', {}).items())[:5]:
                print(f"  - {code}: {info.get('name', 'Unknown')}")
            if len(holdings.get('portfolio', {})) > 5:
                print(f"  ... 还有 {len(holdings['portfolio']) - 5} 只")

        # 显示信源
        sources_path = config_dir / 'sources.yaml'
        if sources_path.exists():
            with open(sources_path, 'r', encoding='utf-8') as f:
                sources = yaml.safe_load(f)
            print("\n信源状态:")
            for name, cfg in sources.get('sources', {}).items():
                enabled = cfg.get('enabled', False) if isinstance(cfg, dict) else False
                status = "[OK]" if enabled else "[OFF]"
                print(f"  {status} {name}")

        # 显示数据目录
        print(f"\n数据目录: {DATA_DIR}")
        print(f"  数据库: {DATA_DIR / 'mi7.db'}")
        print(f"  报告: {DATA_DIR / 'reports'}")

        print("=" * 60)

    if args.edit:
        import subprocess
        editor = os.getenv('EDITOR', 'notepad' if sys.platform == 'win32' else 'vi')
        config_file = config_dir / 'holdings.yaml'
        subprocess.run([editor, str(config_file)])


def cmd_cache(args):
    """缓存管理命令"""
    from storage.dfcf_cache import DFCFCache

    db_path = DATA_DIR / 'mi7.db'
    cache = DFCFCache(str(db_path))

    if args.stats:
        stats = cache.get_stats()
        print("=" * 60)
        print("DFCF 缓存统计")
        print("=" * 60)
        print(f"  总条目: {stats['total']}")
        print(f"  有效: {stats['valid']}")
        print(f"  过期: {stats['expired']}")
        print("=" * 60)

    if args.clear_expired:
        deleted = cache.clear_expired()
        print(f"已清理 {deleted} 条过期缓存")

    if not args.stats and not args.clear_expired:
        print("使用 --stats 查看缓存统计，或 --clear-expired 清理过期缓存")


def main():
    parser = argparse.ArgumentParser(
        description='MI7 军情七处 - 投资情报系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/run.py collect                    # 采集所有信源
  python scripts/run.py collect --source rss       # 仅采集 RSS
  python scripts/run.py analyze                    # AI 分析
  python scripts/run.py report                     # 生成报告
  python scripts/run.py run                        # 完整流程
  python scripts/run.py config --show              # 显示配置
  python scripts/run.py cache --stats              # 缓存统计
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # collect 命令
    collect_parser = subparsers.add_parser('collect', help='采集数据')
    collect_parser.add_argument('--hours', type=int, default=24,
                                help='采集最近多少小时的内容 (默认: 24)')
    collect_parser.add_argument('--source', type=str, default='all',
                                choices=['all', 'rss', 'dfcf', 'nitter', 'obsidian', 'gmail'],
                                help='选择采集来源')

    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='AI 分析')
    analyze_parser.add_argument('--limit', type=int, default=50,
                                help='每次处理的最大条目数 (默认: 50)')

    # report 命令
    report_parser = subparsers.add_parser('report', help='生成报告')
    report_parser.add_argument('--hours', type=int, default=48,
                               help='报告时间范围 (默认: 48)')
    report_parser.add_argument('--min-relevance', type=int, default=0,
                               help='最小相关性分数 (默认: 0)')

    # run 命令
    run_parser = subparsers.add_parser('run', help='完整流程')
    run_parser.add_argument('--hours', type=int, default=24)
    run_parser.add_argument('--source', type=str, default='all',
                            choices=['all', 'rss', 'dfcf', 'nitter', 'obsidian', 'gmail'])
    run_parser.add_argument('--skip-analysis', action='store_true',
                            help='跳过 AI 分析')

    # config 命令
    config_parser = subparsers.add_parser('config', help='配置管理')
    config_parser.add_argument('--show', action='store_true',
                               help='显示当前配置')
    config_parser.add_argument('--edit', action='store_true',
                               help='编辑持仓配置')

    # cache 命令
    cache_parser = subparsers.add_parser('cache', help='缓存管理')
    cache_parser.add_argument('--stats', action='store_true',
                              help='显示缓存统计')
    cache_parser.add_argument('--clear-expired', action='store_true',
                              help='清理过期缓存')

    args = parser.parse_args()

    if args.command == 'collect':
        cmd_collect(args)
    elif args.command == 'analyze':
        cmd_analyze(args)
    elif args.command == 'report':
        cmd_report(args)
    elif args.command == 'run':
        cmd_run(args)
    elif args.command == 'config':
        cmd_config(args)
    elif args.command == 'cache':
        cmd_cache(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
