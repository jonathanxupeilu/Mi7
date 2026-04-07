"""TXT报告生成器"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import yaml


class ReportGenerator:
    """TXT报告生成器"""

    # Default maximum number of items to include in report
    DEFAULT_MAX_ITEMS = 60

    def __init__(self, output_dir: str = "./reports", config_path: str = "./config/sources.yaml"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_items = self._load_max_items(config_path)

    def _load_max_items(self, config_path: str) -> int:
        """从配置文件加载最大条目数"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                if config and 'report' in config:
                    return config['report'].get('max_items', self.DEFAULT_MAX_ITEMS)
        except Exception as e:
            print(f"  [Report] Using default max_items: {e}")
        return self.DEFAULT_MAX_ITEMS

    def generate(self, date: datetime, items: List[Dict[str, Any]],
                 generate_audio: bool = False,
                 audio_provider: str = "edge") -> Optional[str]:
        """生成报告（TXT、Markdown 和可选的 MP3）"""
        if not items:
            return None

        # Limit to MAX_ITEMS total, keeping highest priority/relevance
        limited_items = self._limit_items(items)
        priority_groups = self._group_by_priority(limited_items)

        # 生成 TXT 报告
        txt_content = self._build_report(date, priority_groups, limited_items)
        txt_filename = f"mi7_report_{date.strftime('%Y-%m-%d')}.txt"
        txt_filepath = self.output_dir / txt_filename
        with open(txt_filepath, 'w', encoding='utf-8') as f:
            f.write(txt_content)

        # 生成 Markdown 报告
        md_content = self._build_markdown_report(date, priority_groups, limited_items)
        md_filename = f"mi7_report_{date.strftime('%Y-%m-%d')}.md"
        md_filepath = self.output_dir / md_filename
        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # 生成音频报告（如果请求）
        if generate_audio:
            try:
                if audio_provider == "elevenlabs":
                    from output.elevenlabs_audio_generator import ElevenLabsAudioGenerator
                    audio_gen = ElevenLabsAudioGenerator(output_dir=str(self.output_dir))
                    audio_path = audio_gen.generate(str(md_filepath))
                    if audio_path:
                        print(f"  音频报告 (ElevenLabs): {audio_path}")
                else:
                    from output.audio_report_generator import AudioReportGenerator
                    audio_gen = AudioReportGenerator(output_dir=str(self.output_dir))
                    audio_path = audio_gen.generate(str(md_filepath))
                    if audio_path:
                        print(f"  音频报告: {audio_path}")
            except Exception as e:
                print(f"  音频生成跳过: {e}")

        return str(txt_filepath)
        
    def _group_by_priority(self, items: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        groups = {'critical': [], 'high': [], 'medium': [], 'low': []}
        for item in items:
            priority = item.get('priority', 'low')
            if priority in groups:
                groups[priority].append(item)
            else:
                groups['low'].append(item)
        return groups
        
    def _build_report(self, date: datetime, groups: Dict[str, List[Dict]], all_items: List[Dict]) -> str:
        lines = []
        lines.append("=" * 80)
        lines.append("                         军情七处 · 每日情报简报")
        lines.append("=" * 80)
        lines.append(f"日期: {date.strftime('%Y-%m-%d')} | 处理条目: {len(all_items)}条")
        lines.append("")
        
        if groups['critical']:
            lines.append("【紧急 - 持仓直接相关】⚠️")
            lines.append("")
            for i, item in enumerate(groups['critical'], 1):
                lines.extend(self._format_item(i, item))
                
        if groups['high']:
            lines.append("【高优先级 - 宏观影响】🔥")
            lines.append("")
            for i, item in enumerate(groups['high'], 1):
                lines.extend(self._format_item(i, item))
                
        lines.append("=" * 80)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        
        return '\n'.join(lines)
        
    def generate_markdown(self, date: datetime, items: List[Dict[str, Any]]) -> str:
        """生成 Markdown 格式报告"""
        priority_groups = self._group_by_priority(items)
        report_content = self._build_markdown_report(date, priority_groups, items)
        filename = f"mi7_report_{date.strftime('%Y-%m-%d')}.md"
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        return str(filepath)

    def _build_markdown_report(self, date: datetime, groups: Dict[str, List[Dict]], all_items: List[Dict]) -> str:
        """构建 Markdown 格式报告内容"""
        lines = []
        lines.append("# 军情七处 · 每日情报简报")
        lines.append("")
        lines.append(f"**日期**: {date.strftime('%Y-%m-%d')} | **处理条目**: {len(all_items)}条")
        lines.append("")

        # 持仓概览
        lines.append("## 持仓概览")
        lines.append("")
        lines.append("| 股票代码 | 名称 | 今日关注 |")
        lines.append("|----------|------|----------|")

        # 统计各持仓相关的新闻数
        from collections import Counter
        holdings_count = Counter()
        for item in all_items:
            metadata = item.get('metadata', '{}')
            if isinstance(metadata, str):
                try:
                    import json
                    metadata = json.loads(metadata.replace("'", '"'))
                except:
                    metadata = {}
            related = metadata.get('related_holdings', [])
            for h in related:
                holdings_count[h] += 1

        # 加载持仓信息
        holdings = self._load_holdings()
        for code, info in holdings.items():
            count = holdings_count.get(code, 0)
            if count > 0:
                lines.append(f"| {code} | {info.get('name', '')} | {count}条相关 |")

        lines.append("")

        # 优先级分组
        if groups['critical']:
            lines.append("## 紧急 - 持仓直接相关")
            lines.append("")
            for i, item in enumerate(groups['critical'], 1):
                lines.extend(self._format_markdown_item(i, item))

        if groups['high']:
            lines.append("## 高优先级 - 宏观影响")
            lines.append("")
            for i, item in enumerate(groups['high'], 1):
                lines.extend(self._format_markdown_item(i, item))

        if groups['medium']:
            lines.append("## 中优先级 - 行业动态")
            lines.append("")
            for i, item in enumerate(groups['medium'], 1):
                lines.extend(self._format_markdown_item(i, item))

        if groups['low']:
            lines.append("## 低优先级 - 参考信息")
            lines.append("")
            for i, item in enumerate(groups['low'], 1):
                lines.extend(self._format_markdown_item(i, item))

        lines.append("")
        lines.append("---")
        lines.append(f"\n*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return '\n'.join(lines)

    def _format_markdown_item(self, index: int, item: Dict[str, Any]) -> List[str]:
        """格式化 Markdown 单条内容"""
        lines = []
        source = item.get('source', 'Unknown')
        title = item.get('title', '')
        url = item.get('url', '')
        summary = item.get('summary', '')
        relevance = item.get('relevance_score', 0)
        impact = item.get('impact_score', 0)
        priority = item.get('priority', 'medium')

        # 处理 metadata 可能是字符串的情况
        metadata = item.get('metadata', '{}')
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata.replace("'", '"'))
            except:
                metadata = {}
        related = metadata.get('related_holdings', [])

        # 优先级图标
        icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚪')

        lines.append(f"### {index}. {icon} [{source}] {title}")
        lines.append("")
        lines.append(f"**相关性**: {relevance}/100 | **影响力**: {impact}/100")

        if related:
            lines.append(f"**相关持仓**: {', '.join(related)}")

        lines.append("")

        if summary:
            lines.append(summary[:500])
            lines.append("")

        if url:
            lines.append(f"[原文链接]({url})")
            lines.append("")

        return lines

    def _load_holdings(self) -> Dict[str, Any]:
        """加载持仓配置"""
        import yaml
        config_path = "./config/holdings.yaml"

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config.get('portfolio', {})
        except Exception as e:
            print(f"警告: 无法加载持仓配置: {e}")
            return {}

    def _format_item(self, index: int, item: Dict[str, Any]) -> List[str]:
        """格式化单条内容"""
        lines = []
        source = item.get('source', 'Unknown')
        title = item.get('title', '')
        url = item.get('url', '')
        summary = item.get('summary', '')
        relevance = item.get('relevance_score', 0)
        impact = item.get('impact_score', 0)

        lines.append(f"{index}. [{source}] {title}")
        lines.append(f"   相关性: {'⭐' * int(relevance/20)}  |  影响力: {'⭐' * int(impact/20)}")
        if summary:
            lines.append(f"   摘要: {summary[:300]}...")
        if url:
            lines.append(f"   原文链接: {url}")
        lines.append("")
        return lines

    def _limit_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        限制报告条目数量，保留最高优先级和相关性的条目

        Args:
            items: 原始条目列表

        Returns:
            限制后的条目列表（最多MAX_ITEMS条）
        """
        if len(items) <= self.max_items:
            return items

        # Sort by priority order and relevance score
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}

        sorted_items = sorted(items, key=lambda x: (
            priority_order.get(x.get('priority', 'low'), 3),
            -x.get('relevance_score', 0)
        ))

        # Take top max_items
        limited = sorted_items[:self.max_items]

        # Log the limiting
        print(f"  [Report] Limited {len(items)} items to {len(limited)} (max: {self.max_items})")

        return limited
