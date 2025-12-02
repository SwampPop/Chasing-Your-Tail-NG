#!/usr/bin/env python3
"""
Behavioral Detection Report Generator
Generates detailed analysis reports for behavioral drone detections.

Creates rich Markdown/HTML reports showing:
- Confidence scores and threat levels
- Pattern-by-pattern analysis
- Visual indicators and charts
- GPS movement tracking
- Historical trends
- Actionable recommendations
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)


@dataclass
class BehavioralDetection:
    """Represents a behavioral detection event."""
    mac: str
    timestamp: float
    confidence: float
    patterns: Dict[str, Any]
    device_history: Any  # DeviceHistory object from behavioral_drone_detector.py
    oui_manufacturer: Optional[str] = None
    threat_level: Optional[str] = None


class BehavioralReportGenerator:
    """Generates detailed reports for behavioral drone detections."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize behavioral report generator.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.report_config = self.config.get('behavioral_report', {})
        self.output_dir = self.report_config.get('output_dir', 'behavioral_reports')

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Threat level thresholds
        self.thresholds = {
            'high': 0.75,    # 75%+ confidence = HIGH threat
            'medium': 0.50,  # 50-75% confidence = MEDIUM threat
            'low': 0.30      # 30-50% confidence = LOW threat
        }

    def determine_threat_level(self, confidence: float) -> Tuple[str, str, str]:
        """
        Determine threat level from confidence score.

        Args:
            confidence: Confidence score (0.0-1.0)

        Returns:
            Tuple of (level, emoji, color)
        """
        if confidence >= self.thresholds['high']:
            return ('HIGH', '🔴', 'red')
        elif confidence >= self.thresholds['medium']:
            return ('MEDIUM', '🟡', 'yellow')
        elif confidence >= self.thresholds['low']:
            return ('LOW', '🟢', 'green')
        else:
            return ('MINIMAL', '⚪', 'gray')

    def generate_confidence_bar(self, confidence: float, width: int = 50) -> str:
        """
        Generate ASCII confidence bar visualization.

        Args:
            confidence: Confidence score (0.0-1.0)
            width: Width of bar in characters

        Returns:
            ASCII bar representation
        """
        filled = int(confidence * width)
        empty = width - filled
        bar = '█' * filled + '░' * empty
        percentage = confidence * 100
        return f"[{bar}] {percentage:.1f}%"

    def generate_pattern_summary(self, patterns: Dict[str, Any]) -> str:
        """
        Generate summary of detected patterns.

        Args:
            patterns: Pattern detection results

        Returns:
            Formatted pattern summary
        """
        lines = []
        lines.append("### 📊 Pattern Detection Summary\n")

        pattern_names = {
            'high_mobility': '🚁 High Mobility',
            'signal_variance': '📡 Signal Variance',
            'hovering': '🎯 Hovering Pattern',
            'brief_appearance': '⏱️  Brief Appearance',
            'no_association': '🔌 No Association',
            'high_signal': '📶 High Signal Strength',
            'probe_frequency': '🔍 Probe Frequency',
            'channel_hopping': '🔀 Channel Hopping',
            'no_clients': '👤 No Clients'
        }

        detected_count = sum(1 for p in patterns.values() if p.get('detected', False))
        total_count = len(patterns)

        lines.append(f"**Patterns Detected:** {detected_count}/{total_count}\n")
        lines.append("| Pattern | Status | Details |")
        lines.append("|---------|--------|---------|")

        for pattern_key, pattern_name in pattern_names.items():
            if pattern_key in patterns:
                pattern_data = patterns[pattern_key]
                detected = pattern_data.get('detected', False)
                status = '✅ **DETECTED**' if detected else '❌ Not Detected'

                # Build details string
                details = []
                if detected:
                    if 'score' in pattern_data:
                        details.append(f"Score: {pattern_data['score']:.3f}")
                    if 'speed_mps' in pattern_data:
                        details.append(f"Speed: {pattern_data['speed_mps']:.1f} m/s")
                    if 'variance' in pattern_data:
                        details.append(f"Variance: {pattern_data['variance']:.2f}")
                    if 'duration_seconds' in pattern_data:
                        mins = pattern_data['duration_seconds'] / 60
                        details.append(f"Duration: {mins:.1f} min")
                    if 'avg_signal' in pattern_data:
                        details.append(f"Signal: {pattern_data['avg_signal']} dBm")
                    if 'probes_per_minute' in pattern_data:
                        details.append(f"Freq: {pattern_data['probes_per_minute']:.1f}/min")
                    if 'channels' in pattern_data:
                        details.append(f"Channels: {len(pattern_data['channels'])}")

                details_str = ', '.join(details) if details else '—'
                lines.append(f"| {pattern_name} | {status} | {details_str} |")

        lines.append("")
        return '\n'.join(lines)

    def generate_detailed_pattern_analysis(self, patterns: Dict[str, Any]) -> str:
        """
        Generate detailed analysis for each detected pattern.

        Args:
            patterns: Pattern detection results

        Returns:
            Formatted detailed analysis
        """
        lines = []
        lines.append("### 🔍 Detailed Pattern Analysis\n")

        # Pattern 1: High Mobility
        if patterns.get('high_mobility', {}).get('detected'):
            data = patterns['high_mobility']
            lines.append("#### 🚁 High Mobility Pattern")
            lines.append("")
            lines.append(f"**Speed:** {data['speed_mps']:.1f} m/s ({data['speed_mps'] * 3.6:.1f} km/h)")
            lines.append(f"**Contribution:** {data['score']:.3f} ({data['score']*100:.1f}%)")
            lines.append("")
            lines.append("**What This Means:**")
            lines.append("This device is moving at speeds consistent with aerial vehicles. "
                        "Ground-based devices (phones, laptops) typically don't move this fast.")
            lines.append("")

        # Pattern 2: Signal Variance
        if patterns.get('signal_variance', {}).get('detected'):
            data = patterns['signal_variance']
            lines.append("#### 📡 Signal Variance Pattern")
            lines.append("")
            lines.append(f"**Variance Level:** {data['variance']:.2f}")
            lines.append(f"**Contribution:** {data['score']:.3f} ({data['score']*100:.1f}%)")
            lines.append("")
            lines.append("**What This Means:**")
            lines.append("Signal strength is changing rapidly, suggesting altitude or distance changes. "
                        "This is common for drones hovering or moving vertically.")
            lines.append("")

        # Pattern 3: Hovering
        if patterns.get('hovering', {}).get('detected'):
            data = patterns['hovering']
            lines.append("#### 🎯 Hovering Pattern")
            lines.append("")
            lines.append(f"**Movement Radius:** {data['radius_meters']} meters")
            lines.append(f"**Contribution:** {data['score']:.3f} ({data['score']*100:.1f}%)")
            lines.append("")
            lines.append("**What This Means:**")
            lines.append("The device is staying within a small area, characteristic of a hovering drone "
                        "or surveillance platform.")
            lines.append("")

        # Pattern 4: Brief Appearance
        if patterns.get('brief_appearance', {}).get('detected'):
            data = patterns['brief_appearance']
            duration_mins = data['duration_seconds'] / 60
            lines.append("#### ⏱️ Brief Appearance Pattern")
            lines.append("")
            lines.append(f"**Total Duration:** {duration_mins:.1f} minutes")
            lines.append(f"**Contribution:** {data['score']:.3f} ({data['score']*100:.1f}%)")
            lines.append("")
            lines.append("**What This Means:**")
            lines.append("Short appearance time suggests reconnaissance or surveillance activity. "
                        "Legitimate devices typically connect for longer periods.")
            lines.append("")

        # Pattern 5: No Association
        if patterns.get('no_association', {}).get('detected'):
            data = patterns['no_association']
            lines.append("#### 🔌 No Association Pattern")
            lines.append("")
            lines.append(f"**Contribution:** {data['score']:.3f} ({data['score']*100:.1f}%)")
            lines.append("")
            lines.append("**What This Means:**")
            lines.append("The device has never connected to any Wi-Fi network. Drones typically don't "
                        "associate with access points - they just observe.")
            lines.append("")

        # Pattern 6: High Signal Strength
        if patterns.get('high_signal', {}).get('detected'):
            data = patterns['high_signal']
            lines.append("#### 📶 High Signal Strength Pattern")
            lines.append("")
            lines.append(f"**Average Signal:** {data['avg_signal']} dBm")
            lines.append(f"**Contribution:** {data['score']:.3f} ({data['score']*100:.1f}%)")
            lines.append("")
            lines.append("**What This Means:**")
            lines.append("Very strong signal suggests the device is close to you. Combined with other "
                        "patterns, this indicates potential close-range surveillance.")
            lines.append("")

        # Pattern 7: Probe Frequency
        if patterns.get('probe_frequency', {}).get('detected'):
            data = patterns['probe_frequency']
            lines.append("#### 🔍 Probe Frequency Pattern")
            lines.append("")
            lines.append(f"**Probes Per Minute:** {data['probes_per_minute']:.1f}")
            lines.append(f"**Contribution:** {data['score']:.3f} ({data['score']*100:.1f}%)")
            lines.append("")
            lines.append("**What This Means:**")
            lines.append("High probe frequency indicates active scanning behavior, common in surveillance "
                        "devices mapping the wireless environment.")
            lines.append("")

        # Pattern 8: Channel Hopping
        if patterns.get('channel_hopping', {}).get('detected'):
            data = patterns['channel_hopping']
            channels = data['channels']
            lines.append("#### 🔀 Channel Hopping Pattern")
            lines.append("")
            lines.append(f"**Channels Seen:** {', '.join(map(str, channels))}")
            lines.append(f"**Total Channels:** {len(channels)}")
            lines.append(f"**Contribution:** {data['score']:.3f} ({data['score']*100:.1f}%)")
            lines.append("")
            lines.append("**What This Means:**")
            lines.append("Device is active on multiple Wi-Fi channels, indicating scanning or "
                        "reconnaissance activity across the spectrum.")
            lines.append("")

        # Pattern 9: No Clients
        if patterns.get('no_clients', {}).get('detected'):
            data = patterns['no_clients']
            lines.append("#### 👤 No Clients Pattern")
            lines.append("")
            lines.append(f"**Contribution:** {data['score']:.3f} ({data['score']*100:.1f}%)")
            lines.append("")
            lines.append("**What This Means:**")
            lines.append("The device has no client connections, suggesting it's a standalone surveillance "
                        "device rather than a legitimate access point serving users.")
            lines.append("")

        return '\n'.join(lines)

    def generate_device_summary(self, detection: BehavioralDetection) -> str:
        """
        Generate device information summary.

        Args:
            detection: BehavioralDetection object

        Returns:
            Formatted device summary
        """
        lines = []
        lines.append("### 📱 Device Information\n")

        lines.append(f"**MAC Address:** `{detection.mac}`")

        if detection.oui_manufacturer:
            lines.append(f"**Manufacturer:** {detection.oui_manufacturer}")
        else:
            lines.append("**Manufacturer:** Unknown (not in OUI database)")

        history = detection.device_history
        lines.append(f"**First Seen:** {datetime.fromtimestamp(history.first_seen).strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Last Seen:** {datetime.fromtimestamp(history.last_seen).strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Total Appearances:** {len(history.appearances)}")

        duration_seconds = history.last_seen - history.first_seen
        duration_mins = duration_seconds / 60
        lines.append(f"**Observation Duration:** {duration_mins:.1f} minutes")

        if history.locations:
            lines.append(f"**GPS Locations Tracked:** {len(history.locations)}")

        lines.append("")
        return '\n'.join(lines)

    def generate_gps_summary(self, detection: BehavioralDetection) -> str:
        """
        Generate GPS movement summary.

        Args:
            detection: BehavioralDetection object

        Returns:
            Formatted GPS summary
        """
        history = detection.device_history
        if not history.locations:
            return "### 🗺️ GPS Movement Analysis\n\n**No GPS data available for this detection.**\n\n"

        lines = []
        lines.append("### 🗺️ GPS Movement Analysis\n")

        lines.append(f"**Total Locations:** {len(history.locations)}")

        # Calculate movement summary
        lats = [loc[0] for loc in history.locations]
        lons = [loc[1] for loc in history.locations]

        lines.append(f"**Latitude Range:** {min(lats):.6f} to {max(lats):.6f}")
        lines.append(f"**Longitude Range:** {min(lons):.6f} to {max(lons):.6f}")

        lines.append("\n**Tracked Positions:**")
        lines.append("| Timestamp | Latitude | Longitude |")
        lines.append("|-----------|----------|-----------|")

        for i, (timestamp, location) in enumerate(zip(history.appearances[:len(history.locations)], history.locations)):
            dt = datetime.fromtimestamp(timestamp)
            lines.append(f"| {dt.strftime('%H:%M:%S')} | {location[0]:.6f} | {location[1]:.6f} |")

        lines.append("")
        return '\n'.join(lines)

    def generate_recommendations(self, detection: BehavioralDetection) -> str:
        """
        Generate actionable recommendations based on detection.

        Args:
            detection: BehavioralDetection object

        Returns:
            Formatted recommendations
        """
        lines = []
        lines.append("### 💡 Recommendations\n")

        threat_level, _, _ = self.determine_threat_level(detection.confidence)

        if threat_level == 'HIGH':
            lines.append("**⚠️ HIGH THREAT - Immediate Action Recommended:**")
            lines.append("1. Document this detection with screenshots")
            lines.append("2. Note the exact time and location")
            lines.append("3. Look for physical drones in the area")
            lines.append("4. Consider reporting to local authorities if pattern continues")
            lines.append("5. Review security camera footage for the timeframe")
        elif threat_level == 'MEDIUM':
            lines.append("**⚠️ MEDIUM THREAT - Monitoring Recommended:**")
            lines.append("1. Continue monitoring for pattern recurrence")
            lines.append("2. Document the detection for future reference")
            lines.append("3. Check if device appears in future sessions")
            lines.append("4. Review physical surroundings during detection time")
        else:
            lines.append("**ℹ️ LOW THREAT - Awareness Level:**")
            lines.append("1. Keep this detection on record")
            lines.append("2. Watch for similar patterns in future")
            lines.append("3. May be a legitimate device with unusual behavior")

        lines.append("")
        lines.append("**General Actions:**")
        lines.append("- Add to watchlist if concerned: `/watchlist add " + detection.mac + "`")
        lines.append("- Add to ignore list if false positive: add to `ignore_lists/mac_list.txt`")
        lines.append("- Export KML file for GPS visualization in Google Earth")

        lines.append("")
        return '\n'.join(lines)

    def generate_markdown_report(self, detection: BehavioralDetection) -> str:
        """
        Generate complete Markdown report for a behavioral detection.

        Args:
            detection: BehavioralDetection object

        Returns:
            Complete Markdown report
        """
        threat_level, emoji, _ = self.determine_threat_level(detection.confidence)
        detection.threat_level = threat_level

        lines = []

        # Header
        lines.append(f"# {emoji} Behavioral Drone Detection Report\n")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Detection Time:** {datetime.fromtimestamp(detection.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Threat Level:** {emoji} **{threat_level}**")
        lines.append("")

        # Executive Summary
        lines.append("## 📋 Executive Summary\n")
        lines.append("This report details a potential drone detection based on behavioral pattern analysis. "
                    "The system analyzed wireless device behavior and assigned a confidence score based on "
                    "suspicious patterns.")
        lines.append("")
        lines.append(f"**Confidence Score:** {detection.confidence:.1%}")
        lines.append("")
        lines.append(self.generate_confidence_bar(detection.confidence))
        lines.append("")

        # Device Information
        lines.append(self.generate_device_summary(detection))

        # Pattern Summary
        lines.append(self.generate_pattern_summary(detection.patterns))

        # Detailed Analysis
        lines.append(self.generate_detailed_pattern_analysis(detection.patterns))

        # GPS Analysis
        lines.append(self.generate_gps_summary(detection))

        # Recommendations
        lines.append(self.generate_recommendations(detection))

        # Footer
        lines.append("---")
        lines.append("*Generated by Chasing Your Tail - Behavioral Drone Detection System*")
        lines.append("")

        return '\n'.join(lines)

    def save_report(self, detection: BehavioralDetection, filename: Optional[str] = None) -> str:
        """
        Generate and save a behavioral detection report.

        Args:
            detection: BehavioralDetection object
            filename: Optional custom filename (without extension)

        Returns:
            Path to saved report file
        """
        if not filename:
            timestamp = datetime.fromtimestamp(detection.timestamp).strftime('%Y%m%d_%H%M%S')
            mac_safe = detection.mac.replace(':', '-')
            filename = f"behavioral_{mac_safe}_{timestamp}"

        # Generate Markdown report
        markdown_content = self.generate_markdown_report(detection)

        # Save Markdown version
        md_path = os.path.join(self.output_dir, f"{filename}.md")
        with open(md_path, 'w') as f:
            f.write(markdown_content)

        logger.info(f"Behavioral detection report saved: {md_path}")
        return md_path


# Standalone testing
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from behavioral_drone_detector import BehavioralDroneDetector, DeviceHistory

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 70)
    print("BEHAVIORAL DETECTION REPORT GENERATOR - TEST")
    print("=" * 70)
    print()

    # Create test detector
    detector = BehavioralDroneDetector()

    # Simulate a suspicious device
    test_mac = "AA:BB:CC:DD:EE:FF"
    print(f"Simulating behavioral detection for device: {test_mac}")
    print()

    # Simulate device appearances
    import time
    current_time = time.time()

    for i in range(5):
        device_data = {
            'signal': -45 + (i * 5),  # Varying signal
            'lat': 37.7749 + (i * 0.0001),  # Moving
            'lon': -122.4194 + (i * 0.0001),
            'channel': 6 if i < 3 else 11,  # Channel hopping
            'type': 'probe'
        }
        detector.update_device_history(test_mac, device_data)
        time.sleep(0.1)

    # Analyze device
    confidence, patterns = detector.analyze_device(test_mac)

    print(f"Analysis Results:")
    print(f"  Confidence: {confidence:.1%}")
    print(f"  Patterns Detected: {sum(1 for p in patterns.values() if p.get('detected', False))}/9")
    print()

    # Create detection object
    detection = BehavioralDetection(
        mac=test_mac,
        timestamp=current_time,
        confidence=confidence,
        patterns=patterns,
        device_history=detector.device_history[test_mac],
        oui_manufacturer="Unknown (Test)"
    )

    # Generate report
    generator = BehavioralReportGenerator()
    report_path = generator.save_report(detection)

    print(f"✅ Report generated successfully!")
    print(f"   Location: {report_path}")
    print()
    print("Preview:")
    print("-" * 70)

    with open(report_path, 'r') as f:
        preview = f.read()[:1000]
        print(preview)
        print("...")
        print("-" * 70)

    print()
    print("Test complete!")
