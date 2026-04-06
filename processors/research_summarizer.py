"""研报摘要生成器 - 基于AI生成专业投资摘要"""
import os
from typing import Dict, Any


class ResearchSummarizer:
    """基于研报元数据生成专业投资摘要"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    def generate_summary(self, report: Dict[str, Any]) -> str:
        """
        基于研报元数据生成结构化投资摘要

        如果配置了Claude API，使用AI生成；
        否则使用模板生成。
        """
        if self.api_key:
            return self._generate_with_ai(report)
        else:
            return self._generate_with_template(report)

    def _generate_with_template(self, report: Dict[str, Any]) -> str:
        """使用模板生成摘要（无需API）"""
        title = report.get('title', '')
        broker = report.get('broker', '未知券商')
        rating = report.get('rating', '')
        eps = report.get('eps_forecast', '')
        pe = report.get('pe_forecast', '')
        stock = report.get('stock_name', '')

        # 解析标题中的投资逻辑
        investment_themes = self._extract_themes(title)

        summary_parts = [
            f"【{broker} | {rating}评级】",
            "",
            f"研报《{title}》核心观点：",
            "",
            "1. 业绩预测:",
        ]

        if eps and pe:
            summary_parts.append(f"   - 预计明年EPS: {eps}元，对应PE {pe}倍")
            # 判断估值水平
            pe_val = float(pe) if pe else 0
            if pe_val < 10:
                summary_parts.append("   - 当前估值处于历史较低水平")
            elif pe_val < 15:
                summary_parts.append("   - 当前估值处于合理区间")
            else:
                summary_parts.append("   - 当前估值相对较高，需关注业绩兑现")

        summary_parts.extend([
            "",
            "2. 投资逻辑:",
            f"   - {title}",
        ])

        if investment_themes:
            summary_parts.append(f"   - 重点关注: {', '.join(investment_themes)}")

        summary_parts.extend([
            "",
            "3. 机构观点:",
            f"   - {broker}给予{rating}评级，显示对{stock}未来表现的{self._rating_attitude(rating)}态度",
        ])

        return "\n".join(summary_parts)

    def _generate_with_ai(self, report: Dict[str, Any]) -> str:
        """使用Claude API生成摘要"""
        # 构建prompt
        prompt = f"""基于以下券商研报信息，生成一份专业的投资摘要（300字以内）：

研报标题: {report.get('title', '')}
发布机构: {report.get('broker', '')}
投资评级: {report.get('rating', '')}
目标股票: {report.get('stock_name', '')}
业绩预测: 明年EPS {report.get('eps_forecast', 'N/A')}元，PE {report.get('pe_forecast', 'N/A')}倍

请按以下结构输出：
1. 核心观点（一句话总结）
2. 业绩预测与估值分析
3. 投资逻辑要点
4. 风险提示（如有）

用中文输出，保持专业投资分析的语气。"""

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)

            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text
        except Exception as e:
            # AI失败时回退到模板
            print(f"AI摘要生成失败: {e}，使用模板生成")
            return self._generate_with_template(report)

    def _extract_themes(self, title: str) -> list:
        """从标题提取投资主题"""
        themes = []
        keywords = {
            '弹性': '业绩弹性',
            '成长': '成长性',
            '降本': '成本控制',
            '涨价': '价格上涨',
            '产能': '产能扩张',
            '并购': '并购整合',
            '分红': '分红回报',
            '现金流': '现金流',
            '周期': '周期反转',
            '新能源': '新能源转型',
        }
        for kw, theme in keywords.items():
            if kw in title:
                themes.append(theme)
        return themes[:3]  # 最多3个主题

    def _rating_attitude(self, rating: str) -> str:
        """根据评级返回态度描述"""
        rating_map = {
            '买入': '积极看好',
            '增持': '看好',
            '推荐': '看好',
            '中性': '谨慎',
            '减持': '看空',
            '卖出': '强烈看空',
        }
        return rating_map.get(rating, '中性')


def enhance_research_items(items: list) -> list:
    """增强研报数据，添加AI生成的摘要"""
    summarizer = ResearchSummarizer()

    for item in items:
        metadata = item.get('metadata', {})

        # 构建report字典
        report = {
            'title': item.get('title', ''),
            'broker': metadata.get('broker', ''),
            'rating': metadata.get('rating', ''),
            'eps_forecast': metadata.get('eps_forecast', ''),
            'pe_forecast': metadata.get('pe_forecast', ''),
            'stock_name': metadata.get('stock_name', ''),
        }

        # 生成摘要
        summary = summarizer.generate_summary(report)

        # 更新content字段
        item['content'] = summary

    return items


if __name__ == '__main__':
    # 测试
    test_report = {
        'title': '主营业务弹性可期，成长在即',
        'broker': '国信证券',
        'rating': '增持',
        'eps_forecast': '1.52',
        'pe_forecast': '11.3',
        'stock_name': '中煤能源',
    }

    summarizer = ResearchSummarizer()
    print(summarizer.generate_summary(test_report))
