"""Nitter RSS采集器"""
import time
import feedparser
from typing import List, Dict, Any
from datetime import datetime, timedelta
from .base_collector import BaseCollector


class NitterCollector(BaseCollector):
    """Nitter RSS采集器 - 支持按优先级分批次延迟采集"""

    # 批次间延迟（秒）
    BATCH_DELAY = 3.0

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.instances = config.get('instances', [])
        self.accounts = config.get('accounts', [])

    def collect(self, hours: int = 24) -> List[Dict[str, Any]]:
        """按优先级分批次采集"""
        items = []
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # 按优先级分组
        priority_groups = {'high': [], 'medium': [], 'low': []}
        for account in self.accounts:
            if not account.get('enabled', True):
                continue
            priority = account.get('priority', 'medium')
            priority_groups[priority].append(account)

        # 按优先级顺序采集：high -> medium -> low
        for priority in ['high', 'medium', 'low']:
            group = priority_groups[priority]
            if not group:
                continue

            print(f"\n[优先级: {priority.upper()}] 采集 {len(group)} 个账号...")

            for account_config in group:
                try:
                    account_items = self._collect_account(account_config, cutoff_time)
                    items.extend(account_items)
                except Exception as e:
                    print(f"Error collecting {account_config.get('username')}: {e}")

            # 非最后批次，添加延迟
            if priority != 'low' and priority_groups['medium'] or priority_groups['low']:
                if priority == 'high' and (priority_groups['medium'] or priority_groups['low']):
                    print(f"  延迟 {self.BATCH_DELAY}s 避免触发限流...")
                    time.sleep(self.BATCH_DELAY)
                elif priority == 'medium' and priority_groups['low']:
                    print(f"  延迟 {self.BATCH_DELAY}s 避免触发限流...")
                    time.sleep(self.BATCH_DELAY)

        return items
        
    def _collect_account(self, account_config: Dict[str, Any], cutoff_time: datetime) -> List[Dict[str, Any]]:
        username = account_config.get('username')
        name = account_config.get('name', username)
        priority = account_config.get('priority', 'medium')
        if not username:
            return []
            
        for instance in self.instances:
            try:
                items = self._fetch_from_instance(instance, username, name, priority, cutoff_time)
                if items:
                    print(f"[OK] From {instance} 采集 @{username}: {len(items)}条")
                    return items
            except Exception as e:
                print(f"[FAIL] Instance {instance} 失败: {e}")
                continue
                
        print(f"[WARN] All Nitter实例都无法采集 @{username}")
        return []
        
    def _fetch_from_instance(self, instance: str, username: str, name: str, 
                             priority: str, cutoff_time: datetime) -> List[Dict[str, Any]]:
        rss_url = f"{instance}/{username}/rss"
        feed = feedparser.parse(rss_url)
        
        if feed.bozo and '404' in str(feed.get('bozo_exception', '')):
            raise Exception(f"User not found or instance down")
            
        items = []
        for entry in feed.entries:
            published = self._get_published_time(entry)
            if published and published < cutoff_time:
                continue
            tweet_id = self._extract_tweet_id(entry)
            tweet_url = f"https://twitter.com/{username}/status/{tweet_id}" if tweet_id else entry.get('link', '')
            item = {
                'title': entry.get('title', '')[:100] + '...',
                'content': entry.get('summary', ''),
                'url': tweet_url,
                'source': f"Twitter/{name}",
                'published_at': published or datetime.now(),
                'metadata': {
                    'username': username,
                    'tweet_id': tweet_id,
                    'media_type': 'twitter_post',
                    'source_platform': 'nitter',
                    'priority': priority
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
        
    def _extract_tweet_id(self, entry) -> str:
        entry_id = entry.get('id', '')
        if '/status/' in entry_id:
            return entry_id.split('/status/')[-1]
        return ''
