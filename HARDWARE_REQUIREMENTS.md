# CYT Hardware Requirements

**Complete hardware shopping guide for CYT deployment**

This guide provides specific hardware recommendations with model numbers, prices, and purchase links.

---

## 🎯 Quick Reference

**Minimum to get started**: $50-80
- Raspberry Pi Zero 2 W ($15) or laptop (reuse existing)
- TP-Link TL-WN722N v1 ($15-20)
- 16GB microSD card ($8)
- Power supply ($10)

**Recommended**: $120-150
- Raspberry Pi 4 Model B 4GB ($55)
- Alfa AWUS036ACH ($40-50)
- 32GB microSD card ($12)
- Quality power supply ($15)
- Case with cooling ($12)

**Professional**: $200-300
- Raspberry Pi 4 Model B 8GB ($75)
- Alfa AWUS1900 ($80-100)
- 64GB microSD card ($15)
- PoE HAT + switch ($50)
- Enclosure ($25)
- External antenna ($30)

---

## 📡 Wireless Adapters (CRITICAL)

**The single most important hardware choice**. Not all adapters support monitor mode!

### ✅ Verified Working Adapters

#### Budget Tier ($15-30)

**1. TP-Link TL-WN722N v1** ($15-20) ⭐ Best Budget Choice
- **Chipset**: Atheros AR9271
- **Bands**: 2.4 GHz only
- **Monitor Mode**: ✅ Yes
- **Packet Injection**: ✅ Yes
- **Driver**: ath9k (built-in Linux)
- **Range**: Good (~100m)
- **Where to Buy**: Amazon, eBay (ensure v1, NOT v2/v3!)
- **Note**: Version 1 ONLY! v2 and v3 do NOT support monitor mode
- **How to verify**: Check chipset on product listing

**2. Panda PAU05** ($18-25)
- **Chipset**: Ralink RT5372
- **Bands**: 2.4 GHz only
- **Monitor Mode**: ✅ Yes
- **Packet Injection**: ✅ Yes
- **Driver**: rt2800usb (built-in)
- **Range**: Good
- **Where to Buy**: Amazon

#### Mid-Range ($30-60)

**3. Alfa AWUS036NHA** ($30-40) ⭐ Recommended
- **Chipset**: Atheros AR9271
- **Bands**: 2.4 GHz
- **Monitor Mode**: ✅ Yes
- **Packet Injection**: ✅ Yes
- **Driver**: ath9k (excellent Linux support)
- **Range**: Excellent (~200m with external antenna)
- **Power**: High transmit power (legal max)
- **Where to Buy**: Amazon, Rokland, official distributors
- **Why recommended**: Industry standard, reliable, great support

**4. Alfa AWUS036ACH** ($40-50) ⭐ Best Overall
- **Chipset**: Realtek RTL8812AU
- **Bands**: Dual-band 2.4 GHz + 5 GHz
- **Monitor Mode**: ✅ Yes (with driver)
- **Packet Injection**: ✅ Yes
- **Driver**: rtl8812au (requires installation)
- **Range**: Excellent
- **Speed**: AC1200
- **Where to Buy**: Amazon, Rokland
- **Note**: Best choice for modern drones (many use 5 GHz)
- **Driver install**:
  ```bash
  git clone https://github.com/aircrack-ng/rtl8812au.git
  cd rtl8812au
  make && sudo make install
  ```

#### Professional ($70-120)

**5. Alfa AWUS1900** ($80-100) ⭐ Professional Choice
- **Chipset**: Realtek RTL8814AU
- **Bands**: Dual-band (AC1900)
- **Monitor Mode**: ✅ Yes
- **Range**: Outstanding (~300m)
- **Antennas**: 4x high-gain external
- **Best for**: Long-range detection, professional deployments
- **Where to Buy**: Amazon, official distributors

**6. WiFi Pineapple Mark VII** ($200+)
- **Purpose**: Professional pentesting platform
- **Monitor Mode**: ✅ Built-in
- **Features**: Complete wireless auditing suite
- **Best for**: Security professionals
- **Where to Buy**: Hak5.org

---

### ❌ Adapters to AVOID

These do NOT support monitor mode:

- **TP-Link TL-WN722N v2/v3** - Different chipset, no monitor mode
- **Netgear WNA1100** - No monitor mode
- **Most Realtek RTL8192** - Poor monitor mode support
- **Broadcom chipsets** - Limited Linux support
- **MediaTek MT76xx** - Hit-or-miss support
- **Most laptop built-in cards** - Restricted by firmware

