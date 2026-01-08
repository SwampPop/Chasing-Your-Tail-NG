# Probe Request Analysis Guide

**Using WiFi Probe Requests to Identify Device Owners**

Probe requests are one of the most valuable pieces of information for identifying who owns an unknown device. This guide explains what they are, how to view them, and how to use them for device identification.

---

## Table of Contents

1. [What Are Probe Requests?](#what-are-probe-requests)
2. [What Probe Requests Reveal](#what-probe-requests-reveal)
3. [How to View Probe Requests](#how-to-view-probe-requests)
4. [Identifying Owners from Probes](#identifying-owners-from-probes)
5. [Modern Privacy Complications](#modern-privacy-complications)
6. [Real-World Examples](#real-world-examples)
7. [Red Flags in Probe Patterns](#red-flags-in-probe-patterns)

---

## What Are Probe Requests?

### The Basics

When a WiFi device (phone, laptop, etc.) is looking for networks to connect to, it broadcasts **probe requests** asking "Is [NetworkName] here?"

**Example:** Your iPhone remembers you've connected to:
- "Home WiFi"
- "Office Network"
- "Starbucks WiFi"
- "Mom's House"

Every few seconds, your iPhone broadcasts:
```
"Is 'Home WiFi' here?"
"Is 'Office Network' here?"
"Is 'Starbucks WiFi' here?"
"Is 'Mom's House' here?"
```

**Anyone with a WiFi adapter in monitor mode can see these requests.**

### Two Types of Probe Requests

**1. Directed Probe Requests** (older devices)
- "Is 'JohnsHomeWiFi' here?"
- "Is 'SecretNetworkName' here?"
- **Reveals specific network names**

**2. Wildcard Probe Requests** (newer devices)
- "Is any network here?"
- **Reveals nothing about networks**
- Privacy feature to prevent tracking

**Modern devices (iOS 14+, Android 10+):**
- Use wildcard probes by default
- Only send directed probes for "important" networks
- Randomize MAC address when probing

**Older devices (pre-2020):**
- Always send directed probes
- Broadcast entire network history
- Use real MAC address

---

## What Probe Requests Reveal

### Direct Owner Identification

Probe requests can reveal:

**1. Person's Name**
```
Probe for: "John's iPhone Hotspot"
Probe for: "Sarah's MacBook Air"
Probe for: "Mike's Home Network"
```
→ Owner's name is literally in the SSID!

**2. Home Address/Location**
```
Probe for: "Smith Family WiFi"
Probe for: "Apartment 3B"
Probe for: "123 Main St Guest"
```
→ Identifies where they live

**3. Workplace**
```
Probe for: "Acme Corp Internal"
Probe for: "Law Office of Smith & Jones"
Probe for: "Hospital_Staff_Only"
```
→ Identifies where they work

**4. Frequented Places**
```
Probe for: "Starbucks"
Probe for: "McDonalds WiFi"
Probe for: "LA Fitness Guest"
Probe for: "Target Guest"
```
→ Shows their habits and travel patterns

**5. Personal Relationships**
```
Probe for: "Mom's WiFi"
Probe for: "Bob's House"
Probe for: "GirlfriendApartment"
```
→ Reveals social connections

**6. Travel History**
```
Probe for: "HolidayInn_LAX"
Probe for: "Airport_Free_WiFi_NYC"
Probe for: "Paris_Hotel_Guest"
```
→ Shows where they've traveled

### Indirect Identification

**Device Type/Model:**
```
Probe for: "Direct-6F-HP OfficeJet Pro"
Probe for: "DIRECT-roku-123-456789"
```
→ Identifies printer model, streaming device

**Operating System:**
- Pattern of probe frequency can indicate iOS vs Android
- Some devices include OS version in probe metadata

**Network Preferences:**
- Corporate WiFi = likely employee
- Public WiFi only = privacy-conscious or homeless/traveler
- Many home networks = tech enthusiast with multiple routers

---

## How to View Probe Requests

### Method 1: Using CYT's Probe Analyzer (Recommended)

CYT includes a built-in tool for analyzing probe requests:

```bash
cd ~/Chasing-Your-Tail-NG
python3 probe_analyzer.py
```

**What it shows:**
- All devices that sent probe requests
- Networks they're looking for
- Frequency of probes
- Suspicious patterns (randomized MACs, excessive probing)

### Method 2: Direct Kismet Database Query

**Connect to Kismet database:**
```bash
cd ~/logs/kismet/
sqlite3 Kismet-*.kismet
```

**View all probe requests from specific device:**
```sql
.mode column
.headers on

SELECT
    datetime(ts_sec, 'unixepoch') as timestamp,
    sourcemac,
    probedssid as "Network Looking For"
FROM probes
WHERE sourcemac = 'AA:BB:CC:DD:EE:FF'  -- Replace with target MAC
ORDER BY ts_sec;
```

**Example output:**
```
timestamp            sourcemac          Network Looking For
-------------------  -----------------  --------------------
2025-12-21 08:15:23  3C:06:30:11:22:33  JohnsHomeWiFi
2025-12-21 08:15:25  3C:06:30:11:22:33  Acme_Corp_Guest
2025-12-21 08:15:27  3C:06:30:11:22:33  Starbucks
```

**Find all networks a device has probed for:**
```sql
SELECT
    probedssid as "Network Name",
    COUNT(*) as "Times Probed"
FROM probes
WHERE sourcemac = 'AA:BB:CC:DD:EE:FF'
GROUP BY probedssid
ORDER BY "Times Probed" DESC;
```

**Find devices probing for specific network:**
```sql
-- Who has connected to "SecretNetwork" before?
SELECT DISTINCT
    sourcemac,
    COUNT(*) as probe_count,
    MIN(datetime(ts_sec, 'unixepoch')) as first_probe,
    MAX(datetime(ts_sec, 'unixepoch')) as last_probe
FROM probes
WHERE probedssid = 'SecretNetwork'
GROUP BY sourcemac
ORDER BY probe_count DESC;
```

**Find all unique networks being probed:**
```sql
-- See what networks people are looking for (might identify locations)
SELECT
    probedssid,
    COUNT(DISTINCT sourcemac) as "Devices Searching",
    COUNT(*) as "Total Probes"
FROM probes
GROUP BY probedssid
ORDER BY "Devices Searching" DESC
LIMIT 50;
```

### Method 3: Export to CSV for Analysis

```bash
# Export all probe data to spreadsheet
sqlite3 -header -csv ~/logs/kismet/*.kismet \
  "SELECT datetime(ts_sec, 'unixepoch') as time,
          sourcemac, probedssid
   FROM probes
   ORDER BY ts_sec;" > probe_requests.csv

# Open in Excel/Google Sheets for filtering and analysis
```

### Method 4: Live Monitoring in Kismet Web UI

1. Open browser to **http://localhost:2501**
2. Click on a device
3. Select "Probed SSIDs" tab
4. See live list of networks device is searching for

---

## Identifying Owners from Probes

### Investigation Workflow

**Step 1: Get the MAC address** of unknown device
```bash
cd ~/Chasing-Your-Tail-NG
python3 investigate_devices.py
# Note the MAC address
```

**Step 2: Query probe requests**
```bash
cd ~/logs/kismet/
sqlite3 Kismet-*.kismet
```

```sql
SELECT probedssid, COUNT(*) as count
FROM probes
WHERE sourcemac = 'AA:BB:CC:DD:EE:FF'
GROUP BY probedssid
ORDER BY count DESC;
```

**Step 3: Analyze the networks**

Look for identifying information:

**Personal Names:**
```
"Mike's iPhone"       → Owner is Mike
"Sarah's Network"     → Owner is Sarah
"Bob's Hotspot"       → Owner is Bob
```

**Addresses/Apartments:**
```
"Apt 3B WiFi"         → Lives in apartment 3B (your building?)
"123 Oak St"          → Lives at 123 Oak Street
"The Johnsons"        → Johnson family network
```

**Workplaces:**
```
"Smith & Associates"  → Works at law firm
"City Hospital"       → Hospital employee
"TechCorp Internal"   → Tech company employee
```

**Locations:**
```
"Starbucks"           → Frequents Starbucks
"Gold's Gym"          → Gym member
"Airport WiFi"        → Travels frequently
```

**Step 4: Cross-reference with other data**

Combine probes with:
- Signal strength (how close are they?)
- Location patterns (same places as you?)
- Time of day (same schedule?)
- Manufacturer (matches probe info?)

**Example:**
```
MAC: 3C:06:30:XX:XX:XX
Manufacturer: Apple
Probes: "Mike's iPhone Hotspot", "Acme Corp WiFi", "Gold's Gym"
Signal: -45 dBm (very close)
Locations: Your office, your gym, your home
```

**Conclusion:**
- Coworker named Mike
- Works at Acme Corp (you too?)
- Goes to Gold's Gym
- iPhone user
- **Very close to you** (might sit nearby at work)

### Google Search Integration

**Once you have network names, Google them:**

```
"Acme Corp WiFi" + company name
"Smith Family WiFi" + address
"Apt 3B WiFi" + apartment building name
```

**Check public WiFi databases:**
- WiGLE.net (maps WiFi networks worldwide)
- Can show approximate location of SSIDs
- Search for SSID to see where it's been detected

**Example WiGLE search:**
```
1. Go to https://wigle.net/
2. Search for SSID: "Mike's Home WiFi"
3. See map showing where this network exists
4. Might reveal home address
```

---

## Modern Privacy Complications

### MAC Address Randomization

**Problem:** Modern devices randomize MAC address when probing

**iOS 14+ (2020 onwards):**
- Uses random MAC for each network probe
- Changes MAC every 24 hours
- Makes tracking by MAC impossible

**Android 10+ (2019 onwards):**
- Similar randomization
- Different random MAC per network

**How to detect randomization:**
```sql
-- Look for locally administered MACs (bit 2 of first byte = 1)
-- Example: x2, x6, xA, xE in second character
SELECT sourcemac, COUNT(*) as probe_count
FROM probes
WHERE sourcemac LIKE '_2:%'
   OR sourcemac LIKE '_6:%'
   OR sourcemac LIKE '_A:%'
   OR sourcemac LIKE '_E:%'
GROUP BY sourcemac
ORDER BY probe_count DESC;
```

**Randomized MACs show pattern:**
- Different MAC, same probed SSIDs
- MAC starts with locally administered bit set
- Short-lived (MAC changes after 24hrs)

**Countermeasure:**
- Track by **probed SSID patterns** instead of MAC
- Devices still probe for same networks, just with different MACs
- Behavioral fingerprinting still works

### Wildcard Probes

**Problem:** Modern devices send wildcard probes (no SSID)

**Detection:**
```sql
-- Count wildcard vs directed probes
SELECT
    CASE
        WHEN probedssid = '' THEN 'Wildcard (Private)'
        ELSE 'Directed (Revealing)'
    END as probe_type,
    COUNT(*) as count
FROM probes
GROUP BY probe_type;
```

**If device sends wildcard probes only:**
- Privacy-conscious user
- Modern device with privacy features enabled
- OR stalker trying to avoid detection

**Countermeasure:**
- Still visible by MAC (before randomization)
- Still trackable by movement correlation
- Still detectable by signal strength

### Probe Request Suppression

**Some devices (rare) suppress all probes:**
- Don't probe for networks, wait for beacons
- More battery efficient
- Nearly invisible

**Detection:**
```sql
-- Devices with no probe requests
SELECT d.devmac, d.manuf, d.strongest_signal
FROM devices d
LEFT JOIN probes p ON d.devmac = p.sourcemac
WHERE p.sourcemac IS NULL
  AND d.type = 'Wi-Fi Device';
```

**Countermeasure:**
- Still visible to Kismet as device
- Trackable by location/signal/movement
- Just can't identify by network names

---

## Real-World Examples

### Example 1: Identifying Coworker

**Unknown MAC:** `A8:66:7F:12:34:56`

**Query probe requests:**
```sql
SELECT probedssid FROM probes
WHERE sourcemac = 'A8:66:7F:12:34:56';
```

**Results:**
```
Acme_Corp_Internal
Mike's iPhone 13
Starbucks
LA_Fitness_Member
```

**Analysis:**
- Works at Acme Corp (same as you!)
- Name is Mike
- Has iPhone 13
- Goes to Starbucks (near office?)
- Member at LA Fitness gym

**Conclusion:** Coworker named Mike, harmless

**Action:** Add to ignore list with comment:
```
A8:66:7F:12:34:56  # Mike from work, iPhone 13, gym buddy
```

### Example 2: Neighbor Identification

**Unknown MAC:** `B4:F1:DA:AA:BB:CC`

**Query probe requests:**
```sql
SELECT probedssid FROM probes
WHERE sourcemac = 'B4:F1:DA:AA:BB:CC';
```

**Results:**
```
Smith_Family_5G
Apt_Building_Guest
CenturyLink5678
```

**Analysis:**
- Smith family network
- Apartment building guest network (your building!)
- CenturyLink ISP (common in your area)

**Signal strength:** -55 dBm (nearby, not in your unit)

**Conclusion:** Neighbor in your apartment building (Smith family)

**Action:** Add to ignore list:
```
B4:F1:DA:AA:BB:CC  # Smith family neighbor, Apt 3B
```

### Example 3: Stalker Detection (THREAT)

**Unknown MAC:** `4C:11:AE:DE:AD:BE`

**Query probe requests:**
```sql
SELECT probedssid FROM probes
WHERE sourcemac = '4C:11:AE:DE:AD:BE';
```

**Results:**
```
(empty - no probe requests)
```

**Additional info:**
- Manufacturer: Espressif (ESP32 - DIY hardware)
- Signal: -40 dBm (VERY close, in your car?)
- Locations: Work parking lot, home driveway, grocery store
- Timing: Appears when you arrive, disappears when you leave

**Analysis:**
🚩 **No probe requests** = Not trying to connect to WiFi (suspicious)
🚩 **Espressif hardware** = DIY GPS tracker common platform
🚩 **Movement correlation** = Follows you to multiple locations
🚩 **Very strong signal** = In/on your vehicle
🚩 **No legitimate purpose** = Not a phone, laptop, or normal device

**Conclusion:** GPS tracker planted in vehicle

**Action:**
1. **DO NOT REMOVE** (may alert stalker)
2. Document thoroughly
3. Contact police immediately
4. File report
5. Consider restraining order

### Example 4: Ex's Phone Detection

**Unknown MAC:** `3C:06:30:AB:CD:EF`

**Query probe requests:**
```sql
SELECT probedssid FROM probes
WHERE sourcemac = '3C:06:30:AB:CD:EF';
```

**Results:**
```
Sarah's iPhone
SarahsHomeWiFi
Downtown_Gym_Guest
Mom_and_Dad_House
Starbucks_WiFi
```

**Additional info:**
- Manufacturer: Apple (iPhone)
- Locations: Near your work, near your home, near your gym
- Timing: Mornings (your commute), evenings (your return), weekends

**Analysis:**
🚩 **Name "Sarah"** in probes = Identifiable owner
🚩 **Movement correlation** = Same locations as you
🚩 **Timing patterns** = Matches your schedule
🚩 **"Mom and Dad"** network = Family connection
⚠️ Legitimate Apple device (iPhone), not tracker hardware

**Possible conclusions:**
- Ex-girlfriend/ex-wife stalking
- Someone who knows your schedule
- Coincidence if Sarah is coworker/neighbor

**Investigation steps:**
1. Check if Sarah is known to you (ex, coworker, neighbor)
2. Monitor for 3+ occurrences at different locations
3. Check timing (coincidence or pattern?)
4. Document evidence
5. Consider restraining order if confirmed stalking

---

## Red Flags in Probe Patterns

### HIGH RISK Probe Patterns

🚩 **No probe requests at all**
- Device is NOT trying to connect to WiFi
- Purpose is tracking, not communication
- Common in GPS trackers, hidden cameras

🚩 **Probing for YOUR personal networks**
```sql
-- Find devices probing for YOUR network names
SELECT sourcemac, COUNT(*) as probes
FROM probes
WHERE probedssid IN ('YourHomeWiFi', 'YourPhoneHotspot', 'YourWorkplace')
GROUP BY sourcemac;
```
- Someone who has been to your locations
- Ex-partner, former friend, stalker who knows you

🚩 **Excessive probe frequency**
```sql
-- Devices probing more than normal (>100 probes/hour)
SELECT sourcemac,
       COUNT(*) as total_probes,
       (MAX(ts_sec) - MIN(ts_sec)) / 3600.0 as hours,
       COUNT(*) / ((MAX(ts_sec) - MIN(ts_sec)) / 3600.0) as probes_per_hour
FROM probes
GROUP BY sourcemac
HAVING probes_per_hour > 100
ORDER BY probes_per_hour DESC;
```
- WiFi attack tool (wardriving, evil twin)
- Surveillance equipment scanning for targets

🚩 **Randomized MAC but identical probe patterns**
```sql
-- Find devices with same probe patterns (possible randomized MAC)
SELECT p1.sourcemac as mac1, p2.sourcemac as mac2, COUNT(*) as shared_ssids
FROM probes p1
JOIN probes p2 ON p1.probedssid = p2.probedssid
WHERE p1.sourcemac != p2.sourcemac
  AND p1.probedssid != ''
GROUP BY p1.sourcemac, p2.sourcemac
HAVING shared_ssids >= 5
ORDER BY shared_ssids DESC;
```
- Same device using MAC randomization
- Still trackable by network preference pattern

### MEDIUM RISK Probe Patterns

⚠️ **Probing for unusual networks**
- Government/military SSIDs
- Surveillance company networks
- Networks matching your employer

⚠️ **Probe pattern changes**
- Suddenly stops probing (enabled privacy mode)
- Changes from directed to wildcard (trying to hide)

⚠️ **Probes for very old networks**
```
"Linksys" (default router name from 2005)
"NETGEAR" (default name)
```
- Device has been around a long time
- Many network connections in history

---

## Advanced Techniques

### Probe Pattern Fingerprinting

Even with MAC randomization, devices have unique "fingerprints":

**1. Network list order**
- iOS probes in alphabetical order
- Android probes in connection preference order
- Pattern identifies device type

**2. Probe interval timing**
- iPhones probe every 15 seconds
- Android every 30 seconds
- Pattern identifies OS

**3. Network preference patterns**
- Unique combination of SSIDs identifies individual
- "Starbucks + Home + Work + Gym" = fingerprint

**Query to find fingerprint matches:**
```sql
-- Group devices by their probe pattern
SELECT
    GROUP_CONCAT(probedssid, ', ') as network_fingerprint,
    sourcemac,
    COUNT(DISTINCT probedssid) as unique_networks
FROM probes
WHERE probedssid != ''
GROUP BY sourcemac
HAVING unique_networks >= 3
ORDER BY unique_networks DESC;
```

### Cross-referencing with Public Data

**WiGLE.net integration:**
```bash
# Export SSIDs seen
sqlite3 -csv ~/logs/kismet/*.kismet \
  "SELECT DISTINCT probedssid FROM probes WHERE probedssid != '';" \
  > ssid_list.csv

# Upload to WiGLE to see where these networks exist
# Might reveal home addresses, workplaces
```

**Google Search automation:**
```bash
# Create Google search URLs for all probed SSIDs
sqlite3 ~/logs/kismet/*.kismet \
  "SELECT DISTINCT 'https://www.google.com/search?q=' || probedssid
   FROM probes WHERE probedssid != '';" \
  > google_searches.txt
```

---

## Summary: Probe Request Intelligence Value

### What You CAN Learn:

✅ **Owner's name** (if in SSID)
✅ **Home location** (network names, WiGLE lookup)
✅ **Workplace** (corporate network names)
✅ **Habits** (gym, coffee shop, travel)
✅ **Device type** (probe patterns)
✅ **Social connections** (family networks)
✅ **Travel history** (hotel, airport WiFi)

### What You CANNOT Learn:

❌ **Passwords** (probes don't contain credentials)
❌ **Traffic content** (just network names)
❌ **Identity** (if using randomization + wildcards)
❌ **Device location** (only that it's probing, not GPS coords)

### Best Use Cases:

1. **Identifying coworkers** - Corporate SSID match
2. **Identifying neighbors** - Apartment/address in SSID
3. **Identifying ex-partners** - Personal network names you recognize
4. **Detecting trackers** - No probes = not a phone/laptop
5. **Verifying suspicions** - Cross-reference with other intel

### Limitations:

- Modern devices use privacy features (2020+)
- MAC randomization defeats simple tracking
- Wildcard probes reveal nothing
- Requires older device or privacy settings off

**Bottom line:** Probe requests are goldmine for older devices, less useful for new iPhones/Android but still valuable when combined with movement correlation.

---

**Version:** 1.0
**Last Updated:** 2025-12-21
**Project:** Chasing Your Tail - Next Generation
