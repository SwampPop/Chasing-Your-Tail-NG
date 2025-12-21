# Device Investigation Queries - Quick Reference

This guide provides SQL queries to help you investigate and categorize devices from your Kismet capture.

## Setup

All queries assume you're in the CYT directory with Kismet database in `logs/kismet/`.

```bash
cd ~/Chasing-Your-Tail-NG

# Find your latest Kismet database
DB=$(ls -t logs/kismet/*.kismet | head -1)
echo "Using database: $DB"
```

---

## Quick Investigation Queries

### 1. Device Type Summary (What's Been Captured?)

**Shows count of each device type:**

```bash
sqlite3 "$DB" << 'EOF'
.mode column
.headers on
SELECT type, COUNT(*) as count
FROM devices
GROUP BY type
ORDER BY count DESC;
EOF
```

**What to look for:**
- `Wi-Fi AP` = Routers (mostly static, should be ignored)
- `Wi-Fi Device` = Clients (phones, laptops - mobile threats)
- `Bluetooth` / `BTLE` = Bluetooth devices (trackers, phones, cars)
- `UAV` = Drones (immediate threat)

---

### 2. WiFi Access Points (Your Routers vs Neighbors')

**Lists all routers sorted by signal strength:**

```bash
sqlite3 "$DB" << 'EOF'
.mode column
.headers on
SELECT
    devmac,
    last_signal as signal,
    packets,
    datetime(first_time, 'unixepoch') as first_seen,
    datetime(last_time, 'unixepoch') as last_seen
FROM devices
WHERE type = 'Wi-Fi AP'
ORDER BY last_signal DESC
LIMIT 30;
EOF
```

**How to categorize:**
- **Signal > -50 dBm** → Very close (yours or immediate neighbor)
  - **Action:** Add to ignore list
- **Signal -50 to -70 dBm** → Nearby neighbor
  - **Action:** If always visible, add to ignore list
- **Signal < -70 dBm** → Far away
  - **Action:** Usually safe to ignore

---

### 3. WiFi Client Devices (Phones, Laptops - Mobile Threats)

**Shows devices that could be following you:**

```bash
sqlite3 "$DB" << 'EOF'
.mode column
.headers on
SELECT
    devmac,
    min_signal,
    max_signal,
    (max_signal - min_signal) as variance,
    packets,
    datetime(last_time, 'unixepoch') as last_seen
FROM devices
WHERE type = 'Wi-Fi Device'
ORDER BY last_time DESC
LIMIT 30;
EOF
```

**How to categorize:**
- **Variance > 20 dBm** → Mobile device (signal changes = movement)
  - **Action:** DO NOT ignore unless it's YOUR device
- **Variance < 10 dBm** → Static device (IoT, security camera, etc.)
  - **Action:** If yours or neighbor's, add to ignore list

---

### 4. Bluetooth Devices (Trackers, TPMS, Phones)

**Shows all Bluetooth/BTLE devices:**

```bash
sqlite3 "$DB" << 'EOF'
.mode column
.headers on
SELECT
    devmac,
    type,
    packets,
    datetime(first_time, 'unixepoch') as first_seen,
    datetime(last_time, 'unixepoch') as last_seen
FROM devices
WHERE type IN ('Bluetooth', 'BTLE')
ORDER BY last_time DESC
LIMIT 30;
EOF
```

**How to categorize:**
- **Your devices** → Add to ignore list (phone BT MAC, watch, car TPMS, earbuds)
- **Parked cars** → Add to ignore list (static TPMS sensors)
- **Unknown** → **DO NOT IGNORE** (could be AirTag or tracking device!)

---

### 5. Investigate Specific Device

**Deep dive into one device (replace MAC address):**

```bash
MAC="AA:BB:CC:DD:EE:FF"  # Replace with actual MAC

sqlite3 "$DB" << EOF
.mode column
.headers on
SELECT
    devmac,
    type,
    phyname,
    min_signal,
    max_signal,
    (max_signal - min_signal) as signal_variance,
    packets,
    datetime(first_time, 'unixepoch') as first_seen,
    datetime(last_time, 'unixepoch') as last_seen,
    min_lat,
    min_lon,
    max_lat,
    max_lon
FROM devices
WHERE devmac = '$MAC';
EOF
```

**Analysis:**
- **Signal variance > 20** → Mobile device
- **Signal variance < 10** → Static device
- **GPS coordinates vary** → Device is moving
- **GPS coordinates same** → Stationary

