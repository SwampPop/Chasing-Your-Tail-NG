# Multi-Threat Detection Guide

**Last Updated**: 2025-12-02
**Feature**: Behavioral Threat Classification System

---

## Overview

Chasing Your Tail's behavioral detection system is **not just for drones** - it's a general-purpose wireless threat detection system that identifies multiple types of threats based on behavioral patterns.

The system analyzes 9 behavioral patterns and classifies threats into 8 distinct categories, each with specific characteristics and appropriate response strategies.

---

## Supported Threat Types

###  🚁 1. DRONE (Aerial Vehicle)

**What It Is:**
Unmanned aerial vehicles (drones) conducting surveillance or reconnaissance.

**Detection Signatures:**
- **Primary**: High mobility (>15 m/s / >54 km/h)
- **Primary**: Signal variance (altitude changes)
- **Primary**: No network association
- Speed consistent with aerial vehicles (faster than ground traffic)

**When You'll See This:**
- DJI drones, Parrot drones, custom-built drones
- Aerial surveillance operations
- Hobbyist drone flights near your location
- Commercial drone deliveries

**Why It's Concerning:**
- Can see over fences and into windows
- May carry cameras or sensors
- Could be mapping your property
- Privacy invasion from above

**Specific Actions:**
1. Visually scan the sky for aerial vehicles
2. Document flight path, altitude, and behavior
3. Note direction of travel and loitering patterns
4. Check local drone regulations (FAA in US)
5. Report to authorities if near sensitive areas
6. Consider RF detection equipment for persistent issues

---

### 🚗 2. WAR DRIVING (Mobile Reconnaissance)

**What It Is:**
Attackers in vehicles driving past your location to map and gather intelligence on Wi-Fi networks.

**Detection Signatures:**
- **Primary**: High mobility (5-25 m/s / 18-90 km/h)
- **Primary**: Channel hopping (scanning all channels)
- **Primary**: High probe frequency (active scanning)
- Speed consistent with vehicle traffic

**When You'll See This:**
- Vehicles with roof-mounted antennas
- Repeated passes by the same vehicle
- Late-night network scanning
- Mapping exercises by potential attackers

**Why It's Concerning:**
- Gathering intelligence for future attacks
- Identifying weak encryption (WEP, WPA)
- Building databases of vulnerable networks
- Planning entry points for intrusion

**Specific Actions:**
1. Note vehicle description (make, model, color, license if visible)
2. Document time patterns (do they return at specific times?)
3. Enable WPA3 encryption if not already active
4. Disable SSID broadcast temporarily if targeted
5. Check for weak authentication methods
6. Report repeated patterns to local authorities

---

### 📡 3. ROGUE AP (Rogue Access Point / Evil Twin)

**What It Is:**
Malicious access point mimicking your legitimate network to capture credentials and intercept traffic.

**Detection Signatures:**
- **Primary**: Stationary device (<1 m/s)
- **Primary**: High signal strength (close proximity)
- **Primary**: No network association
- May mimic your SSID name

**When You'll See This:**
- "Evil twin" attacks on your network
- Unauthorized AP in your building
- Man-in-the-middle attack setup
- Credential harvesting operations

**Why It's Concerning:**
- **CRITICAL THREAT**: Users may connect thinking it's legitimate
- Captures passwords, emails, sensitive data
- All traffic visible to attacker
- Can inject malware or redirect to phishing sites

**Specific Actions:**
1. **URGENT**: Warn all users NOT to connect to unknown networks
2. Perform immediate physical sweep for unauthorized equipment
3. Check if SSID matches or mimics your legitimate network name
4. Disconnect everyone and change Wi-Fi password if compromised
5. Enable 802.1X authentication (enterprise)
6. Report to network administrator/IT security immediately
7. Consider MAC filtering as temporary measure

---

### 👁️ 4. PACKET SNIFFER (Passive Monitor)

**What It Is:**
Device in passive monitoring mode capturing all wireless traffic for analysis.

**Detection Signatures:**
- **Primary**: No network association (passive mode)
- **Primary**: No client connections
- **Primary**: Channel hopping (monitoring all channels)
- Mostly stationary (<2 m/s)

**When You'll See This:**
- Hidden monitoring devices
- Corporate espionage tools
- Long-term surveillance equipment
- Network analysis tools (Wireshark, tcpdump)

**Why It's Concerning:**
- Captures ALL wireless traffic silently
- No indication to users they're being monitored
- Can decrypt weak encryption over time
- Builds database of network activity

**Specific Actions:**
1. Ensure ALL traffic uses end-to-end encryption (HTTPS, VPN)
2. Review what sensitive data was transmitted during timeframe
3. Rotate passwords if unencrypted traffic suspected
4. Enable mandatory VPN for all wireless traffic
5. Perform physical sweep for hidden monitoring devices
6. Check network equipment for tampering/compromises

