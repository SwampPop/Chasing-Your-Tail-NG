# BLE Integration Summary
## Chasing Your Tail - Bluetooth Low Energy Surveillance Detection

**Date**: November 2025
**Feature**: Complete BLE surveillance detection system
**Status**: ✅ Fully Integrated and Operational

---

## What We Built

We successfully integrated **Bluetooth Low Energy (BLE) surveillance detection** into your Chasing Your Tail wireless monitoring system. Your system can now detect and analyze:

- 🏷️ **BLE Trackers** (AirTags, Tiles, SmartTags)
- ⌚ **BLE Wearables** (Fitbit, Garmin, smartwatches)
- 🚁 **BLE Drones** (DJI, Parrot, Autel)
- 📱 **Unknown BLE Devices** (generic surveillance threats)

All BLE devices are now subject to the same **persistence scoring** and **multi-location tracking** as Wi-Fi devices, giving you comprehensive wireless threat detection.

---

## New Features

### 1. BLE Device Classification (`ble_classifier.py`)

**What it does:**
- Classifies BLE devices based on manufacturer IDs, service UUIDs, and device names
- Uses a **priority-based detection strategy** to handle ambiguous devices
- Filters out non-surveillance devices to reduce noise

**Key Components:**
- `BLEClassifier` class with `classify_device()` method
- Known manufacturer ID database (DJI, Apple, Tile, Fitbit, Garmin, etc.)
- Service UUID patterns for trackers and wearables
- Keyword fallback detection for unknown manufacturers

**Example Usage:**
```python
from ble_classifier import BLEClassifier

classifier = BLEClassifier()
device = {
    'manufacturer': 0x0B41,  # DJI
    'name': 'DJI Mavic 3',
    'uuid_list': []
}

device_type = classifier.classify_device(device)
# Returns: DeviceType.BLE_DRONE
```

---

### 2. Extended Device Type Enum (`cyt_constants.py`)

**New device types added:**
```python
class DeviceType(Enum):
    BLE_TRACKER = "BLE Tracker"      # AirTags, Tiles, SmartTags
    BLE_WEARABLE = "BLE Wearable"    # Fitness trackers, smartwatches
    BLE_DRONE = "BLE Drone"          # DJI, Parrot, Autel drones
    BLE_UNKNOWN = "BLE Unknown"      # Generic BLE devices
```

**BLE Manufacturer Constants:**
```python
SystemConstants.BLE_MANUFACTURER_DJI = 0x0B41
SystemConstants.BLE_MANUFACTURER_APPLE = 0x004C
SystemConstants.BLE_MANUFACTURER_TILE = 0x004E
# ... and more
```

---

### 3. BLE Database Queries (`secure_database.py`)

**New methods in `SecureKismetDB`:**

```python
def get_ble_devices_by_time_range(start_time, end_time=None)
    """Query BLE devices from Kismet database by timestamp"""

def check_for_ble_drones_secure(time_window_seconds)
    """Specifically check for BLE drones (DJI, Parrot, Autel)"""
```

**Features:**
- Secure parameterized queries (SQL injection prevention)
- Automatic parsing of `bluetooth.device` JSON structure
- Extraction of manufacturer IDs, device names, and service UUIDs
- Context manager for resource safety

---

### 4. BLE Surveillance Detection (`surveillance_detector.py`)

**New function:**
```python
def load_ble_appearances_from_kismet(db_path, detector, location_id)
    """Load BLE device appearances and classify them for surveillance analysis"""
```

**How it works:**
1. Queries all BLE devices from Kismet database
2. Classifies each device using `BLEClassifier`
3. Filters for surveillance-relevant devices only
4. Adds device appearances to `SurveillanceDetector`
5. Returns count of loaded appearances

**Integration:**
- BLE devices go through same persistence scoring as Wi-Fi
- Multi-location tracking applies to BLE
- Threat levels (Critical/High/Medium/Low) calculated identically

---