**How to check before buying**:
1. Look for "monitor mode" in specifications
2. Check chipset (Atheros AR9271, Ralink, or Realtek 8812AU)
3. Read reviews from pentesters/security users
4. Avoid if listing says "v2" or "v3"

---

## 💻 Computing Platform

### Option 1: Raspberry Pi (Recommended)

**Advantages**:
- Low power consumption (~5W)
- Silent operation (fanless)
- Small form factor
- Always-on deployment
- GPIO for future expansion

**Disadvantages**:
- Requires separate purchase
- Setup complexity (SD card, OS install)
- Limited processing power

#### Raspberry Pi Models

**Raspberry Pi Zero 2 W** ($15) - Budget
- **CPU**: 1GHz quad-core ARM Cortex-A53
- **RAM**: 512MB
- **WiFi**: Built-in (but use external adapter!)
- **Best for**: Stationary deployment, power efficiency
- **CYT Performance**: Basic (single detection only)
- **Where to Buy**: Adafruit, PiShop, official distributors

**Raspberry Pi 4 Model B 4GB** ($55) - Recommended ⭐
- **CPU**: 1.5GHz quad-core ARM Cortex-A72
- **RAM**: 4GB
- **USB**: 2x USB 3.0 (better for WiFi adapters)
- **Best for**: CYT + GUI + API server
- **CYT Performance**: Excellent
- **Where to Buy**: Canakit, Adafruit, Amazon

**Raspberry Pi 4 Model B 8GB** ($75) - Professional
- **RAM**: 8GB (overkill but future-proof)
- **Best for**: Multi-adapter setups, heavy logging
- **Where to Buy**: Same as 4GB model

---

### Option 2: Existing Laptop/Desktop

**Advantages**:
- Free (if you have one)
- More powerful
- Easier debugging (screen, keyboard)
- No additional purchase

**Disadvantages**:
- Higher power consumption
- Not portable
- May need to dedicate machine

**Minimum specs**:
- **OS**: Ubuntu 20.04+ or Debian 11+
- **CPU**: Dual-core 1GHz+
- **RAM**: 2GB+ (4GB recommended)
- **USB**: USB 2.0+ port for adapter
- **Storage**: 16GB+ available

**Compatible Linux distributions**:
- Ubuntu 20.04/22.04 LTS ⭐ Best supported
- Debian 11/12
- Raspberry Pi OS (for Pi)
- Kali Linux ⭐ Pre-configured for wireless
- Arch Linux (advanced users)

---

## 💾 Storage (Raspberry Pi Only)

**microSD Card Requirements**:
- **Minimum**: 16GB Class 10
- **Recommended**: 32GB UHS-I (U1) ⭐
- **Professional**: 64GB UHS-I (U3) + wear leveling

**Specific Models** (proven reliable):
- SanDisk Ultra 32GB ($12) ⭐ Recommended
- Samsung EVO Plus 32GB ($10)
- SanDisk Extreme 64GB ($18) - Professional

**Why size matters**:
- OS: ~4GB
- CYT: ~1GB
- Logs: 100MB-1GB per day (depends on activity)
- Kismet DB: 50MB-500MB per day

**Calculate your needs**:
```
Days of logs = (Card Size - 8GB) / Average Daily Usage

Example with 32GB card, 200MB/day:
(32GB - 8GB) / 0.2GB = 120 days
```

**Where to Buy**: Amazon, Best Buy, B&H Photo

---

## 🔌 Power Supply (Raspberry Pi Only)

**Official Raspberry Pi Power Supply** ($8-15) ⭐
- **Voltage**: 5V
- **Current**: 3A (15W)
- **Connector**: USB-C (Pi 4) or microUSB (older models)
- **Why**: Guaranteed compatibility, stable power
- **Where**: Official distributors, Amazon

**Alternative** (if official unavailable):
- **Requirements**: 5V, 3A minimum, quality brand
- **Avoid**: Cheap phone chargers (voltage drops)
- **Check**: Must deliver 3A continuously

**Power-over-Ethernet (PoE)** - Professional
- **PoE HAT**: Official Raspberry Pi PoE HAT ($20-25)
- **PoE Switch**: Netgear GS305P ($50) or similar
- **Advantages**: Single cable for power + network
- **Best for**: Permanent installations, remote locations

---

## 📦 Complete Kits (Easiest Option)

