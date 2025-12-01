#!/usr/bin/env python3
"""
Behavioral Drone Detector
Detects drones using behavioral pattern analysis beyond OUI matching.

This module identifies drones by analyzing:
- Signal strength patterns (hovering, rapid changes)
- Movement patterns (GPS-based tracking)
- Temporal patterns (brief appearances, time-of-day)
- Probe behavior (frequency, patterns)
- Device characteristics (no clients, no associations)
"""
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)


@dataclass
class DeviceHistory:
    """Tracks historical data for behavioral analysis."""
    mac: str
    first_seen: float
    last_seen: float
    appearances: List[float]  # List of timestamps
    signal_strengths: List[int]  # List of RSSI values
    locations: List[Tuple[float, float]]  # List of (lat, lon) tuples
    channels: List[int]  # List of channels seen on
    probe_count: int
    associated: bool  # Has this device ever been associated with an AP?
    has_clients: bool  # Does this device have client connections?


class BehavioralDroneDetector:
    """
    Detects drones using behavioral pattern analysis.

    Assigns confidence scores (0.0-1.0) based on suspicious behavioral patterns.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize behavioral drone detector.

        Args:
            config: Configuration dictionary with detection thresholds
        """
        self.config = config or {}
        self.behavior_config = self.config.get('behavioral_drone_detection', {})

        # Device tracking
        self.device_history: Dict[str, DeviceHistory] = {}

        # Configuration thresholds
        self.min_appearances = self.behavior_config.get('min_appearances', 3)
        self.signal_variance_threshold = self.behavior_config.get('signal_variance_threshold', 20)
        self.rapid_movement_threshold_mps = self.behavior_config.get('rapid_movement_threshold_mps', 15.0)
        self.hovering_radius_meters = self.behavior_config.get('hovering_radius_meters', 50.0)
        self.brief_appearance_seconds = self.behavior_config.get('brief_appearance_seconds', 300)
        self.high_signal_threshold = self.behavior_config.get('high_signal_threshold', -50)
        self.probe_frequency_threshold = self.behavior_config.get('probe_frequency_per_minute', 10)

        # Confidence score weights
        self.weights = {
            'high_mobility': 0.15,
            'signal_variance': 0.10,
            'hovering': 0.12,
            'brief_appearance': 0.08,
            'no_association': 0.15,
            'high_signal': 0.10,
            'probe_frequency': 0.10,
            'channel_hopping': 0.10,
            'no_clients': 0.10
        }

    def update_device_history(self, mac: str, device_data: Dict[str, Any]) -> None:
        """
        Update historical tracking data for a device.

        Args:
            mac: Device MAC address
            device_data: Current device data from Kismet
        """
        current_time = time.time()
        signal_strength = device_data.get('signal', -100)
        lat = device_data.get('lat')
        lon = device_data.get('lon')
        channel = device_data.get('channel', 0)

        if mac not in self.device_history:
            # New device
            self.device_history[mac] = DeviceHistory(
                mac=mac,
                first_seen=current_time,
                last_seen=current_time,
                appearances=[current_time],
                signal_strengths=[signal_strength],
                locations=[(lat, lon)] if (lat and lon) else [],
                channels=[channel] if channel else [],
                probe_count=1,
                associated=False,
                has_clients=False
            )
        else:
            # Update existing device
            history = self.device_history[mac]
            history.last_seen = current_time
            history.appearances.append(current_time)
            history.signal_strengths.append(signal_strength)

            if lat and lon:
                history.locations.append((lat, lon))

            if channel and channel not in history.channels:
                history.channels.append(channel)

            history.probe_count += 1

            # Check for associations/clients from device_data
            if device_data.get('type') == 'ap':
                history.associated = True
            if device_data.get('num_clients', 0) > 0:
                history.has_clients = True

    def calculate_signal_variance(self, mac: str) -> float:
        """
        Calculate signal strength variance for a device.
        High variance suggests movement (altitude/distance changes).

        Args:
            mac: Device MAC address

        Returns:
            Signal variance (0.0 = no variance, 1.0 = high variance)
        """
        if mac not in self.device_history:
            return 0.0

        signals = self.device_history[mac].signal_strengths

        if len(signals) < 2:
            return 0.0

        # Calculate standard deviation
        mean = sum(signals) / len(signals)
        variance = sum((x - mean) ** 2 for x in signals) / len(signals)
        std_dev = math.sqrt(variance)

        # Normalize to 0-1 scale
        normalized = min(std_dev / self.signal_variance_threshold, 1.0)

        return normalized

    def calculate_movement_speed(self, mac: str) -> Optional[float]:
        """
        Calculate average movement speed in meters per second.

        Args:
            mac: Device MAC address

        Returns:
            Average speed in m/s, or None if insufficient GPS data
        """
        if mac not in self.device_history:
            return None

        history = self.device_history[mac]
        locations = history.locations

        if len(locations) < 2:
            return None

        total_distance = 0.0
        for i in range(1, len(locations)):
            lat1, lon1 = locations[i-1]
            lat2, lon2 = locations[i]
            distance = self._haversine_distance(lat1, lon1, lat2, lon2)
            total_distance += distance

        time_span = history.last_seen - history.first_seen

        if time_span == 0:
            return None

        average_speed = total_distance / time_span
        return average_speed

    def check_hovering_pattern(self, mac: str) -> bool:
        """
        Check if device shows hovering pattern (staying in small radius).

        Args:
            mac: Device MAC address

        Returns:
            True if hovering pattern detected
        """
        if mac not in self.device_history:
            return False

        history = self.device_history[mac]
        locations = history.locations

        if len(locations) < 3:
            return False

        # Calculate centroid
        avg_lat = sum(lat for lat, _ in locations) / len(locations)
        avg_lon = sum(lon for _, lon in locations) / len(locations)

        # Check if all points are within hovering radius
        max_distance = 0.0
        for lat, lon in locations:
            distance = self._haversine_distance(avg_lat, avg_lon, lat, lon)
            max_distance = max(max_distance, distance)

        return max_distance <= self.hovering_radius_meters

    def check_brief_appearance(self, mac: str) -> bool:
        """
        Check if device appeared only briefly (reconnaissance flight pattern).

        Args:
            mac: Device MAC address

        Returns:
            True if brief appearance detected
        """
        if mac not in self.device_history:
            return False

        history = self.device_history[mac]
        time_span = history.last_seen - history.first_seen

        return time_span <= self.brief_appearance_seconds

    def calculate_probe_frequency(self, mac: str) -> float:
        """
        Calculate probe request frequency in probes per minute.

        Args:
            mac: Device MAC address

        Returns:
            Probes per minute
        """
        if mac not in self.device_history:
            return 0.0

        history = self.device_history[mac]
        time_span = (history.last_seen - history.first_seen) / 60.0  # Convert to minutes

        if time_span == 0:
            return 0.0

        return history.probe_count / time_span

    def analyze_device(self, mac: str) -> Tuple[float, Dict[str, Any]]:
        """
        Perform comprehensive behavioral analysis on a device.

        Args:
            mac: Device MAC address

        Returns:
            Tuple of (confidence_score, pattern_details)
            - confidence_score: 0.0-1.0 indicating likelihood of being a drone
            - pattern_details: Dictionary of detected patterns and scores
        """
        if mac not in self.device_history:
            return (0.0, {})

        history = self.device_history[mac]

        # Require minimum appearances before analysis
        if len(history.appearances) < self.min_appearances:
            return (0.0, {'reason': 'insufficient_data'})

        patterns = {}
        confidence = 0.0

        # Pattern 1: High Mobility
        speed = self.calculate_movement_speed(mac)
        if speed is not None and speed > self.rapid_movement_threshold_mps:
            patterns['high_mobility'] = {
                'detected': True,
                'speed_mps': speed,
                'score': self.weights['high_mobility']
            }
            confidence += self.weights['high_mobility']
        else:
            patterns['high_mobility'] = {'detected': False, 'speed_mps': speed}

        # Pattern 2: Signal Variance (altitude/distance changes)
        signal_variance = self.calculate_signal_variance(mac)
        if signal_variance > 0.5:  # Threshold for significant variance
            patterns['signal_variance'] = {
                'detected': True,
                'variance': signal_variance,
                'score': self.weights['signal_variance'] * signal_variance
            }
            confidence += self.weights['signal_variance'] * signal_variance
        else:
            patterns['signal_variance'] = {'detected': False, 'variance': signal_variance}

        # Pattern 3: Hovering Pattern
        is_hovering = self.check_hovering_pattern(mac)
        if is_hovering:
            patterns['hovering'] = {
                'detected': True,
                'radius_meters': self.hovering_radius_meters,
                'score': self.weights['hovering']
            }
            confidence += self.weights['hovering']
        else:
            patterns['hovering'] = {'detected': False}

        # Pattern 4: Brief Appearance (reconnaissance)
        is_brief = self.check_brief_appearance(mac)
        if is_brief:
            duration = history.last_seen - history.first_seen
            patterns['brief_appearance'] = {
                'detected': True,
                'duration_seconds': duration,
                'score': self.weights['brief_appearance']
            }
            confidence += self.weights['brief_appearance']
        else:
            patterns['brief_appearance'] = {'detected': False}

        # Pattern 5: No Association (never connected to AP)
        if not history.associated:
            patterns['no_association'] = {
                'detected': True,
                'score': self.weights['no_association']
            }
            confidence += self.weights['no_association']
        else:
            patterns['no_association'] = {'detected': False}

        # Pattern 6: High Signal Strength (close proximity)
        avg_signal = sum(history.signal_strengths) / len(history.signal_strengths)
        if avg_signal > self.high_signal_threshold:
            patterns['high_signal'] = {
                'detected': True,
                'avg_signal': avg_signal,
                'score': self.weights['high_signal']
            }
            confidence += self.weights['high_signal']
        else:
            patterns['high_signal'] = {'detected': False, 'avg_signal': avg_signal}

        # Pattern 7: High Probe Frequency
        probe_freq = self.calculate_probe_frequency(mac)
        if probe_freq > self.probe_frequency_threshold:
            patterns['probe_frequency'] = {
                'detected': True,
                'probes_per_minute': probe_freq,
                'score': self.weights['probe_frequency']
            }
            confidence += self.weights['probe_frequency']
        else:
            patterns['probe_frequency'] = {'detected': False, 'probes_per_minute': probe_freq}

        # Pattern 8: Channel Hopping
        if len(history.channels) > 3:  # Seen on multiple channels
            patterns['channel_hopping'] = {
                'detected': True,
                'channels': history.channels,
                'score': self.weights['channel_hopping']
            }
            confidence += self.weights['channel_hopping']
        else:
            patterns['channel_hopping'] = {'detected': False, 'channels': history.channels}

        # Pattern 9: No Client Connections
        if not history.has_clients:
            patterns['no_clients'] = {
                'detected': True,
                'score': self.weights['no_clients']
            }
            confidence += self.weights['no_clients']
        else:
            patterns['no_clients'] = {'detected': False}

        # Clamp confidence to 0.0-1.0
        confidence = min(confidence, 1.0)

        return (confidence, patterns)

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula.

        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate

        Returns:
            Distance in meters
        """
        R = 6371000  # Earth radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def get_detection_summary(self, mac: str, confidence: float, patterns: Dict[str, Any]) -> str:
        """
        Generate human-readable detection summary.

        Args:
            mac: Device MAC address
            confidence: Confidence score (0.0-1.0)
            patterns: Pattern analysis details

        Returns:
            Formatted summary string
        """
        if mac not in self.device_history:
            return f"{mac}: No history available"

        history = self.device_history[mac]

        summary_lines = [
            f"BEHAVIORAL DRONE DETECTION: {mac}",
            f"Confidence: {confidence:.1%}",
            f"First seen: {datetime.fromtimestamp(history.first_seen).strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {history.last_seen - history.first_seen:.0f}s",
            f"Appearances: {len(history.appearances)}",
            "",
            "Detected Patterns:"
        ]

        for pattern_name, pattern_data in patterns.items():
            if pattern_data.get('detected'):
                if pattern_name == 'high_mobility':
                    summary_lines.append(f"  ✓ High Mobility: {pattern_data['speed_mps']:.1f} m/s")
                elif pattern_name == 'signal_variance':
                    summary_lines.append(f"  ✓ Signal Variance: {pattern_data['variance']:.2f}")
                elif pattern_name == 'hovering':
                    summary_lines.append(f"  ✓ Hovering Pattern: within {pattern_data['radius_meters']}m")
                elif pattern_name == 'brief_appearance':
                    summary_lines.append(f"  ✓ Brief Appearance: {pattern_data['duration_seconds']:.0f}s")
                elif pattern_name == 'no_association':
                    summary_lines.append(f"  ✓ No Network Association")
                elif pattern_name == 'high_signal':
                    summary_lines.append(f"  ✓ High Signal: {pattern_data['avg_signal']} dBm")
                elif pattern_name == 'probe_frequency':
                    summary_lines.append(f"  ✓ High Probe Frequency: {pattern_data['probes_per_minute']:.1f}/min")
                elif pattern_name == 'channel_hopping':
                    summary_lines.append(f"  ✓ Channel Hopping: {len(pattern_data['channels'])} channels")
                elif pattern_name == 'no_clients':
                    summary_lines.append(f"  ✓ No Client Connections")

        return "\n".join(summary_lines)

    def cleanup_old_history(self, max_age_hours: int = 24):
        """
        Remove old device history to prevent memory growth.

        Args:
            max_age_hours: Maximum age of history to retain
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        macs_to_remove = []
        for mac, history in self.device_history.items():
            age = current_time - history.last_seen
            if age > max_age_seconds:
                macs_to_remove.append(mac)

        for mac in macs_to_remove:
            del self.device_history[mac]

        if macs_to_remove:
            logger.info(f"Cleaned up {len(macs_to_remove)} old device histories")


