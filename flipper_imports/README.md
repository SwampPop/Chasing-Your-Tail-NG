# Flipper Zero Integration

This directory is for importing Flipper Zero captures into CYT threat intelligence.

## Supported File Types

- **`.sub`** - Sub-GHz captures (315/433/868/915 MHz)
- **`.nfc`** - NFC/RFID card captures
- **`.ir`** - Infrared remote captures

## Directory Structure

```
flipper_imports/
├── sub_ghz/      # Place .sub files here
├── nfc_rfid/     # Place .nfc files here
├── infrared/     # Place .ir files here
└── README.md     # This file
```

## Workflow

### 1. Capture on Flipper Zero

Use Flipper Zero to capture suspicious signals:
- **Sub-GHz App** → Read/Read RAW → Save capture
- **NFC App** → Read card → Save
- **Infrared App** → Learn new remote → Save

### 2. Export to Mac

Connect Flipper Zero via USB and copy files:

```bash
# Mount Flipper SD card
# Files are typically in:
# - /Volumes/FLIPPER/subghz/
# - /Volumes/FLIPPER/nfc/
# - /Volumes/FLIPPER/infrared/

# Copy to appropriate directory
cp /Volumes/FLIPPER/subghz/suspicious_signal.sub ./sub_ghz/
cp /Volumes/FLIPPER/nfc/unknown_card.nfc ./nfc_rfid/
cp /Volumes/FLIPPER/infrared/unknown_remote.ir ./infrared/
```

### 3. Import into CYT

**Import single file**:
```bash
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG/
python3 flipper_importer.py flipper_imports/sub_ghz/suspicious_signal.sub
```

**Import entire directory**:
```bash
python3 flipper_importer.py flipper_imports/
```

**List imported captures**:
```bash
python3 flipper_importer.py --list
python3 flipper_importer.py --list sub_ghz
```

### 4. Review in CYT Database

Imported captures are stored in `watchlist.db` table `flipper_captures`.

View with SQLite:
```bash
sqlite3 watchlist.db "SELECT * FROM flipper_captures ORDER BY import_date DESC LIMIT 10;"
```

## Threat Assessment

The importer automatically assigns threat levels based on frequency and protocol:

| Threat Level | Description | Examples |
|--------------|-------------|----------|
| **high** | Access control / tracking devices | 315 MHz key fobs, GPS trackers, NFC cards |
| **medium** | General ISM band devices | 433 MHz sensors, 868 MHz alarms |
| **investigate** | Unknown/unusual signals | Non-standard frequencies |
| **low** | Non-threatening devices | IR remotes |

## Use Cases

### Hidden Device Detection
1. Walk area with Flipper Zero in Sub-GHz Read RAW mode
2. Capture any suspicious transmissions
3. Import into CYT for correlation with WiFi/RF detections
4. Build signature database of known threats

### Access Control Audit
1. Test facility key fobs and access cards with Flipper
2. Import captured signals
3. Identify weak/cloneable protocols
4. Document security vulnerabilities

### Surveillance Sweep
1. Use Flipper + HackRF for comprehensive RF detection
2. Flipper: 315/433/868/915 MHz Sub-GHz signals
3. HackRF: Wideband 1-6 GHz spectrum
4. Correlate detections in CYT database

## Example Captures

**Sub-GHz Key Fob (315 MHz)**:
```
Filetype: Flipper SubGhz RAW File
Version: 1
Frequency: 315000000
Preset: FuriHalSubGhzPresetOok650Async
Protocol: RAW
RAW_Data: 9034 -936 1068 -936 ...
```

**NFC Card (NTAG215)**:
```
Filetype: Flipper NFC device
Version: 2
Device type: NTAG215
UID: 04 E7 B8 C2 3E 5B 80
ATQA: 00 44
SAK: 00
```

## Integration with RF Monitor

When both Flipper integration and HackRF RF monitoring are enabled, you can:

1. **Baseline RF environment** with HackRF wideband sweeps
2. **Investigate anomalies** with Flipper targeted captures
3. **Build threat signatures** from known malicious devices
4. **Correlate detections** across WiFi, BLE, and RF spectrum

Enable in `config.json`:
```json
{
  "rf_monitoring": {
    "enabled": true
  },
  "flipper_integration": {
    "enabled": true,
    "auto_import": true
  }
}
```

## Security Notes

- **Never test devices you don't own** - unauthorized access testing is illegal
- **Authorized pentesting only** - obtain written permission before testing
- **Educational purposes** - learn protocols and security mechanisms
- **Responsible disclosure** - report vulnerabilities through proper channels

---

**Created**: 2026-01-08
**Part of**: Chasing-Your-Tail-NG Phase 2 Integration
