# Device Identification & Stalker Detection Guide

**Comprehensive Guide to Identifying Unknown Wireless Devices**

This guide explains what information is publicly broadcast by wireless devices and how to use it for threat assessment and stalker detection.

---

## Table of Contents

1. [Publicly Available Information](#publicly-available-information)
2. [MAC Address Analysis](#mac-address-analysis)
3. [Behavioral Pattern Analysis](#behavioral-pattern-analysis)
4. [Known Tracker Signatures](#known-tracker-signatures)
5. [Investigation Methodology](#investigation-methodology)
6. [Red Flags for Stalking](#red-flags-for-stalking)
7. [Tools and Commands](#tools-and-commands)
8. [Real-World Examples](#real-world-examples)

---

## Publicly Available Information

### What Devices Broadcast (No Hacking Required)

Every WiFi and Bluetooth device broadcasts information that anyone can capture:

#### WiFi Devices Broadcast:
1. **MAC Address** - Unique hardware identifier (can be randomized)
2. **Signal Strength (RSSI)** - Indicates physical proximity to you
3. **Probe Requests** - List of WiFi networks the device is looking for
4. **Device Capabilities** - 802.11 standards supported (a/b/g/n/ac/ax)
5. **Transmission Power** - How loud the device is broadcasting
6. **Vendor Information** - Embedded in MAC address (OUI lookup)
7. **Associated Network** - For clients, which AP they're connected to
8. **Beacon Intervals** - For access points

#### Bluetooth Devices Broadcast:
1. **MAC Address** - Hardware identifier
2. **Device Class** - Type of device (phone, headset, car, tracker, etc.)
3. **Device Name** - Often includes model info ("John's iPhone", "AirPods Pro")
4. **Services** - What the device can do (audio, file transfer, etc.)
5. **Manufacturer Data** - Company-specific identifiers
6. **Signal Strength** - Physical proximity
7. **UUID** - For BLE devices (like AirTags)

**CRITICAL**: All of this is broadcast in the clear. No hacking, cracking, or illegal activity required to see it.

---

## MAC Address Analysis

### Understanding MAC Addresses

Format: `AA:BB:CC:DD:EE:FF`

- **First 3 bytes (AA:BB:CC)**: **OUI (Organizationally Unique Identifier)** - Identifies manufacturer
- **Last 3 bytes (DD:EE:FF)**: Device-specific identifier

### Manufacturer Lookup (OUI)

**Built into CYT:**
```bash
cd ~/Chasing-Your-Tail-NG
python3 investigate_devices.py
# Option 5: View devices by manufacturer
```

**Manual lookup:**
```bash
# Kismet includes OUI database
sqlite3 ~/logs/kismet/*.kismet "SELECT macaddr, manuf FROM devices LIMIT 20;"
```

**Online lookup:**
- https://maclookup.app/
- https://www.wireshark.org/tools/oui-lookup.html
- https://macvendors.com/

### Common OUI Patterns

#### Apple Devices
```
3C:06:30:XX:XX:XX - Apple, Inc. (iPhones, iPads)
AC:DE:48:XX:XX:XX - Apple, Inc. (MacBooks, iMacs)
F0:99:BF:XX:XX:XX - Apple, Inc. (AirTags, AirPods)
BC:92:6B:XX:XX:XX - Apple, Inc. (various devices)
```

#### Surveillance/Tracking Devices
```
B4:F1:DA:XX:XX:XX - Shenzhen manufacturers (generic WiFi cameras)
38:D5:47:XX:XX:XX - Xiaomi (including Yi cameras)
00:12:17:XX:XX:XX - Cisco (security cameras)
EC:71:DB:XX:XX:XX - EZVIZ cameras (Hikvision)
```

#### GPS Trackers
```
4C:11:AE:XX:XX:XX - Espressif (ESP32 - common in DIY trackers)
A4:CF:12:XX:XX:XX - Espressif (ESP8266)
48:3F:DA:XX:XX:XX - Espressif (ESP-based devices)
```

#### Bluetooth Trackers
```
F0:99:BF:XX:XX:XX - Apple AirTag
EC:58:C5:XX:XX:XX - Tile trackers
1C:52:16:XX:XX:XX - Chipolo trackers
```

**WARNING**: Sophisticated stalkers can:
- Spoof MAC addresses
- Use randomized MACs (privacy feature, but also evasion)
- Buy unbranded Chinese hardware with generic OUIs

---

## Behavioral Pattern Analysis

### The Most Reliable Indicator: Movement Correlation

**MAC addresses can be spoofed, but physics cannot be faked.**

#### Red Flag Patterns

**Pattern 1: Location Correlation**
- Device appears at your work AND your home
- Device appears at gym AND grocery store you visit
- Device shows up at 3+ locations you visit in different days

**How to detect:**
```sql
-- Devices appearing at multiple locations
-- (Requires GPS data in CYT)
SELECT device, COUNT(DISTINCT location) as locations,
       MIN(first_seen) as first, MAX(last_seen) as last
FROM device_history
GROUP BY device
HAVING locations >= 3
ORDER BY locations DESC;
```

**Pattern 2: Temporal Correlation**
- Device appears within 5-10 minutes of your arrival
- Device disappears within 5-10 minutes of your departure
- Pattern repeats over multiple days

**How to detect:**
```bash
cd ~/Chasing-Your-Tail-NG
python3 surveillance_analyzer.py
# Look for "temporal correlation" scores
```

**Pattern 3: Distance Consistency**
- Signal strength remains relatively constant (same distance from you)
- Follows you as you move (signal changes match your movement)
- If you're driving, signal moves with you at same speed

**How to detect:**
```sql
-- Check signal strength consistency
SELECT device, AVG(strongest_signal) as avg_signal,
       MAX(strongest_signal) - MIN(strongest_signal) as variance
FROM devices
GROUP BY device
HAVING variance < 15  -- Consistent distance
ORDER BY variance;
```

**Pattern 4: "Ghost" Behavior**
- No legitimate purpose for device to be there
- Doesn't match environment (AirTag in office parking lot)
- Hidden SSID or no SSID broadcasts
- Unusual manufacturer for the location

---

## Known Tracker Signatures

### AirTags (Apple)

**Bluetooth Signature:**
```
MAC OUI: F0:99:BF (randomizes periodically)
Device Class: 0x200000 (Audio/Video device - misleading)
BLE Services: Find My network (UUID: 0xFD44)
Name: Usually hidden or "AirTag"
```

**Detection in Kismet:**
```sql
SELECT devmac, device_name, strongest_signal, bytes_data
FROM devices
WHERE manuf LIKE '%Apple%'
  AND type = 'BTLE'
  AND (device_name LIKE '%AirTag%' OR device_name = '');
```

**Behavior:**
- Broadcasts BLE beacon every 2 seconds when separated from owner
- Changes MAC address every 15-20 minutes (rolling identifier)
- After 8-24 hours away from owner, plays sound (can be disabled by stalker)
- Detectable by "Find My" network protocol

**CYT Detection:**
```bash
# Check for devices with frequent MAC changes but consistent signal
cd ~/Chasing-Your-Tail-NG
grep -i "airtag\|find.my" logs/cyt_*.log
```

### Tile Trackers

**Bluetooth Signature:**
```
MAC OUI: EC:58:C5
Device Class: 0x000000 (Miscellaneous)
BLE Services: Tile service (proprietary UUID)
Name: "Tile" or hidden
```

**Less sophisticated than AirTag:**
- Does NOT randomize MAC address (easier to track!)
- Shorter range (150 ft vs AirTag's 300+ ft)
- Relies on other Tile users to report location

### GPS Trackers (Cellular/WiFi)

**WiFi Signature:**
```
Common OUIs:
- 4C:11:AE (Espressif ESP32)
- A4:CF:12 (Espressif ESP8266)
- 20:F4:1B (Quectel - cellular modems)

Behavior:
- Intermittent broadcasts (conserving battery)
- May probe for known WiFi networks
- Often cheap Chinese manufacturers
```

**Detection:**
```sql
-- Look for intermittent devices with cheap manufacturers
SELECT devmac, manuf, first_time, last_time,
       (last_time - first_time) as duration
FROM devices
WHERE manuf LIKE '%Espressif%'
   OR manuf LIKE '%Shenzhen%'
   OR manuf LIKE '%Quectel%'
ORDER BY duration DESC;
```

### Hidden Cameras (WiFi)

**WiFi Signature:**
```
Common OUIs:
- B4:F1:DA (Shenzhen manufacturers)
- 38:D5:47 (Xiaomi - Yi cameras)
- EC:71:DB (EZVIZ/Hikvision)
- 00:12:17 (Cisco cameras)

Behavior:
- Operates as WiFi client (connects to AP)
- Constant data transmission (streaming video)
- High packet count relative to signal strength
```

**Detection:**
```sql
-- High data volume devices
SELECT devmac, manuf, strongest_signal, bytes_data,
       CAST(bytes_data AS FLOAT) / (last_time - first_time) as bytes_per_second
FROM devices
WHERE type = 'Wi-Fi Device' OR type = 'Wi-Fi Client'
  AND bytes_data > 1000000  -- 1MB+ transferred
ORDER BY bytes_per_second DESC;
```

---

## Investigation Methodology

### Step-by-Step Process for Unknown Device

#### Step 1: Gather Basic Information

```bash
cd ~/Chasing-Your-Tail-NG
python3 investigate_devices.py
# Option 6: Investigate specific device (by MAC)
```

**Record:**
- MAC address
- Manufacturer (OUI lookup)
- Device type (WiFi AP, client, Bluetooth, BLE)
- Signal strength
- First seen / Last seen timestamps
- Data volume transferred

#### Step 2: Manufacturer Research

**Google the OUI:**
```
"B4:F1:DA OUI" → Search for this exact MAC prefix
```

**Check manufacturer reputation:**
- Legitimate company? (Apple, Samsung, Dell)
- Generic Chinese manufacturer? (Shenzhen, Espressif)
- Surveillance equipment maker? (Hikvision, Dahua)

#### Step 3: Analyze Probe Requests (WiFi Only)

```sql
-- See what networks this device is looking for
SELECT devmac, probedssid, COUNT(*) as probe_count
FROM probes
WHERE devmac = 'AA:BB:CC:DD:EE:FF'  -- Your unknown MAC
GROUP BY probedssid
ORDER BY probe_count DESC;
```

**What this reveals:**
- Personal network names → Might identify owner
- Public WiFi (Starbucks, McDonalds) → Shows travel patterns
- Corporate networks → Might be coworker
- No probes → Device using randomized MAC (privacy-conscious OR stalker)

#### Step 4: Check Bluetooth Name/Services (BT Only)

```sql
-- Get Bluetooth device details
SELECT devmac, device_name, device_class, services
FROM devices
WHERE devmac = 'AA:BB:CC:DD:EE:FF'
  AND (type = 'Bluetooth' OR type = 'BTLE');
```

**Bluetooth Device Class decoder:**
- `0x200404` = Phone (smartphone)
- `0x240404` = Wearable (smartwatch)
- `0x240418` = Headset/earbuds
- `0x04041C` = Car audio
- `0x000000` = Generic (often trackers!)

**Reference:** https://www.bluetooth.com/specifications/assigned-numbers/

#### Step 5: Track Movement Pattern

**Use CYT's surveillance analyzer:**
```bash
cd ~/Chasing-Your-Tail-NG
python3 surveillance_analyzer.py
```

**Manually check history:**
```sql
-- Location correlation
SELECT device, location_lat, location_lon, timestamp
FROM device_history
WHERE device = 'AA:BB:CC:DD:EE:FF'
ORDER BY timestamp;
```

**Questions to answer:**
- Does device appear at multiple places you visit?
- Does timing match your schedule?
- Is signal strength consistent (same distance)?
- Does device move when you move?

#### Step 6: Temporal Analysis

**Check time patterns:**
```sql
-- When does this device appear?
SELECT devmac,
       strftime('%H', first_time, 'unixepoch') as hour,
       COUNT(*) as appearances
FROM devices
WHERE devmac = 'AA:BB:CC:DD:EE:FF'
GROUP BY hour
ORDER BY hour;
```

**Suspicious patterns:**
- Only appears during your commute hours
- Appears when you leave home, disappears when you arrive
- Active during your work hours, quiet at night

#### Step 7: Cross-Reference with Known Devices

**Check against your ignore list:**
```bash
grep -i "AA:BB:CC:DD:EE:FF" ~/Chasing-Your-Tail-NG/ignore_lists/mac_list.txt
```

**Check for similar devices (same manufacturer):**
```sql
-- Find devices from same manufacturer
SELECT devmac, manuf, strongest_signal, first_time, last_time
FROM devices
WHERE manuf = (SELECT manuf FROM devices WHERE devmac = 'AA:BB:CC:DD:EE:FF')
ORDER BY last_time DESC;
```

**Question:** Do you own ANY devices from this manufacturer?

---

## Red Flags for Stalking

### HIGH RISK (Investigate Immediately)

🚩 **Device appears at 3+ different locations you visit**
- Work, home, gym, store, etc.
- Especially if these are not on same route

🚩 **Device timing matches your schedule**
- Appears within 10 min of your arrival
- Disappears within 10 min of your departure
- Pattern repeats over multiple days

🚩 **Signal strength too strong for environment**
- -40 dBm in public parking lot (device is in/on your car)
- -30 dBm at work (device is in your belongings)
- Signal moves with you as you walk

🚩 **Known tracker signatures**
- AirTag without your Apple ID
- Tile tracker with strong signal
- Generic Bluetooth beacon with no name

🚩 **Unusual manufacturer for location**
- Espressif ESP32 in your car (DIY tracker)
- Chinese camera manufacturer in office
- Generic Shenzhen device following you

🚩 **Device behavior changes when you move**
- Signal appears when you start driving
- Signal disappears when you enter building
- Device "wakes up" when you leave home

### MEDIUM RISK (Monitor and Investigate)

⚠️ **Device appears at 2 locations**
- Could be coincidence (neighbor, coworker)
- Monitor for third occurrence

⚠️ **Generic manufacturer with consistent signal**
- Espressif, Shenzhen, unbranded
- Could be legitimate IoT device
- Check for movement correlation

⚠️ **Hidden SSID or no device name**
- Privacy feature OR evasion tactic
- Combined with other factors = higher risk

⚠️ **Probe requests for unusual networks**
- Probing for rare/specific networks
- Pattern matching your networks

### LOW RISK (Probably Benign)

✅ **Strong signal, but clearly identifiable**
- "John's iPhone" with Apple OUI
- "Toyota Camry 2024" with car manufacturer
- Neighbor's router with ISP SSID pattern

✅ **Only appears at one location**
- Probably belongs there (neighbor, business)
- Unless that location is your car!

✅ **Weak signal (-80 dBm or lower)**
- Too far away to be in your belongings
- Could be distant neighbor or passing car

✅ **Legitimate manufacturer + legitimate behavior**
- Samsung phone probing for "Galaxy Note"
- Dell laptop connecting to corporate WiFi
- Fitbit with Fitbit OUI and health services

---

## Tools and Commands

### Kismet Database Queries

**Connect to database:**
```bash
cd ~/logs/kismet/
sqlite3 Kismet-*.kismet
```

**Get device details:**
```sql
.mode column
.headers on

SELECT devmac, type, manuf, device_name,
       strongest_signal, bytes_data,
       datetime(first_time, 'unixepoch') as first_seen,
       datetime(last_time, 'unixepoch') as last_seen
FROM devices
WHERE devmac = 'AA:BB:CC:DD:EE:FF';
```

**Get probe requests:**
```sql
SELECT datetime(ts_sec, 'unixepoch') as time,
       sourcemac, probedssid
FROM probes
WHERE sourcemac = 'AA:BB:CC:DD:EE:FF'
ORDER BY ts_sec;
```

**Get location history (if GPS enabled):**
```sql
SELECT datetime(ts_sec, 'unixepoch') as time,
       lat, lon, alt, speed
FROM snapshots
WHERE sourcemac = 'AA:BB:CC:DD:EE:FF'
ORDER BY ts_sec;
```

### CYT Investigation Tools

**Interactive investigation:**
```bash
cd ~/Chasing-Your-Tail-NG
python3 investigate_devices.py
```

**Surveillance analysis:**
```bash
python3 surveillance_analyzer.py
```

**Probe analysis:**
```bash
python3 probe_analyzer.py
```

**Export device data:**
```bash
# Export to CSV for analysis in Excel/Google Sheets
sqlite3 -header -csv ~/logs/kismet/*.kismet \
  "SELECT * FROM devices;" > devices_export.csv
```

### Online Resources

**MAC Address Lookup:**
- https://maclookup.app/
- https://macvendors.com/
- https://www.wireshark.org/tools/oui-lookup.html

**Bluetooth Device Class Decoder:**
- https://www.bluetooth.com/specifications/assigned-numbers/

**WiFi Standards Reference:**
- https://en.wikipedia.org/wiki/IEEE_802.11

---

## Real-World Examples

### Example 1: AirTag in Car

**Scenario:** Device appears at work parking lot, home driveway, gym

**Investigation:**
```sql
SELECT devmac, manuf, strongest_signal,
       datetime(first_time, 'unixepoch') as first,
       datetime(last_time, 'unixepoch') as last
FROM devices
WHERE manuf LIKE '%Apple%' AND type = 'BTLE';
```

**Red Flags:**
- ✅ Apple OUI (F0:99:BF)
- ✅ Bluetooth LE (BLE)
- ✅ Strong signal (-40 dBm = very close)
- ✅ Appears at 3+ locations
- ✅ Timing matches commute

**Conclusion:** Likely AirTag tracker

**Action:**
1. Physically search car (wheel wells, bumpers, under seats)
2. Use Apple's "Find My" app to detect unknown AirTags
3. Consider police report if found

### Example 2: Neighbor's Router

**Scenario:** Strong WiFi signal at home only

**Investigation:**
```sql
SELECT devmac, manuf, device_name, strongest_signal
FROM devices
WHERE devmac = 'AA:BB:CC:DD:EE:FF';
```

**Indicators:**
- SSID: "NETGEAR_5G_2024" or "ATT-WIFI-1234"
- Manufacturer: Netgear, Cisco, TP-Link
- Signal: -60 dBm (moderate strength)
- Type: WiFi AP
- Only seen at home address

**Conclusion:** Neighbor's router

**Action:** Add to ignore list

### Example 3: Coworker's Phone

**Scenario:** Device appears at work and nearby lunch spots

**Investigation:**
```sql
-- Check probe requests
SELECT probedssid FROM probes
WHERE sourcemac = 'AA:BB:CC:DD:EE:FF';
```

**Results:**
```
CompanyCorporateWiFi
Starbucks
McDonald's WiFi
```

**Indicators:**
- ✅ Apple iPhone OUI
- ✅ Probes for company WiFi
- ✅ Probes for public WiFi near office
- ❌ Does NOT appear at your home
- ❌ Does NOT appear on your commute route

**Conclusion:** Coworker who has lunch nearby

**Action:** Add to ignore list

### Example 4: GPS Tracker (ACTUAL THREAT)

**Scenario:** Espressif device in car, strong signal, moves with you

**Investigation:**
```sql
SELECT devmac, manuf, strongest_signal, bytes_data,
       datetime(first_time, 'unixepoch') as first,
       datetime(last_time, 'unixepoch') as last
FROM devices
WHERE devmac = 'AA:BB:CC:DD:EE:FF';
```

**Red Flags:**
- ✅ Espressif OUI (4C:11:AE) - DIY tracker hardware
- ✅ WiFi client type
- ✅ Very strong signal (-35 dBm = in your car)
- ✅ Appears at work, home, store, gym
- ✅ Intermittent connection (conserving battery)
- ✅ Low data volume (only sending GPS coordinates)

**Conclusion:** GPS tracker planted in vehicle

**Action:**
1. **DO NOT REMOVE IMMEDIATELY** - may alert stalker
2. Document thoroughly (screenshots, logs)
3. Contact police FIRST
4. Consider restraining order
5. Professional vehicle sweep

---

## Privacy vs. Stalking

### Legitimate Privacy Features

Many devices use privacy features that look suspicious:

**MAC Address Randomization (iOS 14+, Android 10+)**
- iPhones/Android randomize MAC when probing for WiFi
- Different MAC at each location
- **Distinguishing factor:** Won't follow you (randomizes each time)

**Hidden SSID**
- Routers can hide network name
- **Distinguishing factor:** Stays in one place (doesn't move)

**Bluetooth Privacy**
- AirPods randomize MAC address periodically
- **Distinguishing factor:** Only changes when reconnecting, not while in use

### Stalker Evasion Tactics

Sophisticated stalkers may:

**MAC Spoofing**
- Change MAC address to blend in
- **Countermeasure:** Track by movement pattern, not MAC

**Generic Hardware**
- Use unbranded Chinese devices
- **Countermeasure:** Track unusual manufacturers in YOUR environment

**Disable Identifiers**
- No SSID, no device name, no probes
- **Countermeasure:** Track by signal strength and timing

**Use of "Normal" Devices**
- Old iPhone configured as tracker
- **Countermeasure:** Device behavior doesn't match environment

---

## Legal Considerations

### What You CAN Do Legally

✅ **Monitor wireless signals in public spaces** - Legal everywhere
✅ **Record MAC addresses and signal strength** - Public broadcast data
✅ **Investigate devices in your property** - Your car, your home
✅ **Document evidence of stalking** - For legal action

### What You CANNOT Do Legally

❌ **Jam or interfere with devices** - Federal crime (FCC violation)
❌ **Hack or decrypt encrypted traffic** - Computer Fraud and Abuse Act
❌ **Trespass to locate tracker** - Even if tracker is illegal
❌ **Destroy suspected tracker without proof** - Could be legitimate property

### Recommended Legal Actions

If you find evidence of tracking:

1. **Document thoroughly** - Screenshots, logs, timestamps
2. **Contact police FIRST** - File report before removing tracker
3. **Seek restraining order** - Legal protection
4. **Consult attorney** - Civil remedies available
5. **Professional sweep** - For hidden cameras, audio bugs

**Resources:**
- National Domestic Violence Hotline: 1-800-799-7233
- Cyber Civil Rights Initiative: cybercivilrights.org
- Local police non-emergency line

---

## Summary Checklist

When investigating unknown device:

- [ ] Record MAC address and manufacturer (OUI lookup)
- [ ] Check device type (WiFi AP, client, Bluetooth, BLE)
- [ ] Note signal strength (-30 to -40 dBm = very close!)
- [ ] Research manufacturer (legitimate company vs. generic Chinese)
- [ ] Check probe requests (what networks is it looking for?)
- [ ] Check Bluetooth name and device class
- [ ] Track locations where device appears
- [ ] Check timing (does it match your schedule?)
- [ ] Look for movement correlation (follows you?)
- [ ] Compare to known tracker signatures (AirTag, Tile, GPS)
- [ ] Cross-reference your devices (is it yours?)
- [ ] Monitor over multiple days (pattern confirmation)
- [ ] Document evidence if suspicious
- [ ] Contact authorities if threat confirmed

**Remember:**
- One occurrence = coincidence
- Two occurrences = monitor closely
- Three+ occurrences = investigate immediately
- Movement correlation = highest risk factor

---

**Version**: 1.0
**Last Updated**: 2025-12-21
**Project**: Chasing Your Tail - Next Generation