---

### 6. Recently Seen Devices (Last Hour)

**Shows devices detected in the last hour:**

```bash
sqlite3 "$DB" << 'EOF'
.mode column
.headers on
SELECT
    devmac,
    type,
    last_signal,
    datetime(last_time, 'unixepoch') as last_seen
FROM devices
WHERE last_time > strftime('%s', 'now', '-1 hour')
ORDER BY last_time DESC;
EOF
```

**Use this to:**
- Find NEW devices that appeared recently
- Check if a specific device is currently nearby
- Monitor for surveillance devices in real-time

---

### 7. Devices by Manufacturer (OUI Lookup)

**Shows top manufacturers by device count:**

```bash
sqlite3 "$DB" << 'EOF'
.mode column
.headers on
SELECT
    substr(devmac, 1, 8) as oui_prefix,
    COUNT(*) as device_count
FROM devices
GROUP BY oui_prefix
ORDER BY device_count DESC
LIMIT 20;
EOF
```

**Then lookup manufacturer online:**

```bash
# On macOS (outside VM):
OUI="AA:BB:CC"  # First 3 bytes of MAC
curl -s "https://api.macvendors.com/$OUI"
```

**Common manufacturers to recognize:**
- Your brands: Apple, Samsung, Google (your devices)
- Router brands: Netgear, TP-Link, Asus, Vantiva (routers to ignore)
- Security: Ring, Nest, Arlo (IoT devices)

---

### 8. Devices That Appeared Multiple Times (Following Pattern)

**Shows devices seen across multiple sessions:**

```bash
sqlite3 "$DB" << 'EOF'
.mode column
.headers on
SELECT
    devmac,
    type,
    COUNT(DISTINCT date(last_time, 'unixepoch')) as days_seen,
    packets,
    datetime(first_time, 'unixepoch') as first_seen,
    datetime(last_time, 'unixepoch') as last_seen
FROM devices
WHERE type IN ('Wi-Fi Device', 'Bluetooth', 'BTLE')
GROUP BY devmac
HAVING days_seen > 1
ORDER BY days_seen DESC
LIMIT 30;
EOF
```

**How to categorize:**
- **Days seen = Total days you've used Kismet** → Your device or static neighbor
  - **Action:** Add to ignore list if yours
- **Days seen = 1-2** → Possibly following or coincidence
  - **Action:** DO NOT ignore, monitor further

---

### 9. Strong Signal Devices (Very Close to You)

**Devices with very strong signal (< -50 dBm):**

```bash
sqlite3 "$DB" << 'EOF'
.mode column
.headers on
SELECT
    devmac,
    type,
    max_signal,
    packets,
    datetime(last_time, 'unixepoch') as last_seen
FROM devices
WHERE max_signal > -50
ORDER BY max_signal DESC;
EOF
```

**Analysis:**
- These are VERY close to you (< 10 meters)
- Should be your devices or immediate neighbors
- Unknown devices with strong signal are suspicious

---

### 10. Export for External Analysis

**Export all devices to CSV for spreadsheet analysis:**

```bash
sqlite3 "$DB" << 'EOF'
.mode csv
.headers on
.output devices_export.csv
SELECT
    devmac,
    type,
    phyname,
    min_signal,
    max_signal,
    packets,
    datetime(first_time, 'unixepoch') as first_seen,
    datetime(last_time, 'unixepoch') as last_seen
FROM devices
ORDER BY last_time DESC;
.output stdout
EOF

echo "Exported to devices_export.csv"
```

**Then open in Excel/LibreOffice:**
- Sort by signal strength
- Filter by device type
- Add column for "My Device?" (Yes/No)
- Add column for "Ignore?" (Yes/No)

---

## Decision Tree for Categorization

### For Each Device, Ask:

```
1. Is the MAC address mine?
   ├─ YES → Add to ignore list with comment
   └─ NO → Continue to step 2

2. What type is it?
   ├─ Wi-Fi AP (Router)
   │   ├─ Signal > -50 dBm → Yours or immediate neighbor → ADD to ignore
   │   ├─ Signal -50 to -70 → Nearby neighbor (if static) → ADD to ignore
   │   └─ Signal < -70 → Far away → ADD to ignore
   │
   ├─ Wi-Fi Device (Client)
   │   ├─ Signal variance > 20 dBm → Mobile device
   │   │   ├─ Yours → ADD to ignore
   │   │   └─ Unknown → DO NOT IGNORE (potential threat)
   │   └─ Signal variance < 10 dBm → Static IoT
   │       ├─ Yours → ADD to ignore
   │       └─ Neighbor's → ADD to ignore
   │
   └─ Bluetooth/BTLE
       ├─ Your phone/watch/car/earbuds → ADD to ignore
       ├─ Parked car (static TPMS) → ADD to ignore
       └─ Unknown → DO NOT IGNORE (could be tracker!)
```

