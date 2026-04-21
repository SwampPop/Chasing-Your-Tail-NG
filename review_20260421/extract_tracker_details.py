#!/usr/bin/env python3
"""Extract per-tracker match_details JSON from watchdog_live.db into a flat CSV."""
import csv
import json
import sqlite3
from datetime import datetime

DB = 'watchdog_live.db'
OUT = 'review_20260421/tracker_details.csv'


def fmt_ts(ts):
    if not ts:
        return ''
    try:
        return datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError):
        return ''


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT mac, manufacturer, ssid, rssi, latitude, longitude, "
        "confidence, detection_method, first_seen, last_seen, seen_count, details "
        "FROM detections WHERE device_type='tracker' "
        "ORDER BY seen_count DESC"
    ).fetchall()

    fields = [
        'mac', 'tracker_type', 'manufacturer',
        'first_seen_local', 'last_seen_local', 'duration_min',
        'db_seen_count', 'in_memory_seen_count', 'unique_locations',
        'is_following', 'detection_method', 'confidence',
        'last_rssi', 'last_lat', 'last_lon',
    ]

    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            try:
                md = json.loads(r['details']) if r['details'] else {}
            except (json.JSONDecodeError, TypeError):
                md = {}
            duration = (r['last_seen'] - r['first_seen']) / 60.0 if (r['last_seen'] and r['first_seen']) else 0.0
            w.writerow({
                'mac': r['mac'],
                'tracker_type': md.get('tracker_type', r['ssid'] or ''),
                'manufacturer': r['manufacturer'],
                'first_seen_local': fmt_ts(md.get('first_seen') or r['first_seen']),
                'last_seen_local': fmt_ts(r['last_seen']),
                'duration_min': round(duration, 2),
                'db_seen_count': r['seen_count'],
                'in_memory_seen_count': md.get('seen_count', ''),
                'unique_locations': md.get('unique_locations', 0),
                'is_following': md.get('is_following', False),
                'detection_method': r['detection_method'],
                'confidence': r['confidence'],
                'last_rssi': r['rssi'],
                'last_lat': r['latitude'],
                'last_lon': r['longitude'],
            })

    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == '__main__':
    main()
