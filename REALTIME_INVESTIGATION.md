# Real-Time Device Investigation Guide

**Finding Active Devices Near You Right Now**

This guide shows you how to investigate devices currently near you, identify your own devices, and detect cloaked/suspicious devices in real-time.

---

## Find the Current Kismet Database

Kismet creates a new database file each time it starts. You need to query the ACTIVE one:

```bash
# Find the most recent (currently active) Kismet database
cd ~/Chasing-Your-Tail-NG
ls -lt Kismet-*.kismet | head -1

# OR find the one with active journal (currently being written)
ls -lt Kismet-*.kismet-journal | head -1
```

The file with `.kismet-journal` is the one currently being written to.

---

## Real-Time Investigation Queries

### 1. Devices Active in Last 5 Minutes (What's Near You NOW)

```sql
-- Connect to current database
sqlite3 Kismet-20251221-*.kismet  -- Replace with current timestamp

.mode column
.headers on

-- Devices seen in last 5 minutes, sorted by signal strength
SELECT
    devmac as "MAC Address",
    manuf as "Manufacturer",
    strongest_signal as "Signal (dBm)",
    type as "Type",
    datetime(last_time, 'unixepoch') as "Last Seen"
FROM devices
WHERE last_time > (strftime('%s', 'now') - 300)  -- Last 5 minutes
ORDER BY strongest_signal DESC;
```

**Signal strength guide:**
- **> -40 dBm** = VERY CLOSE (in your pocket, on desk, in car)
- **-40 to -60 dBm** = Close (same room, nearby parking)
- **-60 to -80 dBm** = Medium distance (other offices, neighbors)
- **< -80 dBm** = Far away (distant building, passing cars)

### 2. Find YOUR Devices (Cross-Reference with Known Info)

```sql
-- Show Apple devices (if you have iPhone/Mac)
SELECT devmac, manuf, strongest_signal, type
FROM devices
WHERE manuf LIKE '%Apple%'
  AND last_time > (strftime('%s', 'now') - 300)
ORDER BY strongest_signal DESC;

-- Show devices probing for YOUR networks
SELECT DISTINCT d.devmac, d.manuf, d.strongest_signal, p.probedssid
FROM devices d
JOIN probes p ON d.devmac = p.sourcemac
WHERE p.probedssid IN ('YourHomeWiFi', 'YourPhoneHotspot', 'YourWorkNetwork')
  AND d.last_time > (strftime('%s', 'now') - 300)
ORDER BY d.strongest_signal DESC;
```

**Replace with your actual network names!**

### 3. Cloaked/Suspicious Devices (No Probe Requests)

```sql
-- Devices with NO probe requests = suspicious (not phones/laptops)
SELECT
    d.devmac as "MAC",
    d.manuf as "Manufacturer",
    d.strongest_signal as "Signal",
    d.type as "Type",
    CASE
        WHEN d.strongest_signal > -40 THEN '🚨 VERY CLOSE'
        WHEN d.strongest_signal > -60 THEN '⚠️  CLOSE'
        ELSE '✓ FAR'
    END as "Distance"
FROM devices d
LEFT JOIN probes p ON d.devmac = p.sourcemac
WHERE p.sourcemac IS NULL
  AND d.type IN ('Wi-Fi Device', 'Wi-Fi Client')
  AND d.last_time > (strftime('%s', 'now') - 300)
ORDER BY d.strongest_signal DESC;
```

**Red flags:**
- Very strong signal (-30 to -40 dBm)
- No probe requests (not looking for WiFi)
- Generic manufacturer (Espressif, Shenzhen, unknown)

### 4. Hidden/Unnamed Bluetooth Devices

```sql
-- Bluetooth devices with no name = suspicious
SELECT
    devmac as "MAC",
    manuf as "Manufacturer",
    strongest_signal as "Signal",
    device_name as "Name"
FROM devices
WHERE type IN ('Bluetooth', 'BTLE')
  AND (device_name = '' OR device_name IS NULL)
  AND last_time > (strftime('%s', 'now') - 300)
ORDER BY strongest_signal DESC;
```

**Look for:**
- AirTags (Apple, no name, BLE)
- Tile trackers (no name)
- Unknown strong signals