### Budget Kit ($80-100) - Get Started Quick
**Components**:
- Raspberry Pi 4 Model B 4GB ($55)
- TP-Link TL-WN722N v1 ($18)
- 32GB SanDisk Ultra microSD ($12)
- Official power supply ($10)
- Basic case ($5)

**Total**: ~$100
**Where**: Assemble from Amazon/Adafruit

---

### Recommended Kit ($150-180) - Best Value
**Components**:
- Raspberry Pi 4 Model B 4GB ($55)
- Alfa AWUS036ACH ($45)
- 32GB microSD (pre-loaded Raspberry Pi OS) ($15)
- Official power supply ($10)
- Case with fan ($15)
- HDMI cable ($8)
- microSD card reader ($8)

**Total**: ~$156
**Benefit**: Dual-band detection, reliable adapter

---

### Professional Kit ($250-300) - Production Ready
**Components**:
- Raspberry Pi 4 Model B 8GB ($75)
- Alfa AWUS1900 ($90)
- 64GB high-endurance microSD ($18)
- PoE HAT ($25)
- Weatherproof case ($30)
- PoE network switch ($50)
- External antenna (optional) ($30)

**Total**: ~$288-318
**Benefit**: Long-range, permanent install, remote power

---

## 🌐 Network Requirements

**For basic CYT operation**:
- No network required (standalone monitoring)

**For AlertManager (Telegram)**:
- Internet connection (Ethernet or WiFi)
- Router with DHCP (automatic IP)

**For API Server**:
- Same network as devices accessing API
- Port 8080 open (default)

**For remote access**:
- Static IP or dynamic DNS
- Port forwarding (if outside network)
- VPN recommended for security

---

## 📍 GPS Module (Optional)

**For location correlation**:

**USB GPS Receivers**:
- **GlobalSat BU-353-S4** ($30-40) ⭐
  - USB connection
  - SiRF Star IV chipset
  - Works with gpsd

- **U-blox 7 GPS Module** ($25)
  - USB or GPIO
  - Good sensitivity

**Setup**:
```bash
# Install gpsd
sudo apt-get install gpsd gpsd-clients

# Configure Kismet to use GPS
sudo nano /etc/kismet/kismet.conf
# Add: gps=gpsd:host=localhost,port=2947
```

**Why GPS**:
- Enables behavioral drone detection (movement patterns)
- Location correlation for detections
- Geographic tracking of threats
- Required for KML export with coordinates

---

## 🎒 Portable Deployment Kit

**For mobile surveillance detection**:

**Components**:
- Raspberry Pi 4 Model B ($55)
- Alfa AWUS036ACH ($45)
- USB battery bank 20,000mAh ($30) ⭐
- 5" HDMI touchscreen ($60) (optional)
- Portable pelican-style case ($40)

**Total**: $170-230

**Battery life estimate**:
- Pi 4 + adapter: ~5-7W
- 20,000mAh @ 5V = 100Wh
- Runtime: ~14-20 hours

**Recommended battery**:
- Anker PowerCore 20100 ($35)
- RAVPower 26800mAh ($40)
- Must support 3A output

---

## 🛠️ Tools & Accessories

