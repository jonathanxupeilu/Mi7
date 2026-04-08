"""MI7 Skill 入口脚本 run.py 的 TDD 测试

测试覆盖:
1. API Key 检查
2. 配置命令 (config --show, --edit)
3. 采集命令 (collect)
4. 分析命令 (analyze)
5. 报告命令 (report)
6. 完整流程命令 (run)
7. 参数解析和错误处理
"""

import pytest
import sys
import os
import io
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from argparse import Namespace

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCheckAPIKey:
    """测试 check_api_key 函数"""

    def test_check_api_key_returns_true_when_set(self):
        """RED: 当 ANTHROPIC_API_KEY 设置时应返回 True"""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key_123'}):
            from scripts.run import check_api_key
            result = check_api_key()
            assert result is True

    def test_check_api_key_returns_false_when_not_set(self):
        """RED: 当 ANTHROPIC_API_KEY 未设置时应返回 False"""
        with patch.dict('os.environ', {}, clear=True):
            from scripts.run import check_api_key
            result = check_api_key()
            assert result is False

    def test_check_api_key_prints_error_when_not_set(self, capsys):
        """RED: API Key 未设置时应打印错误信息"""
        with patch.dict('os.environ', {}, clear=True):
            from scripts.run import check_api_key
            check_api_key()
            captured = capsys.readouterr()
            assert "ANTHROPIC_API_KEY" in captured.out


class TestCmdConfig:
    """测试 cmd_config 命令"""

    @patch('builtins.print')
    def test_config_show_displays_holdings(self, mock_print):
        """RED: config --show 应显示持仓信息"""
        from scripts.run import cmd_config

        args = Namespace(show=True, edit=False)

        # Mock holdings.yaml
        mock_holdings = {
            'portfolio': {
                '600519': {'name': '贵州茅台', 'sector': '白酒', 'weight': 0.08, 'aliases': ['茅台']},
                '000858': {'name': '五粮液', 'sector': '白酒', 'weight': 0.05, 'aliases': ['五粮液']}
            }
        }

        with patch('yaml.safe_load', return_value=mock_holdings):
            with patch('builtins.open', MagicMock()):
                cmd_config(args)

        # 验证打印了持仓信息
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any('贵州茅台' in c or '600519' in c for c in print_calls)

    @patch('subprocess.run')
    def test_config_edit_opens_editor(self, mock_subprocess):
        """RED: config --edit 应打开编辑器"""
        from scripts.run import cmd_config

        args = Namespace(show=False, edit=True)
        cmd_config(args)

        # 验证调用了编辑器
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert 'holdings.yaml' in str(call_args[-1])