if __name__ == "__main__":
    """Test the behavioral detector"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("=" * 70)
    print("Behavioral Drone Detector Test")
    print("=" * 70)

    # Create detector
    detector = BehavioralDroneDetector()

    # Simulate drone-like device
    test_mac = "AA:BB:CC:DD:EE:FF"

    print("\nSimulating drone-like device behavior...")

    # Simulate multiple appearances with varying signal and movement
    for i in range(10):
        device_data = {
            'signal': -55 + (i % 5) * 10,  # Variable signal (hovering/moving)
            'lat': 29.9511 + i * 0.0001,  # Moving
            'lon': -90.0715 + i * 0.0001,
            'channel': (i % 3) + 1,  # Channel hopping
            'type': 'device',
            'num_clients': 0
        }

        detector.update_device_history(test_mac, device_data)
        time.sleep(0.1)  # Simulate rapid appearances

    # Analyze
    confidence, patterns = detector.analyze_device(test_mac)

    print(f"\nConfidence Score: {confidence:.1%}")
    print("\nPattern Analysis:")
    for name, data in patterns.items():
        status = "✓ DETECTED" if data.get('detected') else "✗ Not detected"
        print(f"  {name}: {status}")
        if data.get('detected') and 'score' in data:
            print(f"    Score: {data['score']:.3f}")

    print("\n" + "=" * 70)
    print("\nFull Summary:")
    print("=" * 70)
    summary = detector.get_detection_summary(test_mac, confidence, patterns)
    print(summary)
    print("=" * 70)
