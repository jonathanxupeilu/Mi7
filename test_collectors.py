#!/usr/bin/env python3
"""Test collectors with mock data"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from collectors.rss_collector import RSSCollector
from storage.database import Database
import tempfile
import os
from datetime import datetime

print("MI7 Collector Test")
print("="*60)

temp_dir = tempfile.mkdtemp()
db_path = os.path.join(temp_dir, "test.db")

# Test RSS Collector
rss_config = {'feeds': [{'id': 'test', 'name': 'Test', 'url': 'https://test.com', 'enabled': True}]}
collector = RSSCollector(rss_config)
print(f"RSS Collector: {type(collector).__name__}")
print(f"Enabled: {collector.is_enabled()}")

# Test Database
db = Database(db_path)
print(f"Database created: {os.path.exists(db_path)}")

# Insert mock data
mock_item = {
    'title': 'Test - AAPL Stock Surges 5%',
    'content': 'Apple stock surged 5% today...',
    'url': 'https://test.com/1',
    'source': 'Test',
    'source_type': 'RSSCollector',
    'published_at': datetime.now(),
    'collected_at': datetime.now(),
    'metadata': {}
}
result = db.insert_content(mock_item)
print(f"Insert success: {result}")
print(f"Duplicate check: {db.check_duplicate(mock_item['url'])}")

# Cleanup
import shutil
shutil.rmtree(temp_dir)
print("Test completed successfully!")
