"""
Report Generation System for CYT
Generates detailed intelligence reports from analysis results.
"""
from surveillance_detector import SuspiciousDevice
from cyt_constants import PersistenceLevel, SystemConstants
import logging
from datetime import datetime
from typing import Dict, List, Any
import subprocess

logger = logging.getLogger(__name__)

# NOTE: You need to copy your dataclass definitions here so the reporter understands the data structure


class ReportGenerator:
    """Generates detailed surveillance analysis reports."""

    def __init__(self, suspicious_devices: List[SuspiciousDevice], all_appearances: List[Any],
                 device_history: Dict[str, List[Any]], thresholds: Dict, config: Dict = None):
        self.suspicious_devices = suspicious_devices
        self.all_appearances = all_appearances
        self.device_history = device_history
        self.thresholds = thresholds
        self.config = config or {}
        self.stats = self._generate_analysis_statistics()

    def _generate_analysis_statistics(self) -> Dict:
        """Generate comprehensive statistics for the analysis"""
        # Get detection accuracy from config or use default
        report_settings = self.config.get('report_settings', {})
        detection_accuracy = report_settings.get('detection_accuracy', 0.95)

        if not self.all_appearances:
            return {
                'total_appearances': 0, 'unique_devices': 0,
                'unique_locations': 0, 'analysis_duration_hours': 0,
                'persistence_rate': 0, 'multi_location_rate': 0,
                'detection_accuracy': detection_accuracy
            }

        total_appearances = len(self.all_appearances)
        unique_devices = len(self.device_history)
        unique_locations = len(
            set(a.location_id for a in self.all_appearances))

        timestamps = [a.timestamp for a in self.all_appearances]
        analysis_duration = (max(timestamps) - min(timestamps)
                             if timestamps else 0)
        analysis_duration_hours = (analysis_duration / 3600
                                   if analysis_duration > 0 else 0)

        persistent_devices = [
            mac for mac, apps in self.device_history.items()
            if len(apps) >= self.thresholds.get('min_appearances', 3)]
        persistence_rate = (len(persistent_devices) / unique_devices
                            if unique_devices > 0 else 0)

        multi_location_devices = sum(
            1 for mac, apps in self.device_history.items()
            if len(set(a.location_id for a in apps)) >= 2)
        multi_location_rate = (multi_location_devices / unique_devices
                               if unique_devices > 0 else 0)

        # This is a simplified version of the stats from the original file
        # You can add the other calculations (temporal, off-hours, etc.)
        # here if needed
        return {
            'total_appearances': total_appearances,
            'unique_devices': unique_devices,
            'unique_locations': unique_locations,
            'analysis_duration_hours': analysis_duration_hours,
            'persistence_rate': persistence_rate,
            'multi_location_rate': multi_location_rate,
            'detection_accuracy': detection_accuracy
        }

    def _format_detailed_device_analysis(
            self, device: SuspiciousDevice, persistence_level: PersistenceLevel) -> str:
        """Format detailed analysis for a suspicious device with clear explanations"""
        lines = []

        emoji = persistence_level.emoji

        lines.append(f"#### {emoji} Device Analysis: `{device.mac}`")
        lines.append("")
        lines.append(
            "*A MAC address is like a unique fingerprint for each wireless "
            "device (phone, laptop, etc.)*")
        lines.append("")
        lines.append("**📊 Persistence Analysis:**")
        lines.append(f"- **Pattern Type:** {persistence_level.value} FREQUENCY")
        lines.append(
            f"- **Persistence Score:** {device.persistence_score:.3f}/1.000 "
            "*(Higher = More Suspicious)*")
        lines.append(
            f"- **Confidence:** {min(device.persistence_score * 100, 95):.1f}% "
            "*(How sure we are this is suspicious)*")
        pattern_analysis = (
            '📊 High-frequency appearance pattern'
            if persistence_level == PersistenceLevel.CRITICAL else
            '📈 Notable appearance pattern' if persistence_level == PersistenceLevel.HIGH else
            '📋 Low-frequency pattern')
        lines.append(f"- **Pattern Analysis:** {pattern_analysis}")
        lines.append("")

        duration = device.last_seen - device.first_seen
        duration_hours = duration.total_seconds() / 3600
        lines.append("**⏰ Time-Based Behavior Analysis:**")
        lines.append(
            "*This shows how long the device has been appearing and how often*")
        lines.append("")
        lines.append(
            f"- **Total Surveillance Period:** {duration_hours:.1f} hours "
            f"({duration.days} days)")
        lines.append(
            "- **First Time Spotted:** "
            f"{device.first_seen.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(
            "- **Most Recent Sighting:** "
            f"{device.last_seen.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(
            f"- **Total Appearances:** {device.total_appearances} times")
        lines.append(
            "- **How Often It Appears:** "
            f"{device.total_appearances / max(duration_hours, 1):.2f} "
            "times per hour")
        lines.append("")
        if device.total_appearances > 10:
            lines.append(
                "  📊 **Analysis:** This device appears very frequently, "
                "which is unusual for normal devices.")
        elif device.total_appearances > 5:
            lines.append(
                "  📊 **Analysis:** This device appears regularly, "
                "worth monitoring.")
        else:
            lines.append(
                "  📊 **Analysis:** Low appearance count, "
                "may not be actively tracking.")
        lines.append("")

        lines.append("**🗺️ Location Tracking Analysis:**")
        lines.append(
            "*This shows whether the device follows you to different places*")
        lines.append("")
        lines.append(
            "- **Different Locations Seen:** "
            f"{len(device.locations_seen)}")
        lines.append(
            f"- **Specific Locations:** {', '.join(device.locations_seen)}")
        if len(device.locations_seen) > 1:
            lines.append(
                "- **Following Behavior:** ✅ **CONFIRMED** - This device has "
                "appeared at multiple locations")
            lines.append(
                "  🚨 **This is a major red flag - normal devices don't "
                "follow you around!**")
        else:
            lines.append(
                "- **Following Behavior:** ❌ Only seen at one location")
            lines.append(
                "  ℹ️ **This could be a local device, but monitor for "
                "movement**")
        lines.append("")

        lines.append("**Behavioral Threat Indicators:**")
        for i, reason in enumerate(device.reasons, 1):
            lines.append(f"  {i}. {reason}")
        lines.append("")

        lines.append("**Recent Activity Timeline:**")
        recent_appearances = sorted(
            device.appearances, key=lambda a: a.timestamp, reverse=True)[:10]
        for appearance in recent_appearances:
            dt = datetime.fromtimestamp(appearance.timestamp)
            ssids = (', '.join(appearance.ssids_probed[:2])
                     if appearance.ssids_probed else 'No probes')
            lines.append(
                f"- `{dt.strftime('%Y-%m-%d %H:%M:%S')}` | "
                f"Location: `{appearance.location_id}` | SSIDs: {ssids}")

        if len(device.appearances) > 10:
            lines.append(
                f"- *... and {len(device.appearances) - 10} additional "
                "appearances*")
        lines.append("")

        lines.append("**General Recommendations:**")
        lines.append(
            "- 📊 **Data Analysis**: This device showed repeated "
            "appearances in your wireless environment")
        lines.append(
            "- 🔍 **Consider**: This pattern might be worth noting or "
            "monitoring")
        lines.append(
            "- 📝 **Documentation**: You could keep a log of when/where this "
            "device appears")
        lines.append(
            "- 🤔 **Context**: Remember this could be a neighbor, business "
            "device, or normal wireless traffic")
        lines.append(
            "- ⚖️ **Disclaimer**: These are statistical patterns only - not "
            "definitive proof of surveillance")
        lines.append("")
        lines.append("---")
        lines.append("")

        return '\n'.join(lines)

    def _analyze_temporal_patterns(self) -> List[str]:
        """Analyze temporal patterns across suspicious devices"""
        patterns = []
        if not self.suspicious_devices:
            return ["No suspicious devices to analyze"]

        # Analyze appearance times
        all_hours = []
        for device in self.suspicious_devices:
            for appearance in device.appearances:
                dt = datetime.fromtimestamp(appearance.timestamp)
                all_hours.append(dt.hour)

        if all_hours:
            # Find peak activity hours
            from collections import Counter
            hour_counts = Counter(all_hours)
            peak_hour = hour_counts.most_common(1)[0]
            patterns.append(f"- Peak activity hour: {peak_hour[0]:02d}:00 ({peak_hour[1]} detections)")

            # Check for off-hours activity (late night/early morning)
            off_hours = [h for h in all_hours if h < 6 or h > 22]
            if off_hours:
                off_hours_pct = (len(off_hours) / len(all_hours)) * 100
                patterns.append(f"- Off-hours activity (22:00-06:00): {off_hours_pct:.1f}% of detections")
                if off_hours_pct > 30:
                    patterns.append("  ⚠️ High off-hours activity is unusual")

            # Check for consistent daily patterns
            if len(self.suspicious_devices) > 0:
                avg_appearances = sum(d.total_appearances for d in self.suspicious_devices) / len(self.suspicious_devices)
                patterns.append(f"- Average appearances per device: {avg_appearances:.1f}")

        return patterns if patterns else ["No significant temporal patterns detected"]

    def _analyze_geographic_patterns(self) -> List[str]:
        """Analyze geographic tracking patterns"""
        patterns = []
        if not self.suspicious_devices:
            return ["No suspicious devices to analyze"]

        # Find devices that appear at multiple locations
        multi_location_devices = [d for d in self.suspicious_devices if len(d.locations_seen) > 1]

        if multi_location_devices:
            patterns.append(f"- Devices showing following behavior: {len(multi_location_devices)}")

            # Find most common location
            all_locations = []
            for device in self.suspicious_devices:
                all_locations.extend(device.locations_seen)

            if all_locations:
                from collections import Counter
                location_counts = Counter(all_locations)
                most_common_loc = location_counts.most_common(1)[0]
                patterns.append(f"- Most active location: {most_common_loc[0]} ({most_common_loc[1]} devices)")

            # Analyze cross-location correlation
            max_locations = max(len(d.locations_seen) for d in multi_location_devices)
            patterns.append(f"- Maximum locations tracked: {max_locations}")

            if max_locations >= 3:
                patterns.append("  🚨 Multi-location tracking detected - strong following indicator")
        else:
            patterns.append("- No multi-location following behavior detected")

        return patterns

    def _analyze_device_correlations(self) -> List[str]:
        """Analyze correlations between suspicious devices"""
        correlations = []
        if len(self.suspicious_devices) < 2:
            return correlations

        # Check for devices appearing together at same locations
        location_groups = {}
        for device in self.suspicious_devices:
            for location in device.locations_seen:
                if location not in location_groups:
                    location_groups[location] = []
                location_groups[location].append(device.mac)

        # Find locations with multiple suspicious devices
        multi_device_locations = {loc: macs for loc, macs in location_groups.items() if len(macs) > 1}

        if multi_device_locations:
            correlations.append("**Correlated Devices (appearing together):**")
            for location, macs in multi_device_locations.items():
                correlations.append(f"- Location `{location}`: {len(macs)} suspicious devices")
                correlations.append(f"  MACs: {', '.join(f'`{mac}`' for mac in macs[:3])}")
                if len(macs) > 3:
                    correlations.append(f"  ... and {len(macs) - 3} more")
            correlations.append("")
            correlations.append("⚠️ Multiple suspicious devices at same location may indicate coordinated surveillance")

        # Check for temporal correlation (devices appearing at similar times)
        device_times = {}
        for device in self.suspicious_devices:
            device_times[device.mac] = [a.timestamp for a in device.appearances]

        return correlations

    def generate_surveillance_report(self, output_file: str) -> str:
        """Generate comprehensive surveillance detection report with advanced analytics"""
        report = []

        # Header
        report.append("# 🛡️ SURVEILLANCE DETECTION ANALYSIS")
        report.append("")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("---")
        report.append("")

        # Executive Summary
        report.append("## 📋 Executive Summary")
        report.append("")
        report.append(f"**Total Devices Analyzed:** {self.stats['unique_devices']}")
        report.append(f"**Suspicious Devices Identified:** {len(self.suspicious_devices)}")
        report.append(f"**Total Appearances Recorded:** {self.stats['total_appearances']}")
        report.append(f"**Analysis Duration:** {self.stats['analysis_duration_hours']:.1f} hours")
        report.append(f"**Detection Confidence:** {self.stats['detection_accuracy']*100:.1f}%")
        report.append("")

        if self.suspicious_devices:
            report.append("⚠️ **ALERT:** Suspicious device patterns detected requiring review")
        else:
            report.append("✅ **ALL CLEAR:** No significant suspicious patterns detected")
        report.append("")
        report.append("---")
        report.append("")

        # Analysis Statistics
        report.append("## 📊 Analysis Statistics")
        report.append("")
        report.append(f"- **Unique Locations:** {self.stats['unique_locations']}")
        report.append(f"- **Persistence Rate:** {self.stats['persistence_rate']*100:.1f}%")
        report.append(f"- **Multi-Location Rate:** {self.stats['multi_location_rate']*100:.1f}%")
        report.append("")
        report.append("---")
        report.append("")

        # Temporal Patterns
        report.append("## ⏰ Temporal Pattern Analysis")
        report.append("")
        temporal_patterns = self._analyze_temporal_patterns()
        for pattern in temporal_patterns:
            report.append(pattern)
        report.append("")
        report.append("---")
        report.append("")

        # Geographic Patterns
        report.append("## 🗺️ Geographic Pattern Analysis")
        report.append("")
        geo_patterns = self._analyze_geographic_patterns()
        for pattern in geo_patterns:
            report.append(pattern)
        report.append("")
        report.append("---")
        report.append("")

        # Device Correlations
        if len(self.suspicious_devices) >= 2:
            report.append("## 🔗 Device Correlation Analysis")
            report.append("")
            correlations = self._analyze_device_correlations()
            if correlations:
                for correlation in correlations:
                    report.append(correlation)
            else:
                report.append("No significant device correlations detected")
            report.append("")
            report.append("---")
            report.append("")

        # Detailed Device Analysis
        if self.suspicious_devices:
            report.append("## 🔍 Detailed Device Analysis")
            report.append("")

            # Group devices by threat level using PersistenceLevel enum
            critical = [d for d in self.suspicious_devices
                       if d.persistence_score >= PersistenceLevel.CRITICAL.threshold]
            high = [d for d in self.suspicious_devices
                   if PersistenceLevel.HIGH.threshold <= d.persistence_score < PersistenceLevel.CRITICAL.threshold]
            medium = [d for d in self.suspicious_devices
                     if PersistenceLevel.MEDIUM.threshold <= d.persistence_score < PersistenceLevel.HIGH.threshold]
            low = [d for d in self.suspicious_devices
                  if d.persistence_score < PersistenceLevel.MEDIUM.threshold]

            if critical:
                report.append(f"### {PersistenceLevel.CRITICAL.emoji} CRITICAL Priority Devices")
                report.append("")
                for device in critical:
                    report.append(self._format_detailed_device_analysis(device, PersistenceLevel.CRITICAL))

            if high:
                report.append(f"### {PersistenceLevel.HIGH.emoji} HIGH Priority Devices")
                report.append("")
                for device in high:
                    report.append(self._format_detailed_device_analysis(device, PersistenceLevel.HIGH))

            if medium:
                report.append(f"### {PersistenceLevel.MEDIUM.emoji} MEDIUM Priority Devices")
                report.append("")
                for device in medium:
                    report.append(self._format_detailed_device_analysis(device, PersistenceLevel.MEDIUM))

            if low:
                report.append(f"### {PersistenceLevel.LOW.emoji} LOW Priority Devices")
                report.append("")
                for device in low:
                    report.append(self._format_detailed_device_analysis(device, PersistenceLevel.LOW))

        # Recommendations
        report.append("## 💡 Recommendations")
        report.append("")
        if len(self.suspicious_devices) == 0:
            report.append("- ✅ No immediate action required")
            report.append("- 📊 Continue routine monitoring")
        else:
            report.append("- 🔍 Review suspicious devices listed above")
            report.append("- 📝 Document any recognized devices (neighbors, work devices)")
            report.append("- 📊 Monitor for continued following behavior")
            report.append("- 🛡️ Consider security assessment if patterns persist")
        report.append("")
        report.append("---")
        report.append("")

        # Footer
        report.append("## ℹ️ About This Report")
        report.append("")
        report.append("This report is generated by Chasing Your Tail (CYT) surveillance detection system.")
        report.append("")
        report.append("**Disclaimer:** This analysis identifies statistical patterns in wireless device")
        report.append("appearances and is not definitive proof of surveillance. Many factors can cause")
        report.append("repeated device appearances including neighbors, nearby businesses, or normal")
        report.append("wireless traffic patterns.")
        report.append("")

        report_text = '\n'.join(report)

        with open(output_file, 'w') as f:
            f.write(report_text)

        logger.info(
            f"Advanced surveillance report saved to: {output_file}")

        # Generate HTML version using pandoc
        html_file = output_file.replace('.md', '.html')
        try:
            # Check if pandoc is available
            pandoc_check = subprocess.run(
                ['which', 'pandoc'], capture_output=True, text=True, timeout=5)

            if pandoc_check.returncode != 0:
                logger.info(
                    "Pandoc not found. Skipping HTML report generation. "
                    "Install pandoc to enable HTML reports: https://pandoc.org/installing.html")
                return report_text

            css_content = """<style>
                body { font-family: sans-serif; max-width: 1200px; margin: 40px auto; padding: 20px; }
                h1 { color: #2c3e50; border-bottom: 3px solid #3498db; }
                h2 { color: #34495e; margin-top: 30px; }
                code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
                pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
                </style>"""

            cmd = ['pandoc', output_file, '-o', html_file, '--standalone',
                   '--self-contained', '--metadata',
                   'title=CYT Surveillance Detection Report', '--css',
                   '/dev/stdin']

            result = subprocess.run(
                cmd, input=css_content, text=True, capture_output=True,
                timeout=SystemConstants.PANDOC_TIMEOUT_SECONDS)

            if result.returncode == 0:
                logger.info(f"HTML report generated: {html_file}")
            else:
                logger.error(
                    f"Pandoc failed to generate HTML report. Error: {result.stderr}")
                logger.info(f"Markdown report still available at: {output_file}")

        except subprocess.TimeoutExpired:
            logger.error(f"Pandoc command timed out after {SystemConstants.PANDOC_TIMEOUT_SECONDS} seconds")
        except FileNotFoundError:
            logger.info(
                "Pandoc not installed. Skipping HTML generation. "
                "Markdown report available at: {output_file}")
        except (OSError, subprocess.SubprocessError) as e:
            logger.error(f"Subprocess error while generating HTML: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating HTML report: {e}")

        return report_text
