# Handoff Document - CYT Operational Setup

**Created**: 2026-01-25 13:10
**Last Updated**: 2026-01-28 03:15
**Session Duration**: ~2 hours (this session)

## Goal
Get Chasing-Your-Tail-NG (CYT) fully operational for wireless surveillance detection, including the web dashboard viewable from macOS, with systematic device identification and threat assessment capabilities.

## Session 2026-01-28 Summary (Continued)

### What Was Done This Session
- Verified CYT system status (Kismet PID 46302, CYT Monitor PID 51430)
- Restarted proxy server on macOS (was not running)
- Fixed dashboard access (Chrome tab was hidden in background)
- Fixed Kismet UI access - must use proxy route `localhost:8080/kismet/` NOT direct VM IP
- **OSINT Research**: Deep dive into Benn Jordan and Civil Defense Engineer content
- Validated existing modules: `flock_detector.py`, `imsi_detector.py`, `BENN_JORDAN_GADGETS.md`
- Identified 5 new modules to create for CYT enhancement
- Created equipment purchase list for new capabilities
- **Created `context_engine.py`** (1032 lines) - Situational awareness module:
  - DeFlock API integration for ALPR camera locations
  - Airplanes.live API integration for aircraft tracking
  - Surveillance aircraft pattern matching (FBI, CBP, military)
  - Context snapshot generation with threat scoring
  - Database storage for camera/aircraft sightings
  - Background polling with configurable intervals
- **Integrated context engine into `chasing_your_tail.py`**
- **Updated `config.json`** with context_engine configuration
- **Updated `config_validator.py`** with context_engine schema

### Previous Session Work (2026-01-28 01:22)
- Started CYT system from cold start (VM was running but services stopped)
- Configured Kismet HTTP credentials (username: `kismet`, password: `cyt2026`)
- Added 23 device aliases with vendor identification
- Added Kismet reverse proxy route to cyt_proxy_server.py (partial - WebSocket issues)
- Diagnosed USB WiFi adapter disconnect issue and reconnected
- Discovered Safari HTTPS-Only mode blocking HTTP URLs

### Current Blockers
1. **Safari HTTPS-Only Mode**: Safari blocks `http://` URLs including Kismet and Dashboard
   - **Workaround**: Use Chrome or Firefox instead
   - **Fix**: Safari Settings → Privacy → Uncheck "HTTPS-Only Mode"

2. **USB Adapter Disconnects**: The Alfa AWUS1900 occasionally disconnects from VM
   - **Fix**: Run `prlctl set CYT-Kali --device-connect "802.11ac NIC"`
   - Then re-enable monitor mode and restart Kismet

## Current State

### What's Working
- **Kismet**: Running (PID 46302), capturing 275+ devices
- **Kismet Credentials**: `kismet` / `cyt2026`
- **CYT Monitor**: Running (PID 51430)
- **API Server (VM)**: Running on `http://10.211.55.10:3000`
- **Proxy Server (macOS)**: Running on `http://localhost:8080` (PID 52487)
- **Dashboard API**: Responding correctly (YELLOW alert, 275 devices)
- **Device Aliases**: 24 devices identified with vendor info
- **Alert Level**: YELLOW (high device count, no drones detected)

### What's NOT Working
- **Safari**: Blocks HTTP URLs due to HTTPS-Only mode
- **Kismet UI via Proxy**: WebSocket connections fail through reverse proxy

### VM Details
- **VM Name**: CYT-Kali
- **VM IP**: 10.211.55.10
- **User**: root (running as)
- **CYT Directory**: `/home/parallels/CYT/`
- **Kismet Logs**: `/home/parallels/CYT/logs/kismet/`
- **Kismet Credentials**: Stored in `/root/.kismet/kismet_httpd.conf`

## Device Aliases Added (23 devices)