---

### 🎯 5. STALKING (Following Pattern)

**What It Is:**
Mobile device following your movements across multiple locations - indicates physical stalking.

**Detection Signatures:**
- **Primary**: High mobility with hovering patterns
- **Primary**: Signal variance (distance changes)
- **Primary**: Appears at multiple locations you visit
- Pedestrian to slow vehicle speed (1-10 m/s)
- GPS correlation across locations

**When You'll See This:**
- Stalker's phone appearing wherever you go
- Device matches your route/schedule
- Same MAC at home, work, shopping areas
- Pattern correlates with your movements

**Why It's Concerning:**
- **SERIOUS SAFETY THREAT**: Indicates physical stalking
- Privacy invasion and threat to personal safety
- May escalate to harassment or violence
- Criminal offense in most jurisdictions

**Specific Actions:**
1. **URGENT**: Document ALL appearances with timestamps and exact locations
2. Review physical surroundings at each detection point
3. Vary your routines and routes immediately
4. Report to local law enforcement with full evidence
5. Consider restraining order if identity can be determined
6. Inform workplace/home security of the situation
7. Disable location services on devices when not needed
8. Consider professional security consultation

---

### 🚶 6. WALK-BY ATTACK (Proximity Threat)

**What It Is:**
Attacker on foot passing your location attempting quick exploitation of vulnerabilities.

**Detection Signatures:**
- **Primary**: Brief appearance (<5 minutes)
- **Primary**: High signal strength (close proximity)
- **Primary**: High probe frequency (active scanning)
- Pedestrian speed (1-5 m/s / 3.6-18 km/h)

**When You'll See This:**
- Pedestrian with concealed attack device
- Wi-Fi Pineapple or similar portable tool
- Quick vulnerability assessment
- Targeted attack on specific location

**Why It's Concerning:**
- Attacker can be physically close (5-20 meters)
- May be casing location for future attack
- Could be deploying rogue device
- Indicates targeted interest in your network

**Specific Actions:**
1. Review security camera footage for the exact timeframe
2. Note any pedestrians who lingered or acted suspiciously
3. Increase physical security awareness
4. Disable device auto-connect to open networks
5. Ensure Bluetooth and Wi-Fi are off when not needed
6. Consider motion-activated security cameras if persistent

---

### 🔍 7. PENETRATION TEST (Active Security Assessment)

**What It Is:**
Active network reconnaissance and vulnerability scanning - could be legitimate testing or malicious.

**Detection Signatures:**
- **Primary**: High probe frequency (active scanning)
- **Primary**: Channel hopping (surveying spectrum)
- **Primary**: No network association
- Pattern matches security tool signatures

**When You'll See This:**
- Authorized penetration testing
- Security audits by IT team
- Malicious attacker reconnaissance
- Automated vulnerability scanners

**Why It's Concerning:**
- Could be prelude to attack if unauthorized
- Identifies exploitable vulnerabilities
- Maps your security posture
- May indicate imminent intrusion attempt

**Specific Actions:**
1. **FIRST**: Verify if authorized security testing is scheduled
2. Contact IT/security team immediately to confirm legitimacy
3. If unauthorized, treat as active attack in progress
4. Enable intrusion detection/prevention systems
5. Review firewall logs for scanning patterns
6. Document scan signatures for threat intelligence
7. Report to incident response team (corporate environment)

---

### ❓ 8. UNKNOWN (Unclassified Threat)

**What It Is:**
Suspicious behavior detected but doesn't perfectly match any known threat signature.

**Detection Characteristics:**
- Multiple suspicious patterns detected
- Behavior doesn't match expected threat signatures
- May be novel attack method
- Could be benign device with unusual behavior

**When You'll See This:**
- New/emerging attack techniques
- Legitimate devices with unusual patterns
- Environmental factors causing false signals
- Incomplete data preventing classification

**Why It Shows Up:**
- Threat signatures are based on known patterns
- Real-world threats don't always match textbook examples
- Device behavior may be hybrid or unusual
- Intentional evasion of detection signatures

**Specific Actions:**
1. Review pattern details carefully to understand behavior
2. Monitor for recurrence to identify consistent patterns
3. Document thoroughly for manual pattern analysis
4. Consider whether legitimate use could cause this pattern
5. May require human analysis for proper classification

---

## How Classification Works

### Pattern Analysis Process

1. **Behavioral Detection** (9 patterns analyzed)
   - High Mobility
   - Signal Variance
   - Hovering Pattern
   - Brief Appearance
   - No Association
   - High Signal Strength
   - Probe Frequency
   - Channel Hopping
   - No Client Connections

