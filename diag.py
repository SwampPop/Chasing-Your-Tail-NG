#!/usr/bin/env python3
"""Quick diagnostic: verify Kismet DB data is readable by CYT."""
import sys
import os
import time
import json
import sqlite3

sys.path.insert(0, os.path.dirname(__file__))
from lib.gui_logic import get_kismet_logs_path, find_latest_db_path

# Load config
with open('config.json') as f:
    config = json.load(f)

db_pattern = get_kismet_logs_path(config)
print(f"DB path pattern: {db_pattern}")

db_path, glob_pattern = find_latest_db_path(db_pattern, fallback_path="test_capture.kismet")
print(f"Latest DB: {db_path}")
print(f"Glob pattern: {glob_pattern}")

if db_path == "NOT_FOUND":
    print("FAIL: No database found")
    sys.exit(1)

# Check file stats
stat = os.stat(db_path)
age = time.time() - stat.st_mtime
print(f"DB size: {stat.st_size:,} bytes")
print(f"DB age: {age:.0f} seconds ({age/60:.1f} minutes)")

# Direct query
print("\n--- Direct SQLite query ---")
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Total devices
cur.execute("SELECT COUNT(*) as cnt FROM devices")
total = cur.fetchone()['cnt']
print(f"Total devices in DB: {total}")

# Recent devices (last 2 min)
threshold_2m = int(time.time()) - 120
cur.execute("SELECT COUNT(*) as cnt FROM devices WHERE last_time > ?", (threshold_2m,))
recent_2m = cur.fetchone()['cnt']
print(f"Devices seen in last 2 min: {recent_2m}")

# Recent devices (last 10 min)
threshold_10m = int(time.time()) - 600
cur.execute("SELECT COUNT(*) as cnt FROM devices WHERE last_time > ?", (threshold_10m,))
recent_10m = cur.fetchone()['cnt']
print(f"Devices seen in last 10 min: {recent_10m}")

# Check timestamps
cur.execute("SELECT MAX(last_time) as newest, MIN(last_time) as oldest FROM devices")
row = cur.fetchone()
if row['newest']:
    now = time.time()
    newest_age = now - row['newest']
    print(f"\nNewest device timestamp: {row['newest']} ({newest_age:.0f}s ago)")
    print(f"Oldest device timestamp: {row['oldest']}")
    print(f"Current system time:     {now:.0f}")
    if newest_age > 300:
        print(f"WARNING: Newest device is {newest_age/60:.1f} min old — possible clock skew or stale DB")
else:
    print("WARNING: No device timestamps found — DB may be empty")

# Show 5 most recent devices
print("\n--- 5 Most Recent Devices ---")
cur.execute("SELECT devmac, type, last_time, strongest_signal FROM devices ORDER BY last_time DESC LIMIT 5")
for r in cur.fetchall():
    age_s = time.time() - r['last_time']
    print(f"  {r['devmac']}  sig={r['strongest_signal']}  type={r['type']}  {age_s:.0f}s ago")

conn.close()
print("\nDiagnostic complete.")
