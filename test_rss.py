#!/usr/bin/env python3
"""测试RSS源可用性"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import feedparser
import ssl

# 禁用SSL验证
ssl._create_default_https_context = ssl._create_unverified_context

print("="*60)
print("RSS Feed Availability Test")
print("="*60)
print()

# 测试配置中的RSS源
feeds_to_test = [
    ("CNBC YouTube", "https://www.youtube.com/feeds/videos.xml?channel_id=UCe_3CN7FHPVCIifAnD7hL_A"),
    ("Bloomberg YouTube", "https://www.youtube.com/feeds/videos.xml?channel_id=UChKG8K6YZE"),
    ("ARK Invest YouTube", "https://www.youtube.com/feeds/videos.xml?channel_id=UC-0PpCqHGAw"),
    ("Hacker News", "https://hnrss.org/frontpage"),
    ("GitHub Blog", "https://github.blog/feed/"),
]

working_feeds = []
failed_feeds = []

for name, url in feeds_to_test:
    print(f"Testing: {name}")
    print(f"  URL: {url}")
    try:
        feed = feedparser.parse(url)
        if hasattr(feed, 'entries') and len(feed.entries) > 0:
            print(f"  ✓ SUCCESS: {len(feed.entries)} entries")
            print(f"  Latest: {feed.entries[0].get('title', 'N/A')[:60]}...")
            working_feeds.append((name, url, len(feed.entries)))
        else:
            print(f"  ✗ No entries found")
            print(f"    Feed status: {feed.get('bozo', 'Unknown')}")
            failed_feeds.append((name, url, "No entries"))
    except Exception as e:
        print(f"  ✗ ERROR: {str(e)[:80]}")
        failed_feeds.append((name, url, str(e)))
    print()

# 汇总
print("="*60)
print("SUMMARY")
print("="*60)
print(f"Working feeds: {len(working_feeds)}")
for name, url, count in working_feeds:
    print(f"  ✓ {name} ({count} entries)")
    
if failed_feeds:
    print(f"\nFailed feeds: {len(failed_feeds)}")
    for name, url, error in failed_feeds:
        print(f"  ✗ {name}")
        
print()
