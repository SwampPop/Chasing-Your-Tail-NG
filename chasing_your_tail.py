### Chasing Your Tail V04_15_22.py 
### @matt0177
### Released under the MIT License https://opensource.org/licenses/MIT
###

import sqlite3
import time
from datetime import datetime, timedelta
import glob
import os
import json
import pathlib
import signal
import sys
import logging
from secure_ignore_loader import load_ignore_lists
from secure_database import SecureKismetDB
from secure_main_logic import SecureCYTMonitor
from secure_credentials import secure_config_loader
from lib import history_manager
from config_validator import validate_config_file

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
        self.log_file_handle = None # Added to hold the file handle
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

    def initialize(self):
        """Loads configuration and initializes all components."""
        try:
            # Validate configuration before loading
            logging.info("Validating configuration...")
            is_valid, error_msg, validated_config = validate_config_file('config.json')
            if not is_valid:
                logging.critical(f"Configuration validation failed:\n{error_msg}")
                print(f"\n✗ Configuration Error:\n{error_msg}\n")
                print("Please fix config.json and try again.")
                return False

            logging.info("Loading configuration and credentials...")
            self.config, self.credential_manager = secure_config_loader('config.json')
            
            logging.info("Loading ignore lists securely...")
            self.ignore_list, self.probe_ignore_list = load_ignore_lists(self.config)
            logging.info(f"Loaded {len(self.ignore_list)} MACs and {len(self.probe_ignore_list)} SSIDs to ignore lists.")
            
            db_path_pattern = self.config['paths']['kismet_logs']
            logging.info(f"Searching for Kismet databases with pattern: {db_path_pattern}")
            
            # Check if it's a directory or a file pattern
            if os.path.isdir(db_path_pattern):
                 db_path_pattern = os.path.join(db_path_pattern, "*.kismet")

            list_of_files = glob.glob(db_path_pattern)
            if not list_of_files:
                # Fallback for testing: use the test database if it exists
                if os.path.exists("test_capture.kismet"):
                    logging.warning("No live Kismet DB found. Using test_capture.kismet for simulation.")
                    self.latest_kismet_db = "test_capture.kismet"
                else:
                    raise FileNotFoundError(f"No Kismet database files found at: {db_path_pattern}")
            else:
                self.latest_kismet_db = max(list_of_files, key=os.path.getctime)
            
            logging.info(f"Using Kismet database: {self.latest_kismet_db}")
            
            # Initialize the core logic monitor
            # CHANGED: Passing self.log_file_handle to satisfy the required argument
            self.secure_monitor = SecureCYTMonitor(
                self.config, 
                self.ignore_list, 
                self.probe_ignore_list, 
                self.log_file_handle
            )
            
            # Initialize history database for persistent detection tracking
            logging.info("Initializing history database...")
            try:
                history_manager.initialize_history_database()
                logging.info("History database initialized successfully")
            except Exception as e:
                logging.warning(f"Could not initialize history database: {e}")
                # Continue anyway - history is nice-to-have, not critical

            # Test database connection and initialize tracking lists
            logging.info("Validating database and initializing tracking lists...")
            with SecureKismetDB(self.latest_kismet_db) as db:
                if not db.validate_connection():
                    raise RuntimeError("Database validation failed")
                self.secure_monitor.initialize_tracking_lists(db)

            logging.info("Initialization complete. Starting main loop.")
            return True
        except Exception as e:
            logging.critical(f"Fatal error during initialization: {e}", exc_info=True)
            return False

    def run(self):
        """Runs the main monitoring loop."""
        signal.signal(signal.SIGINT, self._shutdown)

        time_count = 0
        check_interval = self.config.get('timing', {}).get('check_interval', 60)
        list_update_interval = self.config.get('timing', {}).get('list_update_interval', 5)

        logging.info("Starting secure CYT monitoring loop...")
        print(f"🔒 SECURE MODE: All SQL injection vulnerabilities have been eliminated!")
        print(f"Monitoring every {check_interval} seconds, updating lists every {list_update_interval} cycles")
        print("Press Control+C to shut down gracefully.")

        while True:
            try:
                # Process current activity with secure database operations
                with SecureKismetDB(self.latest_kismet_db) as db:
                    self.secure_monitor.process_current_activity(db)

                    # Rotate tracking lists every N cycles
                    time_count += 1
                    if time_count % list_update_interval == 0:
                        logging.info(f"Rotating tracking lists (cycle {time_count})")
                        self.secure_monitor.rotate_tracking_lists(db)

                # Archive detections to history database
                detections = self.secure_monitor.get_and_clear_detections()
                if detections:
                    try:
                        history_manager.archive_appearances(detections)
                        logging.info(f"Archived {len(detections)} detections to history database")
                    except Exception as e:
                        logging.error(f"Failed to archive detections: {e}")

            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}", exc_info=True)

            # Sleep for the configured interval
            time.sleep(check_interval)

if __name__ == "__main__":
    app = CYTMonitorApp()
    if app.initialize():
        app.run()
    else:
        logging.critical("Application failed to initialize. Exiting.")
        sys.exit(1)
