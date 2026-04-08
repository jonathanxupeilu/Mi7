"""Obsidian Vault 采集器 - 从 Obsidian 笔记库获取投资相关内容"""
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import yaml


class ObsidianCollector:
    """Obsidian Vault 采集器 - 搜索并提取笔记内容"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.vault_path = Path(config.get('vault_path', ''))
        self.folders = config.get('folders', [])
        self.keywords = config.get('keywords', [])
        self.tags = config.get('tags', [])
        self.enabled = config.get('enabled', True)
        self.db = None  # 用于数据库去重

        # 验证 vault 路径
        if not self.vault_path.exists():
            print(f"[Obsidian] Vault path not found: {self.vault_path}")
            self.enabled = False

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """解析 YAML frontmatter"""
        frontmatter = {}

        # 匹配 --- 包裹的 frontmatter
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            try:
                frontmatter = yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError:
                pass

        return frontmatter

    def _extract_tags(self, content: str) -> List[str]:
        """提取笔记中的标签"""
        tags = set()

        # 从 frontmatter 提取
        frontmatter = self._parse_frontmatter(content)
        if 'tags' in frontmatter:
            fm_tags = frontmatter['tags']
            if isinstance(fm_tags, list):
                tags.update(fm_tags)
            elif isinstance(fm_tags, str):
                tags.add(fm_tags)

        # 从内容提取 #tag 格式
        content_tags = re.findall(r'#(\w+(?:/\w+)*)', content)
        tags.update(content_tags)

        return list(tags)

    def _extract_wikilinks(self, content: str) -> List[str]:
        """提取 [[wikilink]] 链接"""
        links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)
        return links

    def _matches_criteria(self, content: str, frontmatter: Dict, tags: List[str]) -> bool:
        """检查笔记是否匹配搜索条件"""
        # 如果没有设置条件，返回所有笔记
        if not self.keywords and not self.tags:
            return True

        # 检查关键词
        if self.keywords:
            content_lower = content.lower()
            for kw in self.keywords:
                if kw.lower() in content_lower:
                    return True

        # 检查标签
        if self.tags:
            for tag in self.tags:
                if tag in tags or tag.lstrip('#') in tags:
                    return True

        # 检查 frontmatter 字段
        if self.keywords:
            for key, value in frontmatter.items():
                if isinstance(value, str):
                    for kw in self.keywords:
                        if kw.lower() in value.lower():
                            return True

        return False

    def _get_modified_time(self, file_path: Path) -> datetime:
        """获取文件修改时间"""
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime)

    def _format_item(self, file_path: Path, content: str, frontmatter: Dict, tags: List[str]) -> Dict[str, Any]:
        """格式化为 MI7 标准格式"""
        # 移除 frontmatter 获取正文
        body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)

        # 获取标题
        title = frontmatter.get('title', file_path.stem)

        # 从正文提取标题（如果 frontmatter 没有标题）
        if title == file_path.stem:
            heading_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
            if heading_match:
                title = heading_match.group(1)

        # 截取摘要
        summary = body[:500].strip()
        summary = re.sub(r'#+\s+', '', summary)  # 移除标题标记
        summary = re.sub(r'\[\[|\]\]', '', summary)  # 移除 wikilink 标记
        summary = summary.replace('\n', ' ')[:300]

        # 构建相对路径（从 vault 根目录）
        rel_path = file_path.relative_to(self.vault_path)

        return {
            'title': title,
            'content': body[:3000],
            'summary': summary,
            'url': f"obsidian://open?vault={self.vault_path.name}&file={str(rel_path).replace('/', '%2F')}",
            'source': 'Obsidian',
            'file_path': str(file_path),
            'published_at': self._get_modified_time(file_path),
            'tags': tags,
            'wikilinks': self._extract_wikilinks(content),
            'frontmatter': frontmatter,
            'priority': frontmatter.get('priority', 'medium'),
            'relevance_score': self._calculate_relevance(content, frontmatter, tags)
        }

    def _calculate_relevance(self, content: str, frontmatter: Dict, tags: List[str]) -> int:
        """计算相关性分数"""
        score = 50  # 基础分

        # 关键词匹配加分
        if self.keywords:
            for kw in self.keywords:
                if kw.lower() in content.lower():
                    score += 10

        # 标签匹配加分
        if self.tags:
            for tag in self.tags:
                if tag in tags or tag.lstrip('#') in tags:
                    score += 15

        # frontmatter priority 字段
        priority = frontmatter.get('priority', '')
        if priority == 'critical':
            score += 30
        elif priority == 'high':
            score += 20

        return min(score, 100)

    def _scan_folder(self, folder_path: Path) -> List[Dict[str, Any]]:
        """扫描文件夹中的 Markdown 文件"""
        items = []

        if not folder_path.exists():
            return items

        for md_file in folder_path.rglob('*.md'):
            # 跳过隐藏文件和 .obsidian 目录
            if md_file.name.startswith('.') or '.obsidian' in str(md_file):
                continue

            try:
                content = md_file.read_text(encoding='utf-8')

                # 解析元数据
                frontmatter = self._parse_frontmatter(content)
                tags = self._extract_tags(content)

                # 检查是否匹配条件
                if self._matches_criteria(content, frontmatter, tags):
                    item = self._format_item(md_file, content, frontmatter, tags)
                    items.append(item)

            except Exception as e:
                print(f"[Obsidian] Error reading {md_file}: {e}")

        return items

    def collect(self, hours: int = 48) -> List[Dict[str, Any]]:
        """
        采集 Obsidian Vault 内容

        Args:
            hours: 时间窗口（小时），筛选最近修改的笔记

        Returns:
            笔记列表
        """
        if not self.enabled:
            print("[Obsidian] Disabled")
            return []

        if not self.vault_path.exists():
            print(f"[Obsidian] Vault not found: {self.vault_path}")
            return []

        print(f"[Obsidian] Scanning vault: {self.vault_path.name}")
        print(f"[Obsidian] Folders: {', '.join(self.folders) if self.folders else 'all'}")
        print(f"[Obsidian] Keywords: {len(self.keywords)}, Tags: {len(self.tags)}")

        all_items = []
        cutoff_time = datetime.now() - __import__('datetime').timedelta(hours=hours)

        if self.folders:
            # 扫描指定文件夹
            for folder in self.folders:
                folder_path = self.vault_path / folder
                items = self._scan_folder(folder_path)
                all_items.extend(items)
        else:
            # 扫描整个 vault
            items = self._scan_folder(self.vault_path)
            all_items.extend(items)

        # 按时间筛选
        if hours:
            all_items = [
                item for item in all_items
                if item.get('published_at', datetime.min) >= cutoff_time
            ]

        # 按相关性排序
        all_items.sort(key=lambda x: -x.get('relevance_score', 0))

        print(f"[Obsidian] Found {len(all_items)} matching notes")

        return all_items

    def collect_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """收集所有匹配的笔记（不限时间）"""
        return self.collect(hours=0)[:limit]


if __name__ == '__main__':
    # 测试
    config = {
        'enabled': True,
        'vault_path': 'E:/makeAlife/VaultTech/Vault Tech',
        'folders': ['04-资源'],
        'keywords': ['投资', '股票', '分析', '财务'],
        'tags': ['investing', 'finance', 'stock']
    }

    collector = ObsidianCollector(config)
    items = collector.collect(hours=48)

    print(f"\nCollected {len(items)} items:")
    for item in items[:5]:
        print(f"  - {item['title'][:50]}... (score: {item['relevance_score']})")