**Essential** (you'll need these):
- microSD card reader ($8)
- HDMI cable (for Pi setup) ($8)
- USB keyboard (for Pi setup) (reuse existing)
- Ethernet cable ($5)

**Recommended**:
- USB extension cable ($10) - Position adapter better
- Heat sinks for Pi ($5) - Prevent thermal throttling
- Right-angle USB adapter ($8) - Compact installations

**Professional**:
- Serial console cable ($10) - Headless debugging
- GPIO breakout ($15) - Future hardware integration
- External antenna connectors ($20) - Extended range

---

## 🌡️ Environmental Considerations

**Indoor Deployment**:
- **Cooling**: Passive (case with vents) or active (fan)
- **Temperature**: Keep Pi under 70°C
- **Humidity**: Standard indoor (30-70%)

**Outdoor Deployment**:
- **Enclosure**: IP65 rated weatherproof ($40-80)
- **Cooling**: Passive only (sealed)
- **Temperature**: -20°C to 50°C rated Pi
- **Power**: PoE recommended (no external cables)
- **Mounting**: Weatherproof mount

**Recommended outdoor enclosures**:
- BUD Industries NBF-32402 ($45)
- Polycase WC-41 ($50)
- Custom 3D printed (search "Raspberry Pi outdoor enclosure")

---

## 💰 Budget Planning

### Budget Tier ($50-80)
**Just test the concept**:
- Existing laptop (Free)
- TP-Link TL-WN722N v1 ($18)
- **Total**: ~$18 + laptop

**OR**:
- Raspberry Pi Zero 2 W ($15)
- TP-Link TL-WN722N v1 ($18)
- 16GB microSD ($8)
- Power supply ($10)
- **Total**: ~$51

---

### Recommended Tier ($120-180)
**Best value, production-capable**:
- Raspberry Pi 4 Model B 4GB ($55)
- Alfa AWUS036ACH ($45)
- 32GB microSD ($12)
- Official power supply ($10)
- Case with cooling ($15)
- Accessories ($20)
- **Total**: ~$157

---

### Professional Tier ($250-350)
**Long-range, permanent install**:
- Raspberry Pi 4 Model B 8GB ($75)
- Alfa AWUS1900 ($90)
- 64GB high-endurance microSD ($18)
- PoE HAT ($25)
- PoE switch ($50)
- Weatherproof enclosure ($40)
- GPS module ($35)
- External antenna ($30)
- **Total**: ~$363

---

## 🛒 Where to Buy

### Official Distributors (Best Support)
- **Adafruit** (adafruit.com) - US, good support
- **PiShop.us** - US, Pi specialist
- **The Pi Hut** (thepihut.com) - UK
- **Pimoroni** (pimoroni.com) - UK

### General Retailers
- **Amazon** - Fast shipping, easy returns
- **Newegg** - Tech focus, good prices
- **Micro Center** - In-store pickup (US)
- **B&H Photo** - Professional equipment

### Wireless Specialists
- **Rokland** (rokland.com) - Alfa adapters, US
- **Hak5** (hak5.org) - Security tools, professional
- **WiFi-Adapter** (wifi-adapter.com) - EU specialist

---

## ✅ Pre-Purchase Checklist

Before buying, verify:

- [ ] Wireless adapter explicitly supports monitor mode
- [ ] Adapter chipset is on verified list (Atheros, Ralink, RTL8812AU)
- [ ] NOT buying TP-Link v2 or v3 (only v1!)
- [ ] Raspberry Pi model has USB 3.0 (Pi 4) or sufficient power (Zero 2 W)
- [ ] microSD card is Class 10 or better
- [ ] Power supply delivers 3A continuously (Pi)
- [ ] Have tools needed for setup (keyboard, HDMI cable, etc.)

---

## 🔄 Upgrade Path

**Start small, expand later**:

**Phase 1** ($50): Laptop + budget adapter
- Learn the system
- Test in your environment
- Decide if CYT meets needs

**Phase 2** ($150): Raspberry Pi 4 + Alfa AWUS036ACH
- Dedicated monitoring station
- Better performance
- Production-ready

**Phase 3** ($100): Add GPS + enclosure
- Location correlation
- Portable or permanent deployment
- Professional features

**Phase 4** ($150): PoE + weatherproof + extended range
- Permanent outdoor installation
- Remote monitoring
- Long-range detection

---

## 📊 Performance Comparison

| Platform | CPU | RAM | Adapters | Concurrent Detection | Cost |
|----------|-----|-----|----------|---------------------|------|
| Pi Zero 2 W | 1GHz quad | 512MB | 1 | Basic | $15 |
| Laptop i5 | 2.5GHz dual | 8GB | 2+ | Excellent | Free |
| Pi 4 4GB | 1.5GHz quad | 4GB | 2 | Very Good | $55 |
| Pi 4 8GB | 1.5GHz quad | 8GB | 2+ | Excellent | $75 |

**Recommendation**: Raspberry Pi 4 4GB offers best balance of cost, performance, and power efficiency.

---

## 🎯 Final Recommendations

**Best Overall**: Raspberry Pi 4 4GB + Alfa AWUS036ACH (~$100)
- Proven reliable
- Dual-band detection
- Production-ready
- Room to expand

**Best Budget**: Existing laptop + TP-Link TL-WN722N v1 (~$18)
- Lowest cost
- Test before committing
- Repurpose old hardware

**Best Professional**: Pi 4 8GB + Alfa AWUS1900 + PoE (~$300)
- Long-range detection
- Permanent installation
- Commercial-grade

---

**Next Steps**: Once hardware acquired, see [QUICK_START.md](QUICK_START.md) for setup instructions.
