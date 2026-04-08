"""内容优先级处理器 - 基于权重分配系统"""
import json
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path


class ContentPrioritizer:
    """内容优先级处理器 - 实现权重分配系统"""

    # 默认配置
    DEFAULT_WEIGHTS = {
        'holdings_direct': 40,
        'macro_global': 30,
        'expert_opinion': 20,
        'auxiliary': 10
    }

    DEFAULT_KEYWORDS = [
        '美联储', '加息', '降息', '通胀', 'CPI', 'PPI', '黄金', '油价',
        '战争', '制裁', '关税', '煤炭', '新能源', '电动车', 'AI', '人工智能'
    ]

    DEFAULT_SOURCE_WEIGHTS = {
        '东方财富公告': 1.5,
        '东方财富': 1.4,
        'CNBC': 1.3,
        'Bloomberg Markets': 1.3,
        'Bloomberg': 1.3,
        'Reuters Business': 1.3,
        'Reuters': 1.3,
        'Financial Times': 1.3,
        'Wall Street Journal': 1.3,
        'Seeking Alpha': 1.2,
        'ZeroHedge': 1.1,
        'MarketWatch': 1.1,
        'Investing.com': 1.1,
        'Nitter': 1.0,
        'Twitter': 1.0,
        'The Economist': 1.0,
        '财新网': 1.2,
        '财联社': 1.2,
        '证券时报': 1.1,
        'GitHub Blog': 0.5
    }

    # 优先级阈值
    PRIORITY_THRESHOLDS = {
        'critical': 70,  # 持仓直接影响
        'high': 40,      # 宏观影响
        'medium': 20,    # 投资观点
        'low': 0         # 辅助信息
    }

    def __init__(self, config_path: str = None):
        """
        初始化优先级处理器

        Args:
            config_path: 配置文件路径，如果为None则使用默认配置
        """
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self.priority_keywords = self.DEFAULT_KEYWORDS.copy()
        self.source_weights = self.DEFAULT_SOURCE_WEIGHTS.copy()
        self.holdings = {}

        # 加载持仓配置
        self._load_holdings()

        # 加载自定义配置
        if config_path and Path(config_path).exists():
            self._load_config(config_path)

    def _load_holdings(self):
        """加载持仓配置"""
        try:
            import yaml
            holdings_path = Path(__file__).parent.parent / 'config' / 'holdings.yaml'
            if holdings_path.exists():
                with open(holdings_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self.holdings = config.get('portfolio', {})
        except Exception as e:
            print(f"加载持仓配置失败: {e}")
            self.holdings = {}

    def _load_config(self, config_path: str):
        """加载自定义配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if 'content_weights' in config:
                self.weights.update(config['content_weights'])
            if 'priority_keywords' in config:
                self.priority_keywords = config['priority_keywords']
            if 'source_weights' in config:
                self.source_weights.update(config['source_weights'])
            if 'holdings' in config:
                self.holdings.update(config['holdings'])
        except Exception as e:
            print(f"加载权重配置失败: {e}，使用默认配置")

    def calculate_holdings_relevance(self, item: Dict[str, Any]) -> int:
        """
        计算持仓相关性分数

        Args:
            item: 新闻条目

        Returns:
            相关性分数 (0-100)
        """
        score = 0
        title = item.get('title', '')

        # 检查持仓名称匹配
        for code, info in self.holdings.items():
            # info 可能是字典或字符串
            if isinstance(info, dict):
                name = info.get('name', '')
                aliases = info.get('aliases', [])
            else:
                name = info
                aliases = []

            # 检查名称匹配
            if name and name in title:
                score += 80
                break

            # 检查代码匹配
            if str(code) in title:
                score += 80
                break

            # 检查别名
            for alias in aliases:
                if alias and alias in title:
                    score += 70
                    break

        return min(score, 100)  # 最高100分

    def _get_company_aliases(self) -> Dict[str, List[str]]:
        """获取公司别名"""
        return {
            '601898': ['中煤能源', '中煤'],
            '000807': ['云铝股份', '云铝'],
            '600938': ['中国海油', '中海油'],
            '001965': ['招商公路'],
            '600886': ['国投电力'],
            '000333': ['美的集团', '美的'],
            '000858': ['五粮液'],
            '600900': ['长江电力'],
            '600887': ['伊利股份', '伊利'],
            '600519': ['贵州茅台', '茅台'],
            '000651': ['格力电器', '格力'],
            '600009': ['上海机场'],
            '002738': ['中矿资源'],
            '601318': ['中国平安', '平安'],
            '300059': ['东方财富', '东财'],
            '600547': ['山东黄金'],
            '603993': ['洛阳钼业'],
            '601899': ['紫金矿业', '紫金'],
            '600489': ['中金黄金'],
            '000426': ['兴业银锡']
        }

    def calculate_keyword_relevance(self, item: Dict[str, Any]) -> int:
        """
        计算关键词相关性分数

        Args:
            item: 新闻条目

        Returns:
            相关性分数
        """
        score = 0
        title = item.get('title', '')
        content = item.get('content', '')
        text = f"{title} {content}"

        # 统计匹配的关键词（每个关键词20分）
        matched_keywords = set()
        for keyword in self.priority_keywords:
            if keyword in text:
                matched_keywords.add(keyword)
                score += 20

        # 多个关键词额外加分
        if len(matched_keywords) >= 2:
            score += 10  # 两个及以上关键词额外加10
        if len(matched_keywords) >= 4:
            score += 20  # 四个及以上再加20

        return min(score, 100)  # 最高100分

    def apply_source_weight(self, base_score: int, source: str) -> int:
        """
        应用来源权重

        Args:
            base_score: 基础分数
            source: 来源名称

        Returns:
            加权后的分数
        """
        # 查找来源权重
        weight = 1.0
        for source_name, source_weight in self.source_weights.items():
            if source_name.lower() in source.lower():
                weight = source_weight
                break

        return int(base_score * weight)

    def calculate_priority(self, item: Dict[str, Any]) -> Tuple[str, int]:
        """
        计算最终优先级

        Args:
            item: 新闻条目

        Returns:
            (优先级, 分数)
        """
        # 1. 持仓相关性 (直接加分)
        holdings_score = self.calculate_holdings_relevance(item)

        # 2. 关键词相关性 (加权)
        keyword_score = self.calculate_keyword_relevance(item)
        weighted_keyword = keyword_score * (self.weights['macro_global'] / 100)

        # 3. 来源权重
        source = item.get('source', 'Unknown')
        source_multiplier = self.source_weights.get(source, 1.0)

        # 基础分数 = 持仓分 + 关键词分
        base_score = holdings_score + weighted_keyword

        # 应用来源权重
        final_score = int(base_score * source_multiplier)

        # 根据分数确定优先级
        if final_score >= self.PRIORITY_THRESHOLDS['critical']:
            priority = 'critical'
        elif final_score >= self.PRIORITY_THRESHOLDS['high']:
            priority = 'high'
        elif final_score >= self.PRIORITY_THRESHOLDS['medium']:
            priority = 'medium'
        else:
            priority = 'low'

        # 保存分数到item
        item['relevance_score'] = final_score
        item['priority'] = priority

        return priority, final_score

    def sort_by_priority(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按优先级排序内容

        Args:
            items: 内容列表

        Returns:
            排序后的列表
        """
        # 先计算所有优先级
        for item in items:
            self.calculate_priority(item)

        # 按优先级排序
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        return sorted(items, key=lambda x: (
            priority_order.get(x.get('priority', 'low'), 3),
            -x.get('relevance_score', 0)
        ))

    def group_by_priority(self, items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        按优先级分组内容

        Args:
            items: 内容列表

        Returns:
            按优先级分组的字典
        """
        # 先计算优先级
        for item in items:
            self.calculate_priority(item)

        # 分组
        grouped = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }

        for item in items:
            priority = item.get('priority', 'low')
            if priority in grouped:
                grouped[priority].append(item)
            else:
                grouped['low'].append(item)

        return grouped

    def get_weight_summary(self) -> Dict[str, Any]:
        """
        获取权重配置摘要

        Returns:
            配置摘要
        """
        return {
            'weights': self.weights,
            'priority_keywords_count': len(self.priority_keywords),
            'source_weights_count': len(self.source_weights),
            'holdings_count': len(self.holdings),
            'thresholds': self.PRIORITY_THRESHOLDS
        }


if __name__ == '__main__':
    # 测试
    prioritizer = ContentPrioritizer()

    print("权重系统初始化完成")
    print(f"持仓: {len(prioritizer.holdings)} 只")
    print(f"关键词: {len(prioritizer.priority_keywords)} 个")
    print(f"来源权重: {len(prioritizer.source_weights)} 个")

    # 测试评分
    test_items = [
        {'title': '贵州茅台发布年报，业绩增长20%', 'source': '东方财富公告'},
        {'title': '美联储宣布加息25个基点', 'source': 'Bloomberg'},
        {'title': '一般分析', 'source': 'Seeking Alpha'},
    ]

    print("\n测试评分:")
    for item in test_items:
        priority, score = prioritizer.calculate_priority(item)
        print(f"  [{priority}] {item['title'][:30]}... (得分: {score})")
