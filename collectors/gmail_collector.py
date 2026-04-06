"""Gmail邮件采集器 - 自动采集Google Alerts邮件并提取内容"""
import os
import imaplib
import email
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv
from email.header import decode_header
from email.utils import parsedate_to_datetime

load_dotenv()


class GmailCollector:
    """Gmail邮件采集器"""

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    def __init__(self, db_path: str = "./data/mi7.db"):
        self.db_path = db_path
        self.email = os.getenv("GMAIL_ADDRESS")
        self.password = os.getenv("GMAIL_APP_PASSWORD")

        if not self.email or not self.password:
            raise ValueError("需要设置 GMAIL_ADDRESS 和 GMAIL_APP_PASSWORD 环境变量")

    def collect(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        从Gmail采集Google Alerts邮件

        Args:
            hours: 最近多少小时内的邮件

        Returns:
            解析后的内容列表
        """
        items = []

        try:
            # 连接Gmail
            print(f"连接Gmail ({self.email})...")
            mail = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)
            mail.login(self.email, self.password)
            mail.select("inbox")

            # 搜索Google Alerts邮件
            since_date = (datetime.now() - timedelta(hours=hours)).strftime("%d-%b-%Y")
            search_query = f'(FROM "googlealerts-noreply@google.com" SINCE "{since_date}")'

            print(f"搜索最近{hours}小时的Google Alerts邮件...")
            _, message_numbers = mail.search(None, search_query)

            if not message_numbers[0]:
                print("没有找到新的Google Alerts邮件")
                return items

            msg_ids = message_numbers[0].split()
            print(f"找到 {len(msg_ids)} 封邮件")

            # 解析每封邮件
            for msg_id in msg_ids[-20:]:  # 最多处理20封最新邮件
                try:
                    _, msg_data = mail.fetch(msg_id, "(RFC822)")
                    email_body = msg_data[0][1]
                    msg = email.message_from_bytes(email_body)

                    # 解析邮件内容
                    parsed_items = self._parse_email(msg)
                    items.extend(parsed_items)

                    # 标记为已读（可选）
                    # mail.store(msg_id, '+FLAGS', '\\Seen')

                except Exception as e:
                    print(f"解析邮件失败: {e}")
                    continue

            mail.close()
            mail.logout()

        except Exception as e:
            print(f"Gmail连接失败: {e}")

        return items

    def _parse_email(self, msg) -> List[Dict[str, Any]]:
        """解析单封邮件，提取内容"""
        items = []

        # 获取主题
        subject = self._decode_header(msg["Subject"])

        # 获取发件人
        from_addr = self._decode_header(msg["From"])

        # 获取日期
        date_str = msg["Date"]
        try:
            published_at = parsedate_to_datetime(date_str)
        except:
            published_at = datetime.now()

        # 获取邮件正文
        body = self._get_email_body(msg)
        if not body:
            return items

        # 提取Twitter链接
        twitter_links = self._extract_twitter_links(body)

        # 为每个链接创建条目
        for link in twitter_links:
            item = {
                'title': self._extract_title(body) or subject,
                'content': self._clean_html(body),
                'url': link,
                'source': self._detect_source(body),
                'published_at': published_at,
                'metadata': {
                    'via': 'google_alerts',
                    'email_subject': subject
                }
            }
            items.append(item)

        return items

    def _decode_header(self, header) -> str:
        """解码邮件头"""
        if not header:
            return ""
        decoded = decode_header(header)
        result = []
        for part, charset in decoded:
            if isinstance(part, bytes):
                result.append(part.decode(charset or 'utf-8', errors='ignore'))
            else:
                result.append(part)
        return "".join(result)

    def _get_email_body(self, msg) -> str:
        """获取邮件正文"""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/html":
                    try:
                        return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
                elif content_type == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass
        return ""

    def _extract_twitter_links(self, body: str) -> List[str]:
        """提取Twitter链接"""
        # 匹配 twitter.com/x/status/xxx 或 twitter.com/username/status/xxx
        patterns = [
            r'https?://twitter\.com/[^/\s]+/status/\d+',
            r'https?://x\.com/[^/\s]+/status/\d+',
        ]

        links = []
        for pattern in patterns:
            matches = re.findall(pattern, body)
            links.extend(matches)

        # 去重
        return list(set(links))

    def _extract_title(self, body: str) -> str:
        """从HTML中提取标题"""
        # 尝试提取 <a> 标签的文本
        title_match = re.search(r'<a[^>]*twitter\.com[^>]*>([^<]+)</a>', body)
        if title_match:
            return self._clean_html(title_match.group(1))

        # 尝试提取第一个标题
        title_match = re.search(r'<h[1-6][^>]*>([^<]+)</h[1-6]>', body)
        if title_match:
            return self._clean_html(title_match.group(1))

        return ""

    def _detect_source(self, body: str) -> str:
        """检测来源（Twitter用户名）"""
        # 从链接中检测
        match = re.search(r'twitter\.com/([^/]+)/', body)
        if match:
            username = match.group(1)
            name_map = {
                'PeterSchiff': 'Twitter/Peter Schiff',
                'RayDalio': 'Twitter/Ray Dalio',
                'GaveKal': 'Twitter/Louis-Vincent Gave',
                'HowardMarksBook': 'Twitter/Howard Marks',
                'WarrenBuffett': 'Twitter/Warren Buffett',
                'CathieDWood': 'Twitter/Cathie Wood',
            }
            return name_map.get(username, f"Twitter/{username}")

        return "Google Alerts"

    def _clean_html(self, html: str) -> str:
        """清理HTML标签"""
        # 简单的HTML标签清理
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&quot;', '"', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def save_to_database(self, items: List[Dict[str, Any]]) -> int:
        """保存到数据库"""
        from storage.database import Database

        db = Database(self.db_path)
        saved = 0
        duplicates = 0

        for item in items:
            if not db.check_duplicate(item['url']):
                if db.insert_content(item):
                    saved += 1
            else:
                duplicates += 1

        print(f"保存到数据库: 新增{saved}条, 重复{duplicates}条")
        return saved


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='Gmail邮件采集器')
    parser.add_argument('--hours', type=int, default=24, help='采集最近多少小时的邮件')
    parser.add_argument('--save', action='store_true', help='保存到数据库')
    args = parser.parse_args()

    collector = GmailCollector()
    items = collector.collect(hours=args.hours)

    print(f"\n采集到 {len(items)} 条内容")

    if items:
        print("\n预览:")
        for item in items[:3]:
            print(f"  [{item['source']}] {item['title'][:50]}...")
            print(f"    URL: {item['url'][:60]}...")

    if args.save and items:
        saved = collector.save_to_database(items)
        print(f"\n已保存 {saved} 条到数据库")


if __name__ == '__main__':
    main()