2. **Pattern Combination Matching**
   - System looks for specific combinations of patterns
   - Each threat type has a unique "signature"
   - Example: Drone = High Mobility + Signal Variance + No Association + Speed >15 m/s

3. **Speed-Based Discrimination**
   - **Aerial** (>15 m/s): Drones, aircraft
   - **Vehicle** (5-25 m/s): War driving, mobile threats
   - **Pedestrian** (1-5 m/s): Walk-by attacks, stalking
   - **Stationary** (<1 m/s): Rogue APs, sniffers

4. **Classification Output**
   - **Threat Type**: Primary classification
   - **Confidence**: How well patterns match (0-100%)
   - **Reasoning**: Explanation of why this classification was chosen

### Classification Hierarchy

The system checks threat signatures in priority order:

```
1. DRONE (highest confidence threshold: 90%)
2. WAR_DRIVING (85%)
3. ROGUE_AP (80%)
4. PACKET_SNIFFER (75%)
5. STALKING (70%)
6. WALK_BY_ATTACK (65%)
7. PENETRATION_TEST (60%)
8. UNKNOWN (fallback)
```

If multiple signatures match, the one with highest confidence is selected.

---

## Understanding Reports

### Report Header Example

```markdown
# 🔴 Behavioral Threat Detection Report

**Detection Time:** 2025-12-02 14:30:15
**Threat Level:** 🔴 HIGH
**Threat Type:** 🚗 War Driving / Mobile Reconnaissance
**Classification Confidence:** 85.0%

## Executive Summary

This report details a War Driving / Mobile Reconnaissance detection...

**Classification Reasoning:** Mobile reconnaissance at vehicle speed

**Overall Confidence Score:** 78.5%
```

### Key Sections

1. **Threat Type**: Primary classification with emoji
2. **Classification Confidence**: How sure the system is about threat type
3. **Classification Reasoning**: Why this classification was chosen
4. **Pattern Summary**: Which of 9 patterns were detected
5. **Threat-Specific Recommendations**: Actions tailored to this threat type

---

## Real-World Scenarios

### Scenario 1: Late-Night Vehicle Pass

**Detection:**
- Threat Type: WAR_DRIVING
- Patterns: High Mobility (20 m/s) + Channel Hopping + Probe Frequency
- Time: 2:30 AM

**What Happened:**
Vehicle drove past at 72 km/h scanning all Wi-Fi channels with high probe frequency.

**Response:**
1. Checked WPA3 encryption status
2. Reviewed security camera footage
3. Documented vehicle description
4. Reported to authorities (3rd occurrence)

---

### Scenario 2: Hovering Strong Signal

**Detection:**
- Threat Type: ROGUE_AP
- Patterns: Stationary + High Signal (-35 dBm) + No Association
- SSID: "Home-WiFi" (mimicking legitimate "HomeWiFi")

**What Happened:**
Rogue access point in parking lot mimicking legitimate network to capture credentials.

**Response:**
1. Immediate user warning sent
2. Physical sweep located device in vehicle
3. Police called - equipment seized
4. All passwords rotated
5. Enabled 802.1X authentication

---

### Scenario 3: Appears at Multiple Locations

**Detection:**
- Threat Type: STALKING
- Patterns: High Mobility + Hovering + Multiple Locations (5 different places)
- Speed: 3 m/s (pedestrian)

**What Happened:**
Same MAC address detected at home, workplace, gym, shopping center over 3 days.

**Response:**
1. Law enforcement immediately notified
2. Comprehensive documentation prepared
3. Restraining order obtained
4. Security measures enhanced

---

## False Positives

### Legitimate Devices That May Trigger Detection

**Delivery Drones:**
- Type: DRONE
- Legitimate Use: Package delivery, surveying
- How to Confirm: Check for DJI OUI, expected schedule

**Network Survey Teams:**
- Type: PENETRATION_TEST
- Legitimate Use: ISP site surveys, IT assessments
- How to Confirm: Scheduled with IT/facilities

**Mobile Hotspots:**
- Type: Various
- Legitimate Use: Traveling users, mobile workers
- How to Confirm: Known employee devices, regular patterns

**GPS Tracking Devices:**
- Type: STALKING (false positive)
- Legitimate Use: Fleet vehicles, personal tracking
- How to Confirm: Commercial vehicle patterns, authorized use

### Reducing False Positives

1. **Use Ignore Lists**: Add known legitimate devices
2. **Check Manufacturer** (OUI): Known brands often legitimate
3. **Pattern Review**: Single pattern matches are less concerning
4. **Time Correlation**: Business hours vs. suspicious hours
5. **Location Context**: Expected vs. unexpected locations

---

## Integration with Existing Features