class TestCmdCollect:
    """测试 cmd_collect 命令"""

    @patch('storage.database.Database')
    @patch('yaml.safe_load')
    @patch('collectors.dfcf_collector.DFCFCollector')
    @patch('collectors.rss_collector.RSSCollector')
    def test_collect_all_sources_by_default(self, mock_rss, mock_dfcf, mock_yaml, mock_db):
        """RED: collect 默认应采集所有启用的信源"""
        from scripts.run import cmd_collect

        args = Namespace(source='all', hours=24)

        # Mock 配置
        mock_config = {
            'sources': {
                'rss': {'native': {'enabled': True, 'feeds': []}},
                'nitter': {'enabled': False},
                'obsidian': {'enabled': False}
            }
        }
        mock_yaml.return_value = mock_config

        # Mock RSSCollector
        mock_rss_instance = MagicMock()
        mock_rss_instance.collect.return_value = [
            {'title': 'Test News', 'url': 'http://test.com'}
        ]
        mock_rss.return_value = mock_rss_instance

        # Mock DFCFCollector
        mock_dfcf_instance = MagicMock()
        mock_dfcf_instance.collect_all.return_value = []
        mock_dfcf.return_value = mock_dfcf_instance

        cmd_collect(args)

        # 验证 RSSCollector 被调用
        mock_rss_instance.collect.assert_called_once()

    @patch('storage.database.Database')
    @patch('yaml.safe_load')
    def test_collect_specific_source(self, mock_yaml, mock_db):
        """RED: --source rss 应只采集 RSS"""
        from scripts.run import cmd_collect

        args = Namespace(source='rss', hours=24)

        mock_config = {
            'sources': {
                'rss': {'native': {'enabled': True, 'feeds': [{'id': 'test', 'url': 'http://test.com'}]}}
            }
        }
        mock_yaml.return_value = mock_config

        mock_collector = MagicMock()
        mock_collector.collect.return_value = []

        with patch('collectors.rss_collector.RSSCollector', return_value=mock_collector):
            result = cmd_collect(args)

        # RSS 应该被调用
        mock_collector.collect.assert_called_once_with(hours=24)

    @patch('storage.database.Database')
    @patch('yaml.safe_load')
    def test_collect_saves_to_database(self, mock_yaml, mock_db):
        """RED: 采集的数据应保存到数据库"""
        from scripts.run import cmd_collect

        args = Namespace(source='rss', hours=24)

        mock_config = {'sources': {'rss': {'native': {'enabled': True, 'feeds': []}}}}
        mock_yaml.return_value = mock_config

        # 模拟采集到的数据
        mock_items = [
            {'title': 'News 1', 'url': 'http://test1.com'},
            {'title': 'News 2', 'url': 'http://test2.com'}
        ]

        mock_collector = MagicMock()
        mock_collector.collect.return_value = mock_items

        # 模拟数据库 - 假设没有重复
        mock_db_instance = MagicMock()
        mock_db_instance.check_duplicate.return_value = False
        mock_db_instance.insert_content.return_value = True
        mock_db.return_value = mock_db_instance

        with patch('collectors.rss_collector.RSSCollector', return_value=mock_collector):
            cmd_collect(args)

        # 验证数据被插入数据库
        assert mock_db_instance.insert_content.call_count == 2

    @patch('storage.database.Database')
    @patch('yaml.safe_load')
    def test_collect_skips_duplicates(self, mock_yaml, mock_db):
        """RED: 采集时应跳过重复内容"""
        from scripts.run import cmd_collect

        args = Namespace(source='rss', hours=24)

        mock_config = {'sources': {'rss': {'native': {'enabled': True, 'feeds': []}}}}
        mock_yaml.return_value = mock_config

        mock_items = [
            {'title': 'News 1', 'url': 'http://test1.com'}
        ]

        mock_collector = MagicMock()
        mock_collector.collect.return_value = mock_items

        # 模拟数据库 - 返回重复
        mock_db_instance = MagicMock()
        mock_db_instance.check_duplicate.return_value = True  # 重复
        mock_db.return_value = mock_db_instance

        with patch('collectors.rss_collector.RSSCollector', return_value=mock_collector):
            result = cmd_collect(args)

        # 重复内容不应被插入
        mock_db_instance.insert_content.assert_not_called()


class TestCmdAnalyze:
    """测试 cmd_analyze 命令"""

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'})
    @patch('processors.ai_analyzer.AIAnalyzer')
    def test_analyze_calls_ai_analyzer(self, mock_analyzer_class):
        """RED: analyze 应调用 AIAnalyzer"""
        from scripts.run import cmd_analyze

        args = Namespace(limit=50)

        mock_analyzer = MagicMock()
        mock_analyzer.process_unprocessed_content.return_value = 10
        mock_analyzer_class.return_value = mock_analyzer

        cmd_analyze(args)

        # 验证 AIAnalyzer 被调用
        mock_analyzer.process_unprocessed_content.assert_called_once_with(limit=50)

    @patch.dict('os.environ', {}, clear=True)
    def test_analyze_exits_without_api_key(self):
        """RED: 没有 API Key 时 analyze 应退出"""
        from scripts.run import cmd_analyze

        args = Namespace(limit=50)
        result = cmd_analyze(args)

        # 应该返回 0（没有处理任何内容）
        assert result == 0


class TestCmdReport:
    """测试 cmd_report 命令"""

    @patch('storage.database.Database')
    @patch('output.report_generator.ReportGenerator')
    def test_report_generates_txt_report(self, mock_report_gen, mock_db):
        """RED: report 应生成 TXT 报告"""
        from scripts.run import cmd_report

        args = Namespace(hours=48, min_relevance=0)

        # 模拟数据库返回已分析内容
        mock_items = [
            {
                'id': 1,
                'title': 'Test News',
                'priority': 'high',
                'relevance_score': 80,
                'impact_score': 75
            }
        ]
        mock_db_instance = MagicMock()
        mock_db_instance.get_analyzed_content.return_value = mock_items
        mock_db.return_value = mock_db_instance

        # 模拟报告生成器
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate.return_value = '/path/to/report.txt'
        mock_report_gen.return_value = mock_gen_instance

        cmd_report(args)

        # 验证报告生成器被调用
        mock_gen_instance.generate.assert_called_once()

    @patch('storage.database.Database')
    def test_report_warns_when_no_content(self, mock_db, capsys):
        """RED: 没有可报告内容时应警告"""
        from scripts.run import cmd_report

        args = Namespace(hours=48, min_relevance=0)

        # 模拟空数据库
        mock_db_instance = MagicMock()
        mock_db_instance.get_analyzed_content.return_value = []
        mock_db.return_value = mock_db_instance

        cmd_report(args)

        captured = capsys.readouterr()
        assert "没有可报告的内容" in captured.out or "WARNING" in captured.out