### Personal Devices (category: unknown - needs user classification)
| MAC | Name | Vendor |
|-----|------|--------|
| 9C:3E:53:3D:71:A0 | Apple Device 1 | Apple, Inc. |
| 6C:40:08:9D:BD:BC | Apple Device 2 | Apple, Inc. |
| 00:7C:2D:7D:22:93 | Samsung Device 1 | Samsung Electronics |
| 20:15:DE:40:38:08 | Samsung Device 2 | Samsung Electronics |
| D8:BE:65:60:E7:58 | Amazon Device 1 | Amazon Technologies |
| 18:48:BE:E1:3C:F5 | Amazon Device 2 | Amazon Technologies |
| 08:12:A5:D7:50:C1 | Amazon Device 3 | Amazon Technologies |
| A0:6A:44:78:E9:56 | Vizio Smart TV | Vizio, Inc |
| 78:80:38:26:C2:DA | Funai TV | FUNAI ELECTRIC |
| D0:3F:27:74:79:53 | Wyze Device | Wyze Labs Inc |
| C0:49:EF:14:F0:EC | IoT Device (ESP32) | Espressif Inc. |

### Infrastructure (category: infrastructure)
| MAC | Name | Vendor |
|-----|------|--------|
| C4:4F:D5:D6:3B:40 | Vantiva Equipment | Vantiva Connected Home |
| 40:75:C3:CA:62:FA | Vantiva Equipment 2 | Vantiva USA LLC |
| D0:FC:D0:8D:BD:11 | HUMAX Modem | HUMAX Co., Ltd. |
| 08:A7:C0:1F:98:A0 | Vantiva Router | Vantiva USA LLC |
| 54:A6:5C:B3:2F:45 | Vantiva Router 2 | Vantiva USA LLC |
| D0:FC:D0:8D:BD:18 | HUMAX Router | HUMAX Co., Ltd. |

### Neighbor Devices (category: neighbor)
| MAC | Name | Vendor |
|-----|------|--------|
| D0:16:7C:02:93:6C | Neighbor eero 1 | eero inc. |
| B4:20:46:A6:2C:43 | Neighbor eero 2 | eero inc. |
| 58:11:22:1D:68:54 | ASUS Router | ASUSTek COMPUTER |
| 34:19:4D:BE:D5:89 | Arcadyan Router | Arcadyan Corporation |
| FC:12:63:89:E6:82 | ASKEY Router | ASKEY COMPUTER CORP |
| 1C:BF:CE:39:B1:84 | Generic Router | Shenzhen Century Xinyang |

## Commands to Resume

### Quick Start (Use Chrome, not Safari!)
```bash
# 1. Start proxy server (if not running)
cd /Users/thomaslavoie/my_projects/0_active_projects/Chasing-Your-Tail-NG
export CYT_VM_API_KEY="4irSMYe38Y-5ONUPhcsPr5MtFx2ViKrkTvhea3YuN9Y"
python3 cyt_proxy_server.py &

# 2. Open dashboard in Chrome
open -a "Google Chrome" "http://localhost:8080/"

# 3. Open Kismet in Chrome (via proxy - login: kismet / cyt2026)
open -a "Google Chrome" "http://localhost:8080/kismet/"
```

**NOTE**: Access Kismet via the proxy (`localhost:8080/kismet/`) NOT directly (`10.211.55.10:2501`). Direct VM IP access fails from Chrome.

### Check Status
```bash
# Check all processes
prlctl exec CYT-Kali "pgrep -a kismet; pgrep -a python"

# Test API
curl -s http://localhost:8080/api/status | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Alert: {d[\"alert_level\"]}, Devices: {d[\"traffic_5m\"]}')"

# Test Kismet (via proxy)
curl -s -u kismet:cyt2026 http://localhost:8080/kismet/system/status.json | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Kismet Devices: {d[\"kismet.system.devices.count\"]}')"
```

### If USB Adapter Disconnects
```bash
# Reconnect adapter
prlctl set CYT-Kali --device-connect "802.11ac NIC"
sleep 2

# Re-enable monitor mode
prlctl exec CYT-Kali "sudo ip link set wlan0 down && sudo iw dev wlan0 set type monitor && sudo ip link set wlan0 up"

# Restart Kismet
prlctl exec CYT-Kali "sudo killall kismet; cd /home/parallels/CYT && sudo ./start_kismet_clean.sh wlan0"

# Restart CYT processes
prlctl exec CYT-Kali "pkill -f python3; cd /home/parallels/CYT && nohup python3 chasing_your_tail.py > /tmp/cyt.log 2>&1 & nohup python3 cyt_api_cors.py > /tmp/api.log 2>&1 &"
```

