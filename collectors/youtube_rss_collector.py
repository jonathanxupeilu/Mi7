"""YouTube官方RSS采集器"""
import feedparser
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta
from .base_collector import BaseCollector


class YouTubeRSSCollector(BaseCollector):
    """YouTube官方RSS采集器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.feeds = config.get('feeds', [])

    def collect(self, hours: int = 24) -> List[Dict[str, Any]]:
        items = []
        cutoff_time = datetime.now() - timedelta(hours=hours)

        for feed_config in self.feeds:
            if not feed_config.get('enabled', False):
                continue
            try:
                feed_items = self._parse_feed(feed_config, cutoff_time)
                items.extend(feed_items)
            except Exception as e:
                print(f"Error parsing YouTube feed {feed_config.get('name')}: {e}")
        return items

    def _fetch_with_retry(self, url: str, max_retries: int = 3, backoff: float = 1.0) -> Dict[str, Any]:
        """
        带重试的 RSS 获取

        Args:
            url: RSS URL
            max_retries: 最大重试次数
            backoff: 退避延迟（秒）

        Returns:
            feedparser 解析结果

        Raises:
            Exception: 重试耗尽后抛出最后一次异常
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                feed = feedparser.parse(url)
                # 检查是否有解析错误（YouTube 经常返回 bozo）
                if hasattr(feed, 'bozo_exception') and feed.bozo:
                    # 如果有条目，即使有警告也算成功
                    if feed.entries:
                        return feed
                    # 没有条目，可能是临时错误，继续重试
                    raise Exception(f"Feed parse warning: {feed.bozo_exception}")
                return feed
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    sleep_time = backoff * (2 ** attempt)  # 指数退避
                    print(f"[Retry {attempt + 1}/{max_retries}] {url} failed: {e}. Waiting {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    print(f"[Retry exhausted] {url} failed after {max_retries} attempts")

        raise last_exception

    def _parse_feed(self, feed_config: Dict[str, Any], cutoff_time: datetime) -> List[Dict[str, Any]]:
        url = feed_config.get('url')
        channel_id = feed_config.get('channel_id')
        name = feed_config.get('name', 'Unknown')

        # 使用重试机制获取 feed
        feed = self._fetch_with_retry(url, max_retries=3, backoff=1.0)
        items = []

        for entry in feed.entries:
            published = self._get_published_time(entry)
            if published and published < cutoff_time:
                continue
            video_id = self._extract_video_id(entry)
            item = {
                'title': entry.get('title', ''),
                'content': entry.get('summary', ''),
                'url': entry.get('link', ''),
                'source': name,
                'published_at': published or datetime.now(),
                'metadata': {
                    'channel_id': channel_id,
                    'channel_name': name,
                    'video_id': video_id,
                    'media_type': 'youtube_video'
                }
            }
            items.append(self.normalize_item(item))
        return items

    def _get_published_time(self, entry) -> datetime:
        try:
            if hasattr(entry, 'published_parsed'):
                return datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed'):
                return datetime(*entry.updated_parsed[:6])
        except:
            pass
        return datetime.now()

    def _extract_video_id(self, entry) -> str:
        link = entry.get('link', '')
        if 'v=' in link:
            return link.split('v=')[1].split('&')[0]
        entry_id = entry.get('id', '')
        if ':' in entry_id:
            return entry_id.split(':')[-1]
        return ''
