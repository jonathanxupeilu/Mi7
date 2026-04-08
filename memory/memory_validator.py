"""
Memory 系统验证与恢复工具
符合 Agent Harness 规范
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class MemoryValidator:
    """Memory 系统验证器"""

    REQUIRED_FIELDS = ['status', 'summary']
    OPTIONAL_FIELDS = ['created', 'updated', 'artifacts', 'next_actions']
    VALID_STATUSES = ['active', 'archived', 'deprecated', 'draft']

    def __init__(self, memory_dir: str = None):
        self.memory_dir = Path(memory_dir) if memory_dir else Path(__file__).parent
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.fixed: List[Dict] = []

    def validate_file(self, filepath: Path) -> Tuple[bool, Dict]:
        """
        验证单个 memory 文件
        返回: (是否有效, 元数据字典)
        """
        result = {
            'filepath': str(filepath),
            'valid': False,
            'errors': [],
            'warnings': [],
            'metadata': {}
        }

        try:
            content = filepath.read_text(encoding='utf-8')
        except Exception as e:
            result['errors'].append(f"无法读取文件: {e}")
            return False, result

        # 解析 frontmatter
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not frontmatter_match:
            result['errors'].append("缺少 frontmatter (---)")
            return False, result

        try:
            import yaml
            metadata = yaml.safe_load(frontmatter_match.group(1))
            if not isinstance(metadata, dict):
                result['errors'].append("frontmatter 格式错误，应为 YAML 字典")
                return False, result
        except Exception as e:
            result['errors'].append(f"YAML 解析错误: {e}")
            return False, result

        result['metadata'] = metadata

        # 验证必填字段
        for field in self.REQUIRED_FIELDS:
            if field not in metadata:
                result['errors'].append(f"缺少必填字段: {field}")

        # 验证状态值
        if 'status' in metadata and metadata['status'] not in self.VALID_STATUSES:
            result['errors'].append(
                f"无效的状态值: {metadata['status']}, "
                f"应为: {', '.join(self.VALID_STATUSES)}"
            )

        # 验证日期格式
        for date_field in ['created', 'updated']:
            if date_field in metadata and metadata[date_field]:
                try:
                    datetime.strptime(str(metadata[date_field]), '%Y-%m-%d')
                except ValueError:
                    result['warnings'].append(
                        f"{date_field} 日期格式建议为 YYYY-MM-DD: {metadata[date_field]}"
                    )

        # 验证 artifacts
        if 'artifacts' in metadata:
            if not isinstance(metadata['artifacts'], list):
                result['warnings'].append("artifacts 应为列表")
            else:
                for artifact in metadata['artifacts']:
                    artifact_path = filepath.parent / artifact
                    if not artifact_path.exists():
                        result['warnings'].append(f"artifact 文件不存在: {artifact}")

        result['valid'] = len(result['errors']) == 0
        return result['valid'], result

    def validate_all(self) -> Dict:
        """验证所有 memory 文件"""
        results = {
            'valid_files': [],
            'invalid_files': [],
            'warnings': [],
            'total': 0
        }

        memory_files = list(self.memory_dir.rglob('*.md'))
        results['total'] = len(memory_files)

        for filepath in memory_files:
            valid, result = self.validate_file(filepath)
            if valid:
                results['valid_files'].append(result)
            else:
                results['invalid_files'].append(result)

            if result.get('warnings'):
                results['warnings'].extend(result['warnings'])

        return results

    def fix_file(self, filepath: Path, auto_fix: bool = True) -> bool:
        """
        修复 memory 文件
        返回: 是否修复成功
        """
        try:
            content = filepath.read_text(encoding='utf-8')

            # 检查是否有 frontmatter
            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

            if not frontmatter_match:
                # 添加默认 frontmatter
                new_frontmatter = self._generate_frontmatter(filepath, content)
                new_content = new_frontmatter + '\n' + content
                filepath.write_text(new_content, encoding='utf-8')
                self.fixed.append({
                    'filepath': str(filepath),
                    'action': '添加 frontmatter'
                })
                return True

            # 修复现有 frontmatter
            import yaml
            metadata = yaml.safe_load(frontmatter_match.group(1))
            if not isinstance(metadata, dict):
                metadata = {}

            fixes = []

            # 添加缺失的必填字段
            if 'status' not in metadata:
                metadata['status'] = 'active'
                fixes.append('添加 status: active')

            if 'summary' not in metadata:
                metadata['summary'] = self._extract_summary(content)
                fixes.append('添加 summary')

            # 添加 created 日期
            if 'created' not in metadata:
                metadata['created'] = datetime.now().strftime('%Y-%m-%d')
                fixes.append('添加 created 日期')

            # 更新 updated 日期
            metadata['updated'] = datetime.now().strftime('%Y-%m-%d')

            if fixes and auto_fix:
                new_frontmatter = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
                new_content = f'---\n{new_frontmatter}---\n' + content[frontmatter_match.end():]
                filepath.write_text(new_content, encoding='utf-8')
                self.fixed.append({
                    'filepath': str(filepath),
                    'action': ', '.join(fixes)
                })

            return True

        except Exception as e:
            self.errors.append({
                'filepath': str(filepath),
                'error': str(e)
            })
            return False

    def _generate_frontmatter(self, filepath: Path, content: str) -> str:
        """生成默认 frontmatter"""
        import yaml

        metadata = {
            'status': 'active',
            'summary': self._extract_summary(content),
            'created': datetime.now().strftime('%Y-%m-%d'),
            'updated': datetime.now().strftime('%Y-%m-%d'),
            'artifacts': [],
            'next_actions': []
        }

        frontmatter = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
        return f'---\n{frontmatter}---'

    def _extract_summary(self, content: str) -> str:
        """从内容中提取摘要"""
        # 尝试从第一行标题提取
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            return title_match.group(1)

        # 尝试从第一段提取
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if paragraphs:
            first_para = paragraphs[0]
            # 去掉 markdown 标记
            first_para = re.sub(r'[#\[\]\*\`]', '', first_para)
            return first_para[:100] + '...' if len(first_para) > 100 else first_para

        return "无摘要"

    def get_report(self) -> str:
        """生成验证报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("Memory 系统验证报告")
        lines.append("=" * 60)
        lines.append(f"时间: {datetime.now().isoformat()}")
        lines.append(f"Memory 目录: {self.memory_dir}")
        lines.append("")

        results = self.validate_all()

        lines.append(f"总文件数: {results['total']}")
        lines.append(f"有效文件: {len(results['valid_files'])}")
        lines.append(f"无效文件: {len(results['invalid_files'])}")
        lines.append(f"警告数: {len(results['warnings'])}")
        lines.append("")

        if results['invalid_files']:
            lines.append("-" * 60)
            lines.append("无效文件:")
            lines.append("-" * 60)
            for f in results['invalid_files']:
                lines.append(f"\n文件: {f['filepath']}")
                for error in f['errors']:
                    lines.append(f"  ❌ {error}")

        if results['warnings']:
            lines.append("\n" + "-" * 60)
            lines.append("警告:")
            lines.append("-" * 60)
            for w in results['warnings']:
                lines.append(f"  ⚠️  {w}")

        if self.fixed:
            lines.append("\n" + "-" * 60)
            lines.append("已修复:")
            lines.append("-" * 60)
            for f in self.fixed:
                lines.append(f"  ✅ {f['filepath']}: {f['action']}")

        lines.append("\n" + "=" * 60)
        return '\n'.join(lines)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='Memory 系统验证工具')
    parser.add_argument('--dir', help='Memory 目录路径', default=None)
    parser.add_argument('--fix', action='store_true', help='自动修复问题')
    parser.add_argument('--file', help='验证单个文件')

    args = parser.parse_args()

    validator = MemoryValidator(args.dir)

    if args.file:
        filepath = Path(args.file)
        valid, result = validator.validate_file(filepath)
        print(f"文件: {filepath}")
        print(f"有效: {valid}")
        if result['errors']:
            print("错误:")
            for e in result['errors']:
                print(f"  - {e}")
        if args.fix:
            validator.fix_file(filepath)
            print("已修复")
    else:
        results = validator.validate_all()
        print(validator.get_report())

        if args.fix:
            print("\n正在修复...")
            for filepath in Path(validator.memory_dir).rglob('*.md'):
                validator.fix_file(filepath)
            print(validator.get_report())


if __name__ == '__main__':
    main()