### Full Restart (If Everything Broken)
```bash
# Stop everything
prlctl exec CYT-Kali "sudo killall -9 kismet python3 2>/dev/null"
pkill -f cyt_proxy_server

# Reconnect USB
prlctl set CYT-Kali --device-connect "802.11ac NIC"
sleep 2

# Enable monitor mode
prlctl exec CYT-Kali "sudo ip link set wlan0 down && sudo iw dev wlan0 set type monitor && sudo ip link set wlan0 up"

# Start Kismet
prlctl exec CYT-Kali "cd /home/parallels/CYT && sudo ./start_kismet_clean.sh wlan0"
sleep 3

# Start CYT
prlctl exec CYT-Kali "cd /home/parallels/CYT && nohup python3 chasing_your_tail.py > /tmp/cyt.log 2>&1 &"
prlctl exec CYT-Kali "cd /home/parallels/CYT && nohup python3 cyt_api_cors.py > /tmp/api.log 2>&1 &"
sleep 2

# Start proxy
cd /Users/thomaslavoie/my_projects/0_active_projects/Chasing-Your-Tail-NG
export CYT_VM_API_KEY="4irSMYe38Y-5ONUPhcsPr5MtFx2ViKrkTvhea3YuN9Y"
python3 cyt_proxy_server.py &

# Open in Chrome
open -a "Google Chrome" "http://localhost:8080/"
```

## Current Metrics (as of handoff)
- **Alert Level**: YELLOW
- **Devices (5 min)**: 275
- **Kismet Devices**: 255
- **Drones Detected**: 0
- **Device Aliases**: 24
- **Ignore List**: 58 MACs

## Environment Variables
| Variable | Purpose | Value |
|----------|---------|-------|
| `CYT_VM_API_KEY` | Authenticate to VM API | `4irSMYe38Y-5ONUPhcsPr5MtFx2ViKrkTvhea3YuN9Y` |

## Kismet Credentials
| Setting | Value |
|---------|-------|
| Username | `kismet` |
| Password | `cyt2026` |
| Config File | `/root/.kismet/kismet_httpd.conf` |

## Known Issues

### Safari HTTPS-Only Mode
Safari blocks HTTP URLs. Either:
1. Use Chrome/Firefox instead
2. Or disable in Safari: Settings → Privacy → Uncheck HTTPS-Only

### USB Adapter Disconnects
The Alfa AWUS1900 occasionally disconnects from the VM. Signs:
- Kismet stops updating
- `iwconfig wlan0` shows no signal
- `dmesg` shows "USB disconnect"

Fix: Reconnect with `prlctl set CYT-Kali --device-connect "802.11ac NIC"`

## OSINT Research Findings (Benn Jordan & Civil Defense Engineer)

### Already Implemented in CYT
| Module | Source | Status |
|--------|--------|--------|
| `flock_detector.py` | Benn Jordan | Complete - ESP32 integration for Flock Safety ALPR detection |
| `imsi_detector.py` | Benn Jordan | Complete - HackRF + kalibrate-hackrf for Stingray detection |
| `BENN_JORDAN_GADGETS.md` | Benn Jordan | 61KB comprehensive guide in `pentest/` directory |

### New Modules to Create

#### 1. Context Engine (`context_engine.py`)
**Purpose**: Enrich CYT alerts with situational awareness data
**Data Sources**:
- DeFlock API - 12,000+ crowdsourced ALPR camera locations
- Airplanes.live API - Unfiltered aircraft tracking (surveillance planes)
- Power grid status APIs
- Weather and atmospheric data

