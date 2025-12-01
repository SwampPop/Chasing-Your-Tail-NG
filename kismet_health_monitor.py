#!/usr/bin/env python3
"""
Kismet Health Monitor
Monitors Kismet process and database activity to detect failures and optionally auto-restart.
"""
import os
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class KismetHealthMonitor:
    """
    Monitors Kismet process health and database activity.

    Health checks:
    1. Process check - Is Kismet running?
    2. Database check - Is database file being updated?
    3. Data freshness - Are new packets being captured?
    """

    def __init__(self,
                 db_path_pattern: str,
                 startup_script: str = "./start_kismet_clean.sh",
                 max_restart_attempts: int = 3,
                 data_freshness_threshold_minutes: int = 5,
                 auto_restart: bool = False):
        """
        Initialize Kismet health monitor.

        Args:
            db_path_pattern: Glob pattern for Kismet database files
            startup_script: Path to Kismet startup script
            max_restart_attempts: Max auto-restart attempts before giving up
            data_freshness_threshold_minutes: Alert if no new data in X minutes
            auto_restart: Enable automatic Kismet restart on failure
        """
        self.db_path_pattern = db_path_pattern
        self.startup_script = startup_script
        self.max_restart_attempts = max_restart_attempts
        self.data_freshness_threshold = timedelta(minutes=data_freshness_threshold_minutes)
        self.auto_restart = auto_restart

        # Health state tracking
        self.restart_count = 0
        self.last_restart_time: Optional[float] = None
        self.last_db_mtime: Optional[float] = None
        self.last_health_check: Optional[float] = None
        self.consecutive_failures = 0

        # Restart cooldown (prevent restart loops)
        self.restart_cooldown_seconds = 60  # Don't restart more than once per minute

    def check_process_running(self) -> bool:
        """
        Check if Kismet process is running.

        Returns:
            True if Kismet process found, False otherwise
        """
        try:
            result = subprocess.run(
                ['pgrep', '-x', 'kismet'],
                capture_output=True,
                text=True,
                timeout=5
            )
            is_running = result.returncode == 0

            if is_running:
                pids = result.stdout.strip().split('\n')
                logger.debug(f"Kismet process(es) found: {pids}")
            else:
                logger.warning("Kismet process not found!")

            return is_running

        except subprocess.TimeoutExpired:
            logger.error("Process check timed out")
            return False
        except Exception as e:
            logger.error(f"Error checking Kismet process: {e}")
            return False

    def check_database_exists(self) -> tuple[bool, Optional[str]]:
        """
        Check if Kismet database exists and is accessible.

        Returns:
            Tuple of (exists, db_path)
        """
        import glob

        try:
            # Handle directory pattern
            if os.path.isdir(self.db_path_pattern):
                pattern = os.path.join(self.db_path_pattern, "*.kismet")
            else:
                pattern = self.db_path_pattern

            db_files = glob.glob(pattern)

            if not db_files:
                logger.warning(f"No Kismet database found matching: {pattern}")
                return (False, None)

            # Get most recent database
            latest_db = max(db_files, key=os.path.getctime)
            logger.debug(f"Found Kismet database: {latest_db}")

            return (True, latest_db)

        except Exception as e:
            logger.error(f"Error checking database: {e}")
            return (False, None)

    def check_database_updates(self, db_path: str) -> bool:
        """
        Check if database is being actively updated.

        Args:
            db_path: Path to Kismet database file

        Returns:
            True if database modified recently, False otherwise
        """
        try:
            current_mtime = os.path.getmtime(db_path)

            # First check - just record the modification time
            if self.last_db_mtime is None:
                self.last_db_mtime = current_mtime
                logger.info("Database modification time recorded")
                return True

            # Check if database has been modified since last check
            if current_mtime > self.last_db_mtime:
                logger.debug(f"Database updated: {datetime.fromtimestamp(current_mtime)}")
                self.last_db_mtime = current_mtime
                return True
            else:
                time_since_update = time.time() - current_mtime
                logger.warning(f"Database not updated in {time_since_update:.0f} seconds")
                return False

        except Exception as e:
            logger.error(f"Error checking database updates: {e}")
            return False

    def check_data_freshness(self, db_path: str) -> bool:
        """
        Check if Kismet is capturing fresh data by querying database.

        Args:
            db_path: Path to Kismet database file

        Returns:
            True if recent data found, False otherwise
        """
        try:
            import sqlite3

            with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
                cursor = conn.cursor()

                # Get timestamp of most recent device
                cursor.execute("SELECT MAX(last_time) FROM devices")
                result = cursor.fetchone()

                if not result or result[0] is None:
                    logger.warning("No devices found in database")
                    return False

                last_device_time = result[0]
                time_since_last_device = time.time() - last_device_time

                if time_since_last_device > self.data_freshness_threshold.total_seconds():
                    logger.warning(
                        f"No new devices in {time_since_last_device/60:.1f} minutes "
                        f"(threshold: {self.data_freshness_threshold.total_seconds()/60:.1f} min)"
                    )
                    return False
                else:
                    logger.debug(f"Fresh data found (age: {time_since_last_device:.0f}s)")
                    return True

        except Exception as e:
            logger.error(f"Error checking data freshness: {e}")
            return False

    def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of Kismet.

        Returns:
            Dictionary with health check results:
            {
                'healthy': bool,
                'process_running': bool,
                'database_exists': bool,
                'database_updating': bool,
                'data_fresh': bool,
                'issues': List[str]
            }
        """
        self.last_health_check = time.time()

        health_status = {
            'healthy': True,
            'process_running': False,
            'database_exists': False,
            'database_updating': False,
            'data_fresh': False,
            'issues': []
        }

        # 1. Check if process is running
        health_status['process_running'] = self.check_process_running()
        if not health_status['process_running']:
            health_status['healthy'] = False
            health_status['issues'].append("Kismet process not running")
            return health_status  # No point checking further if process is dead

        # 2. Check if database exists
        db_exists, db_path = self.check_database_exists()
        health_status['database_exists'] = db_exists
        if not db_exists:
            health_status['healthy'] = False
            health_status['issues'].append("Kismet database not found")
            return health_status

        # 3. Check if database is being updated
        health_status['database_updating'] = self.check_database_updates(db_path)
        if not health_status['database_updating']:
            health_status['issues'].append("Database not being updated")
            # Don't mark unhealthy yet - might be no activity

        # 4. Check data freshness
        health_status['data_fresh'] = self.check_data_freshness(db_path)
        if not health_status['data_fresh']:
            health_status['healthy'] = False
            health_status['issues'].append(
                f"No fresh data in {self.data_freshness_threshold.total_seconds()/60:.0f} minutes"
            )

        # Update consecutive failure counter
        if not health_status['healthy']:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0

        return health_status

    def restart_kismet(self, interface: str = "wlan0mon") -> bool:
        """
        Attempt to restart Kismet using startup script.

        Args:
            interface: Wireless interface to use (default: wlan0mon)

        Returns:
            True if restart initiated successfully, False otherwise
        """
        # Check restart cooldown
        if self.last_restart_time:
            time_since_restart = time.time() - self.last_restart_time
            if time_since_restart < self.restart_cooldown_seconds:
                logger.warning(
                    f"Restart cooldown active ({time_since_restart:.0f}s / "
                    f"{self.restart_cooldown_seconds}s)"
                )
                return False

        # Check max restart attempts
        if self.restart_count >= self.max_restart_attempts:
            logger.error(
                f"Max restart attempts reached ({self.restart_count}/{self.max_restart_attempts}). "
                "Manual intervention required."
            )
            return False

        try:
            logger.warning(f"Attempting to restart Kismet (attempt {self.restart_count + 1})")

            # Kill existing Kismet processes
            logger.info("Killing existing Kismet processes...")
            subprocess.run(['sudo', 'pkill', '-9', 'kismet'], timeout=5)
            time.sleep(2)  # Wait for processes to die

            # Start Kismet using startup script
            if not os.path.exists(self.startup_script):
                logger.error(f"Startup script not found: {self.startup_script}")
                return False

            logger.info(f"Starting Kismet with: {self.startup_script} {interface}")
            subprocess.Popen(
                ['sudo', self.startup_script, interface],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.restart_count += 1
            self.last_restart_time = time.time()

            logger.info("Kismet restart initiated. Waiting 10s for startup...")
            time.sleep(10)  # Give Kismet time to start

            # Verify restart was successful
            if self.check_process_running():
                logger.info("Kismet restart successful!")
                return True
            else:
                logger.error("Kismet restart failed - process not running")
                return False

        except Exception as e:
            logger.error(f"Error restarting Kismet: {e}")
            return False

    def monitor_and_recover(self, interface: str = "wlan0mon") -> Dict[str, Any]:
        """
        Perform health check and auto-recover if enabled.

        Args:
            interface: Wireless interface for restart attempts

        Returns:
            Health status dictionary with recovery actions taken
        """
        health_status = self.perform_health_check()
        health_status['recovery_attempted'] = False
        health_status['recovery_successful'] = False

        # If unhealthy and auto-restart enabled, attempt recovery
        if not health_status['healthy'] and self.auto_restart:
            logger.warning(
                f"Kismet unhealthy (consecutive failures: {self.consecutive_failures}). "
                "Attempting auto-recovery..."
            )

            health_status['recovery_attempted'] = True
            recovery_success = self.restart_kismet(interface)
            health_status['recovery_successful'] = recovery_success

            if recovery_success:
                # Reset failure counter on successful recovery
                self.consecutive_failures = 0

        return health_status

    def reset_restart_counter(self):
        """Reset restart counter (call after manual fix)."""
        self.restart_count = 0
        logger.info("Restart counter reset")

    def get_status_summary(self) -> str:
        """Get human-readable status summary."""
        if self.last_health_check is None:
            return "No health checks performed yet"

        time_since_check = time.time() - self.last_health_check

        summary = [
            f"Last check: {time_since_check:.0f}s ago",
            f"Consecutive failures: {self.consecutive_failures}",
            f"Restart count: {self.restart_count}/{self.max_restart_attempts}",
            f"Auto-restart: {'enabled' if self.auto_restart else 'disabled'}"
        ]

        return " | ".join(summary)


if __name__ == "__main__":
    """Test the health monitor"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("=" * 70)
    print("Kismet Health Monitor Test")
    print("=" * 70)

    # Test with current configuration
    monitor = KismetHealthMonitor(
        db_path_pattern="/tmp/kismet",  # Adjust to your path
        auto_restart=False,  # Don't auto-restart in test mode
        data_freshness_threshold_minutes=5
    )

    print("\nPerforming health check...")
    health = monitor.perform_health_check()

    print(f"\nHealth Status: {'✓ HEALTHY' if health['healthy'] else '✗ UNHEALTHY'}")
    print(f"Process running: {health['process_running']}")
    print(f"Database exists: {health['database_exists']}")
    print(f"Database updating: {health['database_updating']}")
    print(f"Data fresh: {health['data_fresh']}")

    if health['issues']:
        print(f"\nIssues detected:")
        for issue in health['issues']:
            print(f"  - {issue}")

    print(f"\n{monitor.get_status_summary()}")
    print("=" * 70)
