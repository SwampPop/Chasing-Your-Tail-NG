# Flipper Zero Integration Guide
## Using Flipper Zero with Chasing Your Tail BLE Detection

This guide explains how to use your Flipper Zero alongside Kismet for comprehensive BLE surveillance detection.

---

## Overview

Your **Flipper Zero** is a powerful BLE pentesting tool that complements Kismet perfectly:

- **Flipper Zero**: Active BLE sniffing, device enumeration, and attack testing
- **Kismet**: Passive long-term BLE monitoring and database storage
- **Chasing Your Tail**: Surveillance pattern analysis across both data sources

---

## Flipper Zero BLE Capabilities

Your Flipper Zero can:

✅ **Scan for BLE devices** - Discover all nearby BLE advertisers
✅ **Read GATT services** - Enumerate device characteristics and UUIDs
✅ **Capture advertisements** - Record BLE advertising packets
✅ **Perform Bad-BT attacks** - Test keystroke injection vulnerabilities
✅ **Spam BLE beacons** - Test detection of beacon flooding attacks

❌ **Cannot do (hardware limitations)**:
- Full packet sniffing of encrypted BLE connections (requires nRF52840 + Sniffle)
- Multi-channel simultaneous capture (single radio limitation)
- Long-range BLE capture (limited antenna)

---

## Workflow: Flipper Zero + Kismet + CYT

###  Option 1: Parallel Monitoring (Recommended)

Use both tools simultaneously for maximum coverage:

```bash
# Terminal 1: Start Kismet for passive monitoring
sudo ./start_kismet_clean.sh wlan0mon

# Meanwhile: Use Flipper Zero to actively enumerate devices
# Flipper Zero: Bluetooth -> Scan -> Save discovered devices

# Terminal 2: After data collection, run CYT analysis
python3 surveillance_analyzer.py --kismet-dir .
```

