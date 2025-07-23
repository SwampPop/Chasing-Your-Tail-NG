"""
Input validation and sanitization for CYT
Prevents injection attacks and ensures data integrity
"""
import re
import json
import logging
from typing import Any, Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)

class InputValidator:
    """Comprehensive input validation for CYT"""
    
    # Regex patterns for validation
    MAC_PATTERN = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    SSID_PATTERN = re.compile(r'^[\x20-\x7E]{1,32}$')  # Printable ASCII, max 32 chars
    PATH_PATTERN = re.compile(r'^[a-zA-Z0-9._\-/\\:]+$')
    FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._\-]+$')
    
    # Dangerous characters to filter
    DANGEROUS_CHARS = ['<', '>', '"', "'", '&', ';', '|', '`', '$', '(', ')', '{', '}', '[', ']']
    SQL_KEYWORDS = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'UNION', 'EXEC', 'SCRIPT']
    
    @classmethod
    def validate_mac_address(cls, mac: str) -> bool:
        """Validate MAC address format"""
        if not isinstance(mac, str):
            return False
        if len(mac) > 17:  # Max length for MAC address
            return False
        return bool(cls.MAC_PATTERN.match(mac))
    
    @classmethod
    def validate_ssid(cls, ssid: str) -> bool:
        """Validate SSID format and content"""
        if not isinstance(ssid, str):
            return False
        if len(ssid) == 0 or len(ssid) > 32:
            return False
        # Check for null bytes and control characters
        if '\x00' in ssid or any(ord(c) < 32 and c not in '\t\n\r' for c in ssid):
            return False
        # Check for dangerous characters
        if any(char in ssid for char in cls.DANGEROUS_CHARS):
            logger.warning(f"SSID contains dangerous characters: {ssid}")
            return False
        return True
    
    @classmethod
    def validate_file_path(cls, path: str) -> bool:
        """Validate file path is safe"""
        if not isinstance(path, str):
            return False
        if len(path) > 4096:  # Max reasonable path length
            return False
        
        # Check for path traversal attempts
        if '..' in path or '~' in path:
            logger.warning(f"Path traversal attempt detected: {path}")
            return False
        
        # Check for dangerous characters
        if any(char in path for char in ['<', '>', '|', '&', ';', '`']):
            logger.warning(f"Dangerous characters in path: {path}")
            return False
        
        return True
    
    @classmethod
    def validate_filename(cls, filename: str) -> bool:
        """Validate filename is safe"""
        if not isinstance(filename, str):
            return False
        if len(filename) > 255:  # Max filename length
            return False
        
        # Check for dangerous patterns
        if filename in ['.', '..', ''] or filename.startswith('.'):
            return False
        
        return bool(cls.FILENAME_PATTERN.match(filename))
    
    @classmethod
    def sanitize_string(cls, input_str: str, max_length: int = 1000) -> str:
        """Sanitize string input by removing dangerous content"""
        if not isinstance(input_str, str):
            return ""
        
        # Truncate if too long
        if len(input_str) > max_length:
            input_str = input_str[:max_length]
            logger.warning(f"Input truncated to {max_length} characters")
        
        # Remove null bytes and control characters (except whitespace)
        sanitized = ''.join(c for c in input_str if ord(c) >= 32 or c in '\t\n\r')
        
        # Remove dangerous characters
        for char in cls.DANGEROUS_CHARS:
            sanitized = sanitized.replace(char, '')
        
        # Check for SQL injection attempts
        upper_sanitized = sanitized.upper()
        for keyword in cls.SQL_KEYWORDS:
            if keyword in upper_sanitized:
                logger.warning(f"Potential SQL injection attempt: {sanitized}")
                sanitized = sanitized.replace(keyword, '')
                sanitized = sanitized.replace(keyword.lower(), '')
        
        return sanitized.strip()
    
    @classmethod
    def validate_config_structure(cls, config: Dict[str, Any]) -> bool:
        """Validate configuration file structure"""
        required_keys = ['paths', 'timing']
        
        if not isinstance(config, dict):
            logger.error("Config must be a dictionary")
            return False
        
        for key in required_keys:
            if key not in config:
                logger.error(f"Missing required config key: {key}")
                return False
        
        # Validate paths section
        paths = config['paths']
        if not isinstance(paths, dict):
            logger.error("Config 'paths' must be a dictionary")
            return False
        
        required_paths = ['log_dir', 'kismet_logs', 'ignore_lists']
        for path_key in required_paths:
            if path_key not in paths:
                logger.error(f"Missing required path: {path_key}")
                return False
            
            path_value = paths[path_key]
            if isinstance(path_value, str):
                if not cls.validate_file_path(path_value):
                    logger.error(f"Invalid path format: {path_key}={path_value}")
                    return False
        
        # Validate timing section
        timing = config['timing']
        if not isinstance(timing, dict):
            logger.error("Config 'timing' must be a dictionary")
            return False
        
        timing_keys = ['check_interval', 'list_update_interval']
        for timing_key in timing_keys:
            if timing_key in timing:
                value = timing[timing_key]
                if not isinstance(value, (int, float)) or value <= 0:
                    logger.error(f"Invalid timing value: {timing_key}={value}")
                    return False
        
        return True
    
    @classmethod
    def validate_ignore_list(cls, ignore_list: List[str], list_type: str) -> List[str]:
        """Validate and filter ignore list entries"""
        if not isinstance(ignore_list, list):
            logger.error(f"Ignore list must be a list, got {type(ignore_list)}")
            return []
        
        validated_list = []
        validator_func = cls.validate_mac_address if list_type == 'mac' else cls.validate_ssid
        
        for item in ignore_list:
            if validator_func(item):
                validated_list.append(item)
            else:
                logger.warning(f"Invalid {list_type} entry removed: {item}")
        
        return validated_list
    
    @classmethod
    def validate_json_input(cls, json_str: str, max_size: int = 1024*1024) -> Optional[Dict]:
        """Safely parse and validate JSON input"""
        if not isinstance(json_str, str):
            logger.error("JSON input must be string")
            return None
        
        if len(json_str) > max_size:
            logger.error(f"JSON input too large: {len(json_str)} > {max_size}")
            return None
        
        try:
            # Parse JSON
            data = json.loads(json_str)
            
            # Basic structure validation
            if isinstance(data, dict):
                # Validate keys and values
                for key, value in data.items():
                    if not isinstance(key, str) or len(key) > 100:
                        logger.warning(f"Invalid JSON key: {key}")
                        return None
                    
                    # Recursively validate nested structures
                    if isinstance(value, (dict, list)):
                        continue  # Could add deeper validation here
                    elif isinstance(value, str):
                        if len(value) > 10000:  # Reasonable string limit
                            logger.warning(f"JSON string value too long: {key}")
                            return None
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            return None
    
    @classmethod
    def validate_database_path(cls, db_path: str) -> bool:
        """Validate database path is safe and accessible"""
        if not cls.validate_file_path(db_path):
            return False
        
        # Check if path exists (for globbed paths, check pattern)
        if '*' in db_path:
            # It's a glob pattern - validate the base directory
            base_dir = db_path.split('*')[0]
            if base_dir and not Path(base_dir).exists():
                logger.warning(f"Database base directory does not exist: {base_dir}")
                return False
        else:
            # It's a specific file
            if not Path(db_path).exists():
                logger.warning(f"Database file does not exist: {db_path}")
                return False
        
        return True


