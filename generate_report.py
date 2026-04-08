#!/usr/bin/env python3
"""Generate TXT report from database"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from storage.database import Database
from datetime import datetime

db = Database()

# Get today's content
from datetime import date
today = date.today()

print("="*70)
print("MI7 - Daily Intelligence Report")
print("="*70)
print(f"Date: {today}")
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Query all content
conn = db.get_connection()
conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
cursor = conn.cursor()
cursor.execute("SELECT * FROM content ORDER BY collected_at DESC LIMIT 50")
rows = cursor.fetchall()

if not rows:
    print("No data available")
else:
    print(f"Total items in database: {len(rows)}")
    print()
    print("Recent items:")
    print("-"*70)
    
    for i, row in enumerate(rows[:10], 1):
        source = row.get('source', 'Unknown')
        title = row.get('title', 'N/A')
        url = row.get('url', '')
        pub = row.get('published_at', 'N/A')
        
        print(f"\n{i}. [{source}]")
        print(f"   Title: {title}")
        print(f"   URL: {url[:60]}..." if len(url) > 60 else f"   URL: {url}")
        print(f"   Published: {pub}")

print()
print("="*70)
print("End of Report")
print("="*70)