class TestCmdRun:
    """测试 cmd_run 完整流程命令"""

    @patch('scripts.run.cmd_collect')
    @patch('scripts.run.cmd_analyze')
    @patch('scripts.run.cmd_report')
    def test_run_executes_full_workflow(self, mock_report, mock_analyze, mock_collect):
        """RED: run 应执行完整流程 collect → analyze → report"""
        from scripts.run import cmd_run

        args = Namespace(hours=24, source='all', skip_analysis=False)
        mock_collect.return_value = 5  # 采集到 5 条

        cmd_run(args)

        # 验证三个步骤都被调用
        mock_collect.assert_called_once()
        mock_analyze.assert_called_once()
        mock_report.assert_called_once()

    @patch('scripts.run.cmd_collect')
    @patch('scripts.run.cmd_analyze')
    @patch('scripts.run.cmd_report')
    def test_run_skips_analysis_when_flag_set(self, mock_report, mock_analyze, mock_collect):
        """RED: --skip-analysis 应跳过分析步骤"""
        from scripts.run import cmd_run

        args = Namespace(hours=24, source='all', skip_analysis=True)
        mock_collect.return_value = 5

        cmd_run(args)

        # 分析步骤不应被调用
        mock_analyze.assert_not_called()
        mock_report.assert_called_once()


class TestArgumentParsing:
    """测试参数解析"""

    def test_main_with_collect_command(self):
        """RED: collect 子命令应正确解析"""
        from scripts.run import main

        test_args = ['collect', '--hours', '12', '--source', 'rss']

        with patch('sys.argv', ['run.py'] + test_args):
            with patch('scripts.run.cmd_collect') as mock_cmd:
                try:
                    main()
                except SystemExit:
                    pass

                # 验证参数被正确传递
                mock_cmd.assert_called_once()
                args = mock_cmd.call_args[0][0]
                assert args.hours == 12
                assert args.source == 'rss'

    def test_main_with_analyze_command(self):
        """RED: analyze 子命令应正确解析"""
        from scripts.run import main

        test_args = ['analyze', '--limit', '100']

        with patch('sys.argv', ['run.py'] + test_args):
            with patch('scripts.run.cmd_analyze') as mock_cmd:
                try:
                    main()
                except SystemExit:
                    pass

                mock_cmd.assert_called_once()
                args = mock_cmd.call_args[0][0]
                assert args.limit == 100

    def test_main_with_no_args_shows_help(self):
        """RED: 无参数时应显示帮助"""
        from scripts.run import main

        with patch('sys.argv', ['run.py']):
            with patch('argparse.ArgumentParser.print_help') as mock_help:
                try:
                    main()
                except SystemExit:
                    pass
                mock_help.assert_called_once()


class TestDataDirectory:
    """测试数据目录处理"""

    def test_data_dir_uses_project_directory(self):
        """RED: 数据目录应使用项目数据目录"""
        from scripts.run import DATA_DIR

        expected_path = Path(__file__).parent.parent / 'data'
        assert DATA_DIR == expected_path

    def test_data_dir_created_if_not_exists(self):
        """RED: 数据目录不存在时应自动创建"""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            # 重新导入以触发目录创建
            import importlib
            import scripts.run
            importlib.reload(scripts.run)

            # 验证 mkdir 被调用
            mock_mkdir.assert_called_with(parents=True, exist_ok=True)


class TestErrorHandling:
    """测试错误处理"""

    @patch('storage.database.Database')
    @patch('yaml.safe_load')
    @patch('collectors.rss_collector.RSSCollector')
    def test_collect_handles_collector_exception(self, mock_rss, mock_yaml, mock_db):
        """RED: 采集器异常时应优雅处理"""
        from scripts.run import cmd_collect

        args = Namespace(source='rss', hours=24)

        mock_config = {'sources': {'rss': {'native': {'enabled': True, 'feeds': []}}}}
        mock_yaml.return_value = mock_config

        # 模拟采集器抛出异常
        mock_rss.side_effect = Exception("Network error")

        # 不应抛出异常
        try:
            result = cmd_collect(args)
        except Exception as e:
            pytest.fail(f"collect 不应抛出异常: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
