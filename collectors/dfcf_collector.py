"""东方财富资讯采集器 - 直接调用 API"""
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
from storage.dfcf_cache import DFCFCache


class DFCFCollector:
    """东方财富资讯采集器"""

    BASE_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search"
    REQUEST_DELAY = 1.0  # API调用间隔（秒），避免触发频率限制

    def __init__(self, db_path: str = "./data/mi7.db"):
        self.db = Database(db_path)
        self.api_key = os.getenv("MX_APIKEY")
        if not self.api_key:
            raise ValueError("MX_APIKEY not set")

        # 初始化缓存
        self.cache = DFCFCache(db_path)

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

    def search_news(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索资讯（带缓存）
        """
        # 从查询中提取股票代码（假设格式: "股票名 代码"）
        stock_code = query.split()[-1] if ' ' in query else 'unknown'

        # 尝试读取缓存
        if self.cache:
            cached = self.cache.get(stock_code, query)
            if cached is not None:
                print(f"    [CACHE HIT] {stock_code}")
                return cached

        # 缓存未命中，调用 API
        result = self._api_search(query)

        # 写入缓存（1小时 TTL）
        if self.cache and result:
            self.cache.set(stock_code, query, result, ttl_hours=1)

        return result

    def _api_search(self, query: str) -> List[Dict[str, Any]]:
        """
        实际的 API 调用
        """
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

            # 转换为标准格式
            items = []
            for item in news_list:
                if isinstance(item, dict):
                    items.append({
                        'title': item.get('title', ''),
                        'content': item.get('content', ''),
                        'source': item.get('source', '东方财富'),
                        'published_at': self._parse_date(item.get('date', '')),
                        'url': item.get('jumpUrl', ''),
                        'metadata': {'info_type': item.get('informationType', '')}
                    })

            return items

        except Exception as e:
            print(f"  Request error: {e}")
            return []

    def search_snowball(self, code: str, name: str) -> List[Dict[str, Any]]:
        """搜索雪球热帖"""
        query = f"{name} {code} 雪球 热帖 讨论"

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

            # 转换为标准格式，筛选雪球相关讨论
            items = []
            for item in news_list:
                if isinstance(item, dict):
                    source = item.get('source', '')
                    title = item.get('title', '')

                    # 筛选雪球来源或包含雪球关键词的内容
                    is_snowball = (
                        '雪球' in source or
                        '雪球' in title or
                        'xueqiu' in item.get('jumpUrl', '').lower()
                    )

                    if is_snowball:
                        items.append({
                            'title': item.get('title', ''),
                            'content': item.get('content', ''),
                            'source': '雪球',
                            'published_at': self._parse_date(item.get('date', '')),
                            'url': item.get('jumpUrl', ''),
                            'metadata': {
                                'stock_code': code,
                                'stock_name': name,
                                'info_type': 'snowball'
                            }
                        })

            return items

        except Exception as e:
            print(f"  Request error: {e}")
            return []

    def _parse_date(self, date_str: str) -> datetime:
        """解析日期"""
        if not date_str:
            return datetime.now()
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return datetime.now()

    def collect_all(self, limit_per_stock: int = 5) -> List[Dict[str, Any]]:
        """采集所有持仓股票新闻，返回采集到的项目列表"""
        holdings = self.load_holdings()
        if not holdings:
            print("No holdings found")
            return []

        print(f"开始采集 {len(holdings)} 只股票新闻...")
        all_items = []

        for idx, (code, name) in enumerate(holdings.items(), 1):
            print(f"\n[{code}] {name} ({idx}/{len(holdings)})")

            # 搜索股票相关新闻
            query = f"{name} {code} 最新新闻"
            items = self.search_news(query)

            saved = 0
            duplicates = 0
            for item in items[:limit_per_stock]:
                # 添加股票元数据
                item['metadata'] = {'stock_code': code, 'stock_name': name}
                item['source_type'] = 'dfcf'

                if not self.db.check_duplicate(item['url']):
                    if self.db.insert_content(item):
                        saved += 1
                        all_items.append(item)
                else:
                    duplicates += 1

            print(f"  New: {saved}, Duplicates: {duplicates}")

            # 添加延迟避免触发API频率限制
            if idx < len(holdings):
                time.sleep(self.REQUEST_DELAY)

        print(f"\nTotal saved: {len(all_items)}")

        # 显示缓存统计
        if self.cache:
            stats = self.cache.get_stats()
            print(f"Cache: {stats['valid']} valid, {stats['expired']} expired")

        return all_items

    def collect_snowball(self, limit_per_stock: int = 5) -> int:
        """采集所有持仓股票雪球热帖"""
        holdings = self.load_holdings()
        if not holdings:
            print("No holdings found")
            return 0

        print(f"开始采集 {len(holdings)} 只股票雪球热帖...")
        total_saved = 0

        for idx, (code, name) in enumerate(holdings.items(), 1):
            print(f"\n[{code}] {name} 雪球 ({idx}/{len(holdings)})")

            items = self.search_snowball(code, name)

            saved = 0
            duplicates = 0
            for item in items[:limit_per_stock]:
                item['source_type'] = 'snowball'

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

        print(f"\n雪球热帖采集完成，新增 {total_saved} 条")
        return total_saved


def main():
    """命令行入口"""
    collector = DFCFCollector()
    count = collector.collect_all(limit_per_stock=5)
    print(f"\n采集完成，新增 {count} 条")


if __name__ == '__main__':
    main()
