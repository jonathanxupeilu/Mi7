"""公告采集器 - 使用东方财富API采集公司重要公告"""
import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from storage.database import Database


class AnnouncementCollector:
    """公告采集器"""

    BASE_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search"
    REQUEST_DELAY = 1.0  # API调用间隔（秒）

    # 重要公告关键词
    KEYWORDS = ["年报", "季报", "半年报", "回购", "减持", "增持", "分红", "业绩预告", "重大事项", "停牌", "复牌"]

    def __init__(self, db_path: str = "./data/mi7.db"):
        self.db = Database(db_path)
        self.api_key = os.getenv("MX_APIKEY")
        if not self.api_key:
            raise ValueError("MX_APIKEY not set")

    def load_holdings(self) -> Dict[str, str]:
        """加载持仓列表"""
        import yaml
        try:
            with open('./config/holdings.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return {code: info.get('name', '') for code, info in config.get('portfolio', {}).items()}
        except Exception as e:
            print(f"Error loading holdings: {e}")
            return {}

    def search_announcements(self, code: str, name: str) -> List[Dict[str, Any]]:
        """搜索公告"""
        # 构建查询词，包含重要公告关键词
        keywords_str = " ".join(self.KEYWORDS)
        query = f"{name} {code} 公告 {keywords_str}"

        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }
        data = {"query": query}

        try:
            response = requests.post(self.BASE_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("status") != 0 and result.get("code") != 0:
                print(f"  API Error: {result.get('message', 'Unknown error')}")
                return []

            # 解析嵌套的 data 结构
            outer_data = result.get("data", {})
            if isinstance(outer_data, dict):
                inner_data = outer_data.get("data", {})
                llm_resp = inner_data.get("llmSearchResponse", {})

                if isinstance(llm_resp, dict):
                    news_list = llm_resp.get("data", [])
                else:
                    news_list = []
            else:
                news_list = []

            # 转换为标准格式，筛选重要公告
            items = []
            for item in news_list:
                if isinstance(item, dict):
                    info_type = item.get('informationType', '')
                    title = item.get('title', '')

                    # 筛选公告类型或包含关键词的标题
                    is_announcement = (
                        info_type in ['NOTICE', 'ANNO', '公告'] or
                        any(kw in title for kw in self.KEYWORDS) or
                        '公告' in title
                    )

                    if is_announcement:
                        # 检测公告类型
                        anno_type = self._detect_announcement_type(title)

                        items.append({
                            'title': item.get('title', ''),
                            'content': item.get('content', ''),
                            'source': item.get('source', '公告'),
                            'published_at': self._parse_date(item.get('date', '')),
                            'url': item.get('jumpUrl', ''),
                            'metadata': {
                                'stock_code': code,
                                'stock_name': name,
                                'info_type': 'announcement',
                                'announcement_type': anno_type
                            }
                        })

            return items

        except Exception as e:
            print(f"  Request error: {e}")
            return []

    def _detect_announcement_type(self, title: str) -> str:
        """检测公告类型"""
        keywords_map = {
            '年报': '年报',
            '季报': '季报',
            '半年报': '半年报',
            '回购': '回购',
            '减持': '减持',
            '增持': '增持',
            '分红': '分红',
            '派息': '分红',
            '业绩预告': '业绩预告',
            '停牌': '停牌',
            '复牌': '复牌',
            '重大事项': '重大事项',
            '关联交易': '关联交易',
            '股权激励': '股权激励',
            '定增': '定增',
            'IPO': 'IPO',
            '可转债': '可转债',
        }

        for keyword, anno_type in keywords_map.items():
            if keyword in title:
                return anno_type

        return '其他公告'

    def _parse_date(self, date_str: str) -> datetime:
        """解析日期"""
        if not date_str:
            return datetime.now()
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return datetime.now()

    def collect_all(self, limit_per_stock: int = 5) -> int:
        """采集所有持仓股票公告"""
        holdings = self.load_holdings()
        if not holdings:
            print("No holdings found")
            return 0

        print(f"开始采集 {len(holdings)} 只股票公告...")
        print(f"关键词: {', '.join(self.KEYWORDS)}")
        total_saved = 0

        for idx, (code, name) in enumerate(holdings.items(), 1):
            print(f"\n[{code}] {name} ({idx}/{len(holdings)})")

            items = self.search_announcements(code, name)

            saved = 0
            duplicates = 0
            for item in items[:limit_per_stock]:
                item['source_type'] = 'announcement'

                if not self.db.check_duplicate(item['url']):
                    if self.db.insert_content(item):
                        saved += 1
                        total_saved += 1
                else:
                    duplicates += 1

            print(f"  New: {saved}, Duplicates: {duplicates}")

            # 添加延迟避免触发API频率限制
            if idx < len(holdings):
                time.sleep(self.REQUEST_DELAY)

        print(f"\n公告采集完成，新增 {total_saved} 条")
        return total_saved


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='公告采集器')
    parser.add_argument('--limit', type=int, default=5, help='每只股票采集条数')
    parser.add_argument('--code', type=str, help='指定股票代码采集')
    args = parser.parse_args()

    collector = AnnouncementCollector()

    if args.code:
        # 采集单只股票
        holdings = collector.load_holdings()
        name = holdings.get(args.code, '')
        if name:
            print(f"采集单只股票公告: {args.code} {name}")
            items = collector.search_announcements(args.code, name)
            print(f"找到 {len(items)} 条公告")
            for item in items[:args.limit]:
                print(f"  [{item['metadata']['announcement_type']}] {item['title'][:50]}...")
        else:
            print(f"未找到股票代码: {args.code}")
    else:
        # 采集全部
        count = collector.collect_all(limit_per_stock=args.limit)
        print(f"\n总计采集: {count} 条公告")


if __name__ == '__main__':
    main()