---

## Quick Identification Workflow

### Step 1: Find Top 10 Closest Devices

```sql
-- Top 10 closest devices right now
SELECT
    devmac,
    manuf,
    strongest_signal,
    type,
    bytes_data
FROM devices
WHERE last_time > (strftime('%s', 'now') - 300)
ORDER BY strongest_signal DESC
LIMIT 10;
```

### Step 2: For Each Unknown Device, Check Probes

```sql
-- What is this device looking for?
SELECT probedssid, COUNT(*) as times
FROM probes
WHERE sourcemac = 'AA:BB:CC:DD:EE:FF'  -- Replace with MAC from Step 1
GROUP BY probedssid
ORDER BY times DESC;
```

### Step 3: Identify Your Devices

**Create a list of YOUR devices as you identify them:**

```bash
# In a text file, track what you find:
nano ~/my_devices.txt
```

```
# My Devices (Signal Strength Reference)
AA:BB:CC:DD:EE:FF  # My iPhone (Apple) - Signal: -35 dBm
11:22:33:44:55:66  # My MacBook (Apple) - Signal: -42 dBm
77:88:99:AA:BB:CC  # My AirPods (Apple) - Signal: -38 dBm
DD:EE:FF:00:11:22  # My Apple Watch (Apple) - Signal: -40 dBm
```

### Step 4: Compare Against Coworkers

```sql
-- Devices probing for corporate network (coworkers)
SELECT DISTINCT d.devmac, d.manuf, d.strongest_signal
FROM devices d
JOIN probes p ON d.devmac = p.sourcemac
WHERE p.probedssid LIKE '%YourCompanyName%'
  AND d.last_time > (strftime('%s', 'now') - 300)
ORDER BY d.strongest_signal DESC;
```

---

## Advanced Real-Time Analysis

### Devices with Strongest Signals (Within 10 Feet)

```sql
-- Devices VERY close to you (likely on your person or desk)
SELECT
    devmac,
    manuf,
    strongest_signal,
    type,
    bytes_data,
    datetime(first_time, 'unixepoch') as first_seen,
    datetime(last_time, 'unixepoch') as last_seen
FROM devices
WHERE strongest_signal > -45  -- Within ~10 feet
  AND last_time > (strftime('%s', 'now') - 300)
ORDER BY strongest_signal DESC;
```

**Expected results at work desk:**
- Your phone: -30 to -40 dBm
- Your laptop: -35 to -45 dBm
- Your watch/earbuds: -35 to -45 dBm
- Coworker's devices nearby: -50 to -65 dBm

**Unexpected/suspicious:**
- Unknown device at -35 dBm (very close, in your belongings?)
- Espressif/Shenzhen at -40 dBm (tracker hardware?)
- No-name Bluetooth at -30 dBm (AirTag?)

### Devices That Just Appeared

```sql
-- Devices first seen in last 10 minutes (just arrived)
SELECT
    devmac,
    manuf,
    strongest_signal,
    type,
    datetime(first_time, 'unixepoch') as appeared
FROM devices
WHERE first_time > (strftime('%s', 'now') - 600)  -- Last 10 min
ORDER BY first_time DESC;
```

**Use case:**
- Just sat down at work? See what appeared with you
- Compare to when you leave (what disappears?)

### Data Volume Analysis (Camera Detection)

```sql
-- High data volume = streaming (cameras, video calls)
SELECT
    devmac,
    manuf,
    strongest_signal,
    bytes_data,
    CAST(bytes_data AS FLOAT) / NULLIF((last_time - first_time), 0) as bytes_per_sec
FROM devices
WHERE bytes_data > 100000  -- >100KB transferred
  AND last_time > (strftime('%s', 'now') - 300)
ORDER BY bytes_per_sec DESC;
```

**Suspicious:**
- Unknown device with high data rate near you
- Could be hidden camera streaming

---

## Interactive Real-Time Dashboard

### Create a Live Monitoring Script

Save this as `live_monitor.sh`:

