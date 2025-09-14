import sqlite3
import time
import os

# This script creates a fake kismet database for testing our GUI.

DB_NAME = 'dummy_kismet.db'

# Clean up any old test database first
if os.path.exists(DB_NAME):
    os.remove(DB_NAME)

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

print("Creating dummy kismet database...")

# Create the necessary tables with the correct schema
cursor.execute('''
    CREATE TABLE devices (
        devmac TEXT PRIMARY KEY,
        first_time INTEGER,
        last_time INTEGER
    )
''')
cursor.execute('''
    CREATE TABLE device_locations (
        devmac TEXT,
        location_uuid TEXT,
        last_time INTEGER
    )
''')

# Insert a follower: a device seen at 3 distinct locations recently
follower_mac = 'AA:BB:CC:11:22:33'
current_time = int(time.time())
print("Inserting follower data...")
cursor.execute("INSERT INTO devices VALUES (?, ?, ?)", (follower_mac, current_time - 300, current_time - 10))
cursor.execute("INSERT INTO device_locations VALUES (?, ?, ?)", (follower_mac, 'uuid-loc-1-garage', current_time - 300))
cursor.execute("INSERT INTO device_locations VALUES (?, ?, ?)", (follower_mac, 'uuid-loc-2-cafe', current_time - 200))
cursor.execute("INSERT INTO device_locations VALUES (?, ?, ?)", (follower_mac, 'uuid-loc-3-highway', current_time - 100))

# Insert a normal device: seen at only 1 location
normal_mac = 'DD:EE:FF:44:55:66'
print("Inserting normal device data...")
cursor.execute("INSERT INTO devices VALUES (?, ?, ?)", (normal_mac, current_time - 50, current_time - 50))
cursor.execute("INSERT INTO device_locations VALUES (?, ?, ?)", (normal_mac, 'uuid-loc-1-garage', current_time - 50))

conn.commit()
conn.close()

print(f"'{DB_NAME}' created successfully. Ready for testing.")