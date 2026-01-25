# Handoff Document - CYT Operational Setup

**Created**: 2026-01-25 13:10
**Last Updated**: 2026-01-25 14:00
**Session Duration**: ~90 minutes

## Goal
Get Chasing-Your-Tail-NG (CYT) fully operational for wireless surveillance detection, including the web dashboard viewable from macOS, with systematic device identification and threat assessment capabilities.

## Progress Summary
- ✅ CYT-Kali VM running (up 18+ hours)
- ✅ Enabled monitor mode on wlan0 (Alfa AWUS1900)
- ✅ Started Kismet - capturing 245+ devices
- ✅ Converted ignore lists from JSON to TXT format
- ✅ Updated config.json kismet_logs path
- ✅ Started CYT monitoring daemon
- ✅ Created CORS-enabled API server (`cyt_api_cors.py`)
- ✅ Created macOS proxy server (`cyt_proxy_server.py`)
- ✅ Dashboard fully operational at `http://localhost:8080/`
- ✅ Added 22 infrastructure devices to ignore list (now 58 MACs total)
- ✅ Investigated all suspicious devices (all LOW THREAT)
- ✅ Installed `mac-vendor-lookup` library on macOS
- ✅ Created `DEVICE_IDENTIFICATION_GUIDE.md` with methodology

## Current State

### What's Working
- **Kismet**: Running, capturing 245+ devices
- **CYT Monitor**: Running in background, tracking device persistence
- **API Server**: Running on `http://10.211.55.10:3000`
- **Proxy Server**: Running on macOS `http://localhost:8080`
- **Dashboard**: Fully operational, auto-refreshes every 10 seconds
- **Alert Level**: YELLOW (high device count, no drones detected)
- **Ignore List**: 58 MACs (infrastructure filtered out)
- **OUI Lookup**: `mac-vendor-lookup` library installed and tested

### VM Details
- **VM Name**: CYT-Kali
- **VM IP**: 10.211.55.10 (also 10.211.55.11)
- **User**: root (running as)
- **CYT Directory**: `/home/parallels/CYT/`
- **Kismet Logs**: `/home/parallels/CYT/logs/kismet/`
- **Current DB**: `Kismet-20260125-18-52-00-1.kismet` (~100MB)

## What Worked
- **Proxy server pattern**: Serves dashboard locally, proxies API to VM - bypasses CORS
- **prlctl exec**: Running VM commands from macOS terminal
- **mac-vendor-lookup**: Offline OUI lookup with auto-update capability
- **Infrastructure ignore list**: Filtering out known Vantiva, HUMAX, Arcadyan devices
- **Device investigation**: Using Kismet DB to see what networks devices connect to

## What Didn't Work
- **file:// + CORS**: Browser blocks cross-origin requests from file:// protocol
- **Direct VM access from browser**: Works with curl but not browser (intermittent)
- **VM IP stability**: DHCP gave VM new IP, had to renew lease

## Device Investigation Results

### Infrastructure Added to Ignore List (22 devices)
| Vendor | Count | OUI Prefixes |
|--------|-------|--------------|
| Vantiva (Cable) | 12 | 6C:55:E8 |
| HUMAX Networks | 4 | A8:40:F8 |
| Arcadyan (ISP) | 5 | 18:A5:FF, 18:A5:D0, 18:A5:B7 |
| GE Lighting | 1 | 78:6D:EB |

### Suspicious Devices Investigated (All LOW THREAT)
| MAC | Type | Signal | Connected To | Assessment |
|-----|------|--------|--------------|------------|
| 5C:E7:53:4E:15:51 | PRIVATE OUI | -50 dBm | Arcadyan Router | Neighbor device |
| B6:EC:31:82:8F:A2 | Randomized | -34 dBm | Vantiva Cable | Neighbor's phone |
| 46:94:29:8B:98:96 | Randomized | -41 dBm | Vantiva Cable | Neighbor's device |

## Key Files

### Created This Session
| File | Description |
|------|-------------|
| `cyt_proxy_server.py` | macOS proxy server for dashboard |
| `dashboard_local.html` | Dashboard using local proxy endpoints |
| `DEVICE_IDENTIFICATION_GUIDE.md` | Methodology for device identification |

### Modified This Session
| File | Description |
|------|-------------|
| `/home/parallels/CYT/ignore_lists/mac_list.txt` | Added 22 infrastructure MACs with comments |
| `HANDOFF.md` | This file |

