"""研报采集器 - 使用东方财富API采集券商研究报告，并补充网页渠道"""
import os
import sys
import json
import time
import re
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from storage.database import Database


class ResearchCollector:
    """研报采集器"""

    BASE_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search"
    REQUEST_DELAY = 1.0  # API调用间隔（秒）

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

    def search_research(self, code: str, name: str) -> List[Dict[str, Any]]:
        """搜索研报"""
        query = f"{name} {code} 研报 研究报告"

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

            # 转换为标准格式，过滤研报类型
            items = []
            for item in news_list:
                if isinstance(item, dict):
                    # 筛选研报类型（RESEARCH或包含研报关键词）
                    info_type = item.get('informationType', '')
                    title = item.get('title', '')

                    if info_type == 'RESEARCH' or '研报' in title or '研究' in title:
                        items.append({
                            'title': item.get('title', ''),
                            'content': item.get('content', ''),
                            'source': item.get('source', '研报'),
                            'published_at': self._parse_date(item.get('date', '')),
                            'url': item.get('jumpUrl', ''),
                            'metadata': {
                                'stock_code': code,
                                'stock_name': name,
                                'info_type': 'research',
                                'broker': item.get('source', '')
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

    def collect_all(self, limit_per_stock: int = 5) -> int:
        """采集所有持仓股票研报"""
        holdings = self.load_holdings()
        if not holdings:
            print("No holdings found")
            return 0

        print(f"开始采集 {len(holdings)} 只股票研报...")
        total_saved = 0

        for idx, (code, name) in enumerate(holdings.items(), 1):
            print(f"\n[{code}] {name} ({idx}/{len(holdings)})")

            items = self.search_research(code, name)

            saved = 0
            duplicates = 0
            for item in items[:limit_per_stock]:
                item['source_type'] = 'research'

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

        print(f"\n研报采集完成，新增 {total_saved} 条")
        return total_saved

    def collect_from_eastmoney_web(self, code: str, name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """补充渠道1: 从东方财富研报中心API爬取（免费，不消耗配额）"""
        items = []
        try:
            # 东方财富研报公开API（无需key）
            begin_time = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            end_time = datetime.now().strftime('%Y-%m-%d')

            url = 'https://reportapi.eastmoney.com/report/list'
            params = {
                'industryCode': '*',
                'pageNo': 1,
                'pageSize': limit,
                'code': code,
                'beginTime': begin_time,
                'endTime': end_time,
                'qType': 0  # 个股研报
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            reports = data.get('data', [])

            for report in reports[:limit]:
                info_code = report.get('infoCode', '')
                report_url = f'https://data.eastmoney.com/report/zw_stock.jshtml?infocode={info_code}' if info_code else ''

                # 构建元数据
                metadata = {
                    'stock_code': code,
                    'stock_name': name,
                    'info_type': 'research',
                    'broker': report.get('orgSName', ''),
                    'rating': report.get('emRatingName', ''),
                    'eps_forecast': report.get('predictNextYearEps', ''),
                    'pe_forecast': report.get('predictNextYearPe', ''),
                    'channel': 'eastmoney_api'
                }

                # 生成AI摘要
                summary = self._generate_research_summary(
                    title=report.get('title', ''),
                    broker=metadata['broker'],
                    rating=metadata['rating'],
                    eps=metadata['eps_forecast'],
                    pe=metadata['pe_forecast'],
                    stock_name=name
                )

                items.append({
                    'title': report.get('title', ''),
                    'content': summary,
                    'source': metadata['broker'],
                    'published_at': datetime.strptime(report.get('publishDate', '')[:10], '%Y-%m-%d') if report.get('publishDate') else datetime.now(),
                    'url': report_url,
                    'metadata': metadata
                })

            print(f"  东方财富API: {len(items)}条")

        except Exception as e:
            print(f"  东方财富采集失败: {e}")

        return items

    def _generate_research_summary(self, title: str, broker: str, rating: str,
                                   eps: str, pe: str, stock_name: str) -> str:
        """生成研报投资摘要（模板版）"""
        summary_parts = [
            f"【{broker} | {rating}评级】",
            "",
            f"研报《{title}》核心观点：",
            "",
        ]

        # 业绩预测
        if eps and pe:
            summary_parts.extend([
                "1. 业绩预测与估值:",
                f"   - 预计明年EPS: {eps}元，对应PE {pe}倍",
            ])
            try:
                pe_val = float(pe)
                if pe_val < 10:
                    summary_parts.append("   - 当前估值处于历史较低水平，具备安全边际")
                elif pe_val < 15:
                    summary_parts.append("   - 当前估值处于合理区间")
                else:
                    summary_parts.append("   - 当前估值相对较高，需关注业绩兑现")
            except:
                pass
            summary_parts.append("")

        # 投资逻辑
        summary_parts.extend([
            "2. 投资逻辑:",
            f"   - {title}",
        ])

        # 提取关键词
        keywords = []
        keyword_map = {
            '弹性': '业绩弹性',
            '成长': '成长性',
            '降本': '成本控制',
            '涨价': '价格上涨',
            '产能': '产能扩张',
            '并购': '并购整合',
            '分红': '分红回报',
            '现金流': '现金流改善',
            '周期': '周期反转',
        }
        for kw, theme in keyword_map.items():
            if kw in title:
                keywords.append(theme)
        if keywords:
            summary_parts.append(f"   - 重点关注: {', '.join(keywords[:3])}")
        summary_parts.append("")

        # 机构态度
        attitude_map = {
            '买入': '积极看好',
            '增持': '看好',
            '推荐': '看好',
            '中性': '持谨慎',
            '减持': '看空',
            '卖出': '强烈看空',
        }
        attitude = attitude_map.get(rating, '中性')
        summary_parts.extend([
            "3. 机构观点:",
            f"   - {broker}给予{rating}评级，显示对{stock_name}未来表现的{attitude}态度",
        ])

        return "\n".join(summary_parts)

    def extract_pdf_content(self, detail_url: str) -> str:
        """
        从研报详情页提取PDF内容

        Args:
            detail_url: 研报详情页URL

        Returns:
            PDF正文文字
        """
        try:
            # 步骤1: 获取详情页，找到PDF链接
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(detail_url, headers=headers, timeout=15)
            resp.raise_for_status()

            html = resp.text

            # 尝试多种方式提取PDF链接
            pdf_url = None

            # 方式1: 从页面中提取PDF下载链接
            import re
            # 匹配常见的PDF链接模式
            pdf_patterns = [
                r'href="([^"]*\.pdf[^"]*)"',
                r'"pdfUrl":"([^"]+)"',
                r'"attachUrl":"([^"]+)"',
                r'data-pdf="([^"]+)"',
            ]

            for pattern in pdf_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    pdf_url = match.group(1)
                    # 处理可能的转义字符
                    pdf_url = pdf_url.replace('\\/', '/')
                    break

            # 方式2: 东方财富的PDF链接通常基于infoCode
            if not pdf_url:
                info_code_match = re.search(r'infocode=([A-Z0-9]+)', detail_url)
                if info_code_match:
                    info_code = info_code_match.group(1)
                    # 东方财富PDF链接格式
                    pdf_url = f'https://pdf.dfcfw.com/pdf/H2_{info_code}_1.pdf'

            if not pdf_url:
                print(f"  未找到PDF链接")
                return ""

            # 确保URL完整
            if pdf_url.startswith('//'):
                pdf_url = 'https:' + pdf_url
            elif pdf_url.startswith('/'):
                pdf_url = 'https://data.eastmoney.com' + pdf_url

            print(f"  找到PDF: {pdf_url[:80]}...")

            # 步骤2: 下载PDF
            pdf_resp = requests.get(pdf_url, headers=headers, timeout=30)
            pdf_resp.raise_for_status()

            # 验证是PDF文件
            content_type = pdf_resp.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not pdf_resp.content.startswith(b'%PDF'):
                print(f"  下载的不是PDF文件: {content_type}")
                return ""

            # 步骤3: 提取PDF文字
            return self._extract_text_from_pdf(pdf_resp.content)

        except Exception as e:
            print(f"  PDF提取失败: {e}")
            return ""

    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """从PDF二进制内容提取文字"""
        try:
            # 尝试使用pdfplumber（推荐）
            import pdfplumber
            import io

            text_parts = []
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

            full_text = "\n".join(text_parts)

            # 清理文本
            full_text = self._clean_pdf_text(full_text)

            return full_text

        except ImportError:
            print("  pdfplumber未安装，尝试使用PyPDF2")
            return self._extract_text_with_pypdf2(pdf_content)
        except Exception as e:
            print(f"  PDF解析失败: {e}")
            return ""

    def _extract_text_with_pypdf2(self, pdf_content: bytes) -> str:
        """使用PyPDF2提取PDF文字（备用方案）"""
        try:
            import PyPDF2
            import io

            reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return self._clean_pdf_text("\n".join(text_parts))

        except Exception as e:
            print(f"  PyPDF2解析失败: {e}")
            return ""

    def _clean_pdf_text(self, text: str) -> str:
        """清理PDF提取的文字"""
        # 移除多余的空白
        text = re.sub(r'\s+', ' ', text)
        # 移除页眉页脚常见模式
        text = re.sub(r'\d+/\d+', '', text)  # 页码
        text = re.sub(r'请仔细阅读在本报告尾部的重要法律声明', '', text)
        # 保留有意义的段落
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # 过滤太短或太长的行
            if len(line) > 10 and len(line) < 500:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines[:100])  # 限制长度

    def collect_from_10jqka(self, code: str, name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """补充渠道2: 从同花顺iFinD爬取研报"""
        items = []
        try:
            # 同花顺个股研报页面
            url = f"https://basic.10jqka.com.cn/{code}/research.html"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://basic.10jqka.com.cn/"
            }

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            html = response.text

            # 尝试提取研报列表（从页面script中提取）
            pattern = r'"reportList":\s*(\[.*?\])'
            match = re.search(pattern, html, re.DOTALL)

            if match:
                reports = json.loads(match.group(1))
                for report in reports[:limit]:
                    items.append({
                        'title': report.get('title', ''),
                        'content': report.get('content', ''),
                        'source': report.get('orgName', '同花顺'),
                        'published_at': datetime.strptime(report.get('datetime', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d %H:%M:%S') if 'datetime' in report else datetime.now(),
                        'url': report.get('url', ''),
                        'metadata': {
                            'stock_code': code,
                            'stock_name': name,
                            'info_type': 'research',
                            'broker': report.get('orgName', ''),
                            'channel': '10jqka'
                        }
                    })
            else:
                # 备用：使用同花顺API
                # 同花顺研报API（公开接口）
                api_url = f"https://d.10jqka.com.cn/v8/line/hs_{code}/01/research_report"
                resp = requests.get(api_url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    for report in data.get('data', [])[:limit]:
                        items.append({
                            'title': report.get('title', ''),
                            'content': report.get('summary', ''),
                            'source': report.get('source', '同花顺'),
                            'published_at': datetime.strptime(report.get('date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d'),
                            'url': report.get('url', ''),
                            'metadata': {
                                'stock_code': code,
                                'stock_name': name,
                                'info_type': 'research',
                                'broker': report.get('org', ''),
                                'channel': '10jqka_api'
                            }
                        })

        except Exception as e:
            print(f"  同花顺采集失败: {e}")

        return items

    def collect_all_with_supplement(self, limit_per_stock: int = 5) -> Dict[str, int]:
        """采集所有持仓股票研报（主渠道+补充渠道）"""
        holdings = self.load_holdings()
        if not holdings:
            print("No holdings found")
            return {}

        stats = {'api': 0, 'eastmoney_web': 0, '10jqka': 0}

        print(f"开始采集 {len(holdings)} 只股票研报（多渠道）...")

        for idx, (code, name) in enumerate(holdings.items(), 1):
            print(f"\n[{code}] {name} ({idx}/{len(holdings)})")

            # 渠道1: 主API
            items_api = self.search_research(code, name)
            saved_api = self._save_items(items_api[:limit_per_stock], 'api')
            stats['api'] += saved_api
            print(f"  API: {saved_api}条")

            time.sleep(1)  # 间隔避免频率限制

            # 渠道2: 东方财富网页
            items_em = self.collect_from_eastmoney_web(code, name, limit_per_stock)
            saved_em = self._save_items(items_em, 'eastmoney_web')
            stats['eastmoney_web'] += saved_em
            print(f"  东方财富网页: {saved_em}条")

            time.sleep(1)

            # 渠道3: 同花顺
            items_ths = self.collect_from_10jqka(code, name, limit_per_stock)
            saved_ths = self._save_items(items_ths, '10jqka')
            stats['10jqka'] += saved_ths
            print(f"  同花顺: {saved_ths}条")

            if idx < len(holdings):
                time.sleep(self.REQUEST_DELAY)

        print(f"\n研报采集完成:")
        print(f"  API: {stats['api']}条")
        print(f"  东方财富网页: {stats['eastmoney_web']}条")
        print(f"  同花顺: {stats['10jqka']}条")
        return stats

    def _save_items(self, items: List[Dict[str, Any]], channel: str) -> int:
        """保存采集的条目到数据库"""
        saved = 0
        for item in items:
            item['source_type'] = 'research'
            if not self.db.check_duplicate(item['url']):
                if self.db.insert_content(item):
                    saved += 1
        return saved


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='研报采集器')
    parser.add_argument('--limit', type=int, default=5, help='每只股票采集条数')
    parser.add_argument('--code', type=str, help='指定股票代码采集')
    parser.add_argument('--supplement', action='store_true', help='使用补充渠道（东方财富网页+同花顺）')
    parser.add_argument('--source', type=str, choices=['api', 'eastmoney', '10jqka', 'all'],
                        default='api', help='选择采集来源')
    args = parser.parse_args()

    collector = ResearchCollector()

    if args.supplement or args.source == 'all':
        # 多渠道采集
        stats = collector.collect_all_with_supplement(limit_per_stock=args.limit)
        print(f"\n总计采集: {sum(stats.values())} 条研报")
    elif args.code:
        # 单只股票指定渠道测试
        holdings = collector.load_holdings()
        name = holdings.get(args.code, '')
        if name:
            print(f"测试采集: {args.code} {name}")
            print(f"来源: {args.source}")

            if args.source == 'eastmoney':
                items = collector.collect_from_eastmoney_web(args.code, name, args.limit)
            elif args.source == '10jqka':
                items = collector.collect_from_10jqka(args.code, name, args.limit)
            else:
                items = collector.search_research(args.code, name)

            print(f"找到 {len(items)} 条研报")
            for item in items[:args.limit]:
                print(f"  - [{item['metadata'].get('channel', 'api')}] {item['title'][:50]}...")
        else:
            print(f"未找到股票代码: {args.code}")
    else:
        # 默认API采集
        count = collector.collect_all(limit_per_stock=args.limit)
        print(f"\n总计采集: {count} 条研报")


if __name__ == '__main__':
    main()
