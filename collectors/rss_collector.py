"""RSS采集器"""
import feedparser
from typing import List, Dict, Any
from datetime import datetime, timedelta
from .base_collector import BaseCollector


class RSSCollector(BaseCollector):
    """RSS采集器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.feeds = config.get('feeds', [])
        
    def collect(self, hours: int = 24) -> List[Dict[str, Any]]:
        items = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for feed_config in self.feeds:
            if not feed_config.get('enabled', True):  # 默认启用
                continue
            try:
                feed_items = self._parse_feed(feed_config, cutoff_time)
                items.extend(feed_items)
            except Exception as e:
                print(f"Error parsing feed {feed_config.get('name')}: {e}")
        return items
        
    def _parse_feed(self, feed_config: Dict[str, Any], cutoff_time: datetime) -> List[Dict[str, Any]]:
        url = feed_config.get('url')
        name = feed_config.get('name', 'Unknown')
        feed = feedparser.parse(url)
        items = []
        
        for entry in feed.entries:
            published = self._get_published_time(entry)
            if published and published < cutoff_time:
                continue
            item = {
                'title': entry.get('title', ''),
                'content': entry.get('summary', entry.get('description', '')),
                'url': entry.get('link', ''),
                'source': name,
                'published_at': published or datetime.now(),
                'metadata': {}
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
