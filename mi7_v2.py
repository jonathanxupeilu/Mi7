#!/usr/bin/env python3
"""MI7 - 简化版测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import yaml
import feedparser
import ssl
from datetime import datetime, timedelta
from storage.database import Database

ssl._create_default_https_context = ssl._create_unverified_context

print("="*60)
print("MI7 - Real RSS Collection Test")
print("="*60)
print()

# Load config
with open('config/sources.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize DB
db = Database('./data/mi7_test.db')
print("Database initialized")
print()

# Get RSS feeds
rss_feeds = config['sources']['rss']['native']['feeds']
print(f"Configured RSS feeds: {len(rss_feeds)}")

all_items = []
cutoff = datetime.now() - timedelta(hours=48)

for feed_config in rss_feeds:
    name = feed_config['name']
    url = feed_config['url']
    print(f"\nCollecting: {name}")
    print(f"  URL: {url}")
    
    try:
        feed = feedparser.parse(url)
        count = 0
        for entry in feed.entries:
            # Check time
            pub_time = None
            if hasattr(entry, 'published_parsed'):
                pub_time = datetime(*entry.published_parsed[:6])
            
            if pub_time and pub_time > cutoff:
                item = {
                    'title': entry.get('title', ''),
                    'content': entry.get('summary', '')[:500],
                    'url': entry.get('link', ''),
                    'source': name,
                    'source_type': 'RSS',
                    'published_at': pub_time,
                    'collected_at': datetime.now(),
                    'metadata': {}
                }
                all_items.append(item)
                count += 1
        
        print(f"  Collected: {count} items")
    except Exception as e:
        print(f"  Error: {e}")

print()
print("="*60)
print(f"Total collected: {len(all_items)} items")
print("="*60)

# Save to DB
saved = 0
for item in all_items:
    if not db.check_duplicate(item['url']):
        if db.insert_content(item):
            saved += 1

print(f"\nSaved to database: {saved} new items")

# Show sample
if all_items:
    print("\nSample items:")
    for i, item in enumerate(all_items[:5]):
        print(f"{i+1}. [{item['source']}] {item['title'][:60]}...")

print("\nDone!")
