import sqlite3
import glob
import json
import os
import pathlib
import logging
from typing import Set
from datetime import datetime

# Use a logger instead of print for better feedback
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def find_latest_kismet_db(path_pattern: str) -> str:
    """Finds the most recently modified file matching a glob pattern."""
    try:
        # Check if it's a directory or a file pattern
        if os.path.isdir(path_pattern):
            path_pattern = os.path.join(path_pattern, "*.kismet")

        list_of_files = glob.glob(path_pattern)
        if not list_of_files:
            raise FileNotFoundError(
                "No Kismet files found matching pattern: "
                f"{path_pattern}")
        latest_file = max(list_of_files, key=os.path.getctime)
        logging.info(f"Found latest Kismet DB: {latest_file}")
        return latest_file
    except Exception as e:
        logging.error(f"Could not find Kismet DB file: {e}")
        raise


def fetch_all_macs(db_path: str) -> Set[str]:
    """Fetches all unique device MAC addresses from the Kismet DB."""
    macs = set()
    try:
        # CHANGED: Use a 'with' statement to ensure the connection is always closed.
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT devmac FROM devices WHERE devmac IS NOT NULL")
            rows = cursor.fetchall()
            for row in rows:
                # CHANGED: Correctly and safely extract the MAC address from the row tuple.
                macs.add(row[0])
    except sqlite3.Error as e:
        logging.error(f"Database error while fetching MACs: {e}")
    return macs


def fetch_all_probed_ssids(db_path: str) -> Set[str]:
    """Fetches all unique probed SSIDs from the Kismet DB."""
    ssids = set()
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            cursor = conn.cursor()
            # Select only rows that have a device JSON blob
            cursor.execute(
                "SELECT device FROM devices WHERE "
                "device IS NOT NULL AND device != ''")
            rows = cursor.fetchall()
            for row in rows:
                try:
                    device_json = json.loads(row[0])
                    # CHANGED: Safely access nested keys using .get() to avoid crashes.
                    ssid = (device_json.get("dot11.device", {})
                            .get("dot11.device.last_probed_ssid_record", {})
                            .get("dot11.probedssid.ssid"))
                    if ssid:  # Ensure ssid is not None or an empty string
                        ssids.add(ssid)
                except (json.JSONDecodeError, KeyError):
                    # Ignore rows with malformed JSON or unexpected structure
                    continue
    except sqlite3.Error as e:
        logging.error(f"Database error while fetching SSIDs: {e}")
    return ssids


def merge_with_existing_file(new_data: Set[str], output_path: pathlib.Path) -> list:
    """
    Merges new data with existing file, preserving comments and structure.
    Returns list of lines to write (preserves comments from old file).
    """
    if not output_path.exists():
        # No existing file, return simple list
        return [f"{item}\n" for item in sorted(list(new_data))]

    # Read existing file with comments
    existing_lines = []
    existing_entries = set()

    with open(output_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Preserve all lines (including comments and blank lines)
            existing_lines.append(line)

            # Extract entry (remove comments)
            entry = line.split('#')[0].strip()
            if entry:
                existing_entries.add(entry)

    # Find new entries not in existing file
    new_entries = new_data - existing_entries

    if new_entries:
        # Add section header for new entries
        existing_lines.append("\n")
        existing_lines.append("# ===== NEW DEVICES (REVIEW AND CATEGORIZE) =====\n")
        existing_lines.append(f"# Added: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        existing_lines.append("# Review these entries and move them to appropriate sections above\n")
        existing_lines.append("\n")

        for entry in sorted(list(new_entries)):
            existing_lines.append(f"{entry}\n")

    return existing_lines


def write_list_to_file(data: Set[str], output_path: pathlib.Path):
    """
    Writes a set of items to a file, intelligently merging with existing content.
    Preserves comments and structure from existing file.
    """
    try:
        if output_path.exists():
            # Create backup
            backup_path = pathlib.Path(str(output_path) + '.backup')
            import shutil
            shutil.copy2(output_path, backup_path)
            logging.info(f"Backup created: {backup_path}")

            # Merge with existing file
            merged_lines = merge_with_existing_file(data, output_path)

            # Write merged content
            with open(output_path, "w", encoding='utf-8') as f:
                f.writelines(merged_lines)

            new_count = len(data) - len([l for l in merged_lines if l.strip() and not l.strip().startswith('#')] or [])
            if new_count > 0:
                logging.info(f"Added {new_count} new entries to {output_path}")
                logging.info(f"Your existing comments and organization were preserved!")
                logging.info(f"New entries added at the bottom - review and categorize them")
            else:
                logging.info(f"No new entries found - file unchanged")
        else:
            # New file - write simple list
            with open(output_path, "w", encoding='utf-8') as f:
                for item in sorted(list(data)):
                    f.write(f"{item}\n")
            logging.info(f"Created new file with {len(data)} items: {output_path}")

    except IOError as e:
        logging.error(f"Could not write to file {output_path}: {e}")


def main():
    """Main function to run the ignore list creation process."""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logging.critical(f"Failed to load or parse config.json: {e}")
        return
    # Create output directory if it doesn't exist
    output_dir = pathlib.Path('./ignore_lists')
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        db_path_pattern = config['paths']['kismet_logs']
        latest_db = find_latest_kismet_db(db_path_pattern)
    except (KeyError, FileNotFoundError):
        return  # Errors are already logged in the function

    # Process MAC addresses
    mac_list = fetch_all_macs(latest_db)
    mac_output_path = output_dir / "mac_list.txt"  # CHANGED: Using .txt format
    write_list_to_file(mac_list, mac_output_path)

    # Process SSIDs
    ssid_list = fetch_all_probed_ssids(latest_db)
    # CHANGED: Using .txt format
    ssid_output_path = output_dir / "ssid_list.txt"
    write_list_to_file(ssid_list, ssid_output_path)


if __name__ == "__main__":
    main()