### Important Locations
| Path | Description |
|------|-------------|
| `/home/parallels/CYT/` | CYT installation in VM |
| `/home/parallels/CYT/logs/kismet/` | Kismet database files |
| `/tmp/cyt_output.log` | CYT monitor output log |
| `/tmp/cyt_api.log` | API server log |

## Commands to Resume

### Check Status
```bash
# Check all processes
prlctl exec CYT-Kali "pgrep -a kismet; pgrep -a python"

# Test API directly
curl -s -H "X-API-Key: 4irSMYe38Y-5ONUPhcsPr5MtFx2ViKrkTvhea3YuN9Y" http://10.211.55.10:3000/status | python3 -m json.tool

# Check device count
prlctl exec CYT-Kali "sqlite3 /home/parallels/CYT/logs/kismet/*.kismet 'SELECT COUNT(*) FROM devices'"

# Quick status summary
curl -s http://localhost:8080/api/status | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Alert: {d[\"alert_level\"]}, Devices: {d[\"traffic_5m\"]}, Drones: {d[\"drones_detected\"]}')"
```

### Start Services (If Stopped)
```bash
# Enable monitor mode
prlctl exec CYT-Kali "ip link set wlan0 down && iw dev wlan0 set type monitor && ip link set wlan0 up"

# Start Kismet
prlctl exec CYT-Kali "cd /home/parallels/CYT && ./start_kismet_clean.sh wlan0"

# Start CYT monitor
prlctl exec CYT-Kali "cd /home/parallels/CYT && export CYT_TEST_MODE=true && nohup python3 chasing_your_tail.py > /tmp/cyt_output.log 2>&1 &"

# Start API server (VM)
prlctl exec CYT-Kali "cd /home/parallels/CYT && nohup python3 cyt_api_cors.py > /tmp/cyt_api.log 2>&1 &"

# Start proxy server (macOS)
cd /Users/thomaslavoie/my_projects/0_active_projects/Chasing-Your-Tail-NG
python3 cyt_proxy_server.py
```

### View Dashboard
```bash
# Start proxy server and open dashboard
cd /Users/thomaslavoie/my_projects/0_active_projects/Chasing-Your-Tail-NG
python3 cyt_proxy_server.py &
open http://localhost:8080/
```

### Device Investigation
```bash
# Lookup MAC vendor
python3 -c "from mac_vendor_lookup import MacLookup; print(MacLookup().lookup('A8:40:F8:E9:DC:A4'))"

# Query device details from Kismet
prlctl exec CYT-Kali "sqlite3 /home/parallels/CYT/logs/kismet/*.kismet 'SELECT devmac, type, strongest_signal FROM devices WHERE devmac LIKE \"XX:XX:XX%\"'"

# Check what network a device is connected to
prlctl exec CYT-Kali "sqlite3 /home/parallels/CYT/logs/kismet/*.kismet 'SELECT devmac, substr(device, instr(device, \"last_bssid\")+14, 17) FROM devices WHERE devmac = \"XX:XX:XX:XX:XX:XX\"'"
```

## Current Metrics (as of handoff)
- **Alert Level**: YELLOW
- **Devices (5 min)**: 178
- **Devices (15 min)**: 245
- **Drones Detected**: 0
- **Close Contacts**: 37 devices
- **Ignore List**: 58 MACs
- **Threats Identified**: 0 (all investigated devices are normal)

## Tools & Resources Identified

### OUI Lookup
- [maclookup.app](https://maclookup.app/) - Free API
- [Wireshark OUI](https://www.wireshark.org/tools/oui-lookup.html)
- `mac-vendor-lookup` Python library (installed)

### Drone Detection GitHub Projects
- [Sentry](https://github.com/connervieira/Sentry) - WiFi drone detection
- [Sparrow-WiFi](https://github.com/ghostop14/sparrow-wifi) - Advanced WiFi analyzer
- [RF-Drone-Detection](https://github.com/tesorrells/RF-Drone-Detection) - Passive monitoring

### Geolocation
- [WiGLE](https://wigle.net/) - Wireless network location database

## API Credentials
- **API Key**: `4irSMYe38Y-5ONUPhcsPr5MtFx2ViKrkTvhea3YuN9Y`
- **VM API URL**: `http://10.211.55.10:3000`
- **Proxy URL**: `http://localhost:8080`
- **Endpoints**: `/api/status`, `/api/targets`, `/api/health`

## Next Steps
1. **Monitor** for new unknown devices with strong signals
2. **Test GPS tracking** by moving around (currently stationary)
3. **Add more neighbors' devices** to ignore list as identified
4. **Set up WiGLE account** for geolocation queries
5. **Consider Sentry integration** for enhanced drone detection