### 5. Complete Surveillance Analyzer (`surveillance_analyzer.py`)

**New unified analysis workflow:**

```python
class SurveillanceAnalyzer:
    def load_data_from_kismet_databases():
        # Loads BOTH Wi-Fi and BLE devices
        wifi_count = load_appearances_from_kismet(...)
        ble_count = load_ble_appearances_from_kismet(...)

    def analyze_surveillance_patterns():
        # Analyzes Wi-Fi + BLE together

    def generate_reports():
        # Reports show both Wi-Fi and BLE threats

    def export_kml():
        # Maps include BLE device locations
```

**Statistics Tracked:**
- `wifi_appearances` - Wi-Fi device count
- `ble_appearances` - BLE device count
- `total_devices` - Combined device count
- `suspicious_devices` - Threats detected
- `high_threat_devices` - Critical threats

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Kismet Database                          │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │   Wi-Fi Devices  │        │   BLE Devices    │          │
│  │ (dot11.device)   │        │(bluetooth.device)│          │
│  └────────┬─────────┘        └────────┬─────────┘          │
└───────────┼──────────────────────────┼────────────────────┘
            │                           │
            ▼                           ▼
   ┌────────────────┐         ┌────────────────────┐
   │ Wi-Fi Loader   │         │  BLE Loader +      │
   │                │         │  BLE Classifier    │
   └────────┬───────┘         └────────┬───────────┘
            │                          │
            └──────────┬───────────────┘
                       ▼
           ┌───────────────────────┐
           │ Surveillance Detector │
           │  (Persistence Score)  │
           └───────────┬───────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │  Report Generator     │
           │  + KML Exporter       │
           └───────────────────────┘
```

---

## How BLE Classification Works

### Priority-Based Detection Strategy

**Priority 1: Drones (Manufacturer ID)**
```python
if manufacturer == BLE_MANUFACTURER_DJI:
    return DeviceType.BLE_DRONE
```
- **Why first**: Drones are highest threat
- **Reliability**: Manufacturer ID can't be easily spoofed

**Priority 2: Trackers (Manufacturer ID)**
```python
if manufacturer == BLE_MANUFACTURER_APPLE:
    if 'airtag' in name or uuid == 'FD6F':
        return DeviceType.BLE_TRACKER
```
- **Special case**: Apple makes many BLE devices
- **Multi-factor check**: Manufacturer + name or UUID

**Priority 3: Trackers (Service UUIDs)**
```python
if uuid in TRACKER_UUIDS:  # ['FE2C', '181C', 'FD6F']
    return DeviceType.BLE_TRACKER
```
- **Protocol-based**: Standardized Bluetooth SIG UUIDs
- **Catches unknown manufacturers**

**Priority 4-5: Wearables**
- Same pattern as trackers (manufacturer → UUID)

**Priority 6: Name Keyword Fallback**
```python
if 'drone' in name or 'dji' in name:
    return DeviceType.BLE_DRONE
```
- **Last resort**: Device names are user-configurable
- **Low reliability**: Used only when nothing else matches

---

## Key Cybersecurity Concepts You Learned

### 1. Defense in Depth for Device Identification

**Concept**: Never rely on a single indicator for threat detection

**Implementation**:
- Layer 1: Hardware identifiers (manufacturer ID)
- Layer 2: Protocol identifiers (service UUIDs)
- Layer 3: User-controlled data (device names)

**Why it matters**: If an attacker spoofs device name, manufacturer ID still reveals identity

---

### 2. Trust Hierarchy

**Concept**: Prioritize data sources by how difficult they are to spoof

**Trust Levels**:
1. **High Trust**: Manufacturer ID (baked into firmware)
2. **Medium Trust**: Service UUIDs (protocol standards)
3. **Low Trust**: Device names (user-configurable)

**Real-world application**:
- Web security: Server certs > HTTP headers > cookies
- System security: Kernel mode > user mode

---

### 3. Graceful Degradation

**Concept**: Systems should degrade functionality, not fail completely

**Implementation**:
```python
if manufacturer is not None:
    # Try manufacturer-based classification
else:
    # Fall back to UUID-based classification
    if uuid_list:
        # Try UUID classification
    else:
        # Fall back to name-based classification
```

**Why it matters**: BLE devices send varying amounts of data. Your system handles all cases.

---

### 4. False Positive vs False Negative Trade-offs

**False Negative (missed threat)**: Drone marked as "Unknown" → YOU MISS THE THREAT
**False Positive (false alarm)**: Bluetooth speaker marked as "Drone" → ANNOYING BUT SAFE

**Our strategy**: **Minimize false negatives**
- Drones detected first (critical threats)
- Broad keyword matching as fallback (catches unknowns)
- Accept some false positives to avoid missing threats

---

### 5. Defensive Coding Patterns

**Never trust input data:**
```python
if manufacturer is not None:  # Check before comparing
    if manufacturer == 0x0B41:
        # Safe to process
```

**Always handle missing data:**
```python
name = device.get('name', '').lower()  # Default to empty string
uuid_list = device.get('uuid_list', [])  # Default to empty list
```

**Why it matters**: Wireless devices can send incomplete data. Code must not crash.

---

## Usage Examples

### Example 1: Basic BLE Surveillance Detection

```bash
# Start Kismet to capture Wi-Fi + BLE
sudo ./start_kismet_clean.sh wlan0mon

# Let it run for a few hours, then:
python3 surveillance_analyzer.py

# Output:
# Wi-Fi appearances: 127
# BLE appearances: 43
# Suspicious devices: 8
# High-threat devices: 2
#
# TOP THREATS:
# 1. AA:BB:CC:DD:EE:FF
#    Type: BLE Drone
#    Threat Level: CRITICAL 🚨
#    Persistence Score: 0.89
#    Locations: 4
#    Appearances: 12
```

---

### Example 2: Demo Mode (No Kismet Data)

```bash
# Run with simulated GPS data
python3 surveillance_analyzer.py --demo

# Tests the full pipeline without real captures
```

---

### Example 3: Flipper Zero Complementary Workflow

```bash
# Passive monitoring
sudo ./start_kismet_clean.sh wlan0mon

# Active enumeration with Flipper Zero:
# Flipper: Bluetooth → Scan → Save

# Analysis after collection
python3 surveillance_analyzer.py

# Review reports:
open surveillance_reports/surveillance_report_*.html
```

---

## Testing Your New BLE Detection

### Test 1: Detect Your Own Devices

**Goal**: Verify BLE classification works

```bash
# Enable Bluetooth on your phone/watch
# Start Kismet
sudo ./start_kismet_clean.sh wlan0mon

# Wait 5 minutes
# Run analysis
python3 surveillance_analyzer.py

# Check if your device was classified correctly:
grep -i "fitbit\|garmin\|apple" surveillance_reports/surveillance_report_*.md
```

---

### Test 2: Simulated AirTag Tracking

**Goal**: Test tracker detection with Flipper Zero

```bash
# Flipper Zero: Bluetooth → BLE Spam → Apple
# (This simulates many Apple devices)

# Run Kismet during spam attack
sudo ./start_kismet_clean.sh wlan0mon

# Stop Flipper spam after 30 seconds
# Run CYT analysis
python3 surveillance_analyzer.py

# Expected: Multiple "BLE Tracker" detections
```

---

### Test 3: BLE Drone Detection

**Goal**: Verify drone detection (if you have DJI drone)

```bash
# Power on DJI drone remote controller (broadcasts BLE)
# Run Kismet
sudo ./start_kismet_clean.sh wlan0mon

# Wait 2-3 minutes
# Run analysis
python3 surveillance_analyzer.py

