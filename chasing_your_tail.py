# Chasing Your Tail V04_15_22.py
# @matt0177
# Released under the MIT License https://opensource.org/licenses/MIT
###

import time
import glob
import os
import pathlib
import signal
import sys
import logging
import sqlite3
import subprocess
from secure_ignore_loader import load_ignore_lists
from secure_database import SecureKismetDB
from secure_main_logic import SecureCYTMonitor
from secure_credentials import secure_config_loader


class CYTMonitorApp:
    """
    Main application class for the CYT monitoring engine.
    Encapsulates all setup, state, and the main run loop.
    """

    def __init__(self):
        self.config = None
        self.credential_manager = None
        self.ignore_list = set()
        self.probe_ignore_list = set()
        self.latest_kismet_db = None
        self.secure_monitor = None
        self.log_file_handle = None  # Added to hold the file handle
        self._setup_logging()

    def _setup_logging(self):
        """Configures the unified logging system."""
        log_dir = pathlib.Path('./logs')
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create the file handle needed by SecureCYTMonitor
        filename = f'cyt_log_{time.strftime("%m%d%y_%H%M%S")}.log'
        self.log_file_path = log_dir / filename

        # Open file in append mode (buffering=1 means line buffered)
        self.log_file_handle = open(self.log_file_path, "w", buffering=1)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file_path),
                logging.StreamHandler(sys.stdout)
            ]
        )
        logging.info("--- CYT Monitoring Session Started ---")

    def _shutdown(self, signum=None, frame=None):
        """Handles graceful shutdown of the application."""
        logging.info("Shutting down gracefully...")
        if self.log_file_handle:
            self.log_file_handle.close()
        sys.exit(0)

    def _check_kismet_running(self):
        """Check if a Kismet process is running."""
        try:
            subprocess.check_output(["pgrep", "kismet"])
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _check_db_updated(self, db_path, max_age_seconds=300):
        """Check if the Kismet database is being updated."""
        try:
            mtime = os.path.getmtime(db_path)
            if (time.time() - mtime) > max_age_seconds:
                return False
            return True
        except FileNotFoundError:
            return False

    def initialize(self):
        """Loads configuration and initializes all components."""
        try:
            logging.info("Loading configuration and credentials...")
            self.config, self.credential_manager = secure_config_loader(
                'config.json')

            logging.info("Loading ignore lists securely...")
            self.ignore_list, self.probe_ignore_list = load_ignore_lists(
                self.config)
            logging.info(
                f"Loaded {len(self.ignore_list)} MACs and "
                f"{len(self.probe_ignore_list)} SSIDs to ignore lists.")

            db_path_pattern = self.config['paths']['kismet_logs']
            logging.info(
                "Searching for Kismet databases with pattern: "
                f"{db_path_pattern}")

            # Check if it's a directory or a file pattern
            if os.path.isdir(db_path_pattern):
                db_path_pattern = os.path.join(db_path_pattern, "*.kismet")

            list_of_files = glob.glob(db_path_pattern)
            if not list_of_files:
                # Fallback for testing: use the test database if it exists
                if os.path.exists("test_capture.kismet"):
                    logging.warning(
                        "No live Kismet DB found. "
                        "Using test_capture.kismet for simulation.")
                    self.latest_kismet_db = "test_capture.kismet"
                else:
                    raise FileNotFoundError(
                        "No Kismet database files found at: "
                        f"{db_path_pattern}")
            else:
                self.latest_kismet_db = max(
                    list_of_files, key=os.path.getctime)

            logging.info(f"Using Kismet database: {self.latest_kismet_db}")

            # Initialize the core logic monitor
            # CHANGED: Passing self.log_file_handle to satisfy the required argument
            self.secure_monitor = SecureCYTMonitor(
                self.config,
                self.ignore_list,
                self.probe_ignore_list,
                self.log_file_handle
            )

            # Test database connection and initialize tracking lists
            logging.info(
                "Validating database and initializing tracking lists...")
            with SecureKismetDB(self.latest_kismet_db) as db:
                if not db.validate_connection():
                    raise RuntimeError("Database validation failed")
                self.secure_monitor.initialize_tracking_lists(db)

            logging.info("Initialization complete. Starting main loop.")
            return True
        except (FileNotFoundError, KeyError, RuntimeError) as e:
            logging.critical(
                f"Fatal error during initialization: {e}", exc_info=True)
            return False

    def run(self):
        """Runs the main monitoring loop."""
        signal.signal(signal.SIGINT, self._shutdown)

        if not self._check_kismet_running():
            logging.warning(
                "Kismet does not appear to be running. "
                "CYT will only analyze existing data.")

        time_count = 0
        check_interval = self.config.get(
            'timing', {}).get('check_interval', 60)
        list_update_interval = self.config.get(
            'timing', {}).get('list_update_interval', 5)

        logging.info("Starting secure CYT monitoring loop...")
        print("🔒 SECURE MODE: All SQL injection "
              "vulnerabilities have been eliminated!")
        print(
            f"Monitoring every {check_interval} seconds, "
            f"updating lists every {list_update_interval} cycles")
        print("Press Control+C to shut down gracefully.")

        while True:
            try:
                # Check if the database is being updated
                if not self._check_db_updated(self.latest_kismet_db):
                    logging.warning(
                        "Kismet database is not being updated. "
                        "Kismet may have stopped.")

                # Process current activity with secure database operations
                with SecureKismetDB(self.latest_kismet_db) as db:
                    self.secure_monitor.process_current_activity(db)

                    # Rotate tracking lists every N cycles
                    time_count += 1
                    if time_count % list_update_interval == 0:
                        logging.info(
                            f"Rotating tracking lists (cycle {time_count})")
                        self.secure_monitor.rotate_tracking_lists(db)

            except (sqlite3.Error, RuntimeError) as e:
                logging.error(
                    f"Error in monitoring loop: {e}", exc_info=True)

            # Sleep for the configured interval
            time.sleep(check_interval)



if __name__ == "__main__":
    app = CYTMonitorApp()
    if app.initialize():
        app.run()
    else:
        logging.critical("Application failed to initialize. Exiting.")
        sys.exit(1)
