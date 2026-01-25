# CYT Device Identification & Threat Assessment Guide

## Current Device Analysis (2026-01-25)

### Summary
- **Total Close Contacts**: 38 devices
- **Alert Level**: YELLOW (high device count, no known drones)
- **Randomized MACs**: 9 devices (hidden identity)
- **Identifiable MACs**: 29 devices (can be looked up)

---

## Device Categories by OUI Lookup

### Infrastructure (Expected - Add to Ignore List)

| OUI | Vendor | Device Type | Count | Action |
|-----|--------|-------------|-------|--------|
| A8:40:F8 | HUMAX Networks | Cable modem/router | 4 | ✅ Ignore |
| 6C:55:E8 | Vantiva USA | Cable/ISP equipment | 12 | ✅ Ignore |
| 18:A5:FF | Arcadyan Corporation | ISP router | 2 | ✅ Ignore |
| 18:A5:D0 | Arcadyan Corporation | ISP router | 1 | ✅ Ignore |
| 18:A5:B7 | Arcadyan Corporation | ISP router | 1 | ✅ Ignore |
| 78:6D:EB | GE Lighting | Smart bulb/IoT | 1 | ✅ Ignore |

### Consumer Devices (Likely Neighbors - Monitor)

| OUI | Vendor | Device Type | Signal | Assessment |
|-----|--------|-------------|--------|------------|
| 1C:FE:2B | Amazon Technologies | Echo/Fire device | -35 dBm | Normal neighbor device |
| 9C:3E:53 | Apple Inc. | iPhone/iPad/Mac | -59 dBm | Normal, far away |
| A0:A3:B3 | Espressif Inc. | ESP32 IoT device | -45 dBm | Smart home device |
| 2C:C1:F4 | Nokia Solutions | Telecom equipment | -54 dBm | Normal infrastructure |

### Requires Investigation

| OUI | Vendor | Signal | Concern Level |
|-----|--------|--------|---------------|
| 5C:E7:53 | **PRIVATE** | -50 dBm | ⚠️ INVESTIGATE - Hidden registration |

### Randomized MACs (Cannot Identify by OUI)

| MAC Address | Signal | Threat Level | Notes |
|-------------|--------|--------------|-------|
| B6:EC:31:82:8F:A2 | -35 dBm | HIGH | Very close, hidden identity |
| 46:94:29:8B:98:96 | -41 dBm | HIGH | Close proximity |
| C2:D1:98:8F:3D:E6 | -51 dBm | MEDIUM | Moderate distance |
| 1E:FB:C3:DB:95:AA | -52 dBm | MEDIUM | Moderate distance |
| 72:D4:2D:DD:9A:AF | -52 dBm | MEDIUM | Moderate distance |
| F6:FD:C9:CD:AC:99 | -53 dBm | MEDIUM | Moderate distance |
| 36:19:4D:10:B9:D4 | -54 dBm | MEDIUM | Moderate distance |
| 86:F9:32:42:30:EB | -55 dBm | LOW | Further away |
| 36:19:4D:90:B9:D4 | -56 dBm | LOW | Further away |

---

## Systematic Identification Methodology

### Step 1: OUI Lookup (Instant)
```bash
# Using mac-vendor-lookup Python library
pip install mac-vendor-lookup
python3 -c "from mac_vendor_lookup import MacLookup; print(MacLookup().lookup('A8:40:F8'))"
```

