"""AI 分析模块 - 使用 LLM 分析内容并生成摘要和评分"""
import os
import json
import time
from typing import Dict, Any, List
from datetime import datetime

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from storage.database import Database


class AIAnalyzer:
    """AI 内容分析器"""

    def __init__(self, db_path: str = "./data/mi7.db"):
        self.db = Database(db_path)
        # 使用阿里云百炼的 key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://coding.dashscope.aliyuncs.com/v1"
        )
        self.model = "kimi-k2.5"

    def process_unprocessed_content(self, limit: int = 50) -> int:
        """
        处理所有未分析的内容

        Args:
            limit: 每次处理的最大条目数

        Returns:
            成功处理的条目数
        """
        items = self.db.get_unprocessed_content(limit=limit)
        if not items:
            print("没有需要处理的内容")
            return 0

        print(f"开始 AI 分析，共 {len(items)} 条内容...")
        processed = 0

        for item in items:
            try:
                result = self._analyze_item(item)
                self._update_item(item['id'], result)
                processed += 1
                print(f"  [OK] 已分析: {item['title'][:40]}...")

                # 添加延迟避免限流
                time.sleep(0.5)

            except Exception as e:
                print(f"  [FAIL] 分析失败: {item['title'][:40]}... - {e}")
                continue

        print(f"\n完成: {processed}/{len(items)} 条内容已分析")
        return processed

    def _analyze_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 分析单条内容

        Returns:
            {
                'summary': str,
                'relevance_score': int,
                'impact_score': int,
                'priority': str,
                'related_holdings': List[str]
            }
        """
        # 加载持仓配置
        holdings = self._load_holdings()
        keywords = self._load_keywords()

        prompt = self._build_prompt(item, holdings, keywords)

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1500,
            temperature=0.3,
            messages=[
                {"role": "system", "content": "你是一位专业的投资分析师，擅长分析财经新闻并提供简洁、准确的投资见解。"},
                {"role": "user", "content": prompt}
            ]
        )

        # 解析 JSON 响应
        result_text = response.choices[0].message.content
        return self._parse_response(result_text)

    def _build_prompt(self, item: Dict[str, Any], holdings: Dict, keywords: Dict) -> str:
        """构建 LLM 的提示词"""

        holdings_str = "\n".join([
            f"- {code}: {info.get('name', '')} ({info.get('sector', '')})"
            for code, info in holdings.items()
        ])

        keywords_str = ", ".join(keywords.get('priority_keywords', [])[:20])
        investors_str = ", ".join([
            "Louis-Vincent Gave", "Peter Schiff", "Ray Dalio", "Jim Rogers"
        ])

        return f"""请分析以下投资相关内容，并提供结构化分析结果。

【原始内容】
标题: {item['title']}
来源: {item['source']}
内容: {item['content'][:2000] if item.get('content') else 'N/A'}

【我的持仓】
{holdings_str}

【关注关键词】
宏观经济: 美联储, 加息, 降息, 通胀, CPI, PPI, GDP
投资大V: {investors_str}
其他: {keywords_str}

【分析要求】
1. 生成600字以内的中文摘要，保留英文专业术语
2. 评估与我的持仓相关性 (0-100分)
3. 评估对市场的影响力 (0-100分)
4. 确定优先级: critical(紧急)/high(高)/medium(中)/low(低)
5. 列出相关的持仓股票代码

【输出格式】
必须以JSON格式输出，不要包含其他内容:
{{
  "summary": "中文摘要...",
  "relevance_score": 85,
  "impact_score": 70,
  "priority": "high",
  "related_holdings": ["600519", "000858"]
}}
"""

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """解析 LLM 的 JSON 响应"""
        # 提取 JSON 部分
        start = text.find('{')
        end = text.rfind('}')

        if start == -1 or end == -1:
            raise ValueError("响应中没有找到 JSON 格式")

        json_str = text[start:end+1]
        result = json.loads(json_str)

        # 验证必需字段
        required = ['summary', 'relevance_score', 'impact_score', 'priority']
        for field in required:
            if field not in result:
                raise ValueError(f"响应缺少必需字段: {field}")

        # 验证数值范围
        result['relevance_score'] = max(0, min(100, int(result.get('relevance_score', 0))))
        result['impact_score'] = max(0, min(100, int(result.get('impact_score', 0))))

        # 验证优先级
        valid_priorities = ['critical', 'high', 'medium', 'low']
        if result['priority'] not in valid_priorities:
            result['priority'] = 'medium'

        # 确保 related_holdings 是列表
        if 'related_holdings' not in result:
            result['related_holdings'] = []

        return result

    def _update_item(self, item_id: int, result: Dict[str, Any]):
        """更新数据库中的内容"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE content
            SET summary = ?,
                relevance_score = ?,
                impact_score = ?,
                priority = ?,
                is_processed = TRUE
            WHERE id = ?
        ''', (
            result['summary'],
            result['relevance_score'],
            result['impact_score'],
            result['priority'],
            item_id
        ))

        conn.commit()
        conn.close()

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

    def _load_keywords(self) -> Dict[str, Any]:
        """加载关键词配置"""
        import yaml
        config_path = "./config/keywords.yaml"

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return {
                'priority_keywords': config.get('priority_keywords', []),
                'company_aliases': config.get('company_aliases', {})
            }
        except Exception as e:
            print(f"警告: 无法加载关键词配置: {e}")
            return {}


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='AI 内容分析器')
    parser.add_argument('--limit', type=int, default=50, help='每次处理的最大条目数')
    args = parser.parse_args()

    analyzer = AIAnalyzer()
    processed = analyzer.process_unprocessed_content(limit=args.limit)
    print(f"\n总计处理: {processed} 条")


if __name__ == '__main__':
    main()