---

## Practical Workflow

### Step 1: Get Overview

```bash
DB=$(ls -t logs/kismet/*.kismet | head -1)

# See what you have
sqlite3 "$DB" "SELECT type, COUNT(*) FROM devices GROUP BY type;"
```

### Step 2: Investigate Routers (Easy to Categorize)

```bash
# Show all routers
sqlite3 "$DB" << 'EOF'
.mode column
SELECT devmac, last_signal, packets FROM devices
WHERE type = 'Wi-Fi AP' ORDER BY last_signal DESC LIMIT 20;
EOF

# Add YOUR routers to ignore list
nano ignore_lists/mac_list.txt
# Add: AA:BB:CC:DD:EE:FF  # My main router
```

### Step 3: Investigate Client Devices (Harder)

```bash
# Show WiFi clients with signal variance
sqlite3 "$DB" << 'EOF'
.mode column
SELECT devmac, min_signal, max_signal, (max_signal-min_signal) as variance
FROM devices WHERE type = 'Wi-Fi Device'
ORDER BY variance DESC LIMIT 20;
EOF
```

### Step 4: Check Manufacturer for Unknown Devices

```bash
# Lookup each unknown MAC on macOS (outside VM)
curl -s "https://api.macvendors.com/AA:BB:CC:DD:EE:FF"
```

### Step 5: Build Your Ignore List

```bash
# Edit with your categorizations
nano ignore_lists/mac_list.txt
```

**Example annotated list:**

```
# ===== MY WIFI DEVICES =====
AA:BB:CC:DD:EE:FF  # My router (Vantiva) - signal: -42 dBm
BB:CC:DD:EE:FF:00  # My mesh AP upstairs - signal: -55 dBm

# ===== MY BLUETOOTH DEVICES =====
11:22:33:44:55:66  # My iPhone (BT MAC) - different from WiFi!
22:33:44:55:66:77  # My car TPMS (Honda)

# ===== NEIGHBOR'S STATIC DEVICES =====
33:44:55:66:77:88  # North neighbor router (Hellsprinter SSID)
44:55:66:77:88:99  # East neighbor router (Verizon_TH6YWM)
55:66:77:88:99:AA  # South neighbor - always parked car

# ===== DO NOT ADD BELOW =====
# Unknown mobile devices should stay OUT of ignore list
```

---

## Tips & Tricks

### Quickly Check if Device is Yours

**Look it up in your router's DHCP client list:**
1. Login to your router (usually 192.168.1.1 or 192.168.0.1)
2. Find "Connected Devices" or "DHCP Clients"
3. Compare MACs with Kismet output

### Find Your Own Device MACs

**iPhone/iPad:**
```
Settings → General → About
→ Wi-Fi Address: (WiFi MAC)
→ Bluetooth: (BT MAC)
```

**macOS:**
```bash
ifconfig en0 | grep ether  # WiFi MAC
system_profiler SPBluetoothDataType | grep Address  # BT MAC
```

**Android:**
```
Settings → About Phone → Status
→ Wi-Fi MAC Address
→ Bluetooth Address
```

### Track Down Unknown Manufacturer

**Three-step process:**
1. Get OUI (first 3 bytes): `AA:BB:CC:DD:EE:FF` → `AA:BB:CC`
2. Lookup online: `curl -s "https://api.macvendors.com/AA:BB:CC"`
3. Google the manufacturer + device type

**Example:**
```bash
$ curl -s "https://api.macvendors.com/F0:18:98"
Apple, Inc.
# → This is an Apple device (likely your phone/laptop)
```

---

## Next Steps

After categorizing devices:

1. **Update ignore lists** with your categorizations
2. **Run CYT** to verify ignore lists work
3. **Re-run investigation** after a few hours to catch new devices
4. **Monitor** for new unknown devices appearing

**Remember:** When in doubt, DO NOT add to ignore list. False positives (monitoring a neighbor by accident) are better than false negatives (missing a stalker).