### OUI Matching (Layer 1)
- Still works for known drone manufacturers
- Instant RED alerts for DJI, Parrot, 3DR, etc.
- Threat classification adds context to OUI matches

### Behavioral Analysis (Layer 2)
- Now includes automatic threat classification
- Provides specific threat type, not just "suspicious"
- Threat-specific recommendations generated

### Persistence Scoring (Layer 3)
- Combines with threat classification
- Stalking threats scored on persistence
- Multi-location tracking enhanced

---

## Configuration

### Enable/Disable Classification

In `config.json`:

```json
{
  "behavioral_drone_detection": {
    "enabled": true,
    "confidence_threshold": 0.60
  }
}
```

Classification runs automatically when behavioral detection is enabled.

### Adjusting Sensitivity

**Speed Thresholds** (in `behavioral_drone_detector.py`):
- Drone threshold: 15 m/s (54 km/h)
- Vehicle range: 5-25 m/s (18-90 km/h)
- Pedestrian range: 1-5 m/s (3.6-18 km/h)

**Classification Confidence:**
- Affects which threat type is selected
- Higher threshold = more conservative classification
- Lower threshold = more aggressive classification

---

## Advanced Topics

### Multi-Stage Attacks

Some attacks involve multiple phases:

1. **Reconnaissance** (PENETRATION_TEST or WAR_DRIVING)
2. **Deployment** (ROGUE_AP setup)
3. **Exploitation** (Active attack via rogue AP)

CYT can detect each phase if patterns are visible.

### Hybrid Threats

Some threats exhibit characteristics of multiple types:

- **Drone with Rogue AP**: Aerial + Evil Twin combined
- **War Driving with Packet Sniffing**: Mobile + Passive monitoring
- **Stalking with Active Scanning**: Following + Probe attacks

Classification chooses the best match or marks as UNKNOWN if ambiguous.

### Evasion Techniques

Attackers may try to evade detection:

- **Randomized MAC**: Changes MAC to avoid tracking
- **Low Power**: Reduces signal to avoid detection
- **Intermittent Activity**: Brief bursts to avoid pattern matching
- **Mimicry**: Tries to look like legitimate traffic

CYT's behavioral analysis is harder to evade than simple signature-based detection.

---

## Best Practices

### For Home Users

1. **Enable WPA3** encryption
2. **Disable SSID** broadcast if targeted
3. **Monitor reports** for recurring threats
4. **Document everything** for law enforcement
5. **Report stalking** immediately

### For Corporate Environments

1. **Enable 802.1X** authentication
2. **Deploy IDS/IPS** for active monitoring
3. **Coordinate with IT** on authorized testing
4. **Share threat intelligence** across organization
5. **Incident response plan** for each threat type

### For High-Security Locations

1. **Physical security** surveys for rogue devices
2. **RF shielding** for sensitive areas
3. **Active countermeasures** (where legal)
4. **Professional** security consultation
5. **24/7 monitoring** and rapid response

---

## Getting Help

### Uncertain Classification

If you're unsure about a classification:

1. Review the **Classification Reasoning** in the report
2. Check the **Pattern Details** section
3. Look at **GPS movement** if available
4. Consider the **location and time context**
5. Cross-reference with **physical observations**

### Persistent Threats

If same threat appears repeatedly:

1. Document **all occurrences** with timestamps
2. Look for **patterns** in timing or location
3. **Report to authorities** with evidence
4. Consider **professional security** assessment
5. **Escalate** based on threat level

### False Positive Concerns

If you think it's a false positive:

1. Check if device is **known legitimate** device
2. Review **manufacturer** (OUI lookup)
3. Consider **context** (location, time, purpose)
4. Add to **ignore list** if confirmed benign
5. **Monitor** for recurrence with adjusted settings

---

## Future Enhancements

Planned improvements to threat classification:

- **Machine Learning**: Automatic signature refinement from real-world data
- **Threat Intelligence**: Integration with external threat databases
- **Historical Analysis**: Pattern recognition across time
- **Automated Response**: Configurable actions per threat type
- **API Integration**: Push classifications to SIEM/SOC systems

---

## Summary

The multi-threat classification system makes CYT much more than a drone detector:

✅ **8 Distinct Threat Types** identified automatically
✅ **Threat-Specific Recommendations** for each type
✅ **Speed-Based Discrimination** for accurate classification
✅ **Behavioral Pattern Analysis** harder to evade than signatures
✅ **Professional Reports** with classification reasoning
✅ **General-Purpose Detection** for all wireless threats

**The behavioral detection system is now a comprehensive wireless threat intelligence platform.**

---

**Questions?** See the [Behavioral Drone Detection Guide](BEHAVIORAL_DRONE_DETECTION.md) for detailed pattern information, or [Quick Start Guide](QUICK_START.md) for deployment instructions.
