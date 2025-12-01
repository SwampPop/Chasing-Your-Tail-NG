#!/usr/bin/env python3
"""
Configuration Validator for CYT
Validates config.json against a JSON schema to catch errors at startup.
"""
import json
import logging
from typing import Dict, Any

try:
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    logging.warning("jsonschema not installed - config validation disabled")

logger = logging.getLogger(__name__)

# JSON Schema for config.json
CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["paths", "timing"],
    "properties": {
        "paths": {
            "type": "object",
            "required": ["kismet_logs"],
            "properties": {
                "kismet_logs": {
                    "type": "string",
                    "description": "Path pattern to Kismet database files"
                },
                "ignore_lists": {
                    "type": "string",
                    "description": "Directory containing ignore list files"
                },
                "log_directory": {
                    "type": "string",
                    "description": "Directory for log files"
                }
            }
        },
        "timing": {
            "type": "object",
            "required": ["time_windows"],
            "properties": {
                "time_windows": {
                    "type": "object",
                    "required": ["recent", "medium", "old", "oldest"],
                    "properties": {
                        "recent": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 60,
                            "description": "Recent time window in minutes"
                        },
                        "medium": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 120
                        },
                        "old": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 240
                        },
                        "oldest": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 480
                        }
                    }
                },
                "check_interval": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 300,
                    "description": "Monitoring loop interval in seconds"
                },
                "list_update_interval": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "How often to rotate tracking lists (in cycles)"
                }
            }
        },
        "alert_settings": {
            "type": "object",
            "properties": {
                "drone_time_window_seconds": {
                    "type": "integer",
                    "minimum": 30
                },
                "watchlist_time_window_seconds": {
                    "type": "integer",
                    "minimum": 30
                },
                "locations_threshold": {
                    "type": "integer",
                    "minimum": 1
                }
            }
        },
        "detection_thresholds": {
            "type": "object",
            "properties": {
                "min_appearances": {
                    "type": "integer",
                    "minimum": 1
                },
                "min_locations": {
                    "type": "integer",
                    "minimum": 1
                },
                "persistence_score_critical": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "persistence_score_high": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "persistence_score_medium": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            }
        },
        "gps_settings": {
            "type": "object",
            "properties": {
                "location_threshold_meters": {
                    "type": "number",
                    "minimum": 1.0
                },
                "session_timeout_seconds": {
                    "type": "integer",
                    "minimum": 60
                }
            }
        },
        "kismet_health": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "Enable Kismet health monitoring"
                },
                "check_interval_cycles": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "How often to check Kismet health (in monitoring cycles)"
                },
                "data_freshness_threshold_minutes": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 60,
                    "description": "Alert if no new data in X minutes"
                },
                "auto_restart": {
                    "type": "boolean",
                    "description": "Automatically restart Kismet on failure"
                },
                "max_restart_attempts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Max auto-restart attempts before giving up"
                },
                "startup_script": {
                    "type": "string",
                    "description": "Path to Kismet startup script"
                },
                "interface": {
                    "type": "string",
                    "description": "Wireless interface for Kismet (e.g., wlan0mon)"
                }
            }
        },
        "behavioral_drone_detection": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "Enable behavioral drone detection"
                },
                "min_appearances": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Minimum appearances before analysis"
                },
                "confidence_threshold": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Minimum confidence for drone alert (0.0-1.0)"
                },
                "signal_variance_threshold": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Signal variance threshold for movement detection"
                },
                "rapid_movement_threshold_mps": {
                    "type": "number",
                    "minimum": 1.0,
                    "maximum": 100.0,
                    "description": "Rapid movement threshold in meters per second"
                },
                "hovering_radius_meters": {
                    "type": "number",
                    "minimum": 1.0,
                    "maximum": 500.0,
                    "description": "Hovering pattern radius in meters"
                },
                "brief_appearance_seconds": {
                    "type": "integer",
                    "minimum": 10,
                    "maximum": 3600,
                    "description": "Brief appearance threshold in seconds"
                },
                "high_signal_threshold": {
                    "type": "integer",
                    "minimum": -100,
                    "maximum": 0,
                    "description": "High signal threshold in dBm"
                },
                "probe_frequency_per_minute": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "High probe frequency threshold (probes/minute)"
                },
                "history_cleanup_hours": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 168,
                    "description": "How long to keep device history (hours)"
                }
            }
        }
    }
}


def validate_config(config: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate configuration against schema.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)
        If valid: (True, "")
        If invalid: (False, "detailed error message")
    """
    if not JSONSCHEMA_AVAILABLE:
        logger.warning("Skipping config validation - jsonschema not installed")
        return (True, "")  # Don't block startup if jsonschema missing

    try:
        validate(instance=config, schema=CONFIG_SCHEMA)
        logger.info("✓ Configuration validation passed")
        return (True, "")
    except ValidationError as e:
        # Create helpful error message
        error_path = " -> ".join(str(p) for p in e.path) if e.path else "root"
        error_msg = f"Configuration error at '{error_path}': {e.message}"

        # Add helpful context
        if e.validator == "required":
            error_msg += f"\nMissing required field(s): {e.message}"
        elif e.validator in ["minimum", "maximum"]:
            error_msg += f"\nValue must be between {e.schema.get('minimum', 'N/A')} and {e.schema.get('maximum', 'N/A')}"

        logger.error(f"✗ {error_msg}")
        return (False, error_msg)
    except Exception as e:
        error_msg = f"Unexpected error validating config: {e}"
        logger.error(error_msg)
        return (False, error_msg)


def validate_config_file(config_path: str = "config.json") -> tuple[bool, str, Dict[str, Any] | None]:
    """
    Load and validate configuration file.

    Args:
        config_path: Path to config.json file

    Returns:
        Tuple of (is_valid, error_message, config_dict)
        If valid: (True, "", {config data})
        If invalid: (False, "error message", None)
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        return (False, f"Config file not found: {config_path}", None)
    except json.JSONDecodeError as e:
        return (False, f"Invalid JSON in config file: {e}", None)
    except Exception as e:
        return (False, f"Error reading config file: {e}", None)

    is_valid, error_msg = validate_config(config)
    if is_valid:
        return (True, "", config)
    else:
        return (False, error_msg, None)


if __name__ == "__main__":
    """Test the validator"""
    print("=" * 70)
    print("CYT Configuration Validator")
    print("=" * 70)

    is_valid, error, config = validate_config_file("config.json")

    if is_valid:
        print("\n✓ Configuration is VALID")
        print(f"\nLoaded sections:")
        for key in config.keys():
            print(f"  - {key}")
    else:
        print("\n✗ Configuration is INVALID")
        print(f"\nError:\n{error}")
        print("\nPlease fix config.json and try again.")
        exit(1)

    print("=" * 70)