**Free Online Tools:**
- [MAC Lookup App](https://maclookup.app/) - Free API available
- [Wireshark OUI Lookup](https://www.wireshark.org/tools/oui-lookup.html)
- [macvendorlookup.com](https://www.macvendorlookup.com/)

### Step 2: Signal Strength Analysis
- **> -40 dBm**: Very close (same room/next door) - HIGH concern if unknown
- **-40 to -55 dBm**: Nearby (same building) - MEDIUM concern
- **-55 to -70 dBm**: Moderate distance - LOW concern
- **< -70 dBm**: Far away - Usually benign

### Step 3: Persistence Tracking
CYT automatically tracks devices that:
- Appear repeatedly over time windows (5, 10, 15, 20 min)
- Follow you across locations (with GPS)
- Show "stalker" patterns (seen 20 min ago AND now)

### Step 4: Behavioral Analysis
CYT's behavioral detector looks for:
1. High mobility (>15 m/s movement)
2. Signal variance (>20 dBm changes)
3. Hovering patterns (<50m radius)
4. Brief appearances (<5 min)
5. No network association
6. High signal strength (>-50 dBm)
7. High probe frequency (>10/min)
8. Channel hopping (>2 channels)
9. No connected clients

### Step 5: WiGLE Geolocation (Advanced)
Query WiGLE database to see if a device has been seen elsewhere:
- Requires free account at [wigle.net](https://wigle.net)
- Can reveal if device travels or is stationary
- Shows historical locations

---

## Open Databases & APIs

### MAC/OUI Lookup

| Database | Type | Cost | API |
|----------|------|------|-----|
| [maclookup.app](https://maclookup.app/) | OUI Vendor | Free | Yes |
| [macaddress.io](https://macaddress.io/) | OUI + Details | Freemium | Yes |
| [IEEE OUI Database](https://standards-oui.ieee.org/) | Official Source | Free | Download |
| [Wireshark manuf](https://www.wireshark.org/download/automated/data/manuf) | OUI Database | Free | Download |

### Wireless Geolocation

| Database | Coverage | Cost | Notes |
|----------|----------|------|-------|
| [WiGLE](https://wigle.net/) | 1B+ networks | Free* | *Rate limited to contribution ratio |
| [OpenWiFi](https://openwifi.su/) | Russia focus | Free | Limited coverage |
| [Mozilla Location](https://location.services.mozilla.com/) | Deprecated | N/A | No longer active |

### Drone Detection Databases

| Source | Type | Notes |
|--------|------|-------|
| DJI OUI Prefixes | 60:60:1F, 34:D2:62 | Most common consumer drones |
| Parrot OUI | 90:03:B7, 00:12:1C | Consumer drones |
| Autel | A0:14:3D | Consumer drones |
| RemoteID Broadcasts | WiFi Beacon | Required by law (2023+) |

---

## GitHub Tools for Enhanced Detection

### OUI/MAC Lookup Libraries

1. **[mac_vendor_lookup](https://github.com/bauerj/mac_vendor_lookup)** (Python)
   ```bash
   pip install mac-vendor-lookup
   ```
   - Offline lookup with auto-update capability
   - Async support for high performance

2. **[manuf](https://github.com/coolbho3k/manuf)** (Python)
   - Uses Wireshark's comprehensive database
   - Supports netmasks and edge cases

3. **[MAC-Address-Lookup](https://github.com/ScriptTiger/MAC-Address-Lookup)**
   - Self-hosted, free, no API limits
   - Maintains own IEEE database

### Drone Detection Projects

1. **[Sentry](https://github.com/connervieira/Sentry)**
   - WiFi-based drone detection
   - Monitors 2.4, 5, 5.8 GHz bands
   - MAC OUI pattern matching

2. **[RF-Drone-Detection](https://github.com/tesorrells/RF-Drone-Detection)**
   - Uses airodump-ng for passive monitoring
   - Drone manufacturer OUI database
   - GNU Radio integration

3. **[drone-detection](https://github.com/equiroga8/drone-detection)**
   - Channel hopping detection
   - Real-time alerts
   - Works with any monitor-mode capable WiFi adapter

4. **[RemoteIDReceiver](https://github.com/cyber-defence-campus/RemoteIDReceiver)**
   - Captures FAA-mandated Remote ID broadcasts
   - Web interface for monitoring
   - DJI DroneID support

### Advanced WiFi Analysis

1. **[Sparrow-WiFi](https://github.com/ghostop14/sparrow-wifi)**
   - GUI-based WiFi/Bluetooth analyzer
   - GPS integration
   - Drone-mountable for aerial surveys
   - Source hunt mode for tracking

---

## Threat Classification Framework

### GREEN (Safe)
- Known infrastructure (your router, ISP equipment)
- Devices in your ignore list
- Far away signals (< -70 dBm)
- Known neighbor devices (consistent patterns)

### YELLOW (Monitor)
- Unknown devices with strong signals
- Randomized MACs nearby
- New devices not seen before
- High device count in area

### RED (Investigate)
- Known drone OUIs detected
- Device following across locations
- Persistence score > 0.6
- Behavioral detection confidence > 60%
- "Private" registered OUIs with strong signal

---

## Recommended Workflow

### Daily Monitoring
1. Check dashboard for alert level
2. Review any new strong-signal devices
3. Look up unknown OUIs
4. Add identified safe devices to ignore list

### Weekly Analysis
1. Export device history from CYT
2. Analyze persistence patterns
3. Query WiGLE for suspicious MACs
4. Update drone OUI database

### Incident Response
1. Note time and location
2. Screenshot dashboard
3. Export raw Kismet data
4. Query all databases for device history
5. Enable GPS tracking if mobile
6. Document for potential reporting

---

## Adding to CYT Ignore List

```bash
# Edit ignore list on VM
prlctl exec CYT-Kali "nano /home/parallels/CYT/ignore_lists/mac_list.txt"

# Or via shared folder from macOS
nano /Users/thomaslavoie/my_projects/0_active_projects/Chasing-Your-Tail-NG/ignore_lists/mac_list.txt

# Format: One MAC per line with optional comment
# Example:
# A8:40:F8:E9:DC:A4  # My HUMAX router
# 6C:55:E8:7A:29:74  # Neighbor's cable box
```

---

## Quick Reference Commands

```bash
# Lookup single MAC
curl -s "https://api.maclookup.app/v2/macs/A8:40:F8" | python3 -m json.tool

# Batch lookup (Python)
python3 << 'EOF'
from mac_vendor_lookup import MacLookup
macs = ["A8:40:F8:E9:DC:A4", "6C:55:E8:7A:29:74", "B6:EC:31:82:8F:A2"]
ml = MacLookup()
for mac in macs:
    try:
        print(f"{mac}: {ml.lookup(mac)}")
    except:
        print(f"{mac}: Unknown/Randomized")
EOF

# Check WiGLE (requires API key)
curl -s -u "YOUR_API_NAME:YOUR_API_KEY" \
  "https://api.wigle.net/api/v2/network/search?netid=A8:40:F8:E9:DC:A4"
```

---

*Document created: 2026-01-25*
*CYT Version: 2.3*