#### 2. Aircraft Correlator (`aircraft_monitor.py`)
**Purpose**: Detect surveillance aircraft patterns
**Features**:
- Track N-numbers of known surveillance planes
- Detect circling/orbiting patterns over your location
- Alert on persistent aircraft presence
- Integrate with ADS-B Exchange or Airplanes.live (unfiltered)

#### 3. DeFlock Integration
**Purpose**: Map nearby ALPR cameras
**Source**: https://deflock.me - Crowdsourced ALPR mapping
**Features**:
- Query cameras within radius of GPS position
- Overlay on CYT dashboard map
- Alert when entering high-surveillance zones

#### 4. Signal Analyzer Enhancement
**Purpose**: Detect anomalous RF patterns
**Equipment**: RTL-SDR + GSM antenna
**Capabilities**:
- Detect IMSI catchers (Stingrays)
- Identify rogue cell towers
- GSM band scanning with kalibrate-hackrf

#### 5. Username Investigator (`username_osint.py`)
**Purpose**: Social media footprint analysis
**Tool**: WhatsMyName integration
**Features**:
- Check username across 600+ platforms
- Export results to CYT reports
- Useful for investigating suspicious devices

### Equipment Purchase List

| Item | Purpose | Est. Cost | Priority |
|------|---------|-----------|----------|
| ESP32 DevKit | Flock detector firmware | $7 | HIGH |
| GSM Antenna | IMSI catcher detection | $20 | HIGH |
| RTL-SDR V3 | RF signal analysis | $40 | MEDIUM |
| HackRF One | Advanced RF analysis | $350 | LOW (already may have) |

**Total for basic expansion**: ~$67

### Implementation Roadmap

**Phase 1 (Week 1)**: ESP32 + Flock Detection
- Purchase ESP32 (~$7)
- Flash with flock-you firmware
- Test `flock_detector.py` integration

**Phase 2 (Week 2)**: Context Engine - **COMPLETE**
- [x] Create `context_engine.py` (620+ lines) - COMPLETE
- [x] Integrate Airplanes.live API - COMPLETE (tested, working)
- [x] DeFlock API structure - COMPLETE (needs endpoint verification)
- [x] Wire into main CYT monitor loop - COMPLETE
- [x] Add config_validator.py schema - COMPLETE
- [x] Add context_engine section to config.json - COMPLETE

**Phase 3 (Week 3)**: Dashboard Enhancement
- Add ALPR camera overlay to map
- Add aircraft tracking overlay
- Context panel for environmental data

**Phase 4 (Week 4)**: IMSI Detection
- Test `imsi_detector.py` with GSM antenna
- Validate against known cell towers
- Tune false positive thresholds

**Phase 5 (Week 5)**: Integration & Polish
- Connect all modules to AlertManager
- Create unified threat score
- Document operational procedures

### Reference Resources
- **Benn Jordan YouTube**: Flock Safety, Stingray detection, Meshtastic privacy
- **Civil Defense Engineer**: OSINT tools, aircraft tracking, surveillance awareness
- **DeFlock**: https://deflock.me (ALPR camera crowdsourcing)
- **ADS-B Exchange**: https://adsbexchange.com (unfiltered aircraft)
- **Airplanes.live**: Alternative unfiltered ADS-B source
- **WhatsMyName**: https://whatsmyname.app (username enumeration)

---

## Next Steps
1. **Use Chrome** to access dashboard and Kismet (Safari won't work)
2. **Classify your devices** - Update the Apple/Samsung/Amazon aliases to category "mine"
3. **Add more to ignore list** - Once you identify your devices
4. **Monitor for drones** - Watch for YELLOW→RED alert transitions
5. **Fix Safari** (optional) - Disable HTTPS-Only in Safari settings
6. **Purchase ESP32** (~$7) - Start Flock detector hardware integration
7. **Create context_engine.py** - Begin DeFlock and aircraft tracking integration

---

**Last Updated**: 2026-01-28 03:15

---

## Auto-Compaction Marker

**Last Auto-Compaction**: 2026-01-28 02:38

*This marker was automatically added by the PreCompact hook. The content above represents the session state at compaction time. Read this file on session resume to restore context.*

