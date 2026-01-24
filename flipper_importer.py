#!/usr/bin/env python3

################################################################################
# flipper_importer.py
# Purpose: Import Flipper Zero Sub-GHz captures into CYT threat intelligence
# Supported: .sub files (Sub-GHz), .nfc files (NFC/RFID), .ir files (Infrared)
# Created: 2026-01-08
################################################################################

import os
import re
import sys
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger('CYT.FlipperImporter')


class FlipperImporter:
    """
    Import Flipper Zero captures into CYT watchlist database

    Supported file types:
    - .sub: Sub-GHz captures (315/433/868/915 MHz)
    - .nfc: NFC/RFID captures
    - .ir: Infrared captures
    """

    def __init__(self, watchlist_db_path: str = 'watchlist.db'):
        """
        Initialize Flipper importer

        Args:
            watchlist_db_path: Path to CYT watchlist database
        """
        self.db_path = watchlist_db_path
        self._init_database()

    def _init_database(self):
        """Initialize flipper_captures table in watchlist database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flipper_captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capture_type TEXT NOT NULL,
                protocol TEXT,
                frequency_mhz REAL,
                modulation TEXT,
                preset TEXT,
                raw_data TEXT,
                file_name TEXT,
                import_date TEXT NOT NULL,
                threat_level TEXT DEFAULT 'investigate',
                notes TEXT
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_flipper_type
            ON flipper_captures(capture_type)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_flipper_freq
            ON flipper_captures(frequency_mhz)
        ''')

        conn.commit()
        conn.close()

        logger.info(f"Flipper captures database initialized: {self.db_path}")

    def parse_sub_file(self, sub_file_path: str) -> Optional[Dict]:
        """
        Parse Flipper Zero .sub file (Sub-GHz capture)

        .sub file format:
        Filetype: Flipper SubGhz RAW File
        Version: 1
        Frequency: 433920000
        Preset: FuriHalSubGhzPresetOok650Async
        Protocol: RAW
        RAW_Data: 9034 -936 1068 -936 ...

        Args:
            sub_file_path: Path to .sub file

        Returns:
            Parsed capture dict or None if parsing fails
        """
        try:
            with open(sub_file_path, 'r') as f:
                content = f.read()

            capture = {
                'capture_type': 'sub_ghz',
                'file_name': os.path.basename(sub_file_path)
            }

            # Extract frequency (Hz -> MHz)
            freq_match = re.search(r'Frequency:\s*(\d+)', content)
            if freq_match:
                freq_hz = int(freq_match.group(1))
                capture['frequency_mhz'] = freq_hz / 1e6

            # Extract protocol
            protocol_match = re.search(r'Protocol:\s*(\w+)', content)
            if protocol_match:
                capture['protocol'] = protocol_match.group(1)

            # Extract preset/modulation
            preset_match = re.search(r'Preset:\s*(\w+)', content)
            if preset_match:
                capture['preset'] = preset_match.group(1)
                # Decode modulation from preset name
                if 'OOK' in capture['preset'].upper():
                    capture['modulation'] = 'OOK'
                elif 'FSK' in capture['preset'].upper():
                    capture['modulation'] = 'FSK'
                elif '2FSK' in capture['preset'].upper():
                    capture['modulation'] = '2FSK'
                else:
                    capture['modulation'] = 'Unknown'

            # Extract RAW data (first 1000 chars for storage)
            raw_match = re.search(r'RAW_Data:\s*(.+)', content, re.DOTALL)
            if raw_match:
                capture['raw_data'] = raw_match.group(1)[:1000]

            # Threat assessment based on frequency
            freq = capture.get('frequency_mhz', 0)
            if freq:
                if 315 <= freq <= 315.5:
                    capture['notes'] = "315 MHz - Car key fob / garage door opener"
                    capture['threat_level'] = 'high'
                elif 433 <= freq <= 434:
                    capture['notes'] = "433 MHz - Remote controls / sensors"
                    capture['threat_level'] = 'medium'
                elif 868 <= freq <= 870:
                    capture['notes'] = "868 MHz - EU ISM band - sensors / alarms"
                    capture['threat_level'] = 'medium'
                elif 902 <= freq <= 928:
                    capture['notes'] = "900 MHz ISM - US sensors / tracking devices"
                    capture['threat_level'] = 'high'
                else:
                    capture['notes'] = f"Unusual frequency: {freq:.2f} MHz"
                    capture['threat_level'] = 'investigate'

            return capture

        except Exception as e:
            logger.error(f"Failed to parse .sub file {sub_file_path}: {e}")
            return None

    def parse_nfc_file(self, nfc_file_path: str) -> Optional[Dict]:
        """
        Parse Flipper Zero .nfc file (NFC/RFID capture)

        .nfc file format:
        Filetype: Flipper NFC device
        Version: 2
        Device type: NTAG215
        UID: 04 E7 B8 C2 3E 5B 80
        ATQA: 00 44
        SAK: 00

        Args:
            nfc_file_path: Path to .nfc file

        Returns:
            Parsed capture dict or None if parsing fails
        """
        try:
            with open(nfc_file_path, 'r') as f:
                content = f.read()

            capture = {
                'capture_type': 'nfc_rfid',
                'file_name': os.path.basename(nfc_file_path),
                'frequency_mhz': 13.56,  # NFC frequency
                'modulation': 'NFC'
            }

            # Extract device type
            device_match = re.search(r'Device type:\s*(.+)', content)
            if device_match:
                capture['protocol'] = device_match.group(1).strip()

            # Extract UID
            uid_match = re.search(r'UID:\s*(.+)', content)
            if uid_match:
                capture['raw_data'] = f"UID: {uid_match.group(1).strip()}"

            capture['notes'] = f"NFC/RFID card: {capture.get('protocol', 'Unknown type')}"
            capture['threat_level'] = 'high'  # Access control cloning

            return capture

        except Exception as e:
            logger.error(f"Failed to parse .nfc file {nfc_file_path}: {e}")
            return None

    def parse_ir_file(self, ir_file_path: str) -> Optional[Dict]:
        """
        Parse Flipper Zero .ir file (Infrared capture)

        .ir file format:
        Filetype: IR signals file
        Version: 1
        name: Power
        type: parsed
        protocol: NECext
        address: 04 00 00 00
        command: 08 00 00 00

        Args:
            ir_file_path: Path to .ir file

        Returns:
            Parsed capture dict or None if parsing fails
        """
        try:
            with open(ir_file_path, 'r') as f:
                content = f.read()

            capture = {
                'capture_type': 'infrared',
                'file_name': os.path.basename(ir_file_path),
                'frequency_mhz': 0.000033,  # ~33 kHz (IR carrier)
                'modulation': 'IR'
            }

            # Extract protocol
            protocol_match = re.search(r'protocol:\s*(\w+)', content)
            if protocol_match:
                capture['protocol'] = protocol_match.group(1)

            # Extract command data
            command_match = re.search(r'command:\s*(.+)', content)
            if command_match:
                capture['raw_data'] = f"Command: {command_match.group(1).strip()}"

            capture['notes'] = f"IR remote: {capture.get('protocol', 'Unknown protocol')}"
            capture['threat_level'] = 'low'  # Typically not a threat

            return capture

        except Exception as e:
            logger.error(f"Failed to parse .ir file {ir_file_path}: {e}")
            return None

    def import_capture(self, file_path: str) -> bool:
        """
        Import a Flipper Zero capture file into CYT watchlist

        Args:
            file_path: Path to .sub, .nfc, or .ir file

        Returns:
            True if import successful, False otherwise
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False

        # Determine file type and parse
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.sub':
            capture = self.parse_sub_file(file_path)
        elif ext == '.nfc':
            capture = self.parse_nfc_file(file_path)
        elif ext == '.ir':
            capture = self.parse_ir_file(file_path)
        else:
            logger.error(f"Unsupported file type: {ext}")
            return False

        if not capture:
            return False

        # Add to database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO flipper_captures
                (capture_type, protocol, frequency_mhz, modulation, preset, raw_data,
                 file_name, import_date, threat_level, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                capture['capture_type'],
                capture.get('protocol'),
                capture.get('frequency_mhz'),
                capture.get('modulation'),
                capture.get('preset'),
                capture.get('raw_data'),
                capture['file_name'],
                datetime.now().isoformat(),
                capture.get('threat_level', 'investigate'),
                capture.get('notes', '')
            ))

            conn.commit()
            conn.close()

            logger.info(f"✓ Imported {capture['file_name']} - {capture['capture_type']}")
            return True

        except Exception as e:
            logger.error(f"Database import failed: {e}")
            return False

    def import_directory(self, directory: str) -> Dict[str, int]:
        """
        Recursively import all Flipper captures from a directory

        Args:
            directory: Path to directory containing captures

        Returns:
            Dict with import statistics
        """
        stats = {'total': 0, 'success': 0, 'failed': 0}

        for root, dirs, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.sub', '.nfc', '.ir']:
                    stats['total'] += 1
                    file_path = os.path.join(root, file)

                    if self.import_capture(file_path):
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1

        logger.info(f"Batch import complete: {stats['success']}/{stats['total']} successful")
        return stats

    def list_captures(self, capture_type: Optional[str] = None) -> List[Dict]:
        """
        List all imported Flipper captures

        Args:
            capture_type: Filter by type (sub_ghz, nfc_rfid, infrared) or None for all

        Returns:
            List of capture dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if capture_type:
            cursor.execute('''
                SELECT * FROM flipper_captures
                WHERE capture_type = ?
                ORDER BY import_date DESC
            ''', (capture_type,))
        else:
            cursor.execute('''
                SELECT * FROM flipper_captures
                ORDER BY import_date DESC
            ''')

        captures = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return captures


def main():
    """CLI interface for Flipper importer"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage:")
        print("  flipper_importer.py <file.sub>           # Import single file")
        print("  flipper_importer.py <directory>          # Import all files in directory")
        print("  flipper_importer.py --list [type]        # List imported captures")
        sys.exit(1)

    importer = FlipperImporter()

    if sys.argv[1] == '--list':
        capture_type = sys.argv[2] if len(sys.argv) > 2 else None
        captures = importer.list_captures(capture_type)

        print(f"\n{'='*80}")
        print(f"Imported Flipper Zero Captures: {len(captures)}")
        print(f"{'='*80}\n")

        for cap in captures:
            print(f"[{cap['threat_level'].upper()}] {cap['file_name']}")
            print(f"  Type: {cap['capture_type']} | Protocol: {cap['protocol']}")
            print(f"  Frequency: {cap['frequency_mhz']} MHz | {cap['notes']}")
            print(f"  Imported: {cap['import_date']}\n")

    elif os.path.isdir(sys.argv[1]):
        print(f"Importing all Flipper captures from: {sys.argv[1]}")
        stats = importer.import_directory(sys.argv[1])
        print(f"\n✓ Import complete: {stats['success']}/{stats['total']} successful")

    elif os.path.isfile(sys.argv[1]):
        print(f"Importing: {sys.argv[1]}")
        if importer.import_capture(sys.argv[1]):
            print("✓ Import successful")
        else:
            print("✗ Import failed")
            sys.exit(1)

    else:
        print(f"Error: {sys.argv[1]} not found")
        sys.exit(1)


if __name__ == '__main__':
    main()
