"""
Secure main logic for Chasing Your Tail - replaces vulnerable SQL operations
"""
import logging
from typing import List, Dict, Set
from secure_database import SecureKismetDB, SecureTimeWindows

logger = logging.getLogger(__name__)

class SecureCYTMonitor:
    """Secure monitoring logic for CYT"""
    
    def __init__(self, config: dict, ignore_list: List[str], ssid_ignore_list: List[str], log_file):
        self.config = config
        self.ignore_list = set(mac.upper() for mac in ignore_list)  # Convert to set for O(1) lookup
        self.ssid_ignore_list = set(ssid_ignore_list)
        self.log_file = log_file
        self.time_manager = SecureTimeWindows(config)
        
        # Initialize tracking lists
        self.past_five_mins_macs: Set[str] = set()
        self.five_ten_min_ago_macs: Set[str] = set()
        self.ten_fifteen_min_ago_macs: Set[str] = set()
        self.fifteen_twenty_min_ago_macs: Set[str] = set()
        
        self.past_five_mins_ssids: Set[str] = set()
        self.five_ten_min_ago_ssids: Set[str] = set()
        self.ten_fifteen_min_ago_ssids: Set[str] = set()
        self.fifteen_twenty_min_ago_ssids: Set[str] = set()
    
    def initialize_tracking_lists(self, db: SecureKismetDB) -> None:
        """Initialize all tracking lists securely"""
        try:
            boundaries = self.time_manager.get_time_boundaries()
            
            # Initialize MAC tracking lists
            self._initialize_mac_lists(db, boundaries)
            
            # Initialize SSID tracking lists  
            self._initialize_ssid_lists(db, boundaries)
            
            self._log_initialization_stats()
            
        except Exception as e:
            logger.error(f"Failed to initialize tracking lists: {e}")
            raise
    
    def _initialize_mac_lists(self, db: SecureKismetDB, boundaries: Dict[str, float]) -> None:
        """Initialize MAC address tracking lists"""
        # Past 5 minutes
        macs = db.get_mac_addresses_by_time_range(boundaries['recent_time'])
        self.past_five_mins_macs = self._filter_macs(macs)
        
        # 5-10 minutes ago
        macs = db.get_mac_addresses_by_time_range(boundaries['medium_time'], boundaries['recent_time'])
        self.five_ten_min_ago_macs = self._filter_macs(macs)
        
        # 10-15 minutes ago
        macs = db.get_mac_addresses_by_time_range(boundaries['old_time'], boundaries['medium_time'])
        self.ten_fifteen_min_ago_macs = self._filter_macs(macs)
        
        # 15-20 minutes ago
        macs = db.get_mac_addresses_by_time_range(boundaries['oldest_time'], boundaries['old_time'])
        self.fifteen_twenty_min_ago_macs = self._filter_macs(macs)
    
    def _initialize_ssid_lists(self, db: SecureKismetDB, boundaries: Dict[str, float]) -> None:
        """Initialize SSID tracking lists"""
        # Past 5 minutes
        probes = db.get_probe_requests_by_time_range(boundaries['recent_time'])
        self.past_five_mins_ssids = self._filter_ssids([p['ssid'] for p in probes])
        
        # 5-10 minutes ago
        probes = db.get_probe_requests_by_time_range(boundaries['medium_time'], boundaries['recent_time'])
        self.five_ten_min_ago_ssids = self._filter_ssids([p['ssid'] for p in probes])
        
        # 10-15 minutes ago
        probes = db.get_probe_requests_by_time_range(boundaries['old_time'], boundaries['medium_time'])
        self.ten_fifteen_min_ago_ssids = self._filter_ssids([p['ssid'] for p in probes])
        
        # 15-20 minutes ago
        probes = db.get_probe_requests_by_time_range(boundaries['oldest_time'], boundaries['old_time'])
        self.fifteen_twenty_min_ago_ssids = self._filter_ssids([p['ssid'] for p in probes])
    
    def _filter_macs(self, mac_list: List[str]) -> Set[str]:
        """Filter MAC addresses against ignore list"""
        return {mac.upper() for mac in mac_list if mac.upper() not in self.ignore_list}
    
    def _filter_ssids(self, ssid_list: List[str]) -> Set[str]:
        """Filter SSIDs against ignore list"""
        return {ssid for ssid in ssid_list if ssid and ssid not in self.ssid_ignore_list}
    
    def _log_initialization_stats(self) -> None:
        """Log initialization statistics"""
        mac_stats = [
            ("Past 5 minutes", len(self.past_five_mins_macs)),
            ("5-10 minutes ago", len(self.five_ten_min_ago_macs)),
            ("10-15 minutes ago", len(self.ten_fifteen_min_ago_macs)),
            ("15-20 minutes ago", len(self.fifteen_twenty_min_ago_macs))
        ]
        
        ssid_stats = [
            ("Past 5 minutes", len(self.past_five_mins_ssids)),
            ("5-10 minutes ago", len(self.five_ten_min_ago_ssids)),
            ("10-15 minutes ago", len(self.ten_fifteen_min_ago_ssids)),
            ("15-20 minutes ago", len(self.fifteen_twenty_min_ago_ssids))
        ]
        
        for period, count in mac_stats:
            message = f"{count} MACs added to the {period} list"
            print(message)
            self.log_file.write(f"{message}\n")
        
        for period, count in ssid_stats:
            message = f"{count} Probed SSIDs added to the {period} list"
            print(message)
            self.log_file.write(f"{message}\n")
    
    def process_current_activity(self, db: SecureKismetDB) -> None:
        """Process current activity and detect matches"""
        try:
            boundaries = self.time_manager.get_time_boundaries()
            
            # Get current devices and probes
            current_devices = db.get_devices_by_time_range(boundaries['current_time'])
            
            for device in current_devices:
                mac = device['mac']
                device_data = device.get('device_data', {})
                
                if not mac:
                    continue
                
                # Check for probe requests
                self._process_probe_requests(device_data, mac)
                
                # Check MAC address tracking
                self._process_mac_tracking(mac)
                
        except Exception as e:
            logger.error(f"Error processing current activity: {e}")
    
    def _process_probe_requests(self, device_data: Dict, mac: str) -> None:
        """Process probe requests from device data"""
        if not device_data:
            return
        
        try:
            dot11_device = device_data.get('dot11.device', {})
            if not isinstance(dot11_device, dict):
                return
            
            probe_record = dot11_device.get('dot11.device.last_probed_ssid_record', {})
            if not isinstance(probe_record, dict):
                return
            
            ssid = probe_record.get('dot11.probedssid.ssid', '')
            if not ssid or ssid in self.ssid_ignore_list:
                return
            
            # Log the probe
            message = f'Found a probe!: {ssid}'
            self.log_file.write(f'{message}\n')
            logger.info(f"Probe detected from {mac}: {ssid}")
            
            # Check against historical lists
            self._check_ssid_history(ssid)
            
        except (KeyError, TypeError, AttributeError) as e:
            logger.debug(f"No probe data for device {mac}: {e}")
    
    def _check_ssid_history(self, ssid: str) -> None:
        """Check SSID against historical tracking lists"""
        if ssid in self.five_ten_min_ago_ssids:
            message = f"Probe for {ssid} in 5 to 10 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(f"Repeated probe detected: {ssid} (5-10 min window)")
        
        if ssid in self.ten_fifteen_min_ago_ssids:
            message = f"Probe for {ssid} in 10 to 15 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(f"Repeated probe detected: {ssid} (10-15 min window)")
        
        if ssid in self.fifteen_twenty_min_ago_ssids:
            message = f"Probe for {ssid} in 15 to 20 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(f"Repeated probe detected: {ssid} (15-20 min window)")
    
    def _process_mac_tracking(self, mac: str) -> None:
        """Process MAC address tracking"""
        if mac.upper() in self.ignore_list:
            return
        
        # Check against historical lists
        if mac in self.five_ten_min_ago_macs:
            message = f"{mac} in 5 to 10 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(f"Device reappeared: {mac} (5-10 min window)")
        
        if mac in self.ten_fifteen_min_ago_macs:
            message = f"{mac} in 10 to 15 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(f"Device reappeared: {mac} (10-15 min window)")
        
        if mac in self.fifteen_twenty_min_ago_macs:
            message = f"{mac} in 15 to 20 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(f"Device reappeared: {mac} (15-20 min window)")
    
    def rotate_tracking_lists(self, db: SecureKismetDB) -> None:
        """Rotate tracking lists and update with fresh data"""
        try:
            # Rotate MAC lists
            self.fifteen_twenty_min_ago_macs = self.ten_fifteen_min_ago_macs
            self.ten_fifteen_min_ago_macs = self.five_ten_min_ago_macs
            self.five_ten_min_ago_macs = self.past_five_mins_macs
            
            # Rotate SSID lists
            self.fifteen_twenty_min_ago_ssids = self.ten_fifteen_min_ago_ssids
            self.ten_fifteen_min_ago_ssids = self.five_ten_min_ago_ssids
            self.five_ten_min_ago_ssids = self.past_five_mins_ssids
            
            # Get fresh data for past 5 minutes
            boundaries = self.time_manager.get_time_boundaries()
            
            # Update past 5 minutes MAC list
            macs = db.get_mac_addresses_by_time_range(boundaries['recent_time'])
            self.past_five_mins_macs = self._filter_macs(macs)
            
            # Update past 5 minutes SSID list
            probes = db.get_probe_requests_by_time_range(boundaries['recent_time'])
            self.past_five_mins_ssids = self._filter_ssids([p['ssid'] for p in probes])
            
            self._log_rotation_stats()
            
        except Exception as e:
            logger.error(f"Error rotating tracking lists: {e}")
    
    def _log_rotation_stats(self) -> None:
        """Log rotation statistics"""
        print("Updated MAC tracking lists:")
        print(f"- 15-20 min ago: {len(self.fifteen_twenty_min_ago_macs)}")
        print(f"- 10-15 min ago: {len(self.ten_fifteen_min_ago_macs)}")
        print(f"- 5-10 min ago: {len(self.five_ten_min_ago_macs)}")
        print(f"- Current: {len(self.past_five_mins_macs)}")
        
        # Log to file
        self.log_file.write(f"{len(self.fifteen_twenty_min_ago_macs)} MACs moved to the 15-20 Min list\n")
        self.log_file.write(f"{len(self.ten_fifteen_min_ago_macs)} MACs moved to the 10-15 Min list\n")
        self.log_file.write(f"{len(self.five_ten_min_ago_macs)} MACs moved to the 5 to 10 mins ago list\n")
        
        print(f"{len(self.fifteen_twenty_min_ago_ssids)} Probed SSIDs moved to the 15 to 20 mins ago list")
        print(f"{len(self.ten_fifteen_min_ago_ssids)} Probed SSIDs moved to the 10 to 15 mins ago list")
        print(f"{len(self.five_ten_min_ago_ssids)} Probed SSIDs moved to the 5 to 10 mins ago list")
        
        self.log_file.write(f"{len(self.fifteen_twenty_min_ago_ssids)} Probed SSIDs moved to the 15 to 20 mins ago list\n")
        self.log_file.write(f"{len(self.ten_fifteen_min_ago_ssids)} Probed SSIDs moved to the 10 to 15 mins ago list\n")
        self.log_file.write(f"{len(self.five_ten_min_ago_ssids)} Probed SSIDs moved to the 5 to 10 mins ago list\n")