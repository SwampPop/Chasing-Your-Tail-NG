"""
Report Generation System for CYT
Generates detailed intelligence reports from analysis results.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict
import subprocess

logger = logging.getLogger(__name__)

# NOTE: You need to copy your dataclass definitions here so the reporter understands the data structure
from surveillance_detector import SuspiciousDevice 

class ReportGenerator:
    """Generates detailed surveillance analysis reports."""

    def __init__(self, suspicious_devices: List[SuspiciousDevice], all_appearances: List[Any], 
                 device_history: Dict[str, List[Any]], thresholds: Dict):
        self.suspicious_devices = suspicious_devices
        self.all_appearances = all_appearances
        self.device_history = device_history
        self.thresholds = thresholds
        self.stats = self._generate_analysis_statistics()

    def _generate_analysis_statistics(self) -> Dict:
        """Generate comprehensive statistics for the analysis"""
        if not self.all_appearances:
            return {
                'total_appearances': 0, 'unique_devices': 0, 'unique_locations': 0,
                'analysis_duration_hours': 0, 'persistence_rate': 0, 'multi_location_rate': 0,
                'detection_accuracy': 0.95
            }

        total_appearances = len(self.all_appearances)
        unique_devices = len(self.device_history)
        unique_locations = len(set(a.location_id for a in self.all_appearances))
        
        timestamps = [a.timestamp for a in self.all_appearances]
        analysis_duration = max(timestamps) - min(timestamps) if timestamps else 0
        analysis_duration_hours = analysis_duration / 3600 if analysis_duration > 0 else 0
        
        persistent_devices = [mac for mac, apps in self.device_history.items() 
                              if len(apps) >= self.thresholds.get('min_appearances', 3)]
        persistence_rate = len(persistent_devices) / unique_devices if unique_devices > 0 else 0
        
        multi_location_devices = sum(1 for mac, apps in self.device_history.items() 
                                     if len(set(a.location_id for a in apps)) >= 2)
        multi_location_rate = multi_location_devices / unique_devices if unique_devices > 0 else 0
        
        # This is a simplified version of the stats from the original file
        # You can add the other calculations (temporal, off-hours, etc.) here if needed
        return {
            'total_appearances': total_appearances, 'unique_devices': unique_devices,
            'unique_locations': unique_locations, 'analysis_duration_hours': analysis_duration_hours,
            'persistence_rate': persistence_rate, 'multi_location_rate': multi_location_rate,
            'detection_accuracy': 0.95
        }
        
    def _format_detailed_device_analysis(self, device: SuspiciousDevice, persistence_level: str) -> str:
        """Format detailed analysis for a suspicious device with clear explanations"""
        lines = []
        
        threat_emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "🟡", "LOW": "🔵"}
        emoji = threat_emoji.get(persistence_level, "⚪")
        
        lines.append(f"#### {emoji} Device Analysis: `{device.mac}`")
        lines.append("")
        lines.append("*A MAC address is like a unique fingerprint for each wireless device (phone, laptop, etc.)*")
        lines.append("")
        lines.append("**📊 Persistence Analysis:**")
        lines.append(f"- **Pattern Type:** {persistence_level} FREQUENCY")
        lines.append(f"- **Persistence Score:** {device.persistence_score:.3f}/1.000 *(Higher = More Suspicious)*")
        lines.append(f"- **Confidence:** {min(device.persistence_score * 100, 95):.1f}% *(How sure we are this is suspicious)*")
        lines.append(f"- **Pattern Analysis:** {'📊 High-frequency appearance pattern' if persistence_level == 'CRITICAL' else '📈 Notable appearance pattern' if persistence_level == 'HIGH' else '📋 Low-frequency pattern'}")
        lines.append("")
        
        duration = device.last_seen - device.first_seen
        duration_hours = duration.total_seconds() / 3600
        lines.append("**⏰ Time-Based Behavior Analysis:**")
        lines.append("*This shows how long the device has been appearing and how often*")
        lines.append("")
        lines.append(f"- **Total Surveillance Period:** {duration_hours:.1f} hours ({duration.days} days)")
        lines.append(f"- **First Time Spotted:** {device.first_seen.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **Most Recent Sighting:** {device.last_seen.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **Total Appearances:** {device.total_appearances} times")
        lines.append(f"- **How Often It Appears:** {device.total_appearances / max(duration_hours, 1):.2f} times per hour")
        lines.append("")
        if device.total_appearances > 10:
            lines.append("  📊 **Analysis:** This device appears very frequently, which is unusual for normal devices.")
        elif device.total_appearances > 5:
            lines.append("  📊 **Analysis:** This device appears regularly, worth monitoring.")
        else:
            lines.append("  📊 **Analysis:** Low appearance count, may not be actively tracking.")
        lines.append("")
        
        lines.append("**🗺️ Location Tracking Analysis:**")
        lines.append("*This shows whether the device follows you to different places*")
        lines.append("")
        lines.append(f"- **Different Locations Seen:** {len(device.locations_seen)}")
        lines.append(f"- **Specific Locations:** {', '.join(device.locations_seen)}")
        if len(device.locations_seen) > 1:
            lines.append(f"- **Following Behavior:** ✅ **CONFIRMED** - This device has appeared at multiple locations")
            lines.append("  🚨 **This is a major red flag - normal devices don't follow you around!**")
        else:
            lines.append(f"- **Following Behavior:** ❌ Only seen at one location")
            lines.append("  ℹ️ **This could be a local device, but monitor for movement**")
        lines.append("")
        
        lines.append("**Behavioral Threat Indicators:**")
        for i, reason in enumerate(device.reasons, 1):
            lines.append(f"  {i}. {reason}")
        lines.append("")
        
        lines.append("**Recent Activity Timeline:**")
        recent_appearances = sorted(device.appearances, key=lambda a: a.timestamp, reverse=True)[:10]
        for appearance in recent_appearances:
            dt = datetime.fromtimestamp(appearance.timestamp)
            ssids = ', '.join(appearance.ssids_probed[:2]) if appearance.ssids_probed else 'No probes'
            lines.append(f"- `{dt.strftime('%Y-%m-%d %H:%M:%S')}` | Location: `{appearance.location_id}` | SSIDs: {ssids}")
        
        if len(device.appearances) > 10:
            lines.append(f"- *... and {len(device.appearances) - 10} additional appearances*")
        lines.append("")
        
        lines.append("**General Recommendations:**")
        lines.append("- 📊 **Data Analysis**: This device showed repeated appearances in your wireless environment")
        lines.append("- 🔍 **Consider**: This pattern might be worth noting or monitoring")
        lines.append("- 📝 **Documentation**: You could keep a log of when/where this device appears")
        lines.append("- 🤔 **Context**: Remember this could be a neighbor, business device, or normal wireless traffic")
        lines.append("- ⚖️ **Disclaimer**: These are statistical patterns only - not definitive proof of surveillance")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        return '\n'.join(lines)

    def _analyze_temporal_patterns(self) -> List[str]:
        """Analyze temporal patterns across suspicious devices"""
        patterns = []
        if not self.suspicious_devices: return ["No suspicious devices to analyze"]
        # ... (full method content)
        return patterns

    def _analyze_geographic_patterns(self) -> List[str]:
        """Analyze geographic tracking patterns"""
        patterns = []
        if not self.suspicious_devices: return ["No suspicious devices to analyze"]
        # ... (full method content)
        return patterns

    def _analyze_device_correlations(self) -> List[str]:
        """Analyze correlations between suspicious devices"""
        correlations = []
        if len(self.suspicious_devices) < 2: return correlations
        # ... (full method content)
        return correlations

    def generate_surveillance_report(self, output_file: str) -> str:
        """Generate comprehensive surveillance detection report with advanced analytics"""
        report = []
        # ... (full method content, starting with the header)
        report.append("# 🛡️ SURVEILLANCE DETECTION ANALYSIS")
        # ... all the way to the end, including the pandoc call
        
        report_text = '\n'.join(report)
        
        with open(output_file, 'w') as f:
            f.write(report_text)
        
        logger.info(f"Advanced surveillance report saved to: {output_file}")
        
        # Generate HTML version using pandoc
        html_file = output_file.replace('.md', '.html')
        try:
            css_content = "<style>...</style>" # Your CSS content here
            cmd = ['pandoc', output_file, '-o', html_file, '--standalone', '--self-contained', '--metadata', 'title=CYT Surveillance Detection Report', '--css', '/dev/stdin']
            result = subprocess.run(cmd, input=css_content, text=True, capture_output=True)
            if result.returncode == 0:
                logger.info(f"HTML report generated: {html_file}")
            else:
                logger.warning(f"Failed to generate HTML report: {result.stderr}")
        except Exception as e:
            logger.warning(f"Could not generate HTML report: {e}")
        
        return report_text