class SecureInputHandler:
    """Wrapper for handling all input validation in CYT"""
    
    def __init__(self):
        self.validator = InputValidator()
    
    def safe_load_config(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Safely load and validate configuration file"""
        try:
            if not self.validator.validate_file_path(config_path):
                logger.error(f"Invalid config path: {config_path}")
                return None
            
            if not Path(config_path).exists():
                logger.error(f"Config file not found: {config_path}")
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Validate JSON structure
            config = self.validator.validate_json_input(content)
            if not config:
                return None
            
            # Validate configuration structure
            if not self.validator.validate_config_structure(config):
                return None
            
            logger.info(f"Configuration loaded and validated: {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return None
    
    def safe_load_ignore_list(self, file_path: Path, list_type: str) -> List[str]:
        """Safely load ignore list with validation"""
        try:
            if not file_path.exists():
                logger.info(f"Ignore list not found: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse as JSON first
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return self.validator.validate_ignore_list(data, list_type)
            except json.JSONDecodeError:
                pass
            
            # Fall back to Python variable parsing (but safer)
            # This is for legacy compatibility
            logger.warning(f"Using legacy ignore list format: {file_path}")
            # We'll implement safer parsing if needed
            
            return []
            
        except Exception as e:
            logger.error(f"Error loading ignore list {file_path}: {e}")
            return []