**Why this works:**
- Kismet captures **all** BLE traffic passively (doesn't alert targets)
- Flipper Zero actively queries devices for **detailed** GATT information
- CYT analyzes Kismet data for **persistence patterns** over time

---

### Option 2: Flipper Zero Log Import (Advanced)

If you capture BLE data with Flipper Zero, you can manually import it into Kismet format:

#### Step 1: Export Flipper Zero Scan Results

1. On Flipper Zero: **Bluetooth → Scan**
2. Let it run for 5-10 minutes in target area
3. Save results to SD card: **Menu → Save**
4. Connect Flipper to computer via USB
5. Copy `.txt` scan log from SD card

#### Step 2: Convert to Kismet-Compatible Format

**Note**: Flipper Zero logs are plain text, not Kismet SQLite format. You'll need to manually add entries.

Create a Python script to parse Flipper logs:

```python
# flipper_to_cyt.py
import json
from surveillance_detector import SurveillanceDetector
from ble_classifier import BLEClassifier
import time

def parse_flipper_log(log_path):
    """Parse Flipper Zero BLE scan log"""
    devices = []

    with open(log_path, 'r') as f:
        for line in f:
            # Flipper format: "MAC: XX:XX:XX:XX:XX:XX, Name: DeviceName, RSSI: -XX"
            if line.startswith('MAC:'):
                parts = line.split(',')
                mac = parts[0].replace('MAC:', '').strip()
                name = parts[1].replace('Name:', '').strip() if len(parts) > 1 else ''

                devices.append({
                    'mac': mac,
                    'name': name,
                    'manufacturer': None,  # Flipper doesn't capture this in basic scan
                    'uuid_list': [],
                    'last_time': time.time()
                })

    return devices

# Usage
detector = SurveillanceDetector({})
classifier = BLEClassifier()

flipper_devices = parse_flipper_log('flipper_scan.txt')

for device in flipper_devices:
    device_type = classifier.classify_device(device)
    if classifier.is_likely_surveillance_device(device_type):
        detector.add_device_appearance(
            mac=device['mac'],
            timestamp=device['last_time'],
            location_id='flipper_scan',
            device_type=device_type.value
        )

# Run analysis
suspicious = detector.analyze_surveillance_patterns()
print(f"Found {len(suspicious)} suspicious devices")
```

---

## Flipper Zero Attack Testing

### Test 1: BLE Beacon Spam Detection

**Goal**: Verify CYT detects beacon flooding attacks

```
Flipper Zero Steps:
1. Bluetooth → BLE Spam → Apple
2. Let it run for 30 seconds
3. Stop spam

Kismet Steps:
1. sudo ./start_kismet_clean.sh wlan0mon
2. Monitor for 30 seconds during spam

CYT Analysis:
python3 surveillance_analyzer.py
# Should detect multiple Apple manufacturer devices with high appearance rate
```

**Expected Result**: CYT should flag numerous Apple tracker detections

---

### Test 2: Bad-BT Keystroke Injection

**Goal**: Test if target Bluetooth keyboards are vulnerable

```
Flipper Zero Steps:
1. Bluetooth → Bad BT
2. Select target keyboard
3. Run test script

Verification:
- If successful: You're vulnerable to keystroke injection
- Defense: Only pair Bluetooth keyboards in secure environments
```

---

### Test 3: GATT Service Enumeration

**Goal**: Identify surveillance-capable devices by their services

```
Flipper Zero Steps:
1. Bluetooth → Scan
2. Select a device
3. Read GATT Services → Note UUIDs

Manual Analysis:
- UUID 180D (Heart Rate) = Fitness tracker
- UUID FD6F (Find My) = Apple AirTag
- UUID 1816 (Cycling) = Sports wearable
```

**Use this to train your classification:**
- Update `ble_classifier.py` TRACKER_UUIDS or WEARABLE_UUIDS
- Add newly discovered surveillance device UUIDs

---

## Flipper Zero + Portapack Integration

You mentioned your **Portapack H4M isn't functioning correctly**. Here's troubleshooting:

### Portapack Common Issues

**Problem**: Portapack won't boot or shows corrupted screen

**Solutions**:
1. **Flash latest firmware**: [Mayhem firmware](https://github.com/portapack-mayhem/mayhem-firmware/releases)
2. **Check SD card**: Reformat as FAT32, use quality SD card
3. **Power issue**: Ensure HackRF battery/power supply provides sufficient current
4. **Antenna**: Check SMA connection is tight

**Problem**: Can't capture BLE with Portapack

**Limitation**: Portapack (HackRF One) is **not optimized for BLE**:
- HackRF bandwidth (20 MHz) > BLE channel width (2 MHz) = inefficient
- Better for wide-spectrum SDR tasks, not BLE sniffing
- **Use Flipper Zero or nRF52840 for BLE instead**

### When to Use Portapack vs Flipper Zero

| Task | Best Tool | Reason |
|------|-----------|--------|
| BLE device scanning | **Flipper Zero** | Purpose-built BLE radio |
| BLE GATT enumeration | **Flipper Zero** | Native BLE stack |
| BLE MITM attacks | **nRF52840 + Sniffle** | Requires connection following |
| Wide RF spectrum analysis | **Portapack** | SDR flexibility |
| GPS jamming detection | **Portapack** | Can monitor GPS L1 band |
| Drone RF detection | **Both** | Flipper for BLE, Portapack for 2.4GHz/5.8GHz |

---

## Real-World BLE Pentesting Scenarios

### Scenario 1: Detect Hidden AirTags

**Threat**: Someone placed an AirTag in your vehicle

**Detection**:
1. Drive your normal route for 1 week
2. Run Kismet continuously: `sudo ./start_kismet_clean.sh wlan0mon`
3. Run CYT analysis: `python3 surveillance_analyzer.py`
4. Look for: Apple manufacturer (0x004C) + Find My UUID (FD6F) + persistence across multiple locations

**Flipper Verification**:
1. Use Flipper Zero to actively scan for nearby AirTags
2. Bluetooth → Scan → Look for "Find My" devices
3. Move vehicle to different location and rescan
4. If same device appears = confirmed tracker

---

### Scenario 2: Identify Surveillance Drones

**Threat**: DJI drone following your movements

**Detection**:
1. Kismet captures BLE from DJI remote controller (manufacturer 0x0B41)
2. CYT detects device appearing at multiple locations where you appear
3. High persistence score triggers alert

**Flipper Verification**:
1. When you suspect drone nearby, use Flipper: Bluetooth → Scan
2. Look for "DJI" in device names or manufacturer data
3. Read GATT services to confirm drone model

---

### Scenario 3: Fitness Tracker Privacy Audit

**Goal**: See if your own wearable leaks location data

**Test**:
1. Wear your Fitbit/Garmin for normal daily activities
2. Run Kismet in background
3. After 24 hours: `python3 surveillance_analyzer.py`
4. Search for your device MAC address
5. Observe: CYT will show every location you visited (proves you're trackable!)

**Privacy Fix**:
- Disable Bluetooth when not needed
- Use BLE privacy features (MAC randomization) if available

---

## Defensive Measures

### Protect Against BLE Surveillance

1. **Enable MAC Randomization**: iOS/Android randomize BLE MACs by default
2. **Disable Bluetooth**: When not actively using devices
3. **Use CYT Regularly**: Run weekly scans to detect persistent trackers
4. **Physical Inspection**: Check vehicle/belongings for hidden AirTags
5. **Faraday Bags**: Store devices in RF-blocking bags when traveling

### Detect BLE Attacks

Your CYT system now alerts you to:
- ✅ Persistent BLE trackers (AirTags, SmartTags)
- ✅ BLE drones following you
- ✅ Wearables with unusual persistence patterns
- ✅ Unknown BLE devices appearing across multiple locations

---

## Advanced: Building Your Own BLE Sniffer

If you want to go beyond Flipper Zero, build an **nRF52840 + Sniffle** setup:

### Hardware Needed
- nRF52840 USB Dongle ($10 from Adafruit/Nordic)
- Computer with Linux

### Setup
```bash
# Install Sniffle
git clone https://github.com/nccgroup/Sniffle.git
cd Sniffle/python_cli
pip3 install -r requirements.txt

# Flash firmware to nRF52840
cd ../fw
# Follow Nordic flashing instructions

# Run sniffer
python3 sniff_receiver.py -l  # Listen mode

# Import captures into Wireshark
python3 sniff_receiver.py -o capture.pcap
wireshark capture.pcap
```

**Advantages over Flipper Zero:**
- Captures ALL advertising channels simultaneously (Flipper only one at a time)
- Can follow BLE connections and decrypt with captured keys
- Wireshark integration for deep packet analysis

---

## Troubleshooting

### Flipper Zero Not Detecting Devices

**Problem**: Flipper scan finds no devices

**Solutions**:
1. Update Flipper firmware: Settings → System → Update
2. Ensure Bluetooth is enabled: Settings → Bluetooth
3. Try different scanning modes: Bluetooth → Scan → Options
4. Check range: BLE range is ~10-30 meters, move closer

### Kismet Not Capturing BLE

**Problem**: No BLE devices in Kismet database

**Solutions**:
1. Ensure Kismet configured for Bluetooth: `sudo kismet -c hci0:name=Bluetooth`
2. Check if your wireless adapter supports BLE (most don't!)
3. Use external Bluetooth adapter: `lsusb | grep Bluetooth`
4. Enable Bluetooth in Kismet config: `/etc/kismet/kismet.conf`

### CYT Not Classifying BLE Devices

**Problem**: All BLE devices show as "BLE Unknown"

**Debugging**:
1. Check if manufacturer ID is captured:
   ```python
   from secure_database import SecureKismetDB
   with SecureKismetDB('Kismet-XXX.kismet') as db:
       devices = db.get_ble_devices_by_time_range(0)
       for d in devices:
           print(d['manufacturer'])
   ```

2. Add manufacturer IDs to `cyt_constants.py`
3. Update `ble_classifier.py` with new device signatures

---

## Next Steps

1. ✅ Test BLE detection with your Flipper Zero
2. ✅ Run your first surveillance analysis: `python3 surveillance_analyzer.py --demo`
3. ✅ Experiment with BLE beacon spam detection
4. ✅ Build nRF52840 sniffer for advanced capture (optional)
5. ✅ Contribute new device signatures back to the project!

---

## Resources

- [Flipper Zero BLE Documentation](https://docs.flipperzero.one/bluetooth)
- [Kismet Bluetooth Support](https://www.kismetwireless.net/docs/readme/datasources_bluetooth/)
- [Sniffle BLE Sniffer](https://github.com/nccgroup/Sniffle)
- [BLE Security Guide](https://www.bluetooth.com/learn-about-bluetooth/key-attributes/bluetooth-security/)
- [Your CYT BLEshark Research](./BLESHARK_RESEARCH.md) - Full BLE pentesting hardware comparison

---

**Happy Hunting! 🦊**

*Remember: Only test on networks/devices you own or have explicit authorization to test.*
