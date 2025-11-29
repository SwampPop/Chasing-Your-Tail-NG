# Chasing Your Tail - Hardware Recommendations Guide

**Version**: 2.2
**Last Updated**: 2025-11-28
**Project**: Wireless Surveillance Detection System

---

## Table of Contents

1. [Quick Start Recommendations](#quick-start-recommendations)
2. [Wi-Fi Adapters](#wi-fi-adapters)
3. [GPS Hardware](#gps-hardware)
4. [Computing Platforms](#computing-platforms)
5. [Antennas](#antennas)
6. [Power Solutions](#power-solutions)
7. [Accessories and Enclosures](#accessories-and-enclosures)
8. [Advanced Equipment](#advanced-equipment)
9. [Complete Build Examples](#complete-build-examples)
10. [Troubleshooting and Compatibility](#troubleshooting-and-compatibility)

---

## Quick Start Recommendations

If you just want to get started immediately, here's the TL;DR:

**Budget Mobile Setup (~$150)**
- ALFA AWUS036NHA (2.4GHz, $35)
- VK-162 USB GPS ($15)
- Raspberry Pi 4 4GB ($55) + 64GB SD card ($15)
- Anker PowerCore 20000 ($30)

**Professional Mobile Setup (~$400)**
- ALFA AWUS036ACH (Dual-band, $50)
- BU-353S4 USB GPS ($40)
- Intel NUC i3 ($250) + 256GB SSD ($40)
- RAVPower 26800mAh PD ($50)
- 9dBi dual-band antenna ($20)

**Stationary Lab Setup (~$600)**
- ALFA AWUS1900 (High-power dual-band, $80)
- BU-353S4 USB GPS ($40)
- Used business laptop (i5/8GB, $200-300)
- 12dBi omnidirectional antenna ($60)
- UPS battery backup ($120)

---

## Wi-Fi Adapters

The adapter is the most critical component. You need rock-solid monitor mode and packet injection support. Here's what actually works in the field.

### Understanding Chipsets

**The Good (Proven for Kismet)**
- **Atheros AR9271**: The gold standard. Ancient but bulletproof. Full monitor mode, injection works perfectly, drivers in mainline kernel since 3.x.
- **Ralink RT3070/RT5370**: Solid workhorses. Great Linux support, stable drivers, good range.
- **Realtek RTL8812AU**: Dual-band king. Requires external drivers but well-maintained. Excellent for 5GHz work.
- **Mediatek MT7612U**: The newer dual-band champion. Better driver support than Realtek, sometimes harder to find.

**The Bad (Avoid for This Project)**
- **Broadcom BCM43xx**: Proprietary nightmare. Driver support is inconsistent, packet injection is hit-or-miss, frequent kernel breakage.
- **Intel AX200/AX210**: Excellent for normal use, terrible for monitoring. iwlwifi driver doesn't properly support monitor mode features.
- **Realtek RTL8188EU**: Too cheap, too unreliable. Works 60% of the time. You'll waste hours debugging.

### Budget Tier ($25-40)

#### ALFA AWUS036NHA
- **Chipset**: Atheros AR9271
- **Frequency**: 2.4GHz only
- **Price**: $35-40
- **Power**: 2000mW (varies by region)
- **Pros**:
  - Bulletproof Linux compatibility (works out-of-box on any kernel 3.0+)
  - No driver installation needed
  - Rock-solid monitor mode and injection
  - Well-documented, massive community support
  - Removable 5dBi antenna (RP-SMA)
- **Cons**:
  - 2.4GHz only (no 5GHz surveillance detection)
  - Older 802.11n standard
  - Bulky form factor
- **CYT Suitability**: 9/10 for 2.4GHz-only deployments
- **Where to Buy**: Amazon, Hak5, ROKland
- **Kismet Notes**: Works perfectly. Set source type to `linuxwifi` and it just works.

#### Panda PAU09 N600
- **Chipset**: Ralink RT5572
- **Frequency**: Dual-band (2.4GHz/5GHz)
- **Price**: $25-30
- **Pros**:
  - Dual-band on a budget
  - Good Linux support
  - Compact design
- **Cons**:
  - Lower power output than ALFA
  - Monitor mode requires manual driver updates on some kernels
  - Inconsistent QC—some units have weak RX sensitivity
- **CYT Suitability**: 7/10 (good backup, not primary recommendation)
- **Where to Buy**: Amazon, Newegg

### Mid-Range Tier ($40-80)

#### ALFA AWUS036ACH
- **Chipset**: Realtek RTL8812AU
- **Frequency**: Dual-band (2.4GHz/5GHz)
- **Price**: $50-55
- **Power**: 300mW (EU models), up to 1000mW (US models)
- **Pros**:
  - Excellent dual-band performance
  - High power output for extended range
  - Dual 5dBi antennas (RP-SMA, removable)
  - AC1200 speeds (not that it matters for monitoring, but nice)
  - Good RX sensitivity
- **Cons**:
  - Requires aircrack-ng RTL8812AU driver from GitHub
  - Driver installation can be tricky on newer kernels (DKMS helps)
  - Occasional issues with kernel updates breaking drivers
- **CYT Suitability**: 10/10 for dual-band surveillance detection
- **Where to Buy**: Amazon, Hak5, ROKland
- **Driver Installation**:
```bash
# Install DKMS driver (recommended method)
git clone https://github.com/aircrack-ng/rtl8812au.git
cd rtl8812au
sudo make dkms_install

# Verify monitor mode support
sudo ip link set wlan1 down
sudo iw dev wlan1 set type monitor
sudo ip link set wlan1 up
iwconfig wlan1  # Should show Mode:Monitor
```
- **Kismet Notes**: After driver install, works beautifully. Use `linuxwifi` source type. Captures both bands simultaneously if you configure two sources.

#### ALFA AWUS036ACHM
- **Chipset**: Mediatek MT7612U
- **Frequency**: Dual-band
- **Price**: $60-65
- **Pros**:
  - Better out-of-box Linux support than RTL8812AU
  - Magnetic base (great for vehicle mounting)
  - Compact form factor
  - Lower power draw than ACH
- **Cons**:
  - Lower TX power than ACH
  - Harder to find in stock
  - Single antenna (less flexibility)
- **CYT Suitability**: 9/10 for mobile/vehicle deployments
- **Where to Buy**: ROKland, Hak5

### Professional Tier ($80-150)

#### ALFA AWUS1900
- **Chipset**: Realtek RTL8814AU
- **Frequency**: Dual-band
- **Price**: $80-90
- **Power**: High (1000mW+)
- **Pros**:
  - Four external antennas for superior MIMO and range
  - AC1900 (3x3 spatial streams)
  - Excellent for stationary/base station deployments
  - Superior RX sensitivity compared to cheaper adapters
- **Cons**:
  - Requires RTL8814AU driver (less mature than 8812au)
  - Large form factor (not portable)
  - Higher power consumption
  - Overkill for simple walking-around surveillance detection
- **CYT Suitability**: 10/10 for fixed installations, 6/10 for mobile
- **Where to Buy**: Amazon, Hak5
- **Driver Installation**:
```bash
git clone https://github.com/morrownr/8814au.git
cd 8814au
sudo ./install-driver.sh
```

#### WiFi Pineapple Mark VII
- **Chipset**: Multiple (Mediatek-based)
- **Frequency**: Dual-band
- **Price**: $140-160
- **Pros**:
  - Purpose-built for wireless auditing
  - Multiple radios for simultaneous monitoring
  - Web-based management UI
  - Active development and community
  - Modular design for attachments
- **Cons**:
  - Not a traditional adapter (standalone device)
  - Requires integration scripting to work with Kismet
  - More expensive than needed for passive monitoring
  - Overkill unless doing active attacks
- **CYT Suitability**: 6/10 (powerful but not designed for this use case)
- **Where to Buy**: Hak5 official store

### Multiple Adapter Strategy

For comprehensive surveillance detection, consider running multiple adapters simultaneously:

**Two-Adapter Setup (Recommended for Drone Detection)**
- **Adapter 1**: ALFA AWUS036ACH on 2.4GHz (channels 1, 6, 11 hopping)
- **Adapter 2**: ALFA AWUS036ACH on 5GHz (channels 36, 40, 44, 48 hopping)
- **Why**: Most consumer drones operate on both bands. DJI often uses 2.4GHz for control and 5GHz for video. Two adapters = simultaneous monitoring.

**Kismet Configuration**:
```
source=wlan0:name=24ghz,hop_channels=2412 2437 2462
source=wlan1:name=5ghz,hop_channels=5180 5200 5220 5240
```

**Three-Adapter Setup (Comprehensive Coverage)**
- **Adapter 1**: 2.4GHz dedicated monitoring
- **Adapter 2**: 5GHz dedicated monitoring
- **Adapter 3**: Fixed channel on known surveillance device channel
- **Use Case**: If you've identified a suspicious device on a specific channel, lock one adapter there while the others continue scanning.

---

## GPS Hardware

GPS integration is critical for CYT's location correlation features. You need accurate coordinates, reliable Bluetooth/USB connectivity, and ideally WAAS/EGNOS support for sub-3-meter accuracy.

### Understanding GPS Accuracy

- **Consumer GPS (no augmentation)**: 5-15m accuracy
- **WAAS/EGNOS/MSAS enabled**: 2-5m accuracy
- **CYT's 100m clustering**: Works fine with consumer GPS, but better accuracy = better location session detection

### Budget Tier ($15-30)

#### VK-162 USB GPS Receiver
- **Chipset**: u-blox 7
- **Interface**: USB (acts as USB serial device)
- **Price**: $15-18
- **Accuracy**: ~3m (WAAS enabled)
- **Update Rate**: 5 Hz
- **Pros**:
  - Dirt cheap and surprisingly accurate
  - Works out-of-box on Linux (appears as /dev/ttyACM0 or /dev/ttyUSB0)
  - Small and lightweight
  - Low power draw
  - WAAS/EGNOS support
- **Cons**:
  - USB cable (not Bluetooth—less convenient for mobile)
  - No internal battery (cold start is slow)
  - Flimsy build quality
  - Poor performance indoors (typical for all GPS, but this is worse)
- **CYT Suitability**: 9/10 for budget builds
- **Where to Buy**: Amazon, eBay
- **Kismet Integration**:
```bash
# Install gpsd
sudo apt install gpsd gpsd-clients

# Test GPS
sudo gpsd /dev/ttyACM0 -F /var/run/gpsd.sock
cgps -s  # Should show coordinates after 30-60s
```

#### Garmin GLO 2 (Bluetooth)
- **Chipset**: Proprietary Garmin
- **Interface**: Bluetooth
- **Price**: $100 (refurb ~$60)
- **Accuracy**: 3m
- **Update Rate**: 10 Hz
- **Pros**:
  - Bluetooth (wireless, convenient)
  - Rechargeable battery (13-hour runtime)
  - Fast TTFF (time to first fix)
  - Waterproof
- **Cons**:
  - More expensive
  - Requires Bluetooth serial profile configuration
  - Overkill for stationary use
- **CYT Suitability**: 8/10 for mobile deployments
- **Where to Buy**: Amazon, Garmin website

### Mid-Range Tier ($40-80)

#### GlobalSat BU-353S4 USB GPS Receiver
- **Chipset**: SiRF Star IV
- **Interface**: USB
- **Price**: $40-45
- **Accuracy**: 2.5m (WAAS)
- **Update Rate**: 1 Hz
- **Pros**:
  - Industry standard for Linux GPS work
  - Magnetic mount base (great for vehicle roof mounting)
  - Excellent WAAS performance
  - Waterproof housing
  - Reliable drivers across all Linux distros
  - 5-year track record of stability
- **Cons**:
  - Larger form factor
  - USB cable (6ft, but still tethered)
  - 1 Hz update (fine for walking/driving, but not high-speed applications)
- **CYT Suitability**: 10/10 (the recommended choice)
- **Where to Buy**: Amazon, GPS City
- **Kismet Integration**: Plug-and-play with gpsd. Just works.

#### Dual Electronics XGPS160 (Bluetooth)
- **Chipset**: MediaTek MT3333
- **Interface**: Bluetooth
- **Price**: $80-90
- **Accuracy**: 2.5m (WAAS/EGNOS)
- **Update Rate**: 10 Hz
- **Pros**:
  - Excellent Bluetooth range (30+ feet)
  - Rechargeable battery (8.5 hours)
  - Fast satellite acquisition
  - Works with multiple devices simultaneously
  - Rugged waterproof design
- **Cons**:
  - More expensive
  - Bluetooth pairing can be finicky on some Linux distros
  - Requires BlueZ RFCOMM setup
- **CYT Suitability**: 9/10 for mobile use
- **Where to Buy**: Amazon, West Marine

**Bluetooth GPS Setup on Linux**:
```bash
# Pair the device
bluetoothctl
> scan on
> pair XX:XX:XX:XX:XX:XX
> trust XX:XX:XX:XX:XX:XX
> connect XX:XX:XX:XX:XX:XX

# Bind to RFCOMM
sudo rfcomm bind /dev/rfcomm0 XX:XX:XX:XX:XX:XX

# Configure gpsd
sudo gpsd /dev/rfcomm0 -F /var/run/gpsd.sock

# Verify
cgps -s
```

### Professional Tier ($150-400)

#### u-blox NEO-M8N USB GPS Module
- **Chipset**: u-blox 8
- **Interface**: USB or UART
- **Price**: $40-60 (module), $150+ (commercial enclosures)
- **Accuracy**: 2.5m (standalone), <1m with RTK
- **Update Rate**: Configurable (up to 18 Hz)
- **Pros**:
  - Professional-grade accuracy
  - Configurable via u-center software
  - Can integrate with external antennas for vehicle/building installations
  - RTK-capable for centimeter accuracy (requires base station)
  - Excellent for permanent installations
- **Cons**:
  - Requires technical setup
  - Raw modules need enclosures
  - RTK setup is complex and expensive
  - Overkill for mobile surveillance detection
- **CYT Suitability**: 7/10 (great for fixed installations, too much for mobile)
- **Where to Buy**: SparkFun, Adafruit, Mouser

#### Bad Elf GPS Pro+ (Bluetooth/USB)
- **Chipset**: SiRF
- **Interface**: Bluetooth and USB
- **Price**: $200-250
- **Accuracy**: 2.5m
- **Update Rate**: 10 Hz
- **Pros**:
  - Dual Bluetooth/USB modes
  - Built-in data logging (64MB)
  - Display screen (shows satellite count, coordinates)
  - Replaceable battery
  - Rugged, waterproof design
  - Works as standalone logger without computer
- **Cons**:
  - Expensive for what it is
  - Battery is proprietary
  - Designed for iOS/Android, Linux support requires manual setup
- **CYT Suitability**: 6/10 (great hardware, but not worth the premium for this project)
- **Where to Buy**: Amazon, Bad Elf website

### GPS Antenna Upgrades

If you're doing vehicle or fixed installations, an external antenna can dramatically improve performance, especially indoors.

#### Bingfu Active GPS Antenna
- **Connector**: SMA male
- **Cable**: 3m/10ft
- **Gain**: 28dB active amplification
- **Price**: $20-25
- **Use Case**: Connect to u-blox modules or GPS units with external antenna jacks. Mount on vehicle roof or window for 2x better signal vs. internal antenna.

---

## Computing Platforms

The computing platform needs to handle real-time packet processing, SQLite database writes, GPS parsing, and the Kivy GUI (if running in graphical mode). Here's what works.

### Minimum Requirements for CYT

- **CPU**: Dual-core 1.5GHz+ (quad-core recommended for GUI mode)
- **RAM**: 2GB minimum, 4GB recommended, 8GB ideal
- **Storage**: 16GB minimum (8GB OS + logs), 64GB+ recommended for long-term database storage
- **I/O**: 2+ USB ports (1 for Wi-Fi adapter, 1 for GPS)
- **Network**: Ethernet or secondary Wi-Fi for remote access (optional)

### Single-Board Computers (SBC)

#### Raspberry Pi 4 Model B (4GB or 8GB)
- **CPU**: Quad-core Cortex-A72 @ 1.8GHz
- **RAM**: 4GB or 8GB LPDDR4
- **Price**: $55 (4GB), $75 (8GB)
- **Storage**: MicroSD (use 64GB+ Samsung EVO Plus or SanDisk Extreme)
- **Pros**:
  - Excellent Linux support (Raspberry Pi OS, Ubuntu)
  - Low power (3-5W under load)
  - Massive community and documentation
  - GPIO for hardware hacking (could add LED indicators, buttons, etc.)
  - Small form factor (credit card size)
  - Can run headless or with display
- **Cons**:
  - USB 3.0 shares bandwidth with Gigabit Ethernet (not an issue for this project)
  - MicroSD can be slow (use A2-rated cards or USB SSD boot)
  - Limited RAM expansion
  - ARM architecture (most software works, but occasionally compatibility issues)
- **CYT Suitability**: 9/10 for mobile, 8/10 for stationary
- **Where to Buy**: Adafruit, CanaKit, Amazon
- **Setup Notes**:
```bash
# Install 64-bit Raspberry Pi OS Lite
# Enable SSH and configure Wi-Fi via raspi-config
sudo raspi-config

# Install Kismet (from official repo for latest version)
wget -O - https://www.kismetwireless.net/repos/kismet-release.gpg.key | sudo apt-key add -
echo 'deb https://www.kismetwireless.net/repos/apt/release/buster buster main' | sudo tee /etc/apt/sources.list.d/kismet.list
sudo apt update
sudo apt install kismet

# Install CYT dependencies
sudo apt install python3-pip gpsd gpsd-clients sqlite3
pip3 install -r /path/to/requirements.txt

# Optional: Boot from USB SSD for better performance
# Use Raspberry Pi Imager to flash SSD, update EEPROM to boot from USB
```

#### Raspberry Pi 5 (8GB)
- **CPU**: Quad-core Cortex-A76 @ 2.4GHz
- **RAM**: 8GB LPDDR4X
- **Price**: $80
- **Pros**:
  - Significantly faster than Pi 4 (2-3x in some workloads)
  - PCIe support (can use M.2 SSDs with HAT)
  - Improved I/O performance
- **Cons**:
  - Higher power consumption (5-8W)
  - Requires active cooling
  - More expensive
  - Newer platform = occasionally software isn't optimized yet
- **CYT Suitability**: 9/10
- **Where to Buy**: Adafruit, CanaKit

#### Orange Pi 5 Plus (16GB)
- **CPU**: Rockchip RK3588 (4x Cortex-A76 + 4x Cortex-A55)
- **RAM**: 16GB LPDDR4X
- **Price**: $130-150
- **Storage**: M.2 NVMe slot (huge advantage)
- **Pros**:
  - Significantly more powerful than any Raspberry Pi
  - 16GB RAM (can run complex analysis and GUI simultaneously)
  - Native M.2 NVMe support (blazing fast database access)
  - Dual 2.5G Ethernet
  - Great for stationary/base station setups
- **Cons**:
  - Less community support than Raspberry Pi
  - Orange Pi OS is Debian-based but occasionally has quirks
  - Higher power consumption
  - Overkill for simple mobile deployments
- **CYT Suitability**: 8/10 (best for stationary/lab setups)
- **Where to Buy**: AliExpress, Amazon

### Mini PCs

#### Intel NUC (Various Models)
- **Recommended Model**: NUC11PAHi3 (i3-1115G4, 8GB RAM, 256GB SSD)
- **Price**: $250-300 (new), $150-200 (used/refurb)
- **CPU**: Dual-core i3 @ 3.0GHz (TurboBoost 4.1GHz)
- **Pros**:
  - x86 architecture (100% software compatibility)
  - Fast Intel SSD storage
  - Low power (15-25W)
  - Silent operation
  - Expandable RAM and storage
  - Multiple USB ports (USB-A and USB-C)
  - Gigabit Ethernet
  - Can run headless or with monitor
  - Easy to install Ubuntu/Debian
- **Cons**:
  - More expensive than SBCs
  - Larger form factor (not pocket-sized)
  - Requires external power adapter (not battery-powered)
- **CYT Suitability**: 10/10 for stationary, 7/10 for mobile (needs power)
- **Where to Buy**: Amazon, Newegg, eBay (used market is great)

#### Beelink Mini PC (e.g., SEi12 i5-12450H)
- **CPU**: Intel i5-12450H (8 cores)
- **RAM**: 16GB DDR4 (expandable to 64GB)
- **Storage**: 500GB NVMe SSD
- **Price**: $350-400
- **Pros**:
  - Powerful desktop-class CPU
  - Massive RAM and storage
  - Multiple display outputs
  - Great for running VM labs alongside CYT
  - Excellent value
- **Cons**:
  - Higher power consumption (35-45W)
  - Larger than NUC
  - Overkill for basic CYT deployments
- **CYT Suitability**: 10/10 for lab/research setups, 5/10 for mobile
- **Where to Buy**: Amazon, AliExpress

### Laptops (Used/Refurbished)

For mobile deployments, a used business laptop is often the best choice. You get a battery, display, keyboard, and trackpad in one package.

#### Recommended Models (Used Market)
- **Lenovo ThinkPad T480 / T490**
  - CPU: i5-8250U or better
  - RAM: 8GB+ (upgradeable)
  - Price: $200-300 refurbished
  - Pros: Legendary build quality, excellent Linux support, hot-swappable battery, plenty of USB ports

- **Dell Latitude 5400 / 7400**
  - CPU: i5-8265U or better
  - RAM: 8GB+
  - Price: $250-350 refurbished
  - Pros: Great keyboard, good battery life, business-grade durability

- **HP EliteBook 840 G5/G6**
  - CPU: i5-8250U or better
  - RAM: 8GB+
  - Price: $200-300 refurbished
  - Pros: Solid build, good Linux compatibility

**Why Used Business Laptops?**
- Built-in battery (6-10 hour runtime for mobile surveillance detection)
- Built-in display and keyboard (no external accessories needed)
- Excellent Linux compatibility (business models are tested extensively)
- Rugged construction (designed for field work)
- Cheap on the used market (companies dump 3-year-old lease returns)

**CYT Suitability**: 10/10 for mobile deployments

**Where to Buy**: eBay, Amazon Renewed, Newegg Marketplace, local university surplus

### Comparison Table

| Platform | CPU Power | RAM | Storage | Power Draw | Price | Best Use Case |
|----------|-----------|-----|---------|------------|-------|---------------|
| Raspberry Pi 4 (4GB) | Medium | 4GB | MicroSD/USB | 3-5W | $55 | Budget mobile |
| Raspberry Pi 5 (8GB) | High | 8GB | MicroSD/USB | 5-8W | $80 | Advanced mobile |
| Orange Pi 5 Plus | Very High | 16GB | NVMe | 10-15W | $150 | Stationary/lab |
| Intel NUC i3 | High | 8GB+ | NVMe | 15-25W | $250 | Stationary |
| Beelink Mini i5 | Very High | 16GB+ | NVMe | 35-45W | $400 | Lab/research |
| Used ThinkPad T480 | High | 8GB+ | SSD | 15-25W (battery) | $250 | Mobile (best overall) |

---

## Antennas

Antennas determine your detection range. The stock antennas on most adapters are fine for close-range work, but upgrading can double or triple your effective range.

### Antenna Basics

**Key Specifications:**
- **Gain (dBi)**: Higher = more range, but narrower beam. 5-9dBi is ideal for mobile, 12-15dBi for stationary.
- **Frequency**: Must match your adapter (2.4GHz, 5GHz, or dual-band).
- **Connector**: Most ALFA adapters use RP-SMA (reverse polarity SMA). Verify before buying.
- **Polarization**: Omnidirectional (360-degree coverage) vs. directional (focused beam).

**CYT Use Case**: For surveillance detection, you want omnidirectional antennas. You don't know where the threat is coming from, so 360-degree coverage is essential. Directional antennas are for direction-finding after you've identified a target.

### Budget Tier ($10-25)

#### ALFA ARS-N19 9dBi Omni (2.4GHz)
- **Frequency**: 2.4GHz
- **Gain**: 9dBi
- **Connector**: RP-SMA male
- **Price**: $15-18
- **Pros**:
  - Affordable upgrade from stock 5dBi antennas
  - Good build quality
  - Noticeable range improvement (30-50% over stock)
  - Magnetic base available
- **Cons**:
  - 2.4GHz only
  - Large form factor (13 inches tall)
  - Not ideal for mobile/pocket deployments
- **CYT Suitability**: 9/10 for stationary 2.4GHz work
- **Where to Buy**: Amazon, ROKland

#### Bingfu Dual-Band 5dBi RP-SMA
- **Frequency**: 2.4GHz + 5GHz
- **Gain**: 5dBi
- **Connector**: RP-SMA male
- **Price**: $12-15
- **Pros**:
  - Cheap dual-band option
  - Compact (6 inches)
  - Articulated base (can angle for optimal positioning)
- **Cons**:
  - Only 5dBi (same as most stock antennas)
  - Build quality is acceptable but not great
  - Minimal range improvement
- **CYT Suitability**: 7/10 (good backup, not a significant upgrade)
- **Where to Buy**: Amazon

### Mid-Range Tier ($25-60)

#### ALFA AOA-2409TF 9dBi Dual-Band Omni
- **Frequency**: 2.4GHz + 5GHz
- **Gain**: 9dBi (both bands)
- **Connector**: RP-SMA male
- **Price**: $35-40
- **Pros**:
  - Excellent dual-band performance
  - Noticeably better range than stock antennas
  - Articulated base
  - Quality construction
  - Designed specifically for wireless auditing
- **Cons**:
  - Tall (10 inches)
  - Not ideal for stealth deployments
- **CYT Suitability**: 10/10 for stationary/vehicle use
- **Where to Buy**: Amazon, ROKland, Hak5

#### ALFA APA-M25 Dual-Band Panel Directional (7dBi)
- **Frequency**: 2.4GHz + 5GHz
- **Gain**: 7dBi
- **Type**: Directional panel
- **Price**: $50-60
- **Pros**:
  - Focused beam (30-degree cone)
  - Great for direction-finding after identifying a suspicious device
  - Can significantly extend range (2-3x vs. omni)
  - Mounting holes for tripod or wall
- **Cons**:
  - Directional (not suitable for initial scanning)
  - Requires manual aiming
  - Larger form factor
- **CYT Suitability**: 7/10 (specialized use case: direction-finding)
- **Where to Buy**: ROKland, Hak5

### Professional Tier ($60-150)

#### L-com HG2409U 9dBi Fiberglass Omni
- **Frequency**: 2.4GHz
- **Gain**: 9dBi
- **Type**: Omnidirectional collinear
- **Price**: $60-70
- **Pros**:
  - Professional-grade construction (fiberglass radome)
  - Weather-resistant (outdoor-rated)
  - N-female connector (requires adapter to RP-SMA)
  - Excellent for permanent installations
  - Reliable performance in all conditions
- **Cons**:
  - Large (24 inches)
  - 2.4GHz only
  - Requires mounting bracket
  - Overkill for portable use
- **CYT Suitability**: 10/10 for fixed outdoor installations
- **Where to Buy**: L-com, Amazon

#### Ubiquiti AirMax 2x2 MIMO Omni (AM-2G16-90)
- **Frequency**: 2.4GHz
- **Gain**: 16dBi
- **Type**: Sector antenna (90-degree beam)
- **Price**: $130-150
- **Pros**:
  - Extreme range (miles with line-of-sight)
  - MIMO support (works with multi-antenna adapters like AWUS1900)
  - Weather-resistant
  - Designed for WISP/long-range applications
- **Cons**:
  - Sector pattern (not true omnidirectional)
  - Massive form factor (3 feet tall)
  - Requires mounting and weatherproof enclosure for adapter
  - Way overkill for typical surveillance detection
- **CYT Suitability**: 6/10 (useful for perimeter monitoring of large properties)
- **Where to Buy**: Ubiquiti, WISP distributors

### Antenna Cables and Adapters

If you're mounting an external antenna (e.g., on a vehicle roof), you'll need quality low-loss cable.

#### LMR-240 or LMR-400 Coaxial Cable
- **Type**: Low-loss 50-ohm coax
- **Connectors**: RP-SMA to N-type or RP-SMA to RP-SMA
- **Lengths**: 3ft, 6ft, 10ft, 25ft
- **Price**: $15-50 depending on length and quality
- **Loss**: LMR-240 = ~0.3dB/ft @ 2.4GHz, LMR-400 = ~0.15dB/ft
- **CYT Use**: Connect external antenna to adapter. Keep cable runs short to minimize signal loss.
- **Where to Buy**: L-com, Amazon, Times Microwave

---

## Power Solutions

For mobile surveillance detection, battery life is critical. You don't want your system dying mid-session.

### Power Consumption Estimates

- **Raspberry Pi 4 + ALFA AWUS036ACH + VK-162 GPS**: ~8-10W under load
- **Laptop (used ThinkPad)**: ~15-25W
- **Intel NUC**: ~15-30W

### USB Power Banks

#### Anker PowerCore 20100 (20000mAh)
- **Capacity**: 20000mAh @ 3.7V = 74Wh
- **Output**: 2x USB-A (5V/3A each)
- **Price**: $30-35
- **Runtime**:
  - Raspberry Pi setup: ~7-9 hours
  - Not suitable for laptops (5V only)
- **Pros**: Cheap, reliable, compact, well-reviewed
- **Cons**: No USB-C PD, 5V only
- **CYT Suitability**: 9/10 for Pi-based mobile setups
- **Where to Buy**: Amazon

#### RAVPower 26800mAh PD 3.0
- **Capacity**: 26800mAh = 99Wh (airline carry-on limit)
- **Output**: 1x USB-C PD (30W), 2x USB-A
- **Price**: $50-60
- **Runtime**:
  - Raspberry Pi: 12-15 hours
  - Laptop (25W draw): 3-4 hours
- **Pros**: USB-C PD for laptops, high capacity, fast charging
- **Cons**: Heavier than smaller banks
- **CYT Suitability**: 10/10 for all mobile setups
- **Where to Buy**: Amazon

#### Omni 20+ USB-C (20000mAh)
- **Capacity**: 20000mAh (73Wh)
- **Output**: 1x 100W USB-C PD, 1x 60W USB-C, 2x USB-A, 1x DC barrel jack
- **Price**: $150-180
- **Pros**:
  - Can power hungry laptops (100W output)
  - Multiple outputs (charge phone + run laptop + power adapter simultaneously)
  - Display screen shows remaining capacity
  - Premium build quality
- **Cons**: Expensive, heavy (1.3 lbs)
- **CYT Suitability**: 8/10 (excellent but pricey)
- **Where to Buy**: Amazon, Omnicharge website

### DC Battery Solutions (12V)

For vehicle installations or extended off-grid use, 12V systems are more efficient.

#### Talentcell 12V 6000mAh Rechargeable Battery
- **Capacity**: 6000mAh @ 12V = 72Wh
- **Output**: 12V DC barrel jack + 5V USB
- **Price**: $30-35
- **Runtime**: Powers Pi or small laptop for 8-12 hours
- **Pros**: True 12V output (more efficient than USB-C PD step-down), compact, cheap
- **Cons**: Proprietary charger, DC barrel connector (requires adapter for USB devices)
- **CYT Suitability**: 9/10 for vehicle/off-grid use
- **Where to Buy**: Amazon

#### 12V LiFePO4 Batteries (various sizes)
- **Example**: Ampere Time 12V 50Ah LiFePO4
- **Capacity**: 50Ah @ 12V = 600Wh
- **Price**: $180-250
- **Runtime**: Days of continuous operation
- **Pros**: Massive capacity, 3000+ charge cycles, safe chemistry, can power inverter for AC devices
- **Cons**: Heavy (15-30 lbs), requires charge controller, overkill for walking-around use
- **CYT Suitability**: 10/10 for permanent off-grid installations
- **Where to Buy**: Amazon, Battle Born, Ampere Time

### Solar Charging (Extended Deployments)

If you're setting up a remote monitoring station, solar keeps you running indefinitely.

#### Goal Zero Nomad 20 Solar Panel
- **Output**: 20W (USB + 8mm port)
- **Price**: $130-150
- **Use Case**: Trickle-charge power banks during daytime
- **Pairs Well With**: Goal Zero Sherpa 100AC power bank
- **CYT Suitability**: 8/10 for remote stationary setups
- **Where to Buy**: Amazon, REI

#### Renogy 50W 12V Solar Panel + Wanderer 10A Charge Controller
- **Output**: 50W
- **Price**: $90 (panel) + $25 (controller) = $115
- **Use Case**: Charge 12V LiFePO4 battery for permanent remote installations
- **CYT Suitability**: 10/10 for off-grid base stations
- **Where to Buy**: Amazon, Renogy

---

## Accessories and Enclosures

### Weatherproof Enclosures

#### Pelican 1200 Case
- **Dimensions**: 9.25" x 7.12" x 4.12"
- **Price**: $50-60
- **Use Case**: Protect Pi/NUC setup in vehicle or outdoor deployment
- **Pros**: Waterproof (IP67), crushproof, foam inserts customizable
- **Cons**: Not cheap, adds bulk
- **Where to Buy**: Amazon, Pelican

#### Outdoor NEMA Electrical Box
- **Dimensions**: Various (12x10x6 is common)
- **Price**: $30-50
- **Use Case**: Permanent outdoor installations
- **Pros**: Weather-resistant, easy to mount, cheap
- **Cons**: Not portable, requires drilling for cables
- **Where to Buy**: Home Depot, Lowe's, Amazon

### Cable Management

#### Velcro Cable Ties
- **Price**: $10 for 100-pack
- **Use Case**: Keep USB cables, antenna cables, power cables organized
- **Where to Buy**: Amazon, Monoprice

#### Cable Glands/Strain Reliefs
- **Price**: $1-3 each
- **Use Case**: Weatherproof cable entry points for outdoor enclosures
- **Where to Buy**: Amazon, electrical supply stores

### Displays (Headless Operation)

Most CYT deployments will run headless (no monitor), accessed via SSH or VNC. But for initial setup or field diagnostics, a display can be handy.

#### Raspberry Pi Official 7" Touchscreen
- **Resolution**: 800x480
- **Price**: $70-80
- **Pros**: Designed for Pi, HDMI-free (DSI connector), touchscreen
- **Cons**: Low resolution, Pi-specific (won't work with other platforms)
- **Where to Buy**: Adafruit, Amazon

#### Portable HDMI Monitor (e.g., ASUS MB16AC)
- **Resolution**: 1920x1080
- **Size**: 15.6"
- **Price**: $180-220
- **Pros**: Works with any HDMI device, USB-C powered, great quality
- **Cons**: Expensive, adds bulk
- **Where to Buy**: Amazon, Newegg

---

## Advanced Equipment

### Software Defined Radio (SDR)

SDR extends CYT's detection capabilities beyond Wi-Fi to the entire RF spectrum. Great for detecting non-Wi-Fi surveillance devices (Bluetooth trackers, GPS jammers, hidden cameras on 1.2GHz, etc.).

#### RTL-SDR Blog V3
- **Frequency Range**: 500kHz - 1.7GHz
- **Price**: $35-40
- **Pros**:
  - Extremely cheap entry into SDR
  - Excellent community support
  - Works with GQRX, SDR++, Kismet (for Bluetooth)
  - Can monitor aircraft (ADS-B), weather satellites (NOAA), Bluetooth, etc.
- **Cons**:
  - Limited to receive-only (no transmit)
  - 8-bit ADC (lower dynamic range than professional SDRs)
  - Requires significant software setup
- **CYT Integration**: Can feed Bluetooth data to Kismet for tracker detection (AirTags, Tiles)
- **Where to Buy**: RTL-SDR.com, Amazon

#### HackRF One
- **Frequency Range**: 1MHz - 6GHz
- **Price**: $300-350
- **Pros**:
  - Full-duplex transmit/receive (half-duplex in practice)
  - Wide frequency coverage (covers all ISM bands, cellular, etc.)
  - Open-source hardware
  - Great for research and experimentation
- **Cons**:
  - Expensive for hobbyist use
  - Transmitting is legally complex (requires amateur radio license or controlled environment)
  - Steeper learning curve
- **CYT Integration**: Overkill for passive surveillance detection, but useful for advanced research (e.g., analyzing proprietary drone protocols)
- **Where to Buy**: Great Scott Gadgets, Hak5

### Cellular/Stingray Detection

CYT already has a Stingray detection module. Here's the hardware to support it.

#### Cellular USB Modem (e.g., Quectel EG25-G)
- **Technology**: 4G LTE
- **Price**: $60-80 (module), $100+ (USB development board)
- **Use Case**: Monitors cellular network parameters (signal strength, serving cell ID, neighboring cells)
- **CYT Integration**: Detect IMSI catchers by identifying fake cell towers (abnormal signal patterns, cell ID changes)
- **Complexity**: High—requires AT command scripting and understanding of cellular protocols
- **Where to Buy**: Quectel, AliExpress, Amazon

#### bladeRF 2.0 Micro xA4
- **Frequency Range**: 47MHz - 6GHz
- **Price**: $400-500
- **Use Case**: Advanced cellular monitoring and research
- **Pros**: Excellent for analyzing LTE/5G downlink signals, identifying fake base stations
- **Cons**: Expensive, very steep learning curve, requires GNURadio expertise
- **CYT Integration**: Research-grade overkill, but possible for advanced users
- **Where to Buy**: Nuand

### Direction Finding

Once you've detected a suspicious device, direction finding helps you physically locate it.

#### Directional Antenna + Signal Strength Monitoring
- **Equipment**: ALFA APA-M25 panel antenna + Kismet signal strength logging
- **Technique**: Point antenna in different directions, track signal strength, triangulate
- **Price**: $50 (antenna)
- **Pros**: Simple, works with existing equipment
- **Cons**: Slow, requires manual process

#### Yagi Antenna (e.g., TP-Link TL-ANT2414A)
- **Frequency**: 2.4GHz
- **Gain**: 14dBi
- **Price**: $40-50
- **Use Case**: High-gain directional antenna for precision direction finding
- **Where to Buy**: Amazon, Newegg

#### HackRF + RDF Techniques
- **Technique**: Use HackRF to measure signal phase difference with two antennas spaced apart, calculate bearing
- **Complexity**: Very high—requires custom software and signal processing
- **Use Case**: Research and advanced users only

---

## Complete Build Examples

Let me tie this all together with recommended complete builds for different use cases.

### Build 1: Budget Mobile Surveillance Detection ($200)

**Goal**: Walking-around surveillance detection on a tight budget.

**Components**:
- Raspberry Pi 4 4GB - $55
- ALFA AWUS036NHA (2.4GHz) - $35
- VK-162 USB GPS - $15
- 64GB Samsung EVO Plus MicroSD - $12
- Anker PowerCore 20100 - $30
- Basic case for Pi - $10
- USB cables and adapters - $10
- **Total**: ~$170

**Capabilities**:
- 2.4GHz surveillance detection (most drones, trackers, cameras)
- 7-9 hour runtime
- Pocket-sized (can fit in backpack or large jacket pocket)
- Headless operation (SSH from phone)

**Limitations**:
- No 5GHz detection
- Limited processing power (can't run heavy GUI, command-line only)
- MicroSD storage (slower database writes)

**Setup Difficulty**: Medium (requires Linux familiarity)

---

### Build 2: Professional Mobile Setup ($450)

**Goal**: Comprehensive mobile surveillance detection for serious field work.

**Components**:
- Used Lenovo ThinkPad T480 (i5, 8GB, 256GB SSD) - $250
- ALFA AWUS036ACH (dual-band) - $50
- BU-353S4 USB GPS - $40
- ALFA AOA-2409TF 9dBi dual-band antenna - $35
- RAVPower 26800mAh PD battery - $50
- LMR-240 6ft cable (for external antenna) - $20
- Velcro cable ties and accessories - $10
- **Total**: ~$455

**Capabilities**:
- Dual-band (2.4GHz + 5GHz) surveillance detection
- Full CYT GUI operation
- 4-6 hour runtime on battery
- Built-in display and keyboard for field diagnostics
- Extended range with upgraded antenna
- Fast SSD for large database storage

**Limitations**:
- Heavier than SBC solution (3-4 lbs)
- Laptop form factor (less discrete than pocket-sized)

**Setup Difficulty**: Easy (Ubuntu install, standard PC hardware)

**This is the recommended build for most users.**

---

### Build 3: Vehicle-Mounted Continuous Monitoring ($600)

**Goal**: Permanent vehicle installation for continuous monitoring during travel.

**Components**:
- Intel NUC i3 (8GB, 256GB) - $250
- 2x ALFA AWUS036ACH (dual-band, one for 2.4GHz, one for 5GHz) - $100
- BU-353S4 GPS with magnetic mount - $40
- 2x ALFA AOA-2409TF 9dBi antennas - $70
- 12V Talentcell 6000mAh battery - $35
- 12V to 19V DC-DC converter for NUC - $20
- 2x LMR-240 10ft cables - $40
- Pelican 1200 case - $60
- Mounting hardware and cable glands - $20
- **Total**: ~$635

**Capabilities**:
- Dual-adapter simultaneous 2.4GHz + 5GHz monitoring (no channel hopping gaps)
- Roof-mounted antennas for maximum range
- 8-12 hour runtime on battery
- Magnetic GPS mount on vehicle roof
- Weatherproof enclosure
- Can wire directly to vehicle 12V system for unlimited runtime

**Setup**:
- Mount Pelican case in vehicle trunk or under seat
- Route antenna cables to roof-mounted antennas
- Mount GPS on roof (magnetic base)
- Power from battery or vehicle 12V with DC-DC converter

**Setup Difficulty**: High (requires vehicle installation, cable routing)

---

### Build 4: Stationary Base Station / Home Lab ($800)

**Goal**: Permanent installation for monitoring a fixed location (home, office, property perimeter).

**Components**:
- Beelink Mini PC (i5, 16GB, 500GB) - $400
- ALFA AWUS1900 (high-power dual-band) - $80
- BU-353S4 GPS - $40
- L-com HG2409U 9dBi fiberglass omni (2.4GHz) - $70
- ALFA AOA-2409TF 9dBi antenna (5GHz) - $35
- 2x LMR-400 25ft cables - $80
- NEMA outdoor enclosure - $50
- UPS battery backup (CyberPower 1000VA) - $120
- Mounting pole/mast - $40
- Cable glands, weatherproofing - $20
- **Total**: ~$935

**Capabilities**:
- 24/7 continuous monitoring
- High-power adapter + high-gain antennas = mile+ range
- Outdoor-rated antennas mounted on roof or pole
- UPS keeps system running during power outages
- Large storage for months of historical data
- Powerful CPU for running analysis, reports, and GUI simultaneously

**Setup**:
- Mount antennas on roof or pole
- Run LMR-400 cables to indoor Mini PC location
- Place adapter and PC in climate-controlled space
- Set up Kismet and CYT as systemd services for auto-start
- Configure remote access (SSH, VNC, or web UI)

**Setup Difficulty**: High (requires outdoor installation, cable routing, Linux sysadmin)

---

### Build 5: Research / Advanced Detection Platform ($1500+)

**Goal**: Comprehensive RF surveillance detection covering Wi-Fi, Bluetooth, cellular, and unknown signals.

**Components**:
- High-end laptop (ThinkPad P14s or similar, 32GB RAM) - $800
- 2x ALFA AWUS036ACH (dual-band) - $100
- ALFA AWUS1900 (high-power) - $80
- RTL-SDR Blog V3 - $40
- HackRF One - $350
- BU-353S4 GPS - $40
- Directional Yagi antenna (2.4GHz) - $50
- ALFA panel antenna (dual-band) - $60
- Multiple LMR-240/400 cables - $100
- Battery bank (Omni 20+) - $180
- Accessories, adapters, tools - $100
- **Total**: ~$1900

**Capabilities**:
- Multi-adapter Wi-Fi monitoring (simultaneous channels)
- SDR for Bluetooth, ADS-B, satellite, unknown signals
- HackRF for transmit/receive experimentation
- Direction-finding capability
- Advanced research platform
- Powerful laptop for signal processing and analysis

**Use Case**: Security research, professional penetration testing, advanced threat hunting

**Setup Difficulty**: Expert (requires deep RF and Linux knowledge)

---

## Troubleshooting and Compatibility

### Common Issues and Solutions

#### Wi-Fi Adapter Not Entering Monitor Mode

**Symptom**: `sudo iw dev wlan1 set type monitor` fails with "operation not supported"

**Causes and Fixes**:
1. **Wrong chipset/driver**: Verify chipset with `lsusb` and cross-reference against known-good lists.
2. **Driver not installed**: For RTL8812AU adapters, install aircrack-ng driver from GitHub.
3. **NetworkManager interfering**: Kill NetworkManager: `sudo systemctl stop NetworkManager`
4. **Adapter in use**: Kill processes: `sudo airmon-ng check kill`

**Verification**:
```bash
sudo ip link set wlan1 down
sudo iw dev wlan1 set type monitor
sudo ip link set wlan1 up
iwconfig wlan1  # Should show "Mode:Monitor"
```

#### GPS Not Providing Coordinates

**Symptom**: `cgps -s` shows "No Fix" or no satellites

**Causes and Fixes**:
1. **Indoors**: GPS requires line-of-sight to sky. Go outside or near window.
2. **Cold start**: Wait 2-5 minutes for initial satellite acquisition.
3. **gpsd not running**: Start with `sudo gpsd /dev/ttyACM0 -F /var/run/gpsd.sock`
4. **Wrong device path**: Check `dmesg | grep tty` after plugging in GPS to find correct device.
5. **USB power issue**: Some hubs don't provide enough power. Try direct connection.

**Verification**:
```bash
sudo gpsd /dev/ttyACM0 -F /var/run/gpsd.sock
cgps -s  # Wait 2 minutes, should show lat/lon and satellite count
```

#### Kismet Not Detecting Wi-Fi Adapter

**Symptom**: Kismet starts but shows no sources or "no packet sources available"

**Causes and Fixes**:
1. **Permissions**: Add user to kismet group: `sudo usermod -aG kismet $USER` (then log out/in)
2. **Wrong source configuration**: Edit `/etc/kismet/kismet_site.conf`, add: `source=wlan1:name=adapter1`
3. **Adapter not in monitor mode**: Use `iwconfig` to verify before starting Kismet
4. **Driver issue**: Check `dmesg | tail` for errors

#### Kismet Database Locked

**Symptom**: CYT fails to read Kismet database with "database is locked" error

**Causes and Fixes**:
1. **Kismet still writing**: CYT should use read-only connection (already implemented in `secure_database.py`)
2. **Permission issue**: Ensure user has read access: `sudo chmod 644 /path/to/kismet.kismet`
3. **NFS/network storage**: SQLite doesn't play well with network filesystems. Use local storage.

#### Poor GPS Accuracy

**Symptom**: GPS coordinates jump around, 20-50m error

**Causes and Fixes**:
1. **No WAAS/EGNOS**: Check if GPS supports augmentation and if it's enabled.
2. **Multipath interference**: Metal roofs, buildings cause reflections. Move to open area.
3. **Low satellite count**: Need 6+ satellites for good accuracy. Check `cgps -s` satellite view.
4. **GPS antenna placement**: For vehicle mounting, ensure GPS is on roof with clear sky view, not in trunk.

#### Adapter Overheating

**Symptom**: ALFA adapter gets very hot, eventually disconnects

**Causes and Fixes**:
1. **Normal for high-power adapters**: AWUS1900 and AWUS036ACH run hot (60-70C is normal).
2. **Poor ventilation**: Ensure airflow around adapter. Don't stuff in enclosed space.
3. **Add heatsink**: Adhesive heatsinks ($5 on Amazon) help dissipate heat.
4. **Reduce TX power** (if not needed): `sudo iw dev wlan1 set txpower fixed 1000` (10dBm)

---

## Vendor and Purchasing Guide

### Recommended Vendors

**Wi-Fi Adapters and Antennas**:
- **ROKland Technologies** (rokland.com): Specializes in ALFA products, excellent support
- **Hak5** (shop.hak5.org): Security-focused vendor, curated hardware
- **Amazon**: Convenient but verify seller (counterfeit ALFA adapters exist)

**GPS Hardware**:
- **Amazon**: Good for consumer GPS (VK-162, BU-353S4)
- **GPS City** (gpscity.com): Professional GPS equipment
- **SparkFun / Adafruit**: Excellent for GPS modules and development boards

**Computing Platforms**:
- **Adafruit / CanaKit**: Official Raspberry Pi distributors
- **Amazon Renewed / eBay**: Used laptops and NUCs (check seller ratings)
- **Newegg / B&H Photo**: New laptops and Mini PCs

**Antennas and RF Accessories**:
- **L-com** (l-com.com): Professional-grade RF components
- **Times Microwave**: High-quality coax cables
- **Amazon / Monoprice**: Budget cables and adapters

### Avoiding Counterfeits

**ALFA Adapters**: Counterfeits are common on Amazon. Verify:
- Ships from ROKland or ALFA directly
- Packaging has holographic authenticity sticker
- Driver CD included (real ALFA includes drivers)
- Check MAC address OUI (first 3 bytes should match ALFA's registered OUIs)

**GPS Receivers**: Less of an issue, but verify chipset if buying cheap:
- u-blox chips are quality (u-blox 7, u-blox 8)
- Avoid "generic GPS USB" listings without chipset info

---

## CYT Software Integration Guide

This section provides hardware-specific configuration and integration notes for the CYT codebase.

### Wi-Fi Adapter Configuration

#### ALFA AWUS036NHA (AR9271) - Plug and Play
```bash
# Verify adapter is recognized
lsusb | grep Atheros
# Should show: 0cf3:9271 Atheros Communications, Inc. AR9271 802.11n

# Check wireless interface
iwconfig
# Should show: wlan1 (or similar) IEEE 802.11

# Kismet configuration (no special setup needed)
# Edit /etc/kismet/kismet_site.conf or start with:
sudo kismet -c wlan1
```

**CYT Integration**:
- Works out-of-box with `start_kismet_clean.sh wlan1`
- Monitor mode: `sudo airmon-ng start wlan1` (if not using Kismet's auto-enable)
- No driver installation required on any Linux kernel 3.0+

#### ALFA AWUS036ACH (RTL8812AU) - Requires Driver Installation
```bash
# Install DKMS and build tools
sudo apt install dkms build-essential linux-headers-$(uname -r) git

# Clone aircrack-ng RTL8812AU driver (most stable)
cd ~/
git clone https://github.com/aircrack-ng/rtl8812au.git
cd rtl8812au

# Build and install
sudo make dkms_install

# Verify installation
sudo dkms status
# Should show: rtl8812au/5.x.x.x, kernel version, architecture: installed

# Check if adapter is recognized
lsusb | grep Realtek
# Should show: 0bda:8812 Realtek Semiconductor Corp. RTL8812AU

iwconfig
# Should show: wlan1 IEEE 802.11
```

**Troubleshooting RTL8812AU**:
```bash
# If driver doesn't load, check kernel messages
dmesg | grep 8812
dmesg | grep rtl

# Common issue: Secure Boot blocking unsigned drivers
# Solution: Disable Secure Boot in BIOS, or sign the module

# Verify module is loaded
lsmod | grep 8812

# If not loaded, try manually:
sudo modprobe 88XXau

# Check power management (can cause dropouts)
sudo iwconfig wlan1 power off
```

**CYT Integration**:
- Once driver installed, works with `start_kismet_clean.sh wlan1`
- Dual-band support: Kismet will automatically handle both 2.4GHz and 5GHz
- **Important**: Set `source=wlan1:name=dual_band,hop_rate=10` in Kismet config for best results

**Persistent Driver Installation** (survives kernel updates):
```bash
# DKMS handles automatic rebuild on kernel updates
# Verify after kernel upgrade:
sudo dkms status

# If driver missing after upgrade:
cd ~/rtl8812au
sudo make dkms_remove
sudo make dkms_install
```

#### ALFA AWUS1900 (RTL8814AU) - High-Power Dual-Band
```bash
# Similar to RTL8812AU but different driver
cd ~/
git clone https://github.com/aircrack-ng/rtl8814au.git
cd rtl8814au

sudo make dkms_install

# Verify
lsusb | grep Realtek
# Should show: 0bda:8813 Realtek Semiconductor Corp.

# This is a high-power adapter - may require powered USB hub
# Check dmesg for power warnings:
dmesg | grep "usb.*power"
```

**CYT Integration**:
- Same configuration as AWUS036ACH
- Higher TX power available: Check `/etc/kismet/kismet_site.conf` for power settings
- Recommended for stationary setups due to power requirements

### GPS Configuration

#### USB GPS (BU-353S4, VK-162, etc.)

**Install gpsd** (GPS daemon):
```bash
sudo apt install gpsd gpsd-clients python3-gps

# Stop gpsd service (we'll run it manually for testing)
sudo systemctl stop gpsd
sudo systemctl disable gpsd
```

**Identify GPS Device**:
```bash
# Plug in GPS and check which device it creates
dmesg | tail -20
# Look for: usb 1-1: pl2303 converter now attached to ttyUSB0

# Usually /dev/ttyUSB0 or /dev/ttyACM0
ls -la /dev/tty* | grep USB
```

**Test GPS**:
```bash
# Start gpsd manually
sudo gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock -n

# Check GPS data
cgps -s
# Should show satellites, fix status, lat/long (once fix acquired)

# Takes 30-60 seconds for first fix (cold start)
# 5-15 seconds for warm start (if powered off recently)
```

**Indoor vs Outdoor GPS Tips**:
- **Indoors**: USB GPS rarely works. Bluetooth GPS (e.g., Garmin GLO 2) with GLONASS/Galileo has better indoor performance.
- **Outdoors**: Position GPS receiver near window or use magnetic mount on vehicle roof.
- **Assisted GPS**: Some USB GPS receivers support A-GPS for faster fix (check manufacturer docs).

**CYT Integration with gpsd**:
```bash
# Edit config.json to use gpsd
# CYT will connect to gpsd socket for GPS data

# Start CYT with GPS enabled
python3 surveillance_analyzer.py
# GPS coordinates will be automatically extracted from Kismet if Bluetooth GPS paired
# Or use external GPS file: --gps-file coordinates.json

# Verify GPS in Kismet
# Kismet can log GPS from gpsd automatically
# Edit /etc/kismet/kismet_site.conf:
# gps=gpsd:host=localhost,port=2947
```

**Bluetooth GPS (Garmin GLO 2, Dual XGPS160, etc.)**:

```bash
# Pair Bluetooth GPS to system
bluetoothctl
# > scan on
# > pair [GPS MAC ADDRESS]
# > trust [GPS MAC ADDRESS]
# > connect [GPS MAC ADDRESS]
# > exit

# GPS will create /dev/rfcomm0 or similar
# Point gpsd at Bluetooth device:
sudo gpsd /dev/rfcomm0 -F /var/run/gpsd.sock -n

# Verify
cgps -s
```

**CYT Integration - Bluetooth GPS**:
- Kismet can automatically detect Bluetooth GPS devices
- Advantages: Better indoor performance, no USB cable, built-in battery
- **Recommended for mobile deployments**

### Kismet Database Integration

CYT reads from Kismet `.kismet` SQLite databases. Here's how to configure optimal database settings:

**Kismet Database Location**:
```bash
# Default Kismet database path
/var/log/kismet/

# CYT expects databases matching pattern in config.json:
"kismet_db_path": "/var/log/kismet/*.kismet"

# Or specify custom path:
"kismet_db_path": "/home/user/kismet_logs/*.kismet"
```

**Kismet Configuration** (`/etc/kismet/kismet_site.conf`):
```bash
# Set database location
log_prefix=/var/log/kismet/

# Enable GPS logging
gps=gpsd:host=localhost,port=2947

# Optimize database writes for CYT
# (Reduce write frequency to avoid locks while CYT reads)
db_log_commit_interval=30

# Enable channel hopping for comprehensive coverage
source=wlan1:name=surveillance,hop_rate=10,hop_channels=1,2,3,4,5,6,7,8,9,10,11,36,40,44,48,149,153,157,161

# For dual adapters (2.4GHz + 5GHz simultaneously)
source=wlan0:name=24ghz,channels=1,6,11
source=wlan1:name=5ghz,channels=36,40,44,48,149,153,157,161
```

**CYT Database Access**:
```python
# CYT uses SecureKismetDB to read Kismet databases
from secure_database import SecureKismetDB

# All database access is read-only to prevent conflicts
with SecureKismetDB(db_path) as db:
    devices = db.get_devices_by_time_range(start_time, end_time)
    # Process devices...
```

**Avoiding Database Locks**:
- Kismet writes to database every 30 seconds (configurable)
- CYT uses read-only mode: `file:{path}?mode=ro`
- If you see "database locked" errors:
  ```bash
  # Option 1: Let Kismet finish current write cycle (wait 30 sec)
  # Option 2: Copy .kismet file to separate location for analysis
  cp /var/log/kismet/Kismet-*.kismet ~/analysis/
  python3 surveillance_analyzer.py --kismet-db ~/analysis/Kismet-*.kismet
  ```

### Multi-Adapter Configuration

For comprehensive drone detection, use two adapters simultaneously:

**Setup**:
```bash
# Adapter 1: 2.4GHz (ALFA AWUS036NHA)
# Adapter 2: 5GHz capable (ALFA AWUS036ACH)

# Check both adapters detected
iwconfig
# wlan0: AR9271 (2.4GHz only)
# wlan1: RTL8812AU (dual-band, we'll use for 5GHz)

# Kismet configuration for dual-adapter monitoring
sudo kismet -c wlan0:name=24ghz,hop_channels=1,6,11 \
             -c wlan1:name=5ghz,hop_channels=36,40,44,48,149,153,157,161
```

**CYT Integration**:
- Single Kismet database will contain devices from both adapters
- Drone detection (`probe_analyzer.py`) will see both 2.4GHz and 5GHz devices
- **Critical for DJI Mavic 3, Skydio 2**: These drones use 5GHz exclusively

### Performance Tuning

**For Raspberry Pi**:
```bash
# Increase USB buffer size for better packet capture
sudo sh -c 'echo 128 > /sys/module/usbcore/parameters/usbfs_memory_mb'

# Disable Wi-Fi power management (prevents packet loss)
sudo iwconfig wlan1 power off

# Reduce Kismet logging verbosity (saves CPU)
# Edit /etc/kismet/kismet_logging.conf:
# log_types=kismet,pcapng
# Remove: gps, alert, device

# Use lighter GUI or headless operation
python3 chasing_your_tail.py  # CLI only, lower resource usage
```

**For Laptops**:
```bash
# Disable laptop Wi-Fi power saving
sudo iwconfig wlan0 power off

# Ensure USB selective suspend disabled (prevents GPS dropouts)
# Edit /etc/default/grub:
# GRUB_CMDLINE_LINUX_DEFAULT="... usbcore.autosuspend=-1"
sudo update-grub
```

**Database Storage Considerations**:
```bash
# Kismet databases grow quickly (100-500MB per hour in dense areas)
# Monitor disk usage
du -h /var/log/kismet/

# CYT history database (cyt_history.db) grows more slowly
du -h ./cyt_history.db

# Recommended: 64GB+ storage for 1 week of 24/7 monitoring
# Or use log rotation:
# Create /etc/logrotate.d/kismet
/var/log/kismet/*.kismet {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

---

## Vehicle Mounting and Personal Carry Options

Effective surveillance detection requires mobile deployment. Here are proven mounting and carry solutions.

### Vehicle Mounting Solutions

#### Roof-Mounted GPS + Wi-Fi Setup (Professional)

**Components**:
- BU-353S4 GPS with magnetic mount - $40
- ALFA AOA-2409TF 9dBi antenna with magnetic mount - $35
- LMR-240 ultra-low-loss coax cable (10-15ft) - $30
- RAM Mounts X-Grip phone holder (for laptop/SBC) - $40
- 12V car charger (USB-C PD for laptop) - $25
- **Total**: ~$170

**Installation**:
```
1. Magnetic GPS Mount:
   - Place BU-353S4 on vehicle roof (magnetic base)
   - Route USB cable through door seal or window
   - Tape cable edge along door frame to prevent pinching
   - Secure with electrical tape or velcro strips

2. Wi-Fi Antenna:
   - Magnetic mount for ALFA antenna on roof
   - Use LMR-240 coax from antenna → adapter inside vehicle
   - LMR-240 reduces signal loss (better than RG-58 or cheap coax)
   - SMA/RP-SMA adapter: antenna → cable → Wi-Fi adapter

3. Computing Platform Mounting:
   - Dashboard: Use RAM Mounts with adhesive base
   - Center console: Velcro platform mount
   - Passenger seat: Laptop bag with rigid base
   - Ensure airflow for cooling

4. Power:
   - 12V socket → USB-C PD charger (45W+ for laptops)
   - Or hardwired: 12V → 5V buck converter → USB
   - Add inline fuse (3A) for safety

5. Cable Management:
   - Use spiral cable wrap or velcro straps
   - Avoid routing near pedals or shifter
   - Label cables (GPS, Wi-Fi, Power) for easy disconnect
```

**Advantages**:
- Optimal GPS reception (roof mount, clear sky view)
- Extended Wi-Fi range (roof antenna vs. internal adapter)
- Semi-permanent installation (quick connect/disconnect)
- Professional appearance

**Disadvantages**:
- Visible external hardware (less discrete)
- Requires drilling holes or careful cable routing
- Theft risk (magnetic mounts can be pulled off)

#### Dashboard Mounted (Discrete)

**Components**:
- Laptop or NUC with built-in display
- USB GPS puck (VK-162 or BU-353S4 without external mount)
- ALFA AWUS036ACH adapter (compact, no external antenna)
- RAM Mounts suction cup mount - $30
- 12V car charger - $25
- **Total**: ~$55 (excluding computer/adapter)

**Installation**:
```
1. Laptop/NUC Position:
   - Use RAM Mounts suction cup on windshield or dashboard
   - Angle display for easy viewing without blocking forward vision
   - Passenger side dashboard preferred (not in driver's line of sight)

2. GPS Placement:
   - Place GPS puck on dashboard near windshield
   - Use velcro or adhesive putty (removable)
   - Ensure clear sky view (avoid metal dashboard, heated glass)

3. Wi-Fi Adapter:
   - Plug directly into laptop USB port
   - Or use short USB extension (6") to position adapter near window

4. Power:
   - Run 12V cable from cigarette lighter → laptop charger
   - Secure cable along dashboard edge with clips

5. Cable Management:
   - Use cable clips along dashboard
   - Bundle with velcro straps
   - Ensure cables don't interfere with vents or controls
```

**Advantages**:
- Quick setup/teardown (under 5 minutes)
- All components inside vehicle (less theft risk)
- Discrete (looks like laptop navigation)
- No permanent modifications

**Disadvantages**:
- GPS performance limited (dashboard vs. roof mount)
- Wi-Fi range reduced (no external antenna)
- Dashboard space required

#### Center Console / Passenger Seat (Mobile)

**Best for**: Uber/Lyft drivers, rideshare surveillance detection, temporary deployments

**Components**:
- Laptop or tablet (with CYT running)
- USB GPS (internal placement)
- USB Wi-Fi adapter
- Laptop bag or padded case
- Velcro strips for cable management
- 12V charger or battery pack

**Installation**:
```
1. Laptop Position:
   - Center console cubby or cup holder (if fits)
   - Passenger seat with non-slip mat
   - Laptop bag with rigid bottom (prevents sliding)

2. GPS Placement:
   - Window ledge (passenger side)
   - Dashboard (velcro mount)
   - Rear window deck (if vehicle has clear view)

3. Wi-Fi Adapter:
   - USB extension cable to position near window
   - Angle adapter upward for better reception

4. Power:
   - Battery pack in console (4-6 hour runtime)
   - Or 12V charger with coiled cable (prevents tangling)

5. Concealment (optional):
   - Use laptop bag that doesn't show equipment
   - Route cables inside bag or console
   - GPS can be hidden under dashboard (reduced performance)
```

**Advantages**:
- Completely removable (take with you when parked)
- Zero permanent installation
- Can move between vehicles
- Concealed if desired

**Disadvantages**:
- GPS may have limited sky view
- Equipment can shift during driving
- Requires securing laptop/tablet

#### Trunk-Mounted (Covert)

**Best for**: Long-term covert surveillance detection, monitoring while parked

**Components**:
- Raspberry Pi or NUC (headless)
- USB GPS (roof-mounted with long cable)
- Wi-Fi adapter
- 12V → 5V buck converter (hardwired to vehicle battery)
- Weatherproof enclosure
- 4G LTE USB modem (for remote access)

**Installation**:
```
1. Computing Platform:
   - Mount Pi/NUC in weatherproof box in trunk
   - Secure with velcro or mounting brackets
   - Ensure ventilation (don't seal box completely)

2. GPS:
   - Route GPS cable from trunk → roof via rear hatch seal
   - Magnetic mount on roof (rear position)
   - Or inside rear window deck (if no metallic tint)

3. Wi-Fi Adapter:
   - Mount inside rear bumper or near rear window
   - Use USB extension to position optimally
   - External antenna (if roof-mounted): LMR-240 cable

4. Power (Hardwired):
   - 12V → 5V buck converter
   - Connect to vehicle battery (fused at 3A)
   - Run power cable from engine bay → trunk
   - Use relay (ignition-switched) to avoid draining battery

5. Remote Access:
   - 4G LTE USB modem for SSH access
   - Configure VPN for secure remote connection
   - Monitor CYT via web interface or SSH tunnel

6. Data Storage:
   - Large MicroSD (256GB+) or USB SSD
   - Set up log rotation to prevent filling storage
```

**Advantages**:
- Completely hidden (no visible equipment)
- Always operational (hardwired power)
- Remote monitoring possible
- Permanent installation for daily-driver vehicles

**Disadvantages**:
- Requires electrical skills (hardwiring to battery)
- Risk of draining vehicle battery if not using relay
- Difficult to access for maintenance
- Heat buildup in trunk (summer)

### Personal Carry Options

#### Backpack Setup (Walking Surveillance Detection)

**Components**:
- Laptop (13" recommended for weight) or Raspberry Pi + small display
- USB Wi-Fi adapter
- USB GPS
- Battery pack (20000-26800mAh)
- Backpack with laptop compartment
- Velcro cable organizers

**Configuration**:
```
1. Backpack Selection:
   - Laptop backpack with padded compartment
   - Top-loading for quick equipment access
   - Mesh pockets for GPS/adapter routing
   - Recommended: Timbuk2, SwissGear, or tactical backpack

2. Equipment Placement:
   - Laptop in padded compartment (vertical)
   - Battery pack in bottom compartment (weight distribution)
   - GPS in top mesh pocket (best sky view)
   - Wi-Fi adapter: USB extension to top of backpack

3. Antenna Extension:
   - Use SMA extension cable (12-24")
   - Route antenna to top of backpack
   - Secure with velcro to strap or attachment point
   - Aim upward for best omni-directional coverage

4. Cable Management:
   - Route all USB cables inside backpack
   - Use velcro cable wraps to bundle cables
   - Label cables for quick reconnection
   - Leave slack for laptop removal

5. Operation:
   - Headless: Pi with SSH over phone hotspot
   - With display: Use laptop, SSH from phone as backup
   - GPS should be outside metal frame of backpack (top pocket)
   - Battery: 4-6 hour runtime (20000mAh pack)
```

**Advantages**:
- Completely portable
- Hands-free operation
- Easy to carry for hours
- Quick setup (under 2 minutes)

**Disadvantages**:
- GPS may have reduced performance (backpack blocks some sky view)
- Wi-Fi range limited (no external antenna at height)
- Weight (~5-8 lbs with laptop/battery)

#### Tactical Vest / Chest Rig (Hands-Free, High-Mobility)

**Best for**: Security professionals, wilderness surveillance detection, tactical scenarios

**Components**:
- Raspberry Pi Zero 2 W (ultra-compact) or Pi 4
- USB Wi-Fi adapter (compact, e.g., AWUS036NHA)
- USB GPS (compact, e.g., VK-162)
- Battery pack (10000mAh slim profile)
- Tactical vest with MOLLE webbing
- Smartphone for display (SSH or VNC)

**Configuration**:
```
1. Vest Selection:
   - Condor MOLLE vest or Haley Strategic chest rig
   - Multiple pouches for equipment
   - Breathable (will wear for extended periods)

2. Equipment Mounting:
   - Raspberry Pi: MOLLE-compatible pouch (admin pouch size)
   - Battery: Inside vest (rear panel or side)
   - GPS: Top of vest (shoulder strap or rear panel, upward-facing)
   - Wi-Fi adapter: USB extension to shoulder height

3. Antenna:
   - Use flexible antenna or stubby antenna (avoid long rigid antenna)
   - Mount on shoulder strap (upward-facing)
   - Secure with velcro or ranger bands

4. Wiring:
   - Route cables inside vest or along MOLLE straps
   - Use cable clips or zip ties to secure
   - Waterproof connectors recommended (if outdoor use)

5. Display:
   - Smartphone: SSH or VNC app (Terminus, JuiceSSH)
   - Connect to Pi via:
     - Wi-Fi (Pi acts as hotspot)
     - USB tethering (direct connection)
     - Bluetooth SSH (slower but works)

6. Power Management:
   - Inline USB power switch (easy on/off without unplugging)
   - 10000mAh pack = 6-8 hours runtime (Pi Zero 2 W)
   - Spare battery in vest pouch for 12-16 hour ops
```

**Advantages**:
- Hands completely free
- Low profile (can wear under jacket)
- Quick access to all components
- Professional appearance (security/LE contexts)

**Disadvantages**:
- Requires tactical vest (conspicuous in civilian settings)
- Setup time (15-20 minutes initial configuration)
- Comfort (weight on chest/shoulders)

#### Concealed Carry (Covert Detection)

**Best for**: Personal safety, stalking detection, high-risk scenarios

**Components**:
- Raspberry Pi Zero 2 W (smallest)
- Compact USB Wi-Fi adapter (AWUS036NHA or smaller)
- Slim GPS (VK-162)
- Slim battery pack (10000mAh flat profile)
- Large jacket with internal pockets or photographer's vest

**Configuration**:
```
1. Jacket Selection:
   - Photographer's vest (internal pockets)
   - Cargo jacket (multiple large pockets)
   - Concealed carry jacket (built-in equipment pockets)

2. Equipment Placement:
   - Pi Zero: Inside breast pocket
   - Battery: Inside pocket (bottom weight distribution)
   - GPS: Outside chest pocket (or inside, near window/opening)
   - Wi-Fi adapter: Inside pocket with USB extension to jacket edge

3. Concealment:
   - No visible antennas (use internal adapter antennas)
   - Cables routed inside jacket lining
   - Equipment flat against body (slim battery essential)
   - GPS: Position near jacket zipper or collar (partial sky view)

4. Operation:
   - Headless: SSH from phone
   - Scheduled operation: Cron job starts CYT on boot
   - Data logging: Write to MicroSD, review later
   - Battery: 4-6 hours (slim pack), swap mid-day if needed

5. Heat Management:
   - Pi Zero generates minimal heat
   - Ensure some airflow (don't seal equipment in plastic)
   - Avoid placing in back pocket (body heat + lack of airflow)
```

**Advantages**:
- Completely concealed
- Appears as normal clothing
- Comfortable for all-day wear
- No visible equipment

**Disadvantages**:
- Reduced GPS performance (body blocking, partial sky view)
- Reduced Wi-Fi range (body attenuation, no external antenna)
- Limited access to equipment (must remove jacket)
- Heat buildup (Pi + battery against body)

#### Messenger Bag / Sling Bag (Urban Mobility)

**Best for**: City environments, public transit, coffee shops

**Components**:
- Laptop (13-14") or tablet with keyboard
- USB Wi-Fi adapter
- USB GPS
- Battery pack (20000mAh)
- Messenger bag with quick-access flap

**Configuration**:
```
1. Bag Selection:
   - Messenger bag with padded laptop compartment
   - Quick-release flap for easy laptop access
   - Cross-body strap (hands-free)
   - Recommended: Timbuk2 Classic, Chrome Industries

2. Equipment Placement:
   - Laptop: Main compartment (vertical)
   - Battery: Bottom of bag (weight distribution)
   - GPS: Front external pocket (sky view)
   - Wi-Fi adapter: USB extension to bag edge (window-facing)

3. Quick Deployment:
   - Open flap, pull laptop (hinged design, can use without removing)
   - GPS already positioned in external pocket
   - Wi-Fi adapter pre-connected (USB extension cable)
   - Battery in internal pocket with cable to laptop

4. Operation on the Go:
   - Coffee shop: Open bag on table, laptop visible
   - Walking: GPS in external pocket, laptop in bag (headless)
   - Transit: Laptop on lap, GPS in bag pocket (partial sky view)

5. Discrete Surveillance Detection:
   - Bag looks like normal laptop bag
   - GPS can be positioned for sky view without opening bag
   - Operate headless (SSH from phone) for maximum discretion
```

**Advantages**:
- Urban-friendly (doesn't look tactical)
- Quick access to laptop
- Comfortable for all-day carry
- Discrete operation possible

**Disadvantages**:
- Single strap (can be tiring on long walks)
- GPS may have reduced sky view (bag pocket)
- Less organized than backpack

### Weatherproofing and Environmental Protection

#### Outdoor Deployments

**Rain Protection**:
```
- Laptop: Use waterproof sleeve or dry bag
- Raspberry Pi: Use IP65-rated enclosure (Polycase, Bud Industries)
- GPS: Most USB GPS are splash-resistant, but use conformal coating on PCB for prolonged exposure
- Wi-Fi adapter: Use balloon or plastic bag over adapter (don't block antenna pattern)
- Cables: Use waterproof glands for cable entry points
```

**Temperature Extremes**:
```
Cold (< 32°F / 0°C):
- Battery performance degrades (carry battery in inner pocket, keep warm)
- LCD displays can freeze (use OLED or backlit displays)
- Condensation risk (bring equipment to room temperature slowly)

Heat (> 95°F / 35°C):
- Laptop cooling (use external fan or laptop cooling pad)
- Raspberry Pi: Heatsinks + fan essential (or passive heatsink case)
- GPS: Place in shade (direct sunlight can heat GPS module to 140°F+)
- Battery: Avoid direct sunlight (risk of thermal runaway)
```

**Dust and Sand**:
```
- Use sealed enclosures (IP65 or better)
- Cover ports with dust caps
- Avoid placing equipment on ground (use elevated mount)
- Clean equipment with compressed air after deployment
```

### Cable and Accessory Checklist

**Essential Cables**:
- USB-A to USB-C (laptop charging) - 6ft coiled or straight
- USB-A extension (6-12") for GPS positioning
- USB-A extension (3-6ft) for Wi-Fi adapter positioning
- LMR-240 coax (10-15ft) for external antenna (if roof-mounted)
- 12V car charger (USB-C PD 45W+) for laptops
- USB-A to Micro-USB (for Raspberry Pi power)

**Mounting Accessories**:
- Velcro strips (heavy-duty, 2" wide)
- RAM Mounts X-Grip or suction cup
- Magnetic mounts (for GPS and antenna)
- Cable clips and organizers
- Zip ties (assorted sizes)
- Electrical tape

**Optional Accessories**:
- USB-powered fan (Raspberry Pi cooling)
- Inline USB power switch
- USB voltmeter (monitor power consumption)
- Right-angle USB adapters (tight spaces)
- SMA/RP-SMA adapters and extensions
- Waterproof enclosures (Pelican, Polycase)

---

## Final Recommendations

### For Most Users (Best Overall Value):
**Used ThinkPad T480 + ALFA AWUS036ACH + BU-353S4 GPS** (~$350)
- Maximum flexibility (battery, display, keyboard included)
- Excellent Linux compatibility
- Dual-band Wi-Fi detection
- Professional-grade GPS
- Expandable and upgradeable

### For Budget-Conscious Users:
**Raspberry Pi 4 4GB + ALFA AWUS036NHA + VK-162 GPS** (~$170)
- Gets the job done for 2.4GHz detection
- Low power consumption
- Portable
- Great learning platform

### For Stationary/Lab Setups:
**Beelink Mini PC + ALFA AWUS1900 + upgraded antennas** (~$700)
- 24/7 operation
- High power and range
- Large storage for historical data
- Can run VMs and other services alongside CYT

### For Advanced Research:
**High-end laptop + multiple adapters + SDR** (~$1500)
- Comprehensive RF coverage
- Experimentation and development
- Direction-finding capability
- Professional toolkit

---

## Appendix: Chipset Reference

### Confirmed Working Chipsets (Monitor Mode + Injection)

| Chipset | Frequency | Driver | Kernel Support | Notes |
|---------|-----------|--------|----------------|-------|
| Atheros AR9271 | 2.4GHz | ath9k_htc | Mainline | Gold standard |
| Ralink RT3070 | 2.4GHz | rt2800usb | Mainline | Very reliable |
| Ralink RT5370 | 2.4GHz | rt2800usb | Mainline | Solid choice |
| Ralink RT5572 | Dual-band | rt2800usb | Mainline | Good dual-band option |
| Realtek RTL8812AU | Dual-band | rtl8812au (external) | DKMS | Requires aircrack-ng driver |
| Realtek RTL8814AU | Dual-band | rtl8814au (external) | DKMS | High-power, requires driver |
| Mediatek MT7612U | Dual-band | mt76x2u | Mainline (5.4+) | Modern dual-band, good support |

### Chipsets to Avoid

| Chipset | Reason |
|---------|--------|
| Broadcom BCM43xx | Poor monitor mode support, proprietary drivers |
| Intel AX200/AX210 | iwlwifi driver doesn't support full monitor mode |
| Realtek RTL8188EU | Unreliable, poor injection support |
| Realtek RTL8188CUS | Old, inconsistent driver support |

---

**End of Hardware Guide**

For questions, updates, or contributions to this guide, see the main CYT project repository.
