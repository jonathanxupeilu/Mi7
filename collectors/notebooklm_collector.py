"""NotebookLM 采集器 - 从 NotebookLM 获取投资相关内容"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 添加 notebooklm skill 路径
sys.path.insert(0, str(Path.home() / '.agents' / 'skills' / 'notebooklm'))


class NotebookLMCollector:
    """NotebookLM 采集器 - 基于关键词搜索内容"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.notebook_url = config.get('notebook_url')
        # 支持 'keywords' 和 'search_keywords' 两种配置
        self.keywords = config.get('keywords', config.get('search_keywords', []))
        self.enabled = config.get('enabled', True)
        self.db = None  # 用于数据库去重

    def _query_notebooklm(self, question: str) -> List[Dict[str, Any]]:
        """兼容测试的方法名"""
        return self._search_notebooklm(question)

        # 尝试导入 NotebookLM skill 的查询功能
        try:
            sys.path.insert(0, str(Path.home() / '.agents' / 'skills' / 'notebooklm' / 'scripts'))
            # 使用 skill 的认证状态
            self.auth_file = Path.home() / '.agents' / 'skills' / 'notebooklm' / 'data' / 'browser_state' / 'state.json'
        except Exception as e:
            print(f"[WARN] NotebookLM skill not configured: {e}")

    def _keyword_matches(self, content: str, keywords: List[str]) -> bool:
        """检查内容是否包含任一关键词（不区分大小写）"""
        if not keywords:
            return True
        content_lower = content.lower()
        return any(kw.lower() in content_lower for kw in keywords)

    def _search_notebooklm(self, query: str) -> List[Dict[str, Any]]:
        """
        查询 NotebookLM
        使用 skill 的 ask_question.py 脚本
        """
        try:
            import subprocess
            import json

            # 尝试多个可能的路径
            possible_paths = [
                Path.home() / '.agents' / 'skills' / 'notebooklm',
                Path('C:/Users/jonath/.agents/skills/notebooklm'),
                Path.home() / '.claude' / 'skills' / 'notebooklm',
            ]

            skill_dir = None
            for p in possible_paths:
                if p.exists():
                    skill_dir = p
                    break

            if not skill_dir:
                print("[ERROR] NotebookLM skill not found in any standard location")
                return []

            venv_python = skill_dir / '.venv' / 'Scripts' / 'python.exe'
            script = skill_dir / 'scripts' / 'ask_question.py'

            if not venv_python.exists():
                print(f"[ERROR] NotebookLM venv not found at: {venv_python}")
                return []

            # 运行查询
            result = subprocess.run(
                [str(venv_python), str(script), '--question', query, '--notebook-url', self.notebook_url],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=120
            )

            if result.returncode != 0:
                print(f"[WARN] NotebookLM query failed: {result.stderr[:200]}")
                return []

            # 解析输出，提取答案部分
            output = result.stdout

            # 找到答案部分
            items = []
            if 'Got answer' in output or '====' in output:
                # 提取实际内容
                content_start = output.find('====')
                if content_start > 0:
                    content = output[content_start:].replace('=', '').strip()

                    # 只要内容不为空就添加（关键词已在查询时使用）
                    if content and len(content) > 50:
                        items.append({
                            'title': f'NotebookLM: {query}',
                            'content': content[:3000],
                            'url': self.notebook_url,
                            'source': 'NotebookLM',
                            'published_at': datetime.now(),
                            'matched_keyword': query
                        })

            return items

        except Exception as e:
            print(f"[ERROR] NotebookLM search failed: {e}")
            return []

    def _get_matched_keyword(self, content: str) -> str:
        """获取匹配的关键词"""
        content_lower = content.lower()
        for kw in self.keywords:
            if kw.lower() in content_lower:
                return kw
        return ''

    def _format_content(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """格式化为 MI7 标准格式"""
        return {
            'title': raw.get('title', 'NotebookLM Content'),
            'content': raw.get('content', '')[:3000],  # 限制长度
            'url': raw.get('url', self.notebook_url),
            'source': 'NotebookLM',
            'published_at': raw.get('published_at', datetime.now()),
            'priority': 'medium',  # 默认优先级
            'relevance_score': 70,  # 基础相关性分数
            'matched_keyword': raw.get('matched_keyword', '')
        }

    def _filter_duplicates(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于标题去重，可选数据库检查"""
        seen_titles = set()
        unique_items = []
        for item in items:
            title = item.get('title', '')
            if not title or title in seen_titles:
                continue

            # 如果配置了数据库，检查数据库重复
            if self.db and hasattr(self.db, 'check_duplicate'):
                try:
                    # 构造一个 URL 用于去重检查
                    url = item.get('url', self.notebook_url or '')
                    if self.db.check_duplicate(url):
                        continue
                except:
                    pass

            seen_titles.add(title)
            unique_items.append(item)
        return unique_items

    def query_with_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        使用指定关键词查询
        """
        if not self.enabled:
            return []

        all_results = []
        for kw in keywords:
            results = self._query_notebooklm(kw)  # 使用兼容测试的方法名
            all_results.extend(results)

        # 去重并格式化
        unique_results = self._filter_duplicates(all_results)
        return [self._format_content(r) for r in unique_results]

    def collect(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        采集 NotebookLM 内容
        基于配置的关键词列表搜索
        """
        if not self.enabled:
            print("[NotebookLM] Disabled")
            return []

        if not self.notebook_url:
            print("[NotebookLM] No notebook URL configured")
            return []

        if not self.keywords:
            print("[NotebookLM] No keywords configured")
            return []

        print(f"[NotebookLM] Searching with {len(self.keywords)} keywords...")

        # 使用配置的关键词搜索
        results = self.query_with_keywords(self.keywords)

        print(f"[NotebookLM] Found {len(results)} matching items")
        return results


if __name__ == '__main__':
    # 测试
    config = {
        'enabled': True,
        'notebook_url': 'https://notebooklm.google.com/notebook/972f8723-f63c-40d8-946b-e9f4e9c18a4f',
        'keywords': ['economy', 'debt', 'investment', 'stock', 'louis gave', 'inflation', 'macro', 'geopolitical']
    }

    collector = NotebookLMCollector(config)
    items = collector.collect(hours=24)

    print(f"\nCollected {len(items)} items:")
    for item in items[:3]:
        print(f"  - {item['title'][:50]}... (matched: {item.get('matched_keyword', 'N/A')})")