# Expected: DJI device classified as "BLE Drone"
```

---

## File Structure

### New Files Created

```
Chasing-Your-Tail-NG/
├── ble_classifier.py              # NEW: BLE device classification
├── BLE_INTEGRATION_SUMMARY.md     # NEW: This document
├── FLIPPER_ZERO_GUIDE.md          # NEW: Flipper Zero integration guide
├── cyt_constants.py               # MODIFIED: Added BLE device types
├── secure_database.py             # MODIFIED: Added BLE query methods
├── surveillance_detector.py       # MODIFIED: Added BLE loading function
└── surveillance_analyzer.py       # REBUILT: Full BLE integration
```

### Modified Files

1. **`cyt_constants.py`** (Lines 15-18, 109-118)
   - Added `BLE_TRACKER`, `BLE_WEARABLE`, `BLE_DRONE`, `BLE_UNKNOWN` enums
   - Added manufacturer ID constants for DJI, Apple, Tile, etc.

2. **`secure_database.py`** (Lines 209-279)
   - Added `get_ble_devices_by_time_range()` method
   - Added `check_for_ble_drones_secure()` method
   - Parses `bluetooth.device` JSON structure

3. **`surveillance_detector.py`** (Lines 143-207)
   - Added `load_ble_appearances_from_kismet()` function
   - Integrates BLE classifier
   - Filters surveillance-relevant BLE devices

4. **`surveillance_analyzer.py`** (Completely rebuilt, 414 lines)
   - Loads both Wi-Fi and BLE data
   - Unified analysis workflow
   - Separate statistics for Wi-Fi vs BLE
   - Command-line interface with `--demo` mode

---

## Next Steps

### Immediate Actions

1. ✅ **Test the system**:
   ```bash
   python3 surveillance_analyzer.py --demo
   ```

2. ✅ **Capture real BLE data**:
   ```bash
   sudo ./start_kismet_clean.sh wlan0mon
   # Wait a few hours
   python3 surveillance_analyzer.py
   ```

3. ✅ **Review the reports**:
   ```bash
   ls -la surveillance_reports/
   open surveillance_reports/surveillance_report_*.html
   ```

4. ✅ **Experiment with Flipper Zero**:
   - Read `FLIPPER_ZERO_GUIDE.md`
   - Try BLE beacon spam detection
   - Enumerate GATT services on your devices

---

### Advanced Enhancements

**Suggested improvements you can make:**

1. **Add MAC address randomization detection**:
   - Track BLE devices that change MACs but have consistent service UUIDs
   - Harder to implement but defeats privacy features

2. **Build manufacturer ID database**:
   - Add more manufacturers to `SystemConstants`
   - Download official Bluetooth SIG company ID list
   - Auto-update classifier with new devices

3. **Improve wearable detection**:
   - Add more service UUIDs (blood oxygen, ECG, etc.)
   - Distinguish smartwatches from fitness bands
   - Detect health data leakage

4. **Create BLE-specific reports**:
   - Separate section for BLE threats
   - Explain BLE-specific risks (tracking, privacy)
   - Recommend defenses (MAC randomization, Bluetooth off)

5. **Integrate with GUI**:
   - Add BLE tab to `cyt_gui.py`
   - Real-time BLE threat alerts
   - Visual BLE device classification

---

## Troubleshooting

### Issue: No BLE devices detected

**Cause**: Kismet not configured for Bluetooth capture

**Solution**:
```bash
# Check if Bluetooth interface exists
hciconfig

# Start Kismet with Bluetooth source
sudo kismet -c hci0:name=Bluetooth

# Verify in web interface: localhost:2501
```

---

### Issue: All BLE devices classified as "BLE Unknown"

**Cause**: Manufacturer IDs not in Kismet database

**Debugging**:
```python
from secure_database import SecureKismetDB

with SecureKismetDB('Kismet-XXX.kismet') as db:
    devices = db.get_ble_devices_by_time_range(0)
    for d in devices[:5]:
        print(f"MAC: {d['mac']}, Manufacturer: {d.get('manufacturer')}, Name: {d.get('name')}")
