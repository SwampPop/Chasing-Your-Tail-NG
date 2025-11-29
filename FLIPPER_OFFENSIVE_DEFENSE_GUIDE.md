# Flipper Zero Offensive Defense Guide
## Think Like a Hacker to Defend Like a Pro

**Author**: Offensive Security Research via Gemini + InfoSec Homelab Guru
**Date**: November 2025
**Purpose**: Learn offensive wireless security techniques to build better defenses
**Legal Status**: ✅ Authorized pentesting of YOUR OWN systems only

---

## 🎯 Philosophy: The Offensive-Defensive Mindset

> "To defeat a hacker, you must think like a hacker." - Kevin Mitnick

This guide teaches you to **attack your own systems** so you can defend against real threats. Every vulnerability you find in your own network is one less vulnerability an attacker can exploit.

**Core Principles**:
1. **Curiosity Drives Learning**: Ask "how does this work?" about every wireless device
2. **Skepticism is Healthy**: Question every security claim (even your own)
3. **Authorization is Sacred**: Only test what you own or have written permission to test
4. **Document Everything**: Your future self (and lawyers) will thank you
5. **Share Responsibly**: Teach others to defend, don't enable attackers

---

## 📚 Table of Contents

1. [Your Arsenal](#your-arsenal)
2. [Firmware Selection Guide](#firmware-selection-guide)
3. [WiFi Marauder Setup](#wifi-marauder-setup)
4. [Dual Touch V2 Antenna](#dual-touch-v2-antenna)
5. [Protocol-by-Protocol Attack/Defense](#protocol-by-protocol-attackdefense)
6. [CYT Integration Workflows](#cyt-integration-workflows)
7. [8-Week Hacker Training Program](#8-week-hacker-training-program)
8. [Legal & Ethical Framework](#legal--ethical-framework)
9. [Troubleshooting](#troubleshooting)
10. [Quick Reference Commands](#quick-reference-commands)

---

## Your Arsenal

**Hardware You Have**:
- ✅ **Flipper Zero**: Multi-protocol pentesting tool (Sub-GHz, RFID, NFC, IR, GPIO, Bad USB)
- ✅ **Dual Touch V2 Antenna**: VHF/UHF tactical antenna (136-174 MHz, 400-470 MHz)
- ✅ **Portapack H4M**: HackRF-based SDR (1 MHz - 6 GHz) - *Currently non-functional*
- ✅ **Chasing Your Tail (CYT)**: BLE/WiFi surveillance detection system with Kismet

**What You'll Build**:
- 🔧 **WiFi Marauder** (ESP32 module): Deauth, packet capture, evil portals, beacon spam
- 🔧 **GPS Integration**: Wardriving with location correlation
- 🔧 **Automated Threat Response**: CYT detects → Flipper enumerates → Auto-report

**Capabilities Matrix**:

| Protocol | Flipper Native | With Marauder | With CYT | Portapack (Future) |
|----------|----------------|---------------|----------|---------------------|
| **Sub-GHz (315/433/868/915 MHz)** | ✅ Read/Replay | ❌ | ❌ | ✅ Wide scan |
| **WiFi 2.4 GHz** | ❌ | ✅ Full pentest | ✅ Passive detect | ✅ Spectrum analysis |
| **WiFi 5 GHz** | ❌ | ❌ | ✅ Passive detect | ✅ Spectrum analysis |
| **BLE** | ✅ Scan/Spam | ❌ | ✅ Surveillance detect | ✅ Spectrum analysis |
| **RFID 125 kHz** | ✅ Read/Write/Emulate | ❌ | ❌ | ❌ |
| **NFC 13.56 MHz** | ✅ Read/Write/Emulate | ❌ | ❌ | ❌ |
| **Infrared** | ✅ Read/Transmit | ❌ | ❌ | ❌ |
| **iButton** | ✅ Read/Write/Emulate | ❌ | ❌ | ❌ |
| **Bad USB** | ✅ Keystroke injection | ❌ | ❌ | ❌ |

---

## Firmware Selection Guide

### Quick Recommendation

**For You (Serious Pentesting + Stability)**:
- **Primary Choice**: **Unleashed Firmware**
- **Reason**: Best balance of advanced features + stability + active development
- **Key Features**: Full spectrum, rolling code testing, stable community apps

**Alternative (Max Features, Accept Crashes)**:
- **Secondary Choice**: **RogueMaster Firmware**
- **Reason**: Most apps pre-installed, bleeding edge features
- **Trade-off**: Less stable, occasional crashes

### Detailed Firmware Comparison

| Feature | Official | Unleashed ⭐ | RogueMaster | Xtreme (Discontinued) |
|---------|----------|-------------|-------------|------------------------|
| **Legal Compliance** | ✅ FCC Certified | ⚠️ Use Responsibly | ⚠️ Use Responsibly | ⚠️ N/A |
| **Stability** | 🟢 Excellent | 🟢 Very Good | 🟡 Good | 🟢 Very Good |
| **Update Frequency** | Regular | Regular | **Very Active (Nov 28, 2025)** | ❌ Discontinued Nov 2024 |
| **Sub-GHz Spectrum** | Regional Limits | **Full Unlock** | **Full Unlock** | Full Unlock |
| **Rolling Code Support** | Read Only | **Enhanced Testing** | **Enhanced Testing** | Enhanced Testing |
| **Pre-installed Apps** | Core Only | Stable Community | **Maximum Variety** | Maximum (legacy) |
| **WiFi Marauder Compatible** | ❌ Need GPIO app | ✅ Yes | ✅ Yes | ✅ Yes |
| **Custom Animations** | No | Limited | ✅ Extensive | ✅ Extensive (legacy) |
| **Installation Difficulty** | Beginner | Beginner | Beginner-Int | Intermediate |

### Installation Instructions

**Option 1: Web Installer (Easiest)**
```bash
# 1. Visit firmware project page
# Unleashed: https://github.com/DarkFlippers/unleashed-firmware
# RogueMaster: https://github.com/RogueMaster/flipperzero-firmware-wPlugins

# 2. Click "Web Updater" link

# 3. Connect Flipper via USB

# 4. Select firmware version → Flash

# 5. Wait for completion (2-5 minutes)

# 6. Flipper reboots with new firmware
```

**Option 2: qFlipper Desktop App**
```bash
# Download qFlipper: https://flipperzero.one/update

# Linux:
wget https://update.flipperzero.one/latest/qFlipper-x86_64.AppImage
chmod +x qFlipper-x86_64.AppImage
./qFlipper-x86_64.AppImage

# macOS:
# Download .dmg from website, install

# Windows:
# Download installer.exe, run

# Usage:
# 1. Open qFlipper
# 2. Connect Flipper
# 3. Install from file → Select .tgz firmware archive
# 4. Wait for flash completion
```

**Option 3: Manual DFU Mode (Recovery)**
```bash
# If Flipper is bricked or unresponsive:

# 1. Power off Flipper
# 2. Hold LEFT + BACK buttons
# 3. Plug in USB while holding
# 4. Screen stays black (DFU mode)
# 5. Flash with dfu-util:
sudo dfu-util -a 0 -s 0x08000000 -D flipper-z-f7-full.dfu

# 6. Unplug, power on - should boot to recovery
```

### Critical Discovery: Rolling Code Exploit (2024-2025)

⚠️ **EXTREME RISK**: Dark web firmware available for Flipper Zero that **completely bypasses rolling code security**.

**What This Means**:
- **Single Capture Attack**: Capture rolling code with one button press → Instantly usable
- **No Jamming Required**: Works from passive capture alone
- **Full Vehicle Control**: Lock, unlock, trunk - all key fob functions cloned
- **Affected Vehicles**: Chrysler, Dodge, Fiat, Ford, Hyundai, Jeep, Kia, Mitsubishi, Subaru

**Cost on Dark Web**: $1000+ for custom firmware

**Defense Implications**:
- **Rolling codes are NOT safe**: Previously considered secure, now fully compromised
- **Your car may be vulnerable**: Even modern vehicles with rolling codes
- **Test Yourself**:
  ```bash
  # With Unleashed/RogueMaster firmware:
  # 1. Flipper: Apps → Sub-GHz → Read → Capture key fob press
  # 2. Save capture
  # 3. Attempt replay (should fail with normal rolling code)
  # 4. If it WORKS → Your car is using broken rolling code variant
  ```

**Mitigation**:
- Check manufacturer for firmware updates to key fob
- Use physical steering wheel lock as backup
- Consider aftermarket immobilizer
- Park in secure locations

**Ethical Note**: We do **NOT** provide or endorse the dark web firmware. This is disclosed so you understand the threat landscape and can test your own vehicles' vulnerability.

---

## WiFi Marauder Setup

### What is WiFi Marauder?

WiFi Marauder is ESP32-based firmware that transforms your Flipper Zero into a powerful WiFi pentesting platform.

**Capabilities**:
- 📡 **Network Scanning**: Enumerate all WiFi APs, clients, channels
- 💥 **Deauthentication Attacks**: Force disconnect devices (test WPA2 vs WPA3 resilience)
- 📦 **Packet Capture**: Save traffic to PCAP for Wireshark/Kismet analysis
- 🎣 **Evil Portal**: Create fake captive portals (test phishing awareness)
- 📢 **Beacon Spam**: Flood with fake networks (test device handling)
- 🗺️ **War Driving**: Mobile WiFi mapping with GPS integration

### Hardware Shopping List

**Essential (Minimum Setup)**:
- [ ] **ESP32-S2 Mini Dev Board** ($8-12)
  - Recommended: ESP32-S2-DevKitC-1
  - Buy: Amazon, AliExpress, Adafruit
  - **Why S2**: Single UART connection (simpler wiring)

**Recommended (Full Setup)**:
- [ ] **ESP32-S2 with Built-in Display** ($15-25)
  - Pre-assembled Marauder boards available
  - No wiring needed - plug and play
  - Example: "ESP32 WiFi Marauder V4 with Screen"
- [ ] **MicroSD Card Adapter** ($3-5)
  - For saving large PCAP files
  - Solderless options available
- [ ] **GPS Module** ($8-15)
  - NEO-6M or better
  - For wardriving with geolocation

**Professional (All-in-One)**:
- [ ] **Marauder Kit with GPS + SD** ($35-50)
  - Complete pre-assembled module
  - Saves time, no soldering
  - Search: "Flipper Zero WiFi Devboard Marauder V6"

### Installation Method 1: Web Flasher (Easiest)

```bash
# 1. Visit Marauder web flasher (search "ESP32 Marauder web flasher")

# 2. Connect ESP32 to computer via USB

# 3. Hold BOOT button on ESP32, click "Connect" in web flasher

# 4. Select your board type:
#    - ESP32-S2 (recommended)
#    - ESP32 WROOM
#    - ESP32-C3

# 5. Select firmware version:
#    - Latest stable recommended
#    - v0.13.x series (as of Nov 2025)

# 6. Click "Flash" → Wait 2-3 minutes

# 7. When complete, ESP32 will reboot with Marauder firmware

# 8. Test:
#    - Connect ESP32 to Flipper GPIO
#    - Flipper: Apps → ESP32 WiFi Marauder (install from catalog if missing)
#    - Should show "Connected" status
```

### Installation Method 2: Flasher Script

```bash
# Download ESP32 Marauder Flasher
git clone https://github.com/justcallmekoko/ESP32Marauder.git
cd ESP32Marauder/esp32_marauder_flasher

# Install dependencies
pip3 install esptool pyserial

# Run flasher
python3 esp32_marauder_flasher.py

# Follow prompts:
# - Select board type
# - Select COM port (/dev/ttyUSB0 on Linux, COM3 on Windows)
# - Confirm flash → Wait for completion

# Verify installation:
# Connect ESP32 to computer via USB
# Open serial monitor (115200 baud):
screen /dev/ttyUSB0 115200

# Type: help
# Expected output: Marauder command list
```

### Wiring Guide: ESP32 to Flipper Zero

**For ESP32 WROOM (Classic)**:

```
ESP32 WROOM          →    Flipper Zero GPIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PIN 27 (TX0)         →    PIN 14 (RX)     [Orange wire]
PIN 28 (RX0)         →    PIN 13 (TX)     [Yellow wire]
PIN 17 (GND)         →    PIN 18 (GND)    [Black wire]
PIN 16 (3v3)         →    PIN 9 (3v3)     [Red wire] - OPTIONAL*

*Note: 3.3V from Flipper may be insufficient for ESP32
Recommendation: Power ESP32 via USB (5V 1A) separately
```

**For ESP32-S2 (Simplified)**:

```
ESP32-S2             →    Flipper Zero GPIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TX                   →    PIN 14 (RX)     [Orange wire]
RX                   →    PIN 13 (TX)     [Yellow wire]
GND                  →    PIN 18 (GND)    [Black wire]
(Power via USB 5V separately)
```

**CRITICAL**: TX and RX must **cross** (ESP32 TX → Flipper RX, ESP32 RX → Flipper TX)

### GPIO Pin Reference (Flipper Zero)

```
Flipper GPIO Pinout (Top View):
 ___________________________
| 1  3  5  7  9  11 13 15 17|
| 2  4  6  8  10 12 14 16 18|
 ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾

Pin  Function    Use
1    3.3V        Power out (limited current)
2    A7          GPIO
...
9    3.3V        Power out
13   TX (USART)  → ESP32 RX
14   RX (USART)  ← ESP32 TX
15   PC3         GPIO
16   C1          GPIO
17   C0          GPIO
18   GND         Ground
```

### Testing Your Marauder Setup

```bash
# 1. Connect ESP32 to Flipper (follow wiring above)

# 2. Power ESP32 via USB (recommended)

# 3. Flipper: Apps → ESP32 WiFi Marauder
#    If app missing: Apps → Apps Catalog → Search "marauder" → Install

# 4. Check connection:
#    Marauder app → Should show "Connected" or firmware version

# 5. Test AP scan:
#    Marauder → Scan → APs
#    Expected: List of WiFi networks with BSSID, SSID, channel, RSSI

# 6. Test deauth (on YOUR network only):
#    Marauder → Attack → Deauth → Select your AP
#    Duration: 10 seconds
#    Expected: Devices briefly disconnect (test with video stream)

# 7. Test PCAP capture:
#    Insert MicroSD card into ESP32 (if adapter installed)
#    Marauder → Sniff → Start → Stop after 30 seconds
#    Check SD card: capture.pcap should exist

# 8. Import PCAP to Wireshark:
#    Remove SD card → Insert into computer
#    wireshark capture.pcap
#    Expected: 802.11 packets visible
```

---

## Dual Touch V2 Antenna

### Research Findings

The "Dual Touch V2" appears to be a generic designation for **dual-band VHF/UHF tactical antennas**. Based on research, here's what you likely have and how to use it effectively.

### Typical Specifications

**Frequency Coverage**:
- **VHF Band**: 136-174 MHz (amateur radio 2m band)
- **UHF Band**: 400-470 MHz (amateur radio 70cm band)
- **Note**: Does NOT typically cover 2.4 GHz WiFi or Sub-GHz 315/433/868/915 MHz

**Physical Characteristics**:
- **Connector**: SMA-Female (standard)
- **Length**: 15-20 inches (38-50 cm) typically
- **Construction**: Stainless steel telescoping or flexible whip
- **Gain**: 2-3 dBi (VHF), 3-5 dBi (UHF)
- **Impedance**: 50Ω
- **Max Power**: 10-20 watts

### Compatibility with Your Devices

| Device | Connector | Compatible? | Adapter Needed | Use Case |
|--------|-----------|-------------|----------------|----------|
| **Flipper Zero** | RP-SMA (reverse polarity) | ⚠️ Maybe | **Yes - SMA to RP-SMA adapter** | Sub-GHz if frequencies overlap |
| **Portapack H4M** | SMA-Male | ✅ Yes | No (if your antenna is SMA-Female) | Wide spectrum reception |
| **HackRF One** | SMA-Male | ✅ Yes | No | General SDR work |
| **WiFi Adapter** | No external antenna | ❌ No | N/A | Use WiFi-specific antenna |

### Frequency Coverage Analysis

**What Your Antenna Covers**:
- ✅ **VHF 136-174 MHz**: Amateur radio, some commercial radios
- ✅ **UHF 400-470 MHz**: Amateur radio 70cm, some IoT devices
- ❌ **Sub-GHz 315 MHz**: NOT covered (outside range)
- ❌ **Sub-GHz 433 MHz**: COVERED! ✅ (within UHF range)
- ❌ **Sub-GHz 868/915 MHz**: NOT covered (above range)
- ❌ **2.4 GHz WiFi/BLE**: NOT covered (much higher frequency)

**Practical Implication**:
- Your antenna will work for **433 MHz** Sub-GHz devices (wireless doorbells, some garage openers, weather stations)
- Will NOT work for 315 MHz (US garage doors), 915 MHz (LoRa, Z-Wave)
- For 2.4 GHz WiFi attacks, you need a **separate 2.4 GHz antenna** (duck antenna, omnidirectional)

### Connection to Flipper Zero

```bash
# Required: SMA to RP-SMA adapter
# Cost: $5-8 on Amazon
# Search: "SMA Female to RP-SMA Male adapter"

# Connection:
# 1. Screw adapter onto Flipper's RP-SMA connector
# 2. Screw Dual Touch V2 antenna onto adapter
# 3. Flipper now uses external antenna for Sub-GHz

# Test:
# Flipper: Apps → Sub-GHz → Frequency Analyzer
# Scan 433 MHz range
# Expected: Stronger signals compared to stock antenna
```

### Use Cases for Your Antenna

**Scenario 1: Enhanced Sub-GHz Reception (433 MHz)**
```bash
# Testing wireless doorbell range:
# Stock antenna: Detectable from ~15 meters
# Dual Touch V2: Detectable from ~40+ meters (estimated)

# Flipper: Apps → Sub-GHz → Read RAW → Frequency 433.92 MHz
# Press doorbell from increasing distances
# Document: Maximum detection range
```

**Scenario 2: Portapack Spectrum Scanning**
```bash
# Once Portapack H4M is repaired:
# Connect Dual Touch V2 to Portapack SMA port
# Portapack: Spectrum Analyzer → 400-470 MHz scan
# Enhanced reception of UHF signals (amateur radio, commercial)

# Use case:
# - Identify unknown UHF transmissions in your environment
# - Hunt for hidden transmitters
# - Map UHF spectrum usage
```

**Scenario 3: Directional Signal Hunting**
```bash
# Flexible antenna can be positioned for basic directionality
# Technique:
# 1. Connect antenna to Portapack
# 2. Rotate antenna while monitoring signal strength
# 3. Strongest signal = direction of transmitter

# Use case:
# - Locate hidden BLE tracker by triangulation
# - Find source of unknown Sub-GHz transmission
# - War driving with directional sensitivity
```

### Recommended Additional Antennas

Since your Dual Touch V2 doesn't cover all frequencies, consider:

**For Flipper Zero Sub-GHz**:
- **ANT500** (75 MHz - 1 GHz telescopic)
  - Cost: $15-25
  - Covers 315/433/868/915 MHz
  - Buy: Great Scott Gadgets, Amazon

**For WiFi Marauder (2.4 GHz)**:
- **2.4 GHz Duck Antenna** (5-7 dBi)
  - Cost: $8-12
  - SMA connector
  - Attach to ESP32 dev board (if has U.FL/SMA connector)

**For 5 GHz WiFi** (if Portapack repaired):
- **Dual-band 2.4/5 GHz omnidirectional**
  - Cost: $15-20
  - Covers both WiFi bands

---

## Protocol-by-Protocol Attack/Defense

For each wireless protocol, learn the offensive technique, then build defenses.

### Sub-GHz (315/433/868/915 MHz)

**🔴 OFFENSIVE: Replay Attack**

```bash
# Target: YOUR garage door opener

# Attack Steps:
# 1. Flipper: Apps → Sub-GHz → Read RAW
# 2. Set frequency (common: 315.000 MHz or 433.920 MHz)
# 3. Press READ
# 4. Press garage remote (door opens)
# 5. Flipper captures signal → Save to SD card
# 6. Later: Apps → Sub-GHz → Saved Signals → Select capture → Transmit
# 7. Door opens again (if using fixed code) ← VULNERABLE

# Expected outcome:
# - Fixed code system: Door opens (VULNERABLE)
# - Rolling code system: Door ignores replay (SECURE)
```

**🔵 DEFENSIVE: Rolling Code Implementation**

```bash
# Test your garage door:
# 1. Capture signal with Flipper
# 2. Replay immediately → Does it work?
# 3. Replay 5 minutes later → Does it work?
# 4. Replay after pressing real remote → Does it work?

# If ANY replay works → VULNERABLE (fixed code)

# Remediation:
# Option 1: Upgrade to Security+ 2.0 opener
# - Chamberlain B970, LiftMaster 8500W
# - Cost: $200-300
# - Rolling code with enhanced security

# Option 2: Add secondary security
# - Physical lock on garage door
# - Security camera with alerts
# - Alarm system integration

# Verify fix:
# Repeat replay attack → Should fail
```

**Additional Defenses**:
- **Time-based validation**: Codes expire after 30 seconds
- **Challenge-response**: Two-way authentication
- **Signal monitoring**: Detect duplicate transmissions
- **Encrypted protocols**: Use AES encryption for commands

---

### BLE (Bluetooth Low Energy)

**🔴 OFFENSIVE: Unauthorized GATT Access**

```bash
# Target: YOUR smart light bulb

# Attack Steps:
# 1. Flipper: Bluetooth → BLE Scanner → Wait for devices
# 2. Select your smart bulb from list
# 3. Attempt to Connect (without pairing)
# 4. If successful: Enumerate GATT services
# 5. Read characteristics (e.g., brightness, color)
# 6. Write characteristics (set brightness to 100%, change color)

# Expected outcome:
# INSECURE device: Connects without pairing, full control
# SECURE device: Requires pairing, rejects unauthorized access
```

**🔵 DEFENSIVE: BLE Security Hardening**

```bash
# Test ALL your BLE devices:
# For each device (lights, locks, sensors, speakers):

# 1. Attempt connection without pairing
# 2. Document results:
#    Device: Philips Hue Bulb
#    Connection without pairing: FAILED ✓
#    Pairing method: Numeric comparison ✓
#    Encryption: Yes ✓
#    Assessment: SECURE

#    Device: Generic Smart Bulb
#    Connection without pairing: SUCCESS ✗
#    Pairing method: None ✗
#    Encryption: No ✗
#    Assessment: INSECURE - Replace or isolate

# Remediation for insecure devices:
# Option 1: Replace with secure devices (e.g., Philips Hue, not generic)
# Option 2: Isolate to separate VLAN (IoT network, no access to main network)
# Option 3: Disable remote access, local control only
```

**Additional Defenses**:
- **MAC Randomization**: Enable on phones (Settings → Privacy → Bluetooth)
- **Secure Pairing**: Use numeric comparison, not "Just Works"
- **Service Minimization**: Disable unused GATT services
- **Regular Firmware Updates**: Patch known vulnerabilities

---

### WiFi 2.4 GHz

**🔴 OFFENSIVE: Deauthentication Attack**

```bash
# Target: YOUR WiFi network
# Purpose: Test WPA2 vs WPA3 resilience

# Attack Steps:
# 1. Marauder: Scan → APs → Select YOUR network
# 2. Marauder: Attack → Deauth → Target: Selected AP
# 3. Duration: 60 seconds
# 4. Monitor: Watch phone/laptop WiFi connection
# 5. Expected:
#    - WPA2 without PMF: Device disconnects ✗
#    - WPA2 with PMF: Device stays connected ✓
#    - WPA3: Device stays connected ✓

# Observe reconnection behavior:
# - Fast reconnection (<5 seconds) = Good implementation
# - Slow reconnection (>30 seconds) = Poor user experience
```

**🔵 DEFENSIVE: Protected Management Frames (PMF)**

```bash
# Enable PMF on your router:
# (Example for common routers, adjust for yours)

# Netgear:
# 1. http://192.168.1.1 → Admin login
# 2. Wireless → Advanced Security
# 3. Management Frame Protection: "Optional" or "Required"
# 4. Save → Test all devices still connect

# TP-Link:
# 1. http://192.168.0.1 → Admin login
# 2. Wireless → Wireless Security
# 3. Enable "Protected Management Frames (PMF)"
# 4. Options: Optional (recommended) or Required

# ASUS:
# 1. http://router.asus.com → Admin login
# 2. Wireless → Professional
# 3. Protected Management Frames: Optional

# Better: Upgrade to WPA3
# If router supports WPA3:
# 1. Wireless → Security
# 2. Security Mode: WPA3-Personal
# 3. Set strong password (20+ characters)
# 4. Save → All devices must support WPA3 (2019+)

# Verify protection:
# Repeat deauth attack
# Expected: Devices stay connected (PMF/WPA3 blocking deauth)
```

**🔴 OFFENSIVE: WPA2 Handshake Capture + Offline Crack**

```bash
# Attack Steps:
# 1. Marauder: Sniff → Capture PMKID/Handshake
# 2. Trigger: Deauth a client to force re-authentication
# 3. Wait: Client reconnects → Handshake captured
# 4. Save PCAP to MicroSD card
# 5. Transfer PCAP to computer
# 6. Convert to hashcat format:
hcxpcapngtool -o hash.hc22000 capture.pcap

# 7. Attempt crack with wordlist:
hashcat -m 22000 hash.hc22000 /usr/share/wordlists/rockyou.txt

# 8. Time to crack:
#    Weak password (8 chars, common): Minutes to hours
#    Medium password (12 chars, uncommon): Days to weeks
#    Strong password (20+ chars, random): INFEASIBLE (centuries)
```

**🔵 DEFENSIVE: Strong WPA3 Passwords**

```bash
# Password Strength Test:
# 1. Capture your own WiFi handshake
# 2. Run hashcat with rockyou.txt (14 million passwords)
# 3. If cracked → Password TOO WEAK

# Recommended Password Policy:
# - Minimum 20 characters
# - Mix of uppercase, lowercase, numbers, symbols
# - NOT based on dictionary words
# - NOT personal information (birthdates, names, etc.)

# Example STRONG passwords:
# Tr0ub4dor&3-Sky-Diving-Purple!Elephant (passphrase style)
# y8$mK2#nQ9@pL5&vR3!wX7^jC4 (random style)

# Password Manager Recommendation:
# Use password manager to generate and store WiFi password
# - Bitwarden (open source, free)
# - 1Password (paid, excellent UX)
# - KeePassXC (open source, offline)

# Implementation:
# 1. Generate 25-character random password in password manager
# 2. Set as WiFi password
# 3. Save to password manager
# 4. Share with family via QR code (Flipper can generate QR codes!)
# 5. Guests: Create separate guest network (different password, isolated VLAN)
```

**Additional WiFi Defenses**:
- **Hidden SSID**: Security through obscurity (minimal value, easily defeated)
- **MAC Filtering**: Whitelist allowed devices (easily spoofed, maintenance burden)
- **Network Segmentation**: Separate IoT, guest, main networks
- **Intrusion Detection**: Kismet continuous monitoring for rogue APs

---

### RFID (125 kHz Low Frequency)

**🔴 OFFENSIVE: Access Card Cloning**

```bash
# Target: YOUR gym membership card or access badge

# Attack Steps:
# 1. Flipper: RFID → Read
# 2. Hold card against Flipper (centered over dolphin logo)
# 3. Card type detected (e.g., EM4100, HID Prox)
# 4. Card ID extracted → Save to SD card
# 5. Flipper: RFID → Saved → Select card → Emulate
# 6. Hold Flipper against reader (emulating card in real-time)
# 7. Expected: Reader grants access (VULNERABLE)

# Permanent clone to physical card:
# 1. Purchase blank T5577 writable cards ($1-2 each on Amazon)
# 2. Flipper: RFID → Saved → Select card → Write to blank
# 3. Hold blank T5577 card against Flipper → Write complete
# 4. Test cloned card on reader → Should grant access
```

**🔵 DEFENSIVE: Encrypted RFID + Multi-Factor Auth**

```bash
# Identify your card type:
# 1. Flipper: RFID → Read → Check "Card type"

# INSECURE card types:
# - EM4100 (125 kHz) ← Trivially clonable
# - HID Prox (125 kHz) ← Clonable
# - Mifare Classic (13.56 MHz) ← Crypto broken, clonable

# SECURE card types:
# - Mifare DESFire EV2/EV3 ← AES encryption, strong
# - HID iCLASS SE/Seos ← Encrypted, challenge-response
# - LEGIC Advant ← Encrypted, secure

# If you have insecure card:
# Speak to building manager / IT security:
# "Our access badges use EM4100, which can be cloned in seconds.
#  I can demonstrate this vulnerability.
#  Recommend upgrading to Mifare DESFire EV2 for AES encryption."

# DIY Defenses (if can't upgrade cards):
# Option 1: Add PIN code
# - Retrofit keypad to existing reader
# - Require badge + 4-6 digit PIN
# - Cost: $100-300

# Option 2: RFID shielding
# - Store badge in Faraday sleeve when not in use
# - Prevents unauthorized proximity reads
# - Cost: $5-10 per sleeve

# Option 3: Dual-factor
# - Badge + biometric (fingerprint/face recognition)
# - More expensive but very secure
# - Cost: $500-2000 for biometric reader upgrade
```

---

### NFC (13.56 MHz High Frequency)

**🔴 OFFENSIVE: Credit Card Skimming**

```bash
# Target: YOUR OWN contactless credit/debit card
# Purpose: Understand data exposure

# Attack Steps:
# 1. Flipper: NFC → Read
# 2. Hold card against Flipper (centered)
# 3. EMV card detected → Data extracted:
#    - Card number (PAN): VISIBLE
#    - Expiration date: VISIBLE
#    - Cardholder name: VISIBLE
#    - CVV: NOT VISIBLE (stored separately in chip)
#    - PIN: NOT VISIBLE (never transmitted)

# Can this be used for fraud?
# NO - Online transactions require CVV (not on contactless)
# NO - In-person requires chip/PIN (contactless is limited to ~$50-100)

# However: Card number + expiration can be used for:
# - Social engineering (pretend to be cardholder)
# - Testing if card is valid
# - Identifying bank issuer

# Expected outcome:
# Demonstrates data exposure, but limited fraud risk
```

**🔵 DEFENSIVE: RFID-Blocking Wallets + Chip/PIN**

```bash
# Test your card's exposure:
# 1. Read your card with Flipper
# 2. Document what data is visible
# 3. Check: Does your card support contactless?
#    Look for: ((( ))) symbol on card

# Defenses:

# Option 1: RFID-blocking wallet
# - Faraday cage blocks NFC reads
# - Cost: $10-30 for wallet or card sleeves
# - Limitation: Only protects when in wallet

# Option 2: Disable contactless
# - Call bank, request non-contactless card
# - Or: Physically damage contactless antenna
#   (Note: May void warranty, proceed at own risk)

# Option 3: Use chip/PIN instead
# - Insert chip instead of tap
# - Requires PIN (stronger auth)
# - No data exposed to skimmers

# Option 4: Virtual cards
# - Use Apple Pay / Google Pay instead
# - Tokenization: Real card number never exposed
# - Each transaction uses unique token
# - Most secure option

# Best practice:
# Monitor credit card statements weekly for unauthorized charges
# Enable fraud alerts from bank (SMS/email for every transaction)
```

---

### Bad USB (Keystroke Injection)

**🔴 OFFENSIVE: Rubber Ducky Attack**

```bash
# Target: YOUR OWN computer (locked vs unlocked)

# Attack Steps:
# 1. Create harmless payload:
#    Flipper: Apps → Bad USB → Create new script
#    Content (macOS example):
#    ---
#    REM Test Bad USB vulnerability
#    DELAY 1000
#    GUI SPACE
#    DELAY 300
#    STRING calculator
#    DELAY 200
#    ENTER
#    STRING This computer is vulnerable to Bad USB!
#    ---

# 2. Save: /badusb/test_calc.txt

# 3. Test on UNLOCKED computer:
#    Flipper: Apps → Bad USB → test_calc.txt → Run
#    Expected: Calculator opens, message typed

# 4. Test on LOCKED computer:
#    Lock screen (Cmd+Ctrl+Q on macOS, Win+L on Windows)
#    Flipper: Apps → Bad USB → test_calc.txt → Run
#    Expected: Nothing happens (password prompt)

# Demonstrates:
# Unlocked computer = complete compromise in seconds
# Locked computer = no access
```

**🔵 DEFENSIVE: Lock Screen + USB Whitelisting**

```bash
# Defense Layer 1: Always Lock Screen
# Set aggressive auto-lock timeout:

# macOS:
# System Preferences → Security & Privacy → General
# - Require password: Immediately
# - Auto-lock: 2 minutes

# Windows:
# Settings → Personalization → Lock Screen
# - Screen timeout: 2 minutes
# - Require sign-in: When PC wakes

# Linux:
# Settings → Privacy → Screen Lock
# - Automatic: 2 minutes
# - Lock screen on suspend: Yes

# Defense Layer 2: Disable USB Autorun
# Windows:
# gpedit.msc → Computer Config → Admin Templates → Windows Components
# → AutoPlay Policies → Turn off AutoPlay: Enabled

# macOS / Linux:
# No autorun by default (good!)

# Defense Layer 3: USB Device Whitelisting
# Windows (with Endpoint Protection):
# - Device Control policies in Microsoft Defender
# - Only allow known USB devices
# - Block new HID devices

# Linux (udev rules):
# Create /etc/udev/rules.d/99-usb-whitelist.rules:
# SUBSYSTEM=="usb", ATTR{idVendor}=="1234", ATTR{idProduct}=="5678", MODE="0666"
# SUBSYSTEM=="usb", MODE="0000"
# (Only specific vendor/product allowed, all others blocked)

# Defense Layer 4: Physical USB Port Locks
# - Small locks that insert into USB ports
# - Prevents physical insertion
# - Cost: $15-30 for pack of 10
# - Use on: Servers, kiosks, unattended workstations

# Defense Layer 5: Endpoint Detection & Response (EDR)
# Software that detects rapid keystroke patterns:
# - CrowdStrike Falcon
# - SentinelOne
# - Carbon Black
# - Open source: OSQuery with custom rules

# Custom detection rule concept:
# Alert if >50 keyboard inputs in <5 seconds from new HID device
# Legitimate typing: ~5-10 keystrokes/second
# Bad USB: 100+ keystrokes/second
```

---

## CYT Integration Workflows

### Workflow 1: Parallel Passive + Active Monitoring

**Goal**: Use Kismet (passive) to detect all devices over time, Flipper (active) to enumerate details.

```bash
# Day 1-7: Passive Collection Phase
# =====================================

# Terminal 1: Start Kismet continuous monitoring
sudo ./start_kismet_clean.sh wlan0mon

# Let run 24/7 for 7 days
# Kismet captures ALL WiFi + BLE devices that appear

# Day 7: Analysis Phase
# =====================

# Step 1: Run CYT surveillance analysis
python3 surveillance_analyzer.py --kismet-dir .

# Review report for suspicious devices:
# - High persistence scores (0.8+)
# - Multiple location appearances
# - Unknown device types

# Example output:
# Device: AA:BB:CC:DD:EE:FF
# Type: BLE Unknown
# Persistence Score: 0.92 (CRITICAL)
# Locations: 4
# Appearances: 15 over 6 days
# Assessment: INVESTIGATE

# Step 2: Active Enumeration with Flipper
# For each suspicious device:

# Flipper: Bluetooth → BLE Scanner → Find AA:BB:CC:DD:EE:FF
# Connect → Enumerate GATT services
# Document:
# - Device name: "Tile Mate"
# - Manufacturer: Tile Inc.
# - Services: 0xFEED (Find My Tile)
# - Assessment: BLE tracker, possibly tracking you

# Step 3: Update CYT Classification
# Edit ble_classifier.py to recognize this device:
# Add Tile manufacturer ID to TRACKER_UUIDS
# Re-run analysis → Device now classified as "BLE Tracker"

# Step 4: Remediation
# - Physical search: Find hidden Tile tracker in vehicle/belongings
# - OR: Use Flipper to locate (signal strength triangulation)
```

### Workflow 2: Automated Threat Response

**Goal**: CYT detects threat → Automatically trigger Flipper enumeration → Generate comprehensive report.

**Step 1: Create Response Script**

```python
# File: auto_threat_response.py

import subprocess
import time
from surveillance_detector import SurveillanceDetector, load_ble_appearances_from_kismet
from ble_classifier import BLEClassifier

def flipper_enumerate_device(mac_address):
    """
    Trigger Flipper Zero to enumerate BLE device via CLI
    Requires Flipper connected via USB
    """
    # Send command to Flipper via serial
    # Example (pseudo-code, actual implementation varies):
    # serial_send("/dev/ttyACM0", f"bt_scan {mac_address}")

    print(f"[Flipper] Enumerating {mac_address}...")
    # In practice, this would:
    # 1. Activate Flipper BLE scanner via CLI
    # 2. Connect to target device
    # 3. Read GATT services
    # 4. Save results to file

    return {
        'device_name': 'Unknown Tracker',
        'services': ['0xFE2C'],
        'manufacturer_id': 0x004C
    }

def main():
    # Load config
    config = {}  # Load from config.json

    # Initialize detector
    detector = SurveillanceDetector(config)

    # Load latest Kismet data
    kismet_db = "latest.kismet"  # Path to most recent Kismet DB
    load_ble_appearances_from_kismet(kismet_db, detector, location_id="home")

    # Analyze for threats
    suspicious_devices = detector.analyze_surveillance_patterns()

    # For each HIGH or CRITICAL threat:
    for device in suspicious_devices:
        if device.persistence_score >= 0.7:
            print(f"\n[ALERT] High-threat device detected: {device.mac}")
            print(f"Persistence Score: {device.persistence_score}")

            # Automatically enumerate with Flipper
            details = flipper_enumerate_device(device.mac)

            # Generate detailed report
            report = f"""
# THREAT REPORT - {time.strftime('%Y-%m-%d %H:%M:%S')}

## Device: {device.mac}

**Threat Level**: {'CRITICAL' if device.persistence_score >= 0.8 else 'HIGH'}
**Persistence Score**: {device.persistence_score}
**Total Appearances**: {device.total_appearances}
**Locations**: {', '.join(device.locations_seen)}
**First Seen**: {device.first_seen}
**Last Seen**: {device.last_seen}

## Active Enumeration (Flipper Zero)

**Device Name**: {details['device_name']}
**Services**: {details['services']}
**Manufacturer**: {hex(details['manufacturer_id'])}

## Recommended Actions

1. Physical search for device in vehicle/belongings
2. Monitor for continued appearances
3. Consider reporting to law enforcement if stalking suspected

---
            """

            # Save report
            report_path = f"threat_reports/threat_{device.mac}_{int(time.time())}.md"
            with open(report_path, 'w') as f:
                f.write(report)

            print(f"[Report] Saved to {report_path}")

if __name__ == '__main__':
    main()
```

**Step 2: Schedule Automatic Execution**

```bash
# Run threat response script every 6 hours
# crontab -e
0 */6 * * * cd /path/to/Chasing-Your-Tail-NG && python3 auto_threat_response.py

# Or: Set up as systemd service for continuous monitoring
```

### Workflow 3: War Driving with GPS Integration

**Goal**: Mobile WiFi/BLE mapping with location correlation, export to Google Earth.

**Hardware Setup**:
```bash
# Required:
# - WiFi adapter in monitor mode (for Kismet)
# - GPS module (USB GPS or phone GPS via Bluetooth)
# - Laptop with battery power
# - Optional: Flipper for additional BLE scanning

# Software Setup:
# Install gpsd for GPS integration
sudo apt install gpsd gpsd-clients

# Start GPS daemon
sudo gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock

# Verify GPS lock
gpsmon
# Wait for "3D FIX" status (may take 2-5 minutes outdoors)
```

**War Driving Script**:
```bash
#!/bin/bash
# File: mobile_wardrive.sh

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="./wardrive_logs"
KISMET_LOG="${LOG_DIR}/wardrive_${TIMESTAMP}"

mkdir -p "$LOG_DIR"

echo "[*] Starting mobile wardriving session"
echo "[*] Logs will be saved to: ${KISMET_LOG}"

# Start Kismet with GPS enabled
sudo kismet -c wlan0mon --override wardrive -p ${KISMET_LOG} -t wardrive --daemonize

echo "[+] Kismet started with GPS logging"
echo "[*] Drive/walk around for 30-60 minutes"
echo "[*] Press Ctrl+C to stop when done"

# Keep script running until user stops
trap "echo '[*] Stopping wardrive...'; sudo killall kismet; echo '[+] Wardrive complete. Analyze with: python3 surveillance_analyzer.py --db ${KISMET_LOG}-1.kismet'; exit" INT

# Wait indefinitely
while true; do
    sleep 1
done
```

**Usage**:
```bash
# 1. Start wardriving session
chmod +x mobile_wardrive.sh
sudo ./mobile_wardrive.sh

# 2. Drive around neighborhood / walk with backpack (30-60 min)

# 3. Stop session (Ctrl+C)

# 4. Analyze captured data
python3 surveillance_analyzer.py --db ./wardrive_logs/wardrive_20241129_143022-1.kismet

# 5. Generate KML for Google Earth visualization
# KML file auto-generated in kml_files/ directory

# 6. Optional: Export to WiGLE format for community mapping
# Create export script (export_to_wigle.py)
```

---

## 8-Week Hacker Training Program

Progressive skill-building from zero to advanced.

### **Week 1-2: Fundamentals & First Tests**

**Objectives**:
- [ ] Install all tools (Flipper firmware, CYT, Kismet)
- [ ] Understand basic wireless security concepts
- [ ] Execute first hands-on attacks on YOUR systems
- [ ] Document baseline security posture

**Week 1 Tasks**:
```bash
# Day 1-2: Setup
- [ ] Flash Flipper firmware (Unleashed recommended)
      qFlipper → Install from file → unleashed-firmware.tgz

- [ ] Verify Flipper functionality:
      Test all apps: Sub-GHz, RFID, NFC, IR, BLE

- [ ] Set up CYT environment:
      cd ~/Desktop/Chasing-Your-Tail-NG
      python3 -m venv venv
      source venv/bin/activate
      pip3 install -r requirements.txt

- [ ] Test CYT with demo mode:
      python3 surveillance_analyzer.py --demo
      # Verify report generation

# Day 3-4: Sub-GHz Testing
- [ ] Test YOUR garage door:
      Flipper: Apps → Sub-GHz → Read RAW → 315.000 MHz
      Press garage remote
      Save capture
      Replay capture → Document: Works or blocked?

- [ ] If vulnerable (replay works):
      Research upgrade options (Security+ 2.0 openers)
      Estimate cost: $200-300

- [ ] If secure (replay blocked):
      Document: Rolling code implementation confirmed

# Day 5-6: RFID/NFC Testing
- [ ] Clone YOUR access badge:
      Flipper: RFID → Read
      Hold badge against Flipper
      Document card type (EM4100, HID Prox, Mifare)

- [ ] Test emulation:
      RFID → Saved → Emulate
      Hold Flipper against reader → Document: Works?

- [ ] Security assessment:
      If works → Badge is clonable (INSECURE)
      Research: Upgrade to DESFire or add PIN requirement

# Day 7: Documentation & Planning
- [ ] Create security inventory spreadsheet:
      | Device | Protocol | Current Security | Risk Level | Remediation |
      | Garage Door | Sub-GHz 315MHz | Fixed Code | HIGH | Upgrade to Security+ 2.0 |
      | Access Badge | RFID EM4100 | Clonable | MEDIUM | Add PIN or Faraday sleeve |
```

**Week 2 Tasks**:
```bash
# Day 1-2: Kismet Setup & Monitoring
- [ ] Install Kismet:
      sudo apt install kismet
      sudo usermod -aG kismet $USER
      # Log out and back in

- [ ] Set WiFi adapter to monitor mode:
      sudo airmon-ng check kill
      sudo airmon-ng start wlan0
      # Creates wlan0mon interface

- [ ] Start Kismet continuous monitoring:
      sudo ./start_kismet_clean.sh wlan0mon

- [ ] Access Kismet web UI:
      http://localhost:2501
      Create admin password

- [ ] Let run for 24+ hours

# Day 3-4: CYT First Analysis
- [ ] After 24 hours, run CYT analysis:
      python3 surveillance_analyzer.py --kismet-dir .

- [ ] Review surveillance report:
      ls -la surveillance_reports/
      cat surveillance_reports/surveillance_report_*.md

- [ ] Document findings:
      Total devices: ___
      WiFi devices: ___
      BLE devices: ___
      Suspicious devices: ___

- [ ] Identify YOUR devices vs unknowns:
      Create list of all your devices (MACs)
      Cross-reference with report
      Flag unknowns for investigation

# Day 5-6: BLE Security Audit
- [ ] Flipper BLE scan:
      Bluetooth → BLE Scanner
      Document all devices in range

- [ ] For each BLE device:
      Attempt connection without pairing
      Document: Secure (pairing required) or Insecure (open)

- [ ] Create BLE inventory:
      | Device | MAC | Pairing Required? | Encryption? | Risk |
      | Smart Bulb | AA:BB:CC... | No | No | HIGH |
      | Smart Lock | 11:22:33... | Yes | Yes | LOW |

# Day 7: Study & Reading
- [ ] Read: "Hacking Exposed Wireless" - Chapters 1-3
- [ ] Watch: "Flipper Zero Workshop" (YouTube - official channel)
- [ ] Review: Your week's findings, plan Week 3 upgrades
```

**Week 1-2 Deliverables**:
- ✅ Flipper Zero fully operational with custom firmware
- ✅ CYT surveillance analysis completed (first run)
- ✅ Security inventory spreadsheet with 10+ devices documented
- ✅ Identified 2+ vulnerabilities in your own systems

---

### **Week 3-4: WiFi Offensive Techniques**

**Objectives**:
- [ ] Build WiFi Marauder module
- [ ] Execute deauth attacks on YOUR network
- [ ] Capture and crack YOUR WiFi password
- [ ] Implement WPA3 or PMF protection

**Week 3 Tasks**:
```bash
# Day 1-2: Marauder Hardware Setup
- [ ] Purchase ESP32-S2 Mini ($10-15)
      Vendor: Amazon, Adafruit, AliExpress

- [ ] Flash Marauder firmware:
      Visit: ESP32 Marauder web flasher
      Connect ESP32 via USB
      Select board: ESP32-S2
      Flash latest stable firmware

- [ ] Wire ESP32 to Flipper:
      ESP32 TX → Flipper Pin 14 (RX) [Orange]
      ESP32 RX → Flipper Pin 13 (TX) [Yellow]
      ESP32 GND → Flipper Pin 18 (GND) [Black]
      Power ESP32 via USB (5V 1A adapter)

- [ ] Test connection:
      Flipper: Apps → ESP32 WiFi Marauder
      Should show "Connected" + firmware version

# Day 3-4: WiFi Scanning & Deauth
- [ ] Scan YOUR network:
      Marauder → Scan → APs
      Document: SSID, BSSID, Channel, Encryption (WPA2/WPA3)

- [ ] Baseline test - Device resilience:
      Start video stream on phone (YouTube, Netflix)

- [ ] Execute deauth attack (YOUR network only):
      Marauder → Attack → Deauth → Select YOUR AP
      Duration: 30 seconds

- [ ] Observe behavior:
      Did phone disconnect? _____
      How long to reconnect? _____
      Video stream interrupted? _____

- [ ] Document current protection:
      WPA2 (no PMF) → Vulnerable to deauth
      WPA2 + PMF → Protected (devices stay connected)
      WPA3 → Protected (devices stay connected)

# Day 5-6: Handshake Capture & Cracking
- [ ] Install hashcat:
      sudo apt install hashcat

- [ ] Download rockyou.txt wordlist:
      wget https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt
      gunzip rockyou.txt.gz

- [ ] Capture WPA2 handshake:
      Marauder → Sniff → Start
      Wait for device to connect (or deauth to force reconnect)
      Handshake captured → Save PCAP to SD card

- [ ] Transfer PCAP to computer:
      Remove SD card from ESP32
      Copy capture.pcap to ~/handshakes/

- [ ] Convert PCAP to hashcat format:
      hcxpcapngtool -o hash.hc22000 capture.pcap

- [ ] Attempt crack (YOUR password):
      hashcat -m 22000 hash.hc22000 rockyou.txt

- [ ] Document results:
      Time to crack: _____ (if successful)
      Password strength: Weak/Medium/Strong

- [ ] If cracked in <24 hours → PASSWORD TOO WEAK
      Action: Change to 20+ character passphrase

# Day 7: Defense Implementation
- [ ] Enable PMF or WPA3:
      Router admin → Wireless → Security
      Option 1: WPA3-Personal (if supported)
      Option 2: WPA2 + PMF "Optional"

- [ ] Change WiFi password:
      Generate 25-char random password (password manager)
      Update on all devices

- [ ] Re-test deauth attack:
      Expected: Devices stay connected (PMF/WPA3 blocking)

- [ ] Re-test handshake crack:
      Capture new handshake
      Attempt crack with rockyou.txt
      Expected: NOT crackable (strong password)
```

**Week 4 Tasks**:
```bash
# Day 1-2: Evil Portal Creation
- [ ] Create test evil portal:
      Marauder → Evil Portal → Generic Login
      SSID: "Free WiFi" or "Starbucks"

- [ ] Test with YOUR phone:
      Connect to evil portal AP
      Observe: Fake login page appears
      Test: Enter fake credentials
      Marauder: View captured credentials

- [ ] Document:
      How realistic is portal? _____
      Would you fall for this? _____
      How to detect fake portal? (Check HTTPS, verify SSID)

# Day 3-4: Beacon Spam & WiFi Congestion
- [ ] Beacon spam test:
      Marauder → Attack → Beacon Spam → Random SSIDs
      Count: 50 fake networks
      Duration: 60 seconds

- [ ] Observe device behavior:
      How does phone WiFi list display 50+ networks? _____
      Can you find YOUR real network? _____
      Impact on WiFi scanning performance? _____

- [ ] Practical defense:
      Memorize YOUR network's exact BSSID (MAC)
      Verify before connecting (prevent fake AP attacks)

# Day 5-6: Packet Capture & Analysis
- [ ] Capture YOUR network traffic:
      Marauder → Sniff → Start
      Duration: 5 minutes
      Save to SD card

- [ ] Analyze in Wireshark:
      wireshark capture.pcap

- [ ] Identify protocols:
      Filter: http (any unencrypted HTTP traffic?)
      Filter: dns (DNS queries - what sites accessed?)
      Filter: wlan.fc.type_subtype == 0x08 (Beacon frames)

- [ ] Privacy assessment:
      Unencrypted data visible? _____
      Device fingerprinting possible? _____
      Defense: Use VPN for all traffic

# Day 7: Comprehensive Testing & Reporting
- [ ] Re-run all attacks post-remediation:
      Deauth: Should FAIL (PMF/WPA3)
      Handshake crack: Should FAIL (strong password)
      Evil portal: Can you detect fake? (verify HTTPS)

- [ ] Create Week 3-4 pentest report:
      Document all findings
      Before/after security posture
      Lessons learned

- [ ] Update security inventory:
      Mark WiFi as "SECURED" with WPA3 + strong password
```

**Week 3-4 Deliverables**:
- ✅ WiFi Marauder functional and tested
- ✅ WPA3 or WPA2+PMF enabled on YOUR network
- ✅ 20+ character WiFi password implemented
- ✅ Pentest report documenting WiFi security improvements

---

### **Week 5-6: CYT Deep Dive & BLE Security**

**Objectives**:
- [ ] Master CYT detection capabilities
- [ ] Build automated threat response system
- [ ] Conduct comprehensive BLE security audit
- [ ] Test MAC randomization and privacy features

**Week 5 Tasks**:
```bash
# Day 1-2: Self-Tracking Test
- [ ] Configure Flipper as persistent BLE beacon:
      Bluetooth → BLE Spam → Custom → Name: "TEST_TRACKER"
      Let broadcast continuously

- [ ] Move to 3+ locations with Flipper:
      Location 1: Home (1 hour)
      Location 2: Work/School (1 hour)
      Location 3: Coffee shop (30 min)
      Location 4: Back home (remainder)

- [ ] Ensure Kismet running during all movements:
      Verify: localhost:2501 shows "Bluetooth" data source

- [ ] After 6+ hours, analyze:
      python3 surveillance_analyzer.py

- [ ] Verify CYT detects:
      Device: Flipper TEST_TRACKER
      Type: BLE Device
      Persistence Score: >0.7 (should be high)
      Locations: 3+
      Assessment: Would be flagged as stalking device ✓

# Day 3-4: Detection Threshold Tuning
- [ ] Review false positives in CYT report:
      Identify: Your own devices flagged as suspicious
      (e.g., Apple Watch, fitness tracker you wear daily)

- [ ] Tune detection thresholds:
      Edit: config.json
      Adjust:
        "min_appearances": 3 → 5 (reduce false positives)
        "persistence_score_high": 0.6 → 0.7 (stricter)
        "min_locations": 2 → 3 (require more location diversity)

- [ ] Re-run analysis with new thresholds:
      python3 surveillance_analyzer.py

- [ ] Compare results:
      False positives before: ___
      False positives after: ___
      Actual threats still detected: ___

- [ ] Iterate until optimal (few false positives, catches real threats)

# Day 5-6: Automated Threat Response
- [ ] Build auto_threat_response.py (see CYT Integration section)

- [ ] Test automated workflow:
      1. CYT detects high-threat device (TEST_TRACKER)
      2. Script triggers Flipper enumeration
      3. Detailed report auto-generated

- [ ] Verify output:
      Check: threat_reports/ directory
      Review: Generated markdown report
      Contains: MAC, persistence score, Flipper enum data

- [ ] Schedule automated execution:
      crontab -e
      Add: 0 */6 * * * cd ~/Chasing-Your-Tail-NG && python3 auto_threat_response.py
      # Runs every 6 hours

# Day 7: Integration Testing
- [ ] Full pipeline test:
      1. Kismet monitoring (24/7 background)
      2. Auto_threat_response.py (every 6 hours)
      3. Review reports daily

- [ ] Simulate threat:
      Use Flipper as persistent tracker
      Verify: Auto-detected within 6 hours
      Verify: Report generated automatically

- [ ] Document workflow efficiency:
      Time from threat appearance to detection: ___
      Manual effort required: ___ (should be minimal)
```

**Week 6 Tasks**:
```bash
# Day 1-3: Comprehensive BLE Security Audit
- [ ] Enumerate ALL BLE devices in home:
      Flipper: Bluetooth → BLE Scanner
      Run for 30 minutes
      Document all unique devices (20-50 typical in home)

- [ ] For EACH device, test security:
      Device 1: Smart TV
      - Attempt connection without pairing: [SUCCESS/FAIL]
      - If success: Read GATT characteristics
      - Document exposed data: [Device name, firmware, etc.]
      - Risk level: [HIGH/MEDIUM/LOW]

      Device 2: Bluetooth Speaker
      - Attempt connection without pairing: [SUCCESS/FAIL]
      - If fail: Pairing method: [Numeric/Passkey/Just Works]
      - Encryption used: [YES/NO]
      - Risk level: [HIGH/MEDIUM/LOW]

      [Repeat for all devices]

- [ ] Create BLE security spreadsheet:
      | Device | MAC | Pairing? | Encryption? | Exposed Data | Risk | Action |
      |--------|-----|----------|-------------|--------------|------|--------|
      | Smart Bulb | AA:BB... | No | No | Full control | HIGH | Replace/Isolate |
      | Smart Lock | 11:22... | Yes | Yes | None | LOW | No action |
      | Fitness Tracker | 22:33... | Yes | No | Steps, HR | MEDIUM | Enable privacy |

# Day 4-5: BLE Privacy Testing
- [ ] Test YOUR phone's MAC randomization:
      iPhone: Settings → Privacy & Security → Tracking → Check status
      Android: Settings → Connections → Bluetooth → Advanced → Randomize

- [ ] Verify MAC changes over time:
      Day 1: Flipper scan → Record phone MAC: _____
      Day 2: Flipper scan → Phone MAC changed? _____
      Expected: MAC changes every ~15 minutes (privacy feature)

- [ ] Test wearable privacy:
      Your fitness tracker / smartwatch
      Does MAC randomize? _____
      If not: Check for firmware update or privacy settings

- [ ] Test smart home device privacy:
      Most IoT devices: NO MAC randomization (static MACs)
      Implication: Trackable over time
      Defense: Disable BLE when not needed, or isolate to IoT VLAN

# Day 6-7: Remediation & Re-testing
- [ ] Fix all HIGH-risk BLE devices:
      Option 1: Replace with secure models
      Option 2: Isolate to separate VLAN (no access to main network)
      Option 3: Disable BLE entirely (if not needed)

- [ ] Enable privacy features:
      All phones: MAC randomization ON
      All wearables: Privacy mode ON (if available)

- [ ] Re-audit after remediation:
      Flipper BLE scan → Fewer insecure devices? ✓
      CYT report → Unknown BLE devices reduced? ✓
```

**Week 5-6 Deliverables**:
- ✅ CYT detection thresholds optimized (low false positives)
- ✅ Automated threat response system operational
- ✅ BLE security audit complete (all home devices assessed)
- ✅ BLE privacy features enabled on all capable devices

---

### **Week 7-8: Advanced Integration & Full Audit**

**Objectives**:
- [ ] Execute comprehensive home network security audit
- [ ] Implement all defensive recommendations
- [ ] Complete wardriving project with GPS
- [ ] Master red team vs blue team methodology

**Week 7 Tasks**:
```bash
# Day 1-2: Network Segmentation (IoT VLAN)
- [ ] Create separate IoT network:
      Router: Settings → Network → VLAN
      Create VLAN 10: "IoT_Devices"
      DHCP Range: 192.168.10.1/24

- [ ] Configure firewall rules:
      Rule 1: IoT VLAN → Internet: ALLOW
      Rule 2: IoT VLAN → Main LAN: DENY
      Rule 3: Main LAN → IoT VLAN: ALLOW (for management)

- [ ] Move all IoT devices to IoT VLAN:
      For each: Smart lights, cameras, sensors, etc.
      Change WiFi network to "IoT_Devices" SSID

- [ ] Test isolation:
      From IoT device: ping 192.168.1.100 (main network device)
      Expected: Timeout (firewall blocking)

      From main device: ping 192.168.10.50 (IoT device)
      Expected: Success (management allowed)

# Day 3-4: Comprehensive Security Audit
- [ ] WiFi Security:
      ✓ WPA3 or WPA2+PMF enabled
      ✓ 20+ character password
      ✓ Hidden SSID: [Enabled/Disabled] (minimal security benefit)
      ✓ Guest network isolated from main network

- [ ] BLE Security:
      ✓ All devices audited (spreadsheet complete)
      ✓ High-risk devices remediated
      ✓ Privacy features enabled

- [ ] Sub-GHz Security:
      ✓ Garage door: [Fixed code/Rolling code]
      ✓ Car key fob: [Fixed code/Rolling code]
      ✓ Wireless sensors: [Encrypted/Unencrypted]

- [ ] RFID Security:
      ✓ Access badges: [EM4100/DESFire/other]
      ✓ Gym cards: [Clonable/Secure]
      ✓ RFID shielding: [Implemented/Not needed]

- [ ] Physical Security:
      ✓ Computers: Auto-lock after 2 minutes
      ✓ USB ports: [Unlocked/Restricted/Physically blocked]
      ✓ BIOS password: [Enabled/Disabled]

# Day 5-6: Remediation of Medium/Low Findings
- [ ] Address all MEDIUM-risk findings:
      Example: Weak RFID badge
      Action: Add PIN requirement or purchase Faraday sleeve

- [ ] Update firmware on all devices:
      Router: Check for latest firmware
      IoT devices: Update via app
      Flipper Zero: Update to latest Unleashed/RogueMaster

- [ ] Document changes:
      Create: remediation_log.md
      Track: What was changed, when, why

# Day 7: Verification Testing
- [ ] Re-test all previously vulnerable systems:
      Garage door replay: Should FAIL (if upgraded)
      WiFi deauth: Should FAIL (PMF/WPA3)
      BLE unauthorized access: Should FAIL (pairing required)
      RFID cloning: [Test on test cards, not real badges]

- [ ] Create before/after comparison:
      Vulnerabilities Week 1: ___
      Vulnerabilities Week 7: ___
      Risk reduction: ____%
```

**Week 8 Tasks**:
```bash
# Day 1-2: Wardriving Project
- [ ] Set up GPS integration:
      Install: gpsd
      Connect: USB GPS or phone GPS via Bluetooth
      Verify: gpsmon shows 3D FIX

- [ ] Run wardriving session:
      sudo ./mobile_wardrive.sh
      Drive/walk for 60 minutes
      Stop: Ctrl+C

- [ ] Analyze captured data:
      python3 surveillance_analyzer.py --db ./wardrive_logs/wardrive_*.kismet

- [ ] Generate KML visualization:
      Check: kml_files/ for output
      Open in Google Earth

- [ ] Export to WiGLE format:
      python3 export_to_wigle.py --db wardrive.kismet --output wigle_upload.csv
      Review CSV for any sensitive data before upload
      (Optional) Upload to wigle.net for community mapping

# Day 3-4: Red Team vs Blue Team Exercise
- [ ] Red Team: Plant simulated threat
      Set up: Flipper as hidden BLE beacon
      Place: In backpack, under car seat, etc.
      Objective: See if Blue Team (CYT) detects within 24 hours

- [ ] Blue Team: Detection challenge
      Run: CYT monitoring as usual
      Goal: Detect planted tracker within 24 hours
      Method: Review reports, investigate unknowns

- [ ] Results:
      Time to detection: ___
      Detection method: [Auto-alert / Manual review]
      Lessons learned: ___

- [ ] Document:
      What worked well? ___
      What needs improvement? ___
      How to speed up detection? ___

# Day 5-6: Security Monitoring SOP
- [ ] Create Standard Operating Procedure:

      Daily:
      - Check CYT GUI for alerts
      - Review any high-persistence devices
      - Investigate unknown MACs

      Weekly:
      - Run full surveillance analysis
      - Review generated reports
      - Update device inventory (new devices?)

      Monthly:
      - Full security audit (repeat Week 7)
      - Update all firmware
      - Review and test defenses

      Quarterly:
      - Pentest with latest techniques
      - Attend security conference / watch talks
      - Update threat models

- [ ] Document SOP:
      File: security_monitoring_SOP.md
      Include: Checklists, commands, escalation procedures

# Day 7: Final Documentation & Celebration
- [ ] Create comprehensive pentest report:
      Executive Summary
      Methodology
      Findings (with risk ratings)
      Remediation actions taken
      Before/after security posture
      Recommendations for future

- [ ] Build portfolio:
      Anonymize sensitive data (MACs, SSIDs, locations)
      Create: portfolio/wireless_security_project.md
      Include: Skills learned, tools mastered, results

- [ ] Reflect on learning:
      What was hardest to learn? ___
      What was most surprising? ___
      How has your security mindset changed? ___
      What will you learn next? ___

- [ ] Share knowledge (responsibly):
      Blog post: "What I Learned Pentesting My Own Home Network"
      GitHub: Contribute to CYT or Marauder projects
      Community: Help others learn in forums/Discord
```

**Week 7-8 Deliverables**:
- ✅ IoT VLAN implemented and tested
- ✅ All CRITICAL and HIGH findings remediated
- ✅ Wardriving project complete with KML visualization
- ✅ Red vs Blue exercise documented
- ✅ Security Monitoring SOP created
- ✅ Final comprehensive pentest report

---

## Legal & Ethical Framework

**CRITICAL**: Unauthorized hacking is a federal crime. Only test systems you own or have explicit written authorization to test.

### What's Legal in the United States

✅ **Authorized Testing**:
- Your own home network, devices, and property
- Devices you personally own (phone, laptop, car, smart home devices)
- Your own access badges/cards (for research, not unauthorized access)
- Systems where you have written authorization (employer, client with signed contract)

✅ **Passive Monitoring**:
- Listening to radio signals on your property (receive-only, no transmission)
- BLE scanning (passive, just listening)
- WiFi monitoring with Kismet (no packet injection or attacks)

✅ **FCC Part 15 Compliant Transmission**:
- Sub-GHz transmission at low power (<1 mW typically)
- WiFi transmission from certified devices
- ISM band usage (2.4 GHz, 915 MHz, 433 MHz) within power limits

✅ **Educational Research**:
- Learning offensive security for defensive purposes
- Participating in bug bounty programs with authorization
- Responsible disclosure of vulnerabilities to vendors

### What's ILLEGAL (Federal Crimes)

❌ **Unauthorized Access (Computer Fraud and Abuse Act)**:
- Hacking networks you don't own (neighbors, public WiFi, etc.)
- Accessing employer systems without IT security approval
- Testing "in the wild" without authorization
- Penalty: Up to 20 years imprisonment + fines

❌ **Jamming (Communications Act of 1934)**:
- Intentionally interfering with radio communications
- WiFi jamming (even as "prank")
- GPS jamming
- Cellular jamming
- Penalty: Up to $112,500 fine + imprisonment + FCC enforcement

❌ **Interception (Wiretap Act)**:
- Capturing communications between other parties
- Man-in-the-middle attacks on others' networks
- Keystroke logging on others' computers
- Penalty: Federal crime, up to 5 years imprisonment

❌ **Credential Theft**:
- Cloning access badges for unauthorized entry
- Using captured WiFi passwords to access others' networks
- Evil portal credential harvesting (without authorization)

### Gray Areas (Proceed with Extreme Caution)

⚠️ **Wardriving**:
- Passive scanning while mobile: LEGAL (just listening)
- Connecting to open networks: GRAY AREA (depends on jurisdiction)
- Attacking networks during wardrive: ILLEGAL

⚠️ **Employer Systems**:
- Even if you're IT staff, get written authorization before pentesting
- Scope: Define exactly what can be tested
- Timing: Specify when testing is allowed
- Without authorization: Violates CFAA (illegal)

⚠️ **Public RFID Scanning**:
- Reading badges on strangers in public: GRAY AREA
- Some states have specific anti-skimming laws
- Better approach: Only test your own cards

### Sample Authorization Letter

```
WIRELESS SECURITY TESTING AUTHORIZATION

I, [Your Name], hereby authorize myself to conduct security testing on the following systems and devices that I personally own:

SCOPE OF TESTING:
- WiFi Networks:
  * Home_5G (BSSID: AA:BB:CC:DD:EE:FF)
  * Home_2.4G (BSSID: AA:BB:CC:DD:EE:01)
  * IoT_Devices (BSSID: AA:BB:CC:DD:EE:02)

- BLE Devices:
  * Philips Hue Bridge (MAC: 11:22:33:44:55:66)
  * Smart Lock (MAC: 22:33:44:55:66:77)
  * Fitness Tracker (MAC: 33:44:55:66:77:88)

- Sub-GHz Devices:
  * Garage door opener (2020 Chamberlain)
  * Car key fob (2019 Honda Civic)

- RFID/NFC:
  * Gym membership card (for personal testing only)
  * Personal access badge (for research, not unauthorized access)

AUTHORIZED TESTING METHODS:
- Passive monitoring (Kismet, BLE scanning)
- Active attacks (WiFi deauth, RFID cloning, Sub-GHz replay)
- Packet capture and analysis
- Credential testing (WPA2 handshake capture + offline cracking)

OUT OF SCOPE (NOT AUTHORIZED):
- Neighbor networks or devices
- Public WiFi networks
- Any system not explicitly listed above
- Transmission on restricted frequencies
- Jamming or interference with others' systems

PURPOSE:
This testing is conducted solely for educational purposes and to improve the security of my own systems. Findings will be documented and used to implement defensive measures.

TIMELINE: [Start Date] to [End Date]

Signed: ___________________________
Name: [Your Name]
Date: [Date]

Witnessed by: ___________________________
Name: [Witness Name - Optional]
Date: [Date]
```

**Keep this authorization letter on file to demonstrate intent if ever questioned.**

### FCC Regulations (United States)

**Key Regulations**:
- **47 CFR Part 15**: Unlicensed RF devices (Flipper Zero, WiFi, Bluetooth, Sub-GHz)
- **FCC ID 2A2V6-FZ**: Flipper Zero is FCC certified for legal RF transmission

**Power Limits**:
- **Sub-GHz (315/433 MHz)**: ~0 dBm typical (Flipper complies)
- **2.4 GHz WiFi**: 30 dBm (1 watt) max (Marauder complies)
- **BLE**: 10 dBm (10 mW) typical (Flipper complies)

**Prohibited Actions**:
- Exceeding FCC power limits (illegal modification of devices)
- Operating on restricted frequencies (cellular, aviation, public safety)
- Jamming any RF communications
- Unlicensed transmission on amateur radio bands (requires ham license)

**Amateur Radio Considerations**:
- Some custom firmware unlocks ham bands (144/430 MHz)
- **Requires**: Valid amateur radio license (Technician class minimum)
- **Without license**: Do NOT transmit on ham frequencies
- Flipper Zero is NOT type-accepted for amateur radio (use at your own risk)

### Best Practices for Legal Compliance

1. **Test Only What You Own**:
   - Your home network
   - Your devices
   - Your access cards (for research, not unauthorized entry)

2. **Get Written Authorization**:
   - Employer systems: IT security written approval
   - Client pentesting: Signed Statement of Work
   - Friend's devices: Written consent (protects you legally)

3. **Use Isolated Test Environments**:
   - Faraday cage for RF experiments
   - Dedicated test network (no internet)
   - Virtual labs for software testing

4. **Document Everything**:
   - What you tested, when, and why
   - Authorization letters
   - Shows good faith if questions arise

5. **Respect FCC Limits**:
   - Don't modify Flipper to increase transmit power
   - Stay within Part 15 regulations
   - No jamming (severe penalties)

6. **Follow Responsible Disclosure**:
   - If you find vulnerabilities, report to manufacturer
   - Allow 90 days for patch before public disclosure
   - Coordinate disclosure timeline with vendor

### Resources

**Legal References**:
- Computer Fraud and Abuse Act (CFAA): 18 U.S.C. § 1030
- Wiretap Act: 18 U.S.C. § 2511
- FCC Communications Act: 47 U.S.C. § 301 et seq.
- FCC Part 15 Regulations: 47 CFR Part 15

**Compliance Documents**:
- Flipper Zero FCC ID: https://fccid.io/2A2V6-FZ
- Flipper Compliance Docs: https://flipperzero.one/compliance

**Legal Guides**:
- EFF: "Know Your Rights: Government Hacking"
- NextTechWorld: "Flipper Zero Legal Use Guide"
- Flipper Unleashed: "Legal Guide by Country"

---

## Troubleshooting

### Flipper Zero Common Issues

**Issue: SD Card Errors**
```bash
# Symptom: "SD Card Error", files not saving

# Solution 1: Format SD card properly
# Backup SD card to computer first!
# Linux:
sudo mkfs.vfat -F 32 -s 64 /dev/sdX1
# (-s 64 = 32KB clusters, required by Flipper)

# macOS:
diskutil eraseDisk FAT32 FLIPPER_SD /dev/diskX

# Windows:
# Use "SD Card Formatter" official tool
# https://www.sdcard.org/downloads/formatter/

# Solution 2: Replace SD card
# Recommended: SanDisk Extreme, Samsung EVO (8-32 GB)
# Avoid: Generic no-name brands (high failure rate)
```

**Issue: Firmware Update Failure**
```bash
# Symptom: Update stuck or fails

# Solution 1: Use qFlipper official updater
# https://flipperzero.one/update
# Download → Install → Connect Flipper → Update

# Solution 2: Manual DFU mode flash
# 1. Power off Flipper
# 2. Hold LEFT + BACK buttons
# 3. Plug USB while holding
# 4. Screen stays black (DFU mode)
# 5. Flash with dfu-util:
sudo dfu-util -a 0 -s 0x08000000 -D firmware.dfu

# Solution 3: Recovery mode
# 1. Power off
# 2. Hold OK (center button)
# 3. Plug USB while holding
# 4. "Recovery Mode" appears
# 5. Use qFlipper to reinstall firmware
```

**Issue: GPIO Module Not Recognized**
```bash
# Symptom: Marauder not detected

# Check 1: Verify wiring with multimeter
# Continuity test:
# - Flipper GND to ESP32 GND
# - Flipper TX (pin 13) to ESP32 RX
# - Flipper RX (pin 14) to ESP32 TX

# Check 2: Install Marauder app on Flipper
# Apps → Apps Catalog → Search "marauder" → Install

# Check 3: Power ESP32 separately
# Don't rely on Flipper 3.3V (insufficient current)
# Use USB power adapter (5V 1A minimum)

# Check 4: Verify ESP32 firmware
# Connect ESP32 to PC via USB
# Serial monitor (115200 baud):
screen /dev/ttyUSB0 115200
# Type: help
# Expected: Marauder command list
# If no response: Re-flash Marauder firmware
```

### WiFi Marauder Issues

**Issue: ESP32 Not Detected by Computer**
```bash
# Symptom: No /dev/ttyUSB0 device

# Solution 1: Install USB-to-serial drivers
# CP2102: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
# CH340: http://www.wch-ic.com/downloads/CH341SER_ZIP.html

# Solution 2: Check cable
# Many USB cables are charge-only (no data)
# Test with different cable

# Solution 3: Linux permissions
sudo usermod -a -G dialout $USER
# Log out and back in

# Solution 4: Try different USB port
# USB 2.0 vs 3.0 can have different power characteristics
```

**Issue: Marauder Crashes During Deauth**
```bash
# Symptom: ESP32 reboots mid-attack

# Cause: Insufficient power

# Solution 1: Use separate power supply
# ESP32 USB → Wall adapter (5V 1A minimum)
# Flipper GPIO → ESP32 data only (TX/RX/GND)

# Solution 2: Reduce attack intensity
# Marauder: Deauth → Target 1 AP (not "all")
# Lower packet rate = lower power draw

# Solution 3: Hardware mod (advanced)
# Solder 100µF capacitor across ESP32 VCC/GND
# Smooths power delivery
```

**Issue: Deauth Attack Not Working**
```bash
# Symptom: Deauth frames sent but devices stay connected

# Cause 1: Target has PMF/WPA3 enabled (GOOD for security!)
# Verify:
sudo airodump-ng wlan0mon
# Look for "PMF" column: "R" = Required (protected)

# Expected: If PMF enabled, deauth WON'T work (this is correct behavior)
# Solution: Test on device without PMF (create test AP)

# Cause 2: Wrong channel
# Marauder must be on same channel as target AP
# Solution: Use "Scan" first, select AP (auto-tunes channel)

# Cause 3: Too far from target
# Solution: Move within 10 meters of AP/clients

# Cause 4: Firmware bug
# Solution: Update to latest Marauder firmware
# https://github.com/justcallmekoko/ESP32Marauder/releases
```

### CYT / Kismet Issues

**Issue: No BLE Devices Detected**
```bash
# Symptom: Kismet shows 0 Bluetooth devices

# Solution 1: Enable Bluetooth data source
sudo kismet -c hci0:name=Bluetooth

# Solution 2: Verify Bluetooth adapter
# Check if system has Bluetooth:
hciconfig
# Expected: hci0 UP RUNNING

# If not present:
# Install Bluetooth adapter (USB or built-in)
# On Raspberry Pi: Built-in Bluetooth works

# Solution 3: Check Kismet config
# Edit: /etc/kismet/kismet.conf
# Add: source=hci0:name=Bluetooth
# Restart Kismet

# Solution 4: Permissions
sudo usermod -aG bluetooth $USER
# Log out and back in
```

**Issue: Kismet Database Locked**
```bash
# Symptom: "database is locked" error

# Cause: Kismet still has database open

# Solution 1: Wait for Kismet to finish
# Let current capture complete cleanly
# sudo killall kismet (graceful shutdown)

# Solution 2: Copy database to new location
cp Kismet-20241129.kismet analysis/
# Analyze the copy instead

# Solution 3: Read-only mode
# CYT uses SecureKismetDB with read-only by default
# Should prevent this issue (verify in secure_database.py)
```

---

## Quick Reference Commands

**Flipper Zero** (via serial CLI):
```bash
# Connect to Flipper serial console
screen /dev/ttyACM0 115200

# Sub-GHz commands (examples):
# Read frequency: storage read /ext/subghz/captures/file.sub
# Transmit: subghz tx /ext/subghz/captures/file.sub

# Exit screen: Ctrl+A, then K, then Y
```

**Kismet**:
```bash
# Start Kismet with monitor interface
sudo kismet -c wlan0mon

# Start with Bluetooth
sudo kismet -c wlan0mon -c hci0:name=Bluetooth

# Read mode (analyze PCAP)
kismet -r capture.pcap

# Access web UI
http://localhost:2501

# Stop Kismet
sudo killall kismet
```

**CYT (Chasing Your Tail)**:
```bash
# Run surveillance analysis
python3 surveillance_analyzer.py

# Demo mode (no Kismet data required)
python3 surveillance_analyzer.py --demo

# Specify Kismet database directory
python3 surveillance_analyzer.py --kismet-dir ./wardrive_logs/

# GUI interface
python3 cyt_gui.py

# Drone detection with WiGLE
python3 probe_analyzer.py --wigle
```

**WiFi Marauder** (via Flipper):
```bash
# All done via Flipper UI:
# Apps → ESP32 WiFi Marauder → [Scan/Attack/Sniff]

# Or via ESP32 serial (direct):
screen /dev/ttyUSB0 115200
# Commands:
# scan -a (scan all APs)
# attack -t deauth -m AA:BB:CC:DD:EE:FF (deauth specific AP)
# sniff -s (start packet capture)
# pcap -d (dump PCAP to SD)
```

**Hashcat** (WiFi cracking):
```bash
# Convert PCAP to hashcat format
hcxpcapngtool -o hash.hc22000 capture.pcap

# Crack with wordlist
hashcat -m 22000 hash.hc22000 /usr/share/wordlists/rockyou.txt

# GPU-accelerated crack
hashcat -m 22000 -w 3 -O hash.hc22000 rockyou.txt

# Resume session
hashcat --session mysession --restore

# Show cracked passwords
hashcat -m 22000 hash.hc22000 --show
```

**nmap** (Network scanning):
```bash
# Discover devices on network
sudo nmap -sn 192.168.1.0/24

# Service detection
sudo nmap -sV -p- 192.168.1.100

# Aggressive scan (OS detection, scripts, traceroute)
sudo nmap -A 192.168.1.100

# Specific ports
sudo nmap -p 22,80,443 192.168.1.100
```

**Monitor Mode Setup**:
```bash
# Kill interfering processes
sudo airmon-ng check kill

# Enable monitor mode
sudo airmon-ng start wlan0
# Creates: wlan0mon

# Verify
iwconfig
# Should show: wlan0mon Mode:Monitor

# Disable monitor mode
sudo airmon-ng stop wlan0mon
```

**GPS Utilities**:
```bash
# Start GPS daemon
sudo gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock

# Monitor GPS status
gpsmon

# Test GPS data
cgps

# Check for fix (wait for "3D FIX")
# Outdoors: 2-5 minutes typical
```

**Wireshark Filters**:
```bash
# Open PCAP in Wireshark
wireshark capture.pcap

# Useful filters:
wlan.fc.type_subtype == 0x08         # Beacon frames (APs)
wlan.fc.type_subtype == 0x0c         # Deauth frames
eapol                                 # WPA handshakes
http                                  # Unencrypted HTTP traffic
dns                                   # DNS queries
wlan.sa == AA:BB:CC:DD:EE:FF         # Specific source MAC
```

**Troubleshooting**:
```bash
# Check monitor mode
iwconfig wlan0mon

# Kill interfering processes
sudo airmon-ng check kill

# Verify Flipper connection
ls /dev/ttyACM*

# Check ESP32 connection
ls /dev/ttyUSB*

# Check GPS
gpsmon

# Check Bluetooth adapter
hciconfig
```

---

## Final Thoughts: The Hacker Mindset

You've now learned the offensive techniques. Use them to **build better defenses**.

**Remember**:
1. **Think Like an Attacker**: Question every security claim. "Is this really secure? How would I break it?"
2. **Test Your Own Systems**: Don't assume they're secure. Verify with hands-on testing.
3. **Stay Legal**: Authorization is everything. Only test what you own or have written permission to test.
4. **Document Everything**: Your findings, methodologies, and remediation steps.
5. **Share Responsibly**: Teach others to defend, don't enable attackers.
6. **Keep Learning**: Security is an arms race. New techniques emerge constantly.

**You Now Have**:
- ✅ Flipper Zero with custom firmware (Unleashed/RogueMaster)
- ✅ WiFi Marauder for WiFi pentesting
- ✅ CYT for surveillance detection
- ✅ Knowledge of offensive techniques across 8 wireless protocols
- ✅ Defensive strategies for every attack vector
- ✅ 8-week structured learning program
- ✅ Legal/ethical framework for responsible testing

**Use this knowledge to**:
- Secure your own home network
- Educate friends and family about wireless security
- Contribute to open-source security projects
- Pursue a career in cybersecurity (OSWP, GPEN, CEH certifications)
- Build defenses that would frustrate the best attackers

**The Journey Continues**:
- Week 9+: Repair Portapack H4M, explore wide-spectrum SDR
- Month 3+: Cellular security (Stingray detection with RayHunter)
- Month 6+: RF protocol reverse engineering
- Year 2+: Contribute to Flipper firmware, publish security research

**Welcome to offensive security. Stay curious. Stay ethical. Stay persistent.**

---

**End of Guide**

For questions, updates, or contributions, see:
- Flipper Zero Discord: https://flipperzero.one/discord
- ESP32 Marauder GitHub: https://github.com/justcallmekoko/ESP32Marauder
- Chasing Your Tail Project: This repository

*Happy hacking (responsibly)!* 🦊🔒
