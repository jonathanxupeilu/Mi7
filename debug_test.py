#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import feedparser
import ssl
from datetime import datetime, timedelta

ssl._create_default_https_context = ssl._create_unverified_context

print("MI7 RSS Debug Test")
print("="*60)

test_urls = [
    ("CNBC YouTube", "https://www.youtube.com/feeds/videos.xml?channel_id=UCe_3CN7FHPVCIifAnD7hL_A"),
    ("Hacker News", "https://hnrss.org/frontpage"),
]

for name, url in test_urls:
    print(f"\nTesting: {name}")
    try:
        feed = feedparser.parse(url)
        print(f"  Entries: {len(feed.entries)}")
        if feed.entries:
            print(f"  Latest: {feed.entries[0].title[:50]}")
    except Exception as e:
        print(f"  Error: {e}")

print("\nDone!")