```bash
#!/bin/bash

# Find current Kismet database
KISMET_DB=$(ls -t ~/Chasing-Your-Tail-NG/Kismet-*.kismet 2>/dev/null | head -1)

if [ -z "$KISMET_DB" ]; then
    echo "No Kismet database found!"
    exit 1
fi

echo "Monitoring: $KISMET_DB"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    clear
    echo "═══════════════════════════════════════════════════"
    echo "  REAL-TIME DEVICE MONITOR"
    echo "  $(date)"
    echo "═══════════════════════════════════════════════════"
    echo ""

    sqlite3 "$KISMET_DB" <<EOF
.mode column
.headers on
SELECT
    SUBSTR(devmac, 1, 17) as MAC,
    SUBSTR(manuf, 1, 20) as Manufacturer,
    strongest_signal as Signal,
    SUBSTR(type, 1, 12) as Type,
    CASE
        WHEN strongest_signal > -40 THEN '🔴 VERY CLOSE'
        WHEN strongest_signal > -60 THEN '🟡 CLOSE'
        ELSE '🟢 FAR'
    END as Distance
FROM devices
WHERE last_time > (strftime('%s', 'now') - 60)
ORDER BY strongest_signal DESC
LIMIT 20;
EOF

    echo ""
    echo "Updating every 10 seconds..."
    sleep 10
done
```

Make it executable:
```bash
chmod +x live_monitor.sh
./live_monitor.sh
```

---

## Identifying Your Devices Checklist

### Apple Devices (iPhone, Mac, AirPods, Watch)

**Characteristics:**
```sql
SELECT devmac, manuf, strongest_signal, type
FROM devices
WHERE manuf LIKE '%Apple%'
  AND last_time > (strftime('%s', 'now') - 300)
ORDER BY strongest_signal DESC;
```

**Your devices will:**
- Have Apple manufacturer
- Very strong signal (-30 to -45 dBm)
- Probe for your home WiFi
- Probe for your known networks

**Check probes to confirm:**
```sql
SELECT p.probedssid
FROM probes p
WHERE p.sourcemac = 'AA:BB:CC:DD:EE:FF'  -- Apple MAC from above
GROUP BY p.probedssid;
```

Do you recognize the network names? → It's yours!

### Android Devices

**Characteristics:**
```sql
SELECT devmac, manuf, strongest_signal, type
FROM devices
WHERE manuf LIKE '%Samsung%'
   OR manuf LIKE '%Google%'
   OR manuf LIKE '%LG%'
   OR manuf LIKE '%Motorola%'
  AND last_time > (strftime('%s', 'now') - 300)
ORDER BY strongest_signal DESC;
```

### Bluetooth Devices (AirPods, Watch, Earbuds)

```sql
SELECT devmac, manuf, strongest_signal, device_name
FROM devices
WHERE type IN ('Bluetooth', 'BTLE')
  AND last_time > (strftime('%s', 'now') - 300)
ORDER BY strongest_signal DESC;
```

**Your Bluetooth devices:**
- Strong signal (-30 to -45 dBm)
- Might show name ("AirPods Pro", "Galaxy Buds")
- Apple manufacturer for AirPods/Watch

---

## Red Flags to Watch For

### 🚨 CRITICAL (Investigate Immediately)

```sql
-- Unknown device VERY close with no probe requests
SELECT d.devmac, d.manuf, d.strongest_signal, d.type
FROM devices d
LEFT JOIN probes p ON d.devmac = p.sourcemac
WHERE d.strongest_signal > -40
  AND p.sourcemac IS NULL
  AND d.last_time > (strftime('%s', 'now') - 300)
ORDER BY d.strongest_signal DESC;
```

**This means:**
- Device is within 10 feet of you
- Not looking for WiFi (not a phone/laptop)
- Could be tracker, camera, or other surveillance

### ⚠️ WARNING (Monitor Closely)

```sql
-- Generic Chinese manufacturers close to you
SELECT devmac, manuf, strongest_signal, type
FROM devices
WHERE (manuf LIKE '%Espressif%'
   OR manuf LIKE '%Shenzhen%'
   OR manuf LIKE '%Generic%'
   OR manuf IS NULL)
  AND strongest_signal > -60
  AND last_time > (strftime('%s', 'now') - 300)
ORDER BY strongest_signal DESC;
```

