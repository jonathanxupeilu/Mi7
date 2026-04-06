#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import feedparser
import ssl
from datetime import datetime, timedelta

ssl._create_default_https_context = ssl._create_unverified_context

print("Testing Time Filter Logic")
print("="*60)

# Test Hacker News
url = "https://hnrss.org/frontpage"
feed = feedparser.parse(url)

print(f"Total entries: {len(feed.entries)}")
print()

# Check time window
cutoff_48h = datetime.now() - timedelta(hours=48)
cutoff_168h = datetime.now() - timedelta(hours=168)  # 7 days

recent_48h = []
recent_168h = []

for entry in feed.entries:
    try:
        if hasattr(entry, 'published_parsed'):
            pub_time = datetime(*entry.published_parsed[:6])
            if pub_time > cutoff_48h:
                recent_48h.append(entry)
            if pub_time > cutoff_168h:
                recent_168h.append(entry)
    except:
        pass

print(f"Entries in last 48 hours: {len(recent_48h)}")
print(f"Entries in last 168 hours (7 days): {len(recent_168h)}")
print()

if recent_168h:
    print("Sample entries from last 7 days:")
    for i, entry in enumerate(recent_168h[:3]):
        print(f"  {i+1}. {entry.title[:60]}...")
else:
    print("No entries found in last 7 days")
    print("\nAll entries timestamps:")
    for i, entry in enumerate(feed.entries[:5]):
        pub = entry.get('published', 'N/A')
        print(f"  {i+1}. {pub}")
