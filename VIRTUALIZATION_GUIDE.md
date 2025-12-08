# Virtual Machines on MacBook Air M3 - Comprehensive Guide

**Last Updated**: 2025-12-07
**Platform**: MacBook Air M3 (Apple Silicon ARM64)
**Use Case**: CYT Development, Testing, and Deployment

---

## Table of Contents

1. [Overview: VMs on Apple Silicon](#overview-vms-on-apple-silicon)
2. [Virtualization Software Options](#virtualization-software-options)
3. [Recommended Setup for CYT](#recommended-setup-for-cyt)
4. [Installation Guide: UTM (Free)](#installation-guide-utm-free)
5. [Installation Guide: Parallels Desktop (Pro)](#installation-guide-parallels-desktop-pro)
6. [Creating Your First Linux VM](#creating-your-first-linux-vm)
7. [USB Passthrough for Wireless Adapters](#usb-passthrough-for-wireless-adapters)
8. [Resource Allocation & Performance](#resource-allocation--performance)
9. [Networking Configuration](#networking-configuration)
10. [Use Cases for CYT Development](#use-cases-for-cyt-development)
11. [VM vs Native macOS: Pros & Cons](#vm-vs-native-macos-pros--cons)
12. [Troubleshooting Common Issues](#troubleshooting-common-issues)
13. [Advanced Topics](#advanced-topics)

---

## Overview: VMs on Apple Silicon

### What is a Virtual Machine?

A **virtual machine (VM)** is a software-based computer that runs inside your MacBook Air. It's like having a second computer running in a window, with its own operating system, applications, and files.

**Key Concepts**:
- **Host**: Your MacBook Air M3 (running macOS)
- **Guest**: The VM running inside (typically Linux for CYT)
- **Hypervisor**: Software that manages VMs (UTM, Parallels, VMware)
- **ARM64**: Architecture of M3 chip (NOT x86_64 like Intel Macs)

### ARM Architecture Implications

**CRITICAL**: MacBook Air M3 uses ARM64 (Apple Silicon) architecture.

**What This Means**:
- ✅ Can run ARM64 Linux distros (Ubuntu ARM, Debian ARM, Kali ARM, etc.)
- ✅ Native performance (no emulation overhead)
- ❌ Cannot run x86_64 Linux without emulation (slow)
- ❌ Some software may not have ARM builds

**Best Practice**: Always choose **ARM64/aarch64** versions of Linux distributions.

---

## Virtualization Software Options

### Comparison Matrix

| Software | Cost | Performance | USB Passthrough | Ease of Use | CYT Recommendation |
|----------|------|-------------|-----------------|-------------|-------------------|
| **UTM** | Free | Good | Yes (limited) | Moderate | ✅ **Best for Learning** |
| **Parallels Desktop** | $100/yr | Excellent | Yes (excellent) | Easy | ✅ **Best for Production** |
| **VMware Fusion** | $200 (one-time) | Very Good | Yes (good) | Moderate | Good alternative |
| **QEMU (CLI)** | Free | Good | Yes (complex) | Hard | Advanced users only |

### Detailed Breakdown

#### 1. UTM (Recommended for Free/Learning)

**Website**: https://mac.getutm.app/
**Cost**: Free (open source)
**Best For**: Learning, development, testing

**Pros**:
- Completely free
- User-friendly GUI
- Good ARM64 support
- Active development
- USB passthrough supported

**Cons**:
- USB passthrough less reliable than Parallels
- Fewer automation features
- Performance slightly lower than Parallels

**Use for CYT**: Development, testing, learning Kismet setup

#### 2. Parallels Desktop (Recommended for Production)

**Website**: https://www.parallels.com/
**Cost**: $99.99/year (Pro Edition required for USB 3.0)
**Best For**: Production deployment, professional use

**Pros**:
- Excellent performance (near-native)
- Best USB passthrough (critical for Alfa adapter)
- Seamless macOS integration
- Automatic resource management
- Snapshots and cloning

**Cons**:
- Annual subscription cost
- Overkill for simple testing

**Use for CYT**: Production deployment, field operations, intensive testing

#### 3. VMware Fusion (Alternative)

**Website**: https://www.vmware.com/products/fusion.html
**Cost**: $199 (one-time) or Free (personal use)
**Best For**: Professional users familiar with VMware ecosystem

**Pros**:
- One-time purchase option
- Professional-grade features
- Good ARM support
- Enterprise-ready

**Cons**:
- More complex than Parallels
- USB passthrough not as polished
- Heavier resource usage

**Use for CYT**: Alternative to Parallels if you have VMware experience

#### 4. QEMU (Advanced)

**Website**: https://www.qemu.org/
**Cost**: Free (open source)
**Best For**: Advanced users, automation, scripting

**Pros**:
- Ultimate flexibility
- Scriptable/automatable
- No licensing costs
- UTM is built on QEMU

**Cons**:
- Command-line only
- Steep learning curve
- Complex configuration

**Use for CYT**: Not recommended unless you're a QEMU expert

---

## Recommended Setup for CYT

### Scenario 1: Learning & Development (Free)

**Software**: UTM
**Guest OS**: Ubuntu Server 22.04 ARM64
**Resources**: 4 CPU cores, 4GB RAM, 40GB disk
**Use Case**: Learning Kismet, developing CYT features, testing

**Cost**: $0

### Scenario 2: Production Deployment (Professional)

**Software**: Parallels Desktop Pro
**Guest OS**: Kali Linux ARM64 or Ubuntu 22.04 ARM64
**Resources**: 6 CPU cores, 8GB RAM, 100GB disk
**Use Case**: Field deployment, 24/7 monitoring, production testing

**Cost**: $100/year

### Scenario 3: Hybrid Approach (Recommended)

**Development**: UTM (free) for learning and testing
**Production**: Native macOS with Homebrew Kismet
**Backup**: Parallels VM for troubleshooting/isolation

**Cost**: $0 initially, $100/year if you need Parallels later

---

## Installation Guide: UTM (Free)

### Step 1: Download and Install UTM

```bash
# Option A: Download from website
# Visit: https://mac.getutm.app/
# Click "Download" button
# Open UTM.dmg and drag to Applications

# Option B: Install via Homebrew
brew install --cask utm
```

### Step 2: Download Linux ISO (ARM64)

**Recommended Distros for CYT**:

1. **Ubuntu Server 22.04 ARM64** (Best for beginners)
   - Download: https://ubuntu.com/download/server/arm
   - File: `ubuntu-22.04.3-live-server-arm64.iso`
   - Size: ~1.4GB

2. **Kali Linux ARM64** (Best for security tools)
   - Download: https://www.kali.org/get-kali/#kali-installer-images
   - Choose: "Installer (ARM64)"
   - File: `kali-linux-2024.3-installer-arm64.iso`
   - Size: ~3.5GB

3. **Debian 12 ARM64** (Lightweight)
   - Download: https://www.debian.org/CD/netinst/
   - Choose: "ARM64 architecture"
   - File: `debian-12.4.0-arm64-netinst.iso`
   - Size: ~600MB

**Download Location**: Save to `~/Downloads/`

### Step 3: Create Your First VM

1. **Open UTM**
   - Launch UTM from Applications
   - Click "Create a New Virtual Machine"

2. **Choose Virtualization Type**
   - Select "Virtualize" (not Emulate)
   - This uses native ARM64 (fast)

3. **Select Operating System**
   - Choose "Linux"
   - Click "Continue"

4. **Configure VM Resources**
   ```
   Architecture: ARM64 (aarch64)
   System: Default (QEMU 8.x ARM Virtual Machine)
   Memory: 4096 MB (4GB)
   CPU Cores: 4
   ```

5. **Configure Storage**
   ```
   Disk Size: 40 GB (dynamically allocated)
   Shared Directory: None (for now)
   ```

6. **Attach ISO Image**
   - Click "Browse"
   - Select your downloaded ISO (e.g., `ubuntu-22.04.3-live-server-arm64.iso`)
   - Click "Continue"

7. **Review and Create**
   - Name: "CYT-Ubuntu-ARM64"
   - Click "Save"

### Step 4: Install Linux

1. **Start the VM**
   - Select your VM in UTM
   - Click the "Play" button (▶️)

2. **Ubuntu Installation** (example for Ubuntu Server)
   ```
   Language: English
   Keyboard: English (US)
   Network: DHCP (automatic)
   Storage: Use entire disk (40GB)

   Profile Setup:
   - Your name: cyt-user
   - Server name: cyt-monitor
   - Username: cyt
   - Password: [choose strong password]

   SSH Setup: Install OpenSSH server (YES)
   Featured Server Snaps: None (skip)
   ```

3. **First Boot**
   - Wait for installation to complete (10-15 minutes)
   - Remove installation media when prompted
   - Reboot
   - Log in with username/password

4. **Initial Updates**
   ```bash
   sudo apt update
   sudo apt upgrade -y
   sudo apt install -y build-essential git python3-pip
   ```

### Step 5: Install QEMU Guest Agent (Recommended)

This improves VM performance and integration:

```bash
sudo apt install -y qemu-guest-agent
sudo systemctl enable qemu-guest-agent
sudo systemctl start qemu-guest-agent
```

---

## Installation Guide: Parallels Desktop (Pro)

### Step 1: Purchase and Download

1. Visit: https://www.parallels.com/products/desktop/
2. Choose "Parallels Desktop Pro Edition" ($99.99/year)
3. Download installer
4. Run installer and activate with license key

### Step 2: Create Linux VM (Guided Setup)

Parallels has excellent automatic installation:

1. **Open Parallels Desktop**
   - Click "+" to create new VM
   - Select "Install Windows or another OS from a DVD or image file"

2. **Select ISO Image**
   - Click "Select a file..."
   - Choose your Linux ISO (Ubuntu/Kali ARM64)
   - Parallels auto-detects the OS

3. **Configure Installation** (Parallels auto-fills most settings)
   ```
   Name: CYT-Production
   Location: ~/Parallels/

   User Account:
   - Username: cyt
   - Password: [choose strong password]
   ```

4. **Customize Settings Before Installation**
   - Click "Customize settings before installation"
   - **Hardware**:
     - Processors: 6 cores
     - Memory: 8192 MB (8GB)
   - **Hard Disk**: 100 GB
   - **Network**: Shared Network (default)
   - **USB & Bluetooth**: USB 3.0 enabled

5. **Start Installation**
   - Click "Continue"
   - Parallels automatically installs Linux
   - Wait 15-20 minutes

6. **Install Parallels Tools** (Critical)
   ```bash
   # After first boot, Parallels will prompt to install Tools
   # Click "Install Parallels Tools"

   # Or manually:
   sudo mount /dev/cdrom /mnt
   sudo /mnt/install
   sudo reboot
   ```

---

## Creating Your First Linux VM

### Recommended Configuration for CYT

**Operating System**: Ubuntu Server 22.04 ARM64

**Why Ubuntu Server?**
- ✅ ARM64 native support
- ✅ Excellent package availability
- ✅ Well-documented
- ✅ Kismet officially supported
- ✅ Lightweight (no GUI overhead)
- ✅ LTS (Long-Term Support until 2027)

**Resources**:
```
CPU: 4-6 cores (out of 8 available on M3)
RAM: 4-8 GB (out of 8-16GB available)
Disk: 40-100 GB (dynamically allocated)
Network: Shared (NAT) or Bridged
```

### Post-Installation Setup

#### 1. Update System

```bash
sudo apt update
sudo apt upgrade -y
```

#### 2. Install Essential Tools

```bash
sudo apt install -y \
    build-essential \
    git \
    python3 \
    python3-pip \
    python3-venv \
    vim \
    htop \
    net-tools \
    wireless-tools \
    aircrack-ng \
    gpsd \
    gpsd-clients
```

#### 3. Install Kismet

```bash
# Add Kismet repository
wget -O - https://www.kismetwireless.net/repos/kismet-release.gpg.key | sudo apt-key add -
echo 'deb https://www.kismetwireless.net/repos/apt/release/ubuntu jammy main' | sudo tee /etc/apt/sources.list.d/kismet.list

# Install Kismet
sudo apt update
sudo apt install -y kismet

# Add user to kismet group
sudo usermod -aG kismet $USER

# Log out and back in for group changes to take effect
```

#### 4. Clone CYT Repository

```bash
cd ~
git clone https://github.com/SwampPop/Chasing-Your-Tail-NG.git
cd Chasing-Your-Tail-NG

# Install Python dependencies
pip3 install -r requirements.txt
```

#### 5. Configure CYT

```bash
# Validate configuration
python3 config_validator.py

# Set up encrypted credentials (if using Telegram/WiGLE)
python3 secure_credentials.py
```

---

## USB Passthrough for Wireless Adapters

**CRITICAL**: This is essential for using your Alfa AWUS1900 in the VM.

### UTM USB Passthrough

#### Step 1: Enable USB Sharing

1. **Open VM Settings**
   - Right-click VM → "Edit"
   - Go to "USB" section

2. **Add USB Device**
   - Click "New..."
   - Select "USB Device Redirect"
   - Choose your Alfa AWUS1900 from dropdown

3. **Save and Restart VM**

#### Step 2: Verify in Linux

```bash
# Check if adapter is visible
lsusb

# Should see something like:
# Bus 001 Device 003: ID 0bda:8813 Realtek Semiconductor Corp. RTL8814AU

# Check kernel module
lsmod | grep 8814

# If module not loaded, install driver
cd ~
git clone https://github.com/aircrack-ng/rtl8814au.git
cd rtl8814au
make
sudo make install
sudo modprobe 8814au
```

### Parallels USB Passthrough

Parallels makes this much easier:

#### Step 1: Connect Device to VM

1. **Plug in Alfa AWUS1900**
2. **Parallels will prompt**: "USB device detected: Do you want to connect it to macOS or VM?"
3. **Select**: "Connect to VM (CYT-Production)"

Alternatively:

1. **Devices Menu** → **USB & Bluetooth** → **Alfa AWUS1900**
2. Check the box to connect to VM

#### Step 2: Verify in Linux

```bash
lsusb
# Should immediately show the adapter

# Verify wireless interface
iwconfig
# Should see wlan0 or similar
```

### Troubleshooting USB Passthrough

**Problem**: Adapter not visible in VM

**Solutions**:
```bash
# 1. Check USB controller version
# Parallels: Ensure USB 3.0 is enabled (Pro Edition required)
# UTM: May need to select USB 3.0 in settings

# 2. Unplug and replug adapter
# 3. Restart VM
# 4. Check macOS System Settings → Privacy & Security → USB
```

**Problem**: Driver not loading

**Solutions**:
```bash
# Install kernel headers
sudo apt install -y linux-headers-$(uname -r)

# Rebuild driver
cd ~/rtl8814au
make clean
make
sudo make install
sudo modprobe 8814au
```

---

## Resource Allocation & Performance

### MacBook Air M3 Specifications

```
CPU: 8-core (4 performance + 4 efficiency)
RAM: 8GB or 16GB unified memory
GPU: 10-core (shared with RAM)
Storage: SSD (256GB - 2TB)
```

### Resource Allocation Guidelines

#### Conservative Setup (Recommended for 8GB MacBook)

**macOS Host**:
- 4 CPU cores
- 4 GB RAM
- Can run: Web browser, Terminal, VS Code

**Linux VM**:
- 4 CPU cores
- 4 GB RAM
- Can run: Kismet + CYT monitoring

**Total**: 8 cores, 8GB (fully utilized)

#### Balanced Setup (Recommended for 16GB MacBook)

**macOS Host**:
- 4 CPU cores
- 8 GB RAM
- Can run: Full productivity suite

**Linux VM**:
- 4 CPU cores
- 8 GB RAM
- Can run: Kismet + CYT + analysis

**Total**: 8 cores, 16GB (fully utilized)

#### Performance Setup (16GB MacBook, production use)

**macOS Host**:
- 2 CPU cores
- 4 GB RAM
- Minimal apps running

**Linux VM**:
- 6 CPU cores
- 12 GB RAM
- Can run: Full CYT stack + heavy analysis

**Total**: 8 cores, 16GB (VM-prioritized)

### Performance Tips

1. **Use Dynamically Allocated Disk**
   - VM only uses actual storage needed
   - Avoids wasting SSD space

2. **Disable Unused Features**
   - No GUI if using Ubuntu Server
   - Disable unnecessary services
   - Lightweight desktop if needed (XFCE, not GNOME)

3. **Monitor Resource Usage**
   ```bash
   # In VM
   htop

   # On macOS
   Activity Monitor → CPU/Memory tabs
   ```

4. **Optimize for Battery Life**
   - Reduce CPU cores when on battery
   - Lower RAM allocation
   - Pause VM when not in use

---

## Networking Configuration

### Network Modes Explained

#### 1. Shared Network (NAT) - Default

**How it works**:
- VM shares macOS internet connection
- VM gets private IP (e.g., 10.211.55.3)
- macOS acts as router

**Pros**:
- Easy setup (automatic)
- VM can access internet
- macOS can access VM services

**Cons**:
- External devices can't reach VM directly
- Slightly slower than bridged

**Use for CYT**: Development, testing

**Configuration**:
```bash
# VM automatically gets IP via DHCP
# Access VM from macOS: ssh cyt@10.211.55.3
# Access macOS from VM: 10.211.55.2 (gateway)
```

#### 2. Bridged Network

**How it works**:
- VM appears as separate device on network
- VM gets IP from router (e.g., 192.168.1.150)
- VM is network peer with macOS

**Pros**:
- VM has real network presence
- Other devices can connect
- Better for production

**Cons**:
- Requires network configuration
- May expose VM to network threats

**Use for CYT**: Production deployment, API server

**Configuration (Parallels)**:
1. VM Settings → Hardware → Network
2. Source: Bridged Network → Wi-Fi
3. Restart VM

**Configuration (UTM)**:
1. VM Settings → Network
2. Network Mode: Bridged
3. Interface: en0 (Wi-Fi)

#### 3. Host-Only Network

**How it works**:
- VM and macOS communicate privately
- No internet access for VM

**Pros**:
- Isolated testing environment
- Maximum security

**Cons**:
- No internet (must enable NAT too)
- Complex setup

**Use for CYT**: Security testing, malware analysis (not recommended for CYT)

### Port Forwarding (Shared Network)

Access VM services from macOS or external devices:

**Example: Access CYT API Server**

**Parallels**:
1. VM Settings → Hardware → Network
2. Advanced → Port Forwarding
3. Add Rule:
   - Source Port: 5000 (macOS)
   - Destination Port: 5000 (VM)
   - Protocol: TCP

**UTM**:
1. VM Settings → Network
2. Port Forward
3. Guest Port: 5000
4. Host Port: 5000

**Usage**:
```bash
# From macOS or other device
curl http://localhost:5000/api/alerts
```

---

## Use Cases for CYT Development

### Use Case 1: Development & Testing (Recommended)

**Setup**: UTM + Ubuntu Server 22.04 ARM64

**Workflow**:
1. Develop CYT code in macOS (VS Code)
2. Test in Linux VM (Kismet + real wireless adapter)
3. Iterate quickly

**Benefits**:
- Safe testing environment
- Easy to reset (snapshots)
- Learn Linux without risk
- Test Kismet configuration

**Example**:
```bash
# macOS (host)
cd ~/Chasing-Your-Tail-NG
code .  # Edit in VS Code

# Copy to VM via shared folder or git
# OR: Mount macOS folder in VM (Parallels)

# Linux VM
cd ~/Chasing-Your-Tail-NG
python3 chasing_your_tail.py
```

### Use Case 2: Isolated Production Environment

**Setup**: Parallels + Kali Linux ARM64

**Workflow**:
1. Run CYT 24/7 in VM
2. macOS available for other tasks
3. VM suspended when not needed

**Benefits**:
- Isolation from macOS
- Can snapshot before changes
- Easy backup/restore
- Professional deployment

**Example**:
```bash
# Start CYT daemon in VM
sudo python3 cyt_daemon.py start

# Suspend VM (Parallels)
# macOS continues normal operation

# Resume VM when needed
# CYT continues from saved state
```

### Use Case 3: Multi-Environment Testing

**Setup**: Multiple VMs (Ubuntu, Kali, Debian)

**Workflow**:
1. Test CYT on different distros
2. Verify compatibility
3. Test different Kismet versions

**Benefits**:
- Comprehensive testing
- Identify distro-specific issues
- Documentation accuracy

**Example**:
```bash
# VM 1: Ubuntu 22.04 + Kismet 2023.07
# VM 2: Kali 2024.3 + Kismet 2024.11
# VM 3: Debian 12 + Kismet 2023.07

# Test CYT on all three
# Document compatibility matrix
```

### Use Case 4: Learning & Education

**Setup**: UTM + Ubuntu Server

**Workflow**:
1. Learn Linux command line
2. Practice Kismet configuration
3. Understand wireless monitoring
4. Break things without consequences

**Benefits**:
- Safe learning environment
- Unlimited experimentation
- Easy reset (snapshots)
- No risk to macOS

**Example**:
```bash
# Experiment freely
sudo kismet -c wlan0  # Try different configs
python3 surveillance_analyzer.py --demo

# Made a mistake? Restore snapshot!
# VM Settings → Snapshots → Restore
```

---

## VM vs Native macOS: Pros & Cons

### Running CYT in Linux VM

**Pros**:
- ✅ Better wireless tool support (Kismet, aircrack-ng)
- ✅ Isolated environment (safe testing)
- ✅ Snapshots (easy rollback)
- ✅ Multiple environments (different distros)
- ✅ Professional deployment (closer to production)
- ✅ Better documentation (most Kismet guides assume Linux)

**Cons**:
- ❌ USB passthrough complexity (adapter may disconnect)
- ❌ Performance overhead (10-20% slower than native)
- ❌ Resource consumption (VM + macOS = more RAM/CPU)
- ❌ Learning curve (need to know Linux + virtualization)
- ❌ Cost (Parallels Pro $100/year for best USB support)

### Running CYT Natively on macOS

**Pros**:
- ✅ Direct hardware access (no USB passthrough issues)
- ✅ Best performance (native M3)
- ✅ Simpler setup (Homebrew install)
- ✅ Lower resource usage (no VM overhead)
- ✅ Free (no licensing costs)

**Cons**:
- ❌ Kismet on macOS less tested (most users use Linux)
- ❌ Wireless tools may have macOS-specific issues
- ❌ Harder to isolate (changes affect macOS)
- ❌ No snapshots (harder to recover from mistakes)
- ❌ Documentation assumes Linux (may need adaptation)

### Recommendation for CYT

**For Learning (First Month)**:
- Use **native macOS** with Homebrew Kismet
- Simpler, faster, cheaper
- Focus on CYT code, not Linux/VM complexity

**For Production (After Learning)**:
- Consider **Parallels VM** with Ubuntu/Kali
- Better isolation
- Professional deployment
- Easier troubleshooting

**Hybrid Approach (Best)**:
- **Primary**: Native macOS (daily use)
- **Backup**: UTM VM (testing, isolation, learning)
- **Production**: Parallels VM (field deployment, 24/7)

---

## Troubleshooting Common Issues

### Issue 1: USB Adapter Not Detected

**Symptoms**:
- `lsusb` doesn't show Alfa AWUS1900
- `iwconfig` shows no wireless interfaces

**Solutions**:

1. **Check USB Connection**
   ```bash
   # In VM
   lsusb

   # In macOS
   system_profiler SPUSBDataType | grep -A 10 Alfa
   ```

2. **Reconnect USB Device**
   - Parallels: Devices → USB → Reconnect
   - UTM: Unplug physically, replug, select in USB menu

3. **Check USB Version**
   - Parallels Pro required for USB 3.0
   - UTM: Settings → USB → USB 3.0 (check enabled)

4. **Install Driver**
   ```bash
   cd ~/rtl8814au
   make clean && make && sudo make install
   sudo modprobe 8814au
   ```

### Issue 2: VM is Slow

**Symptoms**:
- Laggy interface
- High CPU usage on macOS
- Tasks take much longer than expected

**Solutions**:

1. **Reduce Resource Allocation**
   ```
   Too many cores can cause overhead
   Try: 4 cores instead of 6
   ```

2. **Check macOS Activity Monitor**
   - Is macOS using too much RAM?
   - Close unnecessary apps

3. **Enable Performance Mode (Parallels)**
   - VM Settings → Hardware → Boot Order
   - Optimize for: Performance

4. **Disable Unnecessary Services in VM**
   ```bash
   sudo systemctl disable bluetooth
   sudo systemctl disable cups  # printing
   sudo systemctl disable avahi-daemon
   ```

### Issue 3: Network Not Working

**Symptoms**:
- No internet in VM
- Cannot ping gateway

**Solutions**:

1. **Check Network Adapter in VM**
   ```bash
   ip addr show
   # Should see eth0 or enp0s5 with IP address

   # If no IP:
   sudo dhclient
   ```

2. **Verify Network Mode**
   - Should be "Shared Network" or "Bridged"
   - UTM: Settings → Network → Network Mode
   - Parallels: Settings → Hardware → Network → Source

3. **Restart Networking**
   ```bash
   sudo systemctl restart networking
   # or
   sudo systemctl restart NetworkManager
   ```

4. **Check macOS Internet**
   - VM shares macOS connection
   - If macOS offline, VM offline too

### Issue 4: Kismet Won't Start

**Symptoms**:
- `kismet` command fails
- "Could not open capture interface" error

**Solutions**:

1. **Check Wireless Interface**
   ```bash
   iwconfig
   # Should show wlan0 or similar

   # If not, check driver:
   lsmod | grep 8814au
   ```

2. **Add User to Kismet Group**
   ```bash
   sudo usermod -aG kismet $USER
   # Log out and back in
   ```

3. **Run with Sudo (Not Recommended Long-Term)**
   ```bash
   sudo kismet -c wlan0
   ```

4. **Check Monitor Mode**
   ```bash
   sudo airmon-ng start wlan0
   iwconfig
   # Should show wlan0mon

   sudo kismet -c wlan0mon
   ```

### Issue 5: Cannot Access VM from macOS

**Symptoms**:
- SSH fails: `ssh cyt@10.211.55.3`
- Cannot reach CYT API

**Solutions**:

1. **Check VM IP Address**
   ```bash
   # In VM
   ip addr show
   # Note IP address (e.g., 10.211.55.3)
   ```

2. **Verify SSH is Running**
   ```bash
   sudo systemctl status ssh
   sudo systemctl start ssh
   sudo systemctl enable ssh
   ```

3. **Check Firewall**
   ```bash
   # Ubuntu
   sudo ufw status
   sudo ufw allow ssh

   # If firewall enabled and blocking
   sudo ufw disable  # For testing only
   ```

4. **Ping Test**
   ```bash
   # From macOS
   ping 10.211.55.3

   # If fails, network issue
   # If succeeds, SSH/firewall issue
   ```

---

## Advanced Topics

### Snapshots & Cloning

**Snapshots** = Save VM state at a point in time

**Use Cases**:
- Before major changes
- Before testing destructive commands
- Known-good baseline

**Parallels Snapshots**:
1. VM → Manage Snapshots
2. Click "+" to create snapshot
3. Name: "Clean Ubuntu Install" or "CYT Pre-Testing"
4. Restore: Select snapshot → "Go to Snapshot"

**UTM Snapshots**:
1. Right-click VM → "Clone"
2. Name: "CYT-Backup-2025-12-07"
3. Full clone (not linked)

**Best Practice**:
```
Snapshot Schedule:
- Initial install: "Base System"
- After CYT install: "CYT Installed"
- Before testing: "Pre-Test-YYYY-MM-DD"
- Known-good: "Production Ready"
```

### Shared Folders

Share files between macOS and VM without network.

**Parallels Shared Folders** (Easiest):
1. VM Settings → Options → Sharing
2. Share Mac folders with Linux: ON
3. Check: "Map to a network drive"
4. Access in VM: `/media/psf/Home/` or `/media/psf/Chasing-Your-Tail-NG/`

**Example**:
```bash
# macOS
cd ~/Chasing-Your-Tail-NG
code surveillance_detector.py  # Edit in VS Code

# Linux VM (Parallels)
cd /media/psf/Chasing-Your-Tail-NG
python3 surveillance_detector.py  # Test changes immediately
```

**UTM Shared Folders** (More Complex):
1. Requires SPICE guest tools
2. Settings → Sharing → Select macOS folder
3. Mount in VM: `mount -t 9p -o trans=virtio share /mnt/share`

### Automation with Scripts

**Auto-Start VM on macOS Boot** (Parallels):
1. VM Settings → Options → Startup and Shutdown
2. Startup automatically: When Mac starts
3. Shutdown automatically: Suspend

**Auto-Start CYT in VM**:
```bash
# Add to /etc/rc.local or systemd service
sudo systemctl enable cyt.service
```

**Script: Start CYT Environment**:
```bash
#!/bin/bash
# ~/start_cyt_vm.sh

# Start Parallels VM
prlctl start "CYT-Production"

# Wait for boot
sleep 30

# SSH in and start CYT
ssh cyt@10.211.55.3 "cd ~/Chasing-Your-Tail-NG && sudo python3 cyt_daemon.py start"

echo "CYT VM started and monitoring active"
```

### Remote Access to VM

**SSH from macOS**:
```bash
# Find VM IP
# Parallels: VM → Configure → Network → IP Address
# UTM: In VM run: ip addr show

# SSH in
ssh cyt@10.211.55.3

# Copy files
scp secure_database.py cyt@10.211.55.3:~/Chasing-Your-Tail-NG/
```

**SSH from External Devices** (Bridged Network):
```bash
# If VM on bridged network (e.g., 192.168.1.150)
ssh cyt@192.168.1.150

# Access CYT API
curl http://192.168.1.150:5000/api/alerts
```

**VS Code Remote Development**:
1. Install "Remote - SSH" extension in VS Code
2. Connect to VM: `ssh cyt@10.211.55.3`
3. Edit files directly in VM
4. Full VS Code features (IntelliSense, debugging)

### Performance Benchmarking

**Test VM Performance**:
```bash
# CPU benchmark
sysbench cpu --threads=4 run

# Disk I/O
sudo hdparm -tT /dev/sda

# Network throughput (from macOS)
# Install iperf3 in both macOS and VM
# VM:
iperf3 -s
# macOS:
iperf3 -c 10.211.55.3
```

**CYT-Specific Benchmark**:
```bash
# Test Kismet database query speed
time sqlite3 /tmp/kismet/*.kismet "SELECT COUNT(*) FROM devices;"

# Test behavioral detector performance
time python3 behavioral_drone_detector.py

# Monitor resource usage during CYT operation
htop  # Watch CPU/RAM while CYT runs
```

### Multi-VM Networking

**Scenario**: Multiple VMs need to communicate

**Example**:
- VM1: Kismet + CYT Monitor
- VM2: CYT API Server + Database
- VM3: Test client

**Setup** (Parallels):
1. Create custom network: Preferences → Network → Add
2. Name: "CYT-Network"
3. Type: Host-Only
4. All VMs: Settings → Network → Source: CYT-Network

**Setup** (UTM):
1. All VMs: Network Mode → Shared
2. VMs can see each other via 10.0.2.x subnet

**Test**:
```bash
# VM1
ping 10.211.55.4  # VM2 IP

# VM2
curl http://10.211.55.3:5000/api/alerts  # VM1 API
```

---

## Quick Start Checklist

### For CYT Development (Beginner-Friendly)

**Hardware**:
- [x] MacBook Air M3
- [x] Alfa AWUS1900 (ordered)
- [x] USB-C hub

**Software Setup** (Estimate: 2-3 hours):

1. **Install Virtualization Software**
   - [ ] Download UTM (free): https://mac.getutm.app/
   - [ ] Or purchase Parallels ($100): https://www.parallels.com/

2. **Download Linux ISO**
   - [ ] Ubuntu Server 22.04 ARM64: https://ubuntu.com/download/server/arm
   - [ ] Save to `~/Downloads/`

3. **Create VM**
   - [ ] Follow "Creating Your First Linux VM" section
   - [ ] Allocate: 4 CPU cores, 4GB RAM, 40GB disk
   - [ ] Install Ubuntu Server

4. **Configure VM**
   - [ ] Update system: `sudo apt update && sudo apt upgrade`
   - [ ] Install Kismet (see "Post-Installation Setup")
   - [ ] Clone CYT: `git clone https://github.com/SwampPop/Chasing-Your-Tail-NG.git`

5. **USB Passthrough**
   - [ ] Connect Alfa AWUS1900 to VM
   - [ ] Install driver: `rtl8814au`
   - [ ] Verify: `lsusb` and `iwconfig`

6. **Test CYT**
   - [ ] Run config validator: `python3 config_validator.py`
   - [ ] Start Kismet: `sudo kismet -c wlan0mon`
   - [ ] Run CYT: `python3 chasing_your_tail.py`

**Success Criteria**:
- ✅ VM boots and runs smoothly
- ✅ Alfa adapter visible in VM (`lsusb`)
- ✅ Kismet captures wireless frames
- ✅ CYT detects devices

---

## Conclusion & Recommendations

### For Your CYT Project

**Month 1 (Learning Phase)**:
- **Recommended**: Native macOS + Homebrew Kismet
- **Why**: Simpler, focus on CYT code
- **Backup**: Create UTM VM for experimentation

**Month 2+ (Production Phase)**:
- **Recommended**: Parallels VM + Ubuntu/Kali
- **Why**: Better isolation, professional deployment
- **Cost**: $100/year (worth it for USB reliability)

**Hybrid Strategy** (Best of Both Worlds):
1. **Develop on macOS**: VS Code, git, Python development
2. **Test in UTM**: Free VM for experimentation
3. **Deploy in Parallels**: Production-ready environment

### Key Takeaways

1. **VMs on M3 work great** for ARM64 Linux
2. **USB passthrough works** but Parallels is most reliable
3. **Resource management** is critical (4-6 cores, 4-8GB RAM)
4. **Snapshots** are your friend (backup before changes)
5. **Native macOS** is fine for CYT (don't overcomplicate)

### Next Steps

Once your Alfa AWUS1900 arrives:

1. **Try native macOS first**:
   ```bash
   brew install kismet aircrack-ng
   cd ~/Chasing-Your-Tail-NG
   python3 chasing_your_tail.py
   ```

2. **If issues arise, create VM**:
   - Follow this guide
   - UTM (free) or Parallels ($100)
   - Ubuntu Server 22.04 ARM64

3. **Join our community** (if exists):
   - Share VM setup experiences
   - Document macOS vs VM performance

---

## Resources & Links

**Virtualization Software**:
- UTM: https://mac.getutm.app/
- Parallels Desktop: https://www.parallels.com/
- VMware Fusion: https://www.vmware.com/products/fusion.html

**Linux Distributions (ARM64)**:
- Ubuntu Server: https://ubuntu.com/download/server/arm
- Kali Linux: https://www.kali.org/get-kali/#kali-installer-images
- Debian: https://www.debian.org/CD/netinst/

**Drivers & Tools**:
- RTL8814AU Driver: https://github.com/aircrack-ng/rtl8814au
- Kismet: https://www.kismetwireless.net/
- Aircrack-ng: https://www.aircrack-ng.org/

**CYT Project**:
- GitHub: https://github.com/SwampPop/Chasing-Your-Tail-NG
- Hardware Guide: `HARDWARE_REQUIREMENTS.md`
- Quick Start: `QUICK_START.md`
- Testing Guide: `TESTING_GUIDE.md`

**Learning Resources**:
- QEMU Documentation: https://www.qemu.org/docs/master/
- Ubuntu ARM64 Guide: https://ubuntu.com/download/raspberry-pi
- Parallels Knowledge Base: https://kb.parallels.com/

---

**Document Version**: 1.0
**Last Updated**: 2025-12-07
**Maintained By**: CYT Project
**License**: Same as CYT (MIT/GPL - check repository)

**Questions?** Open an issue on GitHub or consult the CYT community.

**Pro Tip**: Start simple (native macOS), add complexity (VM) only when needed. VMs are powerful but unnecessary for basic CYT testing!