```

**Solution**: Add missing manufacturers to `cyt_constants.py`

---

### Issue: Flipper Zero can't see devices that Kismet sees

**Cause**: Different scanning methods

**Explanation**:
- **Kismet**: Passive monitoring (sees all advertisements)
- **Flipper Zero**: Active scanning (devices must be advertising)

**Solution**: Use both tools together for complete coverage

---

## Security Considerations

### Data Privacy

**Your system now captures BLE data**:
- MAC addresses (can identify individuals)
- Device names (may contain personal info)
- Manufacturer IDs (reveal device ownership)
- Service UUIDs (reveal health data capabilities)

**Legal implications**:
- ✅ **Legal**: Monitoring your own property/vehicles
- ✅ **Legal**: Pentesting your own devices
- ❌ **Illegal**: Monitoring others without consent
- ❌ **Illegal**: Tracking individuals in public spaces

**Best practices**:
- Only analyze your own Kismet captures
- Don't share raw database files (contain PII)
- Sanitize reports before sharing (redact MACs)
- Use for defensive purposes only

---

### Responsible Disclosure

If you discover a vulnerability in a BLE device:

1. **Don't exploit it**: Testing on your own devices only
2. **Document the issue**: Screenshots, logs, reproduction steps
3. **Contact the vendor**: security@ email or bug bounty program
4. **Wait for patch**: Give vendor 90 days to fix
5. **Public disclosure**: After patch or 90 days

---

## Resources

### Documentation
- [Flipper Zero Guide](./FLIPPER_ZERO_GUIDE.md) - Your comprehensive Flipper integration
- [CLAUDE.md](./CLAUDE.md) - Full project architecture documentation
- [config.json](./config.json) - All configurable thresholds

### External Resources
- [Bluetooth Spec - Assigned Numbers](https://www.bluetooth.com/specifications/assigned-numbers/)
- [Kismet Bluetooth Documentation](https://www.kismetwireless.net/docs/readme/datasources_bluetooth/)
- [Sniffle BLE Sniffer](https://github.com/nccgroup/Sniffle)
- [BLE Security Best Practices](https://www.bluetooth.com/learn-about-bluetooth/key-attributes/bluetooth-security/)

---

## Credits & Acknowledgments

**Research**: BLEshark nano analysis via Gemini research agent
**Development**: Built with Claude Code (claude.ai/code)
**Testing**: Your Flipper Zero and Kismet setup
**Inspiration**: Real-world wireless surveillance threats

---

## What You Learned

### Technical Skills
✅ BLE protocol fundamentals (manufacturer IDs, UUIDs, advertising)
✅ Device classification algorithms (priority-based detection)
✅ Secure database queries (parameterized statements, context managers)
✅ Surveillance detection patterns (persistence scoring, multi-location tracking)
✅ Python defensive coding (None checks, default values, exception handling)

### Cybersecurity Concepts
✅ Defense in depth (layered detection)
✅ Trust hierarchies (hardware > protocol > user data)
✅ Graceful degradation (fallback methods)
✅ False positive/negative trade-offs
✅ Threat modeling (prioritize drones > trackers > wearables)

### Practical Tools
✅ Kismet BLE monitoring
✅ Flipper Zero BLE pentesting
✅ Python for wireless security
✅ SQLite database analysis
✅ Git workflow (feature branches, commits)

---

## Conclusion

You now have a **fully operational BLE surveillance detection system** integrated into Chasing Your Tail. Your system can detect:

- Hidden AirTags tracking your vehicle
- DJI drones following you
- Persistent wearables revealing your location
- Unknown BLE devices appearing across multiple locations

**This is a significant cybersecurity capability.** Most people have no idea how many BLE devices are tracking them. You now have the tools to find out.

**Keep learning, stay curious, and use these tools responsibly!** 🦊

---

**Questions?** Review the code comments, check the guides, or experiment with the Flipper Zero integration.

**Next challenge**: Build your own nRF52840 + Sniffle setup for even more advanced BLE MITM attacks! 🚀