**Could be:**
- DIY tracker (Espressif ESP32/ESP8266)
- Generic WiFi camera
- Unknown surveillance device

---

## Building Your Ignore List (Real-Time)

As you identify your devices, add them to ignore list:

```bash
nano ~/Chasing-Your-Tail-NG/ignore_lists/mac_list.txt
```

**Format:**
```
# My Devices - Work
AA:BB:CC:DD:EE:FF  # My iPhone 15 Pro (Apple, -35 dBm)
11:22:33:44:55:66  # My MacBook Pro (Apple, -42 dBm)
77:88:99:AA:BB:CC  # My AirPods Pro (Apple, -38 dBm)

# Coworkers - Identified
DD:EE:FF:00:11:22  # John's laptop (Dell, probes for "JohnsHome")
22:33:44:55:66:77  # Sarah's iPhone (Apple, probes for "SarahWiFi")
```

**To verify an entry:**
```sql
-- Check this MAC before adding to ignore list
SELECT
    d.devmac,
    d.manuf,
    d.strongest_signal,
    GROUP_CONCAT(DISTINCT p.probedssid, ', ') as probes
FROM devices d
LEFT JOIN probes p ON d.devmac = p.sourcemac
WHERE d.devmac = 'AA:BB:CC:DD:EE:FF'
GROUP BY d.devmac;
```

---

## Quick Reference Commands

**1. What's closest to me RIGHT NOW?**
```sql
SELECT devmac, manuf, strongest_signal, type
FROM devices
WHERE last_time > (strftime('%s', 'now') - 60)
ORDER BY strongest_signal DESC LIMIT 10;
```

**2. What's this device looking for?**
```sql
SELECT probedssid FROM probes
WHERE sourcemac = 'AA:BB:CC:DD:EE:FF';
```

**3. Who's probing for my network?**
```sql
SELECT sourcemac, COUNT(*) FROM probes
WHERE probedssid = 'MyNetworkName'
GROUP BY sourcemac;
```

**4. Any cloaked devices near me?**
```sql
SELECT d.devmac, d.manuf, d.strongest_signal
FROM devices d
LEFT JOIN probes p ON d.devmac = p.sourcemac
WHERE p.sourcemac IS NULL
  AND d.strongest_signal > -60
  AND d.last_time > (strftime('%s', 'now') - 300);
```

**5. Export current snapshot for later analysis:**
```bash
sqlite3 -header -csv Kismet-*.kismet \
  "SELECT * FROM devices WHERE last_time > (strftime('%s', 'now') - 300);" \
  > work_snapshot_$(date +%Y%m%d_%H%M%S).csv
```

---

## Example Investigation Workflow

### Scenario: At work, want to identify devices

**Step 1: Find current database**
```bash
ls -lt ~/Chasing-Your-Tail-NG/Kismet-*.kismet-journal
```

**Step 2: Connect and see what's active**
```bash
sqlite3 ~/Chasing-Your-Tail-NG/Kismet-20251221-*.kismet
```

**Step 3: Top 20 closest devices**
```sql
.mode column
.headers on
SELECT devmac, manuf, strongest_signal, type
FROM devices
WHERE last_time > (strftime('%s', 'now') - 300)
ORDER BY strongest_signal DESC LIMIT 20;
```

**Step 4: For each strong signal device, check probes**
```sql
-- For top result from Step 3
SELECT probedssid, COUNT(*) as times
FROM probes
WHERE sourcemac = 'MAC_FROM_STEP3'
GROUP BY probedssid;
```

**Step 5: Categorize**
- Recognize network names → YOUR device or COWORKER
- Don't recognize + strong signal → INVESTIGATE
- No probes + strong signal → 🚨 RED FLAG

**Step 6: Document**
```bash
# Add to ignore list (if yours/coworker)
echo "AA:BB:CC:DD:EE:FF  # Description" >> ~/Chasing-Your-Tail-NG/ignore_lists/mac_list.txt

# OR flag for investigation (if suspicious)
echo "AA:BB:CC:DD:EE:FF  # INVESTIGATE: Strong signal, no probes" >> ~/suspicious_devices.txt
```

---

**Version:** 1.0
**Last Updated:** 2025-12-21
**Project:** Chasing Your Tail - Next Generation
