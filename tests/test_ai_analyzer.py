"""AI 分析模块测试"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Mock openai before import
sys.modules['openai'] = Mock()

from processors.ai_analyzer import AIAnalyzer


class TestAIAnalyzer:
    """测试 AIAnalyzer 类"""

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'})
    @patch('processors.ai_analyzer.OpenAI')
    def test_analyzer_initialization(self, mock_openai):
        """测试 AIAnalyzer 初始化"""
        analyzer = AIAnalyzer()
        assert analyzer.db is not None
        mock_openai.assert_called_once_with(
            api_key='test_key',
            base_url='https://coding.dashscope.aliyuncs.com/v1'
        )

    def test_analyzer_requires_api_key(self):
        """测试没有 API key 时抛出异常"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                AIAnalyzer()
            assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'})
    @patch('processors.ai_analyzer.OpenAI')
    def test_parse_valid_response(self, mock_openai):
        """测试解析有效的 Claude API 响应"""
        analyzer = AIAnalyzer()

        valid_response = '''
        {
          "summary": "测试摘要",
          "relevance_score": 85,
          "impact_score": 70,
          "priority": "high",
          "related_holdings": ["600519"]
        }
        '''

        result = analyzer._parse_response(valid_response)

        assert result['summary'] == "测试摘要"
        assert result['relevance_score'] == 85
        assert result['impact_score'] == 70
        assert result['priority'] == "high"
        assert result['related_holdings'] == ["600519"]

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'})
    @patch('processors.ai_analyzer.OpenAI')
    def test_parse_response_clamps_scores(self, mock_openai):
        """测试评分范围限制在 0-100"""
        analyzer = AIAnalyzer()

        response_with_high_scores = '''
        {
          "summary": "测试",
          "relevance_score": 150,
          "impact_score": -20,
          "priority": "critical"
        }
        '''

        result = analyzer._parse_response(response_with_high_scores)

        assert result['relevance_score'] == 100
        assert result['impact_score'] == 0

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'})
    @patch('processors.ai_analyzer.OpenAI')
    def test_parse_response_defaults_priority(self, mock_openai):
        """测试无效的 priority 默认设为 medium"""
        analyzer = AIAnalyzer()

        response_with_invalid_priority = '''
        {
          "summary": "测试",
          "relevance_score": 50,
          "impact_score": 50,
          "priority": "invalid"
        }
        '''

        result = analyzer._parse_response(response_with_invalid_priority)

        assert result['priority'] == "medium"

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'})
    @patch('processors.ai_analyzer.OpenAI')
    def test_parse_response_missing_fields(self, mock_openai):
        """测试缺少必需字段时抛出异常"""
        analyzer = AIAnalyzer()

        response_missing_fields = '''
        {
          "summary": "只有摘要"
        }
        '''

        with pytest.raises(ValueError) as exc_info:
            analyzer._parse_response(response_missing_fields)

        assert "relevance_score" in str(exc_info.value)

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test_key'})
    @patch('processors.ai_analyzer.OpenAI')
    def test_build_prompt_includes_holdings(self, mock_openai):
        """测试 prompt 包含持仓信息"""
        analyzer = AIAnalyzer()

        # Mock 持仓配置
        mock_holdings = {
            '600519': {'name': '贵州茅台', 'sector': '白酒'},
            '000858': {'name': '五粮液', 'sector': '白酒'}
        }
        analyzer._load_holdings = Mock(return_value=mock_holdings)
        analyzer._load_keywords = Mock(return_value={'priority_keywords': ['AI']})

        item = {
            'title': '测试标题',
            'content': '测试内容',
            'source': 'Test'
        }

        prompt = analyzer._build_prompt(item, mock_holdings, {'priority_keywords': ['AI']})

        assert '贵州茅台' in prompt
        assert '五粮液' in prompt
        assert '600519' in prompt
        assert '测试标题' in prompt
