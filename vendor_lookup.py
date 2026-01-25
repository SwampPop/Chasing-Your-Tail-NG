#!/usr/bin/env python3
"""
Shared vendor lookup utility for CYT.

Provides cached MAC address vendor lookup functionality used by multiple modules.
Eliminates code duplication between cyt_proxy_server.py and ao_tracker.py.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cache MacLookup instance for performance (singleton pattern)
_mac_lookup_instance: Optional[object] = None

# Characters indicating randomized MAC (local bit set in second nibble)
RANDOMIZED_MAC_INDICATORS = frozenset(['2', '6', 'A', 'E'])


def _get_mac_lookup():
    """Get cached MacLookup instance (lazy initialization)."""
    global _mac_lookup_instance
    if _mac_lookup_instance is None:
        try:
            from mac_vendor_lookup import MacLookup
            _mac_lookup_instance = MacLookup()
            logger.debug("MacLookup initialized successfully")
        except ImportError:
            logger.warning("mac_vendor_lookup not installed - vendor lookup disabled")
            _mac_lookup_instance = False  # Mark as unavailable
    return _mac_lookup_instance


def lookup_vendor(mac: str) -> str:
    """
    Look up vendor from MAC address with caching.

    Args:
        mac: MAC address string (format: XX:XX:XX:XX:XX:XX)

    Returns:
        Vendor name string, "Randomized" for randomized MACs, or "Unknown"
    """
    if not mac:
        return "Unknown"

    # Try cached MacLookup
    mac_lookup = _get_mac_lookup()
    if mac_lookup:
        try:
            return mac_lookup.lookup(mac)
        except KeyError:
            # MAC not in database - check if randomized
            pass
        except ValueError as e:
            logger.debug(f"Invalid MAC for lookup: {mac} - {e}")

    # Check if randomized MAC (local bit set in second nibble)
    try:
        if len(mac) >= 2 and mac[1].upper() in RANDOMIZED_MAC_INDICATORS:
            return "Randomized"
    except (IndexError, TypeError):
        pass

    return "Unknown"


def is_randomized_mac(mac: str) -> bool:
    """
    Check if a MAC address is randomized (local bit set).

    Args:
        mac: MAC address string

    Returns:
        True if MAC appears to be randomized, False otherwise
    """
    try:
        return len(mac) >= 2 and mac[1].upper() in RANDOMIZED_MAC_INDICATORS
    except (IndexError, TypeError):
        return False
