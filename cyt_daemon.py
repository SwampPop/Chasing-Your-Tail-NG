#!/usr/bin/env python3
"""
CYT Daemon - Unified Orchestration System
Manages all CYT components: Kismet, Monitoring, API Server

Usage:
    sudo python3 cyt_daemon.py start
    sudo python3 cyt_daemon.py stop
    sudo python3 cyt_daemon.py restart
    sudo python3 cyt_daemon.py status
"""
import os
import sys
import time
import signal
import subprocess
import json
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

# Configuration
DAEMON_NAME = "cyt_daemon"
PID_DIR = Path("./run")
LOG_DIR = Path("./logs")
CONFIG_FILE = "config.json"

# Process tracking
PROCESSES = {
    'kismet': {
        'name': 'Kismet',
        'pid_file': PID_DIR / 'kismet.pid',
        'log_file': LOG_DIR / 'kismet.log',
        'required': True,
        'start_command': None,  # Set from config
        'health_check': 'pgrep -x kismet',
        'startup_delay': 10  # Wait 10s after start
    },
    'cyt_monitor': {
        'name': 'CYT Monitor',
        'pid_file': PID_DIR / 'cyt_monitor.pid',
        'log_file': LOG_DIR / 'cyt_monitor.log',
        'required': True,
        'start_command': ['python3', 'chasing_your_tail.py'],
        'health_check': None,  # Check PID file
        'startup_delay': 3
    },
    'api_server': {
        'name': 'API Server',
        'pid_file': PID_DIR / 'api_server.pid',
        'log_file': LOG_DIR / 'api_server.log',
        'required': False,  # Optional component
        'start_command': ['python3', 'api_server.py'],
        'health_check': None,
        'startup_delay': 2
    }
}

# ANSI Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class CYTDaemon:
    """Unified daemon for managing all CYT components."""

    def __init__(self):
        """Initialize daemon."""
        self.config = self.load_config()
        self.setup_directories()
        self.setup_logging()
        self.running_processes: Dict[str, subprocess.Popen] = {}

        # Configure Kismet startup from config
        kismet_config = self.config.get('kismet_health', {})
        startup_script = kismet_config.get('startup_script', './start_kismet_clean.sh')
        interface = kismet_config.get('interface', 'wlan0mon')
        PROCESSES['kismet']['start_command'] = ['sudo', startup_script, interface]

    def load_config(self) -> Dict:
        """Load configuration from config.json."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"{RED}✗ Failed to load config.json: {e}{RESET}")
            sys.exit(1)

    def setup_directories(self):
        """Create necessary directories."""
        PID_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    def setup_logging(self):
        """Setup daemon logging."""
        log_file = LOG_DIR / f'{DAEMON_NAME}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(DAEMON_NAME)

    def write_pid_file(self, process_name: str, pid: int):
        """Write PID to file."""
        pid_file = PROCESSES[process_name]['pid_file']
        try:
            pid_file.write_text(str(pid))
            self.logger.debug(f"Wrote PID {pid} to {pid_file}")
        except Exception as e:
            self.logger.error(f"Failed to write PID file for {process_name}: {e}")

    def read_pid_file(self, process_name: str) -> Optional[int]:
        """Read PID from file."""
        pid_file = PROCESSES[process_name]['pid_file']
        try:
            if pid_file.exists():
                pid = int(pid_file.read_text().strip())
                return pid
        except Exception as e:
            self.logger.debug(f"Failed to read PID file for {process_name}: {e}")
        return None

    def remove_pid_file(self, process_name: str):
        """Remove PID file."""
        pid_file = PROCESSES[process_name]['pid_file']
        try:
            if pid_file.exists():
                pid_file.unlink()
                self.logger.debug(f"Removed PID file: {pid_file}")
        except Exception as e:
            self.logger.warning(f"Failed to remove PID file for {process_name}: {e}")

    def is_process_running(self, process_name: str) -> bool:
        """Check if process is running."""
        # Check if we're tracking it
        if process_name in self.running_processes:
            proc = self.running_processes[process_name]
            if proc.poll() is None:  # Still running
                return True

        # Check PID file
        pid = self.read_pid_file(process_name)
        if pid:
            try:
                # Send signal 0 to check if process exists
                os.kill(pid, 0)
                return True
            except OSError:
                # Process doesn't exist, clean up stale PID file
                self.remove_pid_file(process_name)
                return False

        # Use health check command if available
        health_check = PROCESSES[process_name].get('health_check')
        if health_check:
            try:
                result = subprocess.run(
                    health_check,
                    shell=True,
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            except Exception:
                return False

        return False

    def start_process(self, process_name: str) -> bool:
        """Start a process."""
        process_info = PROCESSES[process_name]
        name = process_info['name']

        # Check if already running
        if self.is_process_running(process_name):
            self.logger.warning(f"{name} is already running")
            print(f"{YELLOW}⚠ {name} is already running{RESET}")
            return True

        # Get start command
        start_cmd = process_info['start_command']
        if not start_cmd:
            self.logger.error(f"No start command configured for {name}")
            return False

        self.logger.info(f"Starting {name}...")
        print(f"{BLUE}▶ Starting {name}...{RESET}")

        try:
            # Open log file for output
            log_file = process_info['log_file']
            log_handle = open(log_file, 'a', buffering=1)

            # Start process
            if process_name == 'kismet':
                # Kismet needs special handling (sudo script)
                proc = subprocess.Popen(
                    start_cmd,
                    stdout=log_handle,
                    stderr=log_handle,
                    start_new_session=True  # Detach from parent
                )
                # For Kismet, we don't track the script PID, just verify it started
                time.sleep(process_info['startup_delay'])

                if self.is_process_running('kismet'):
                    # Find actual Kismet PIDs
                    result = subprocess.run(
                        ['pgrep', '-x', 'kismet'],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        pids = result.stdout.strip().split('\n')
                        main_pid = int(pids[0])  # Use first PID
                        self.write_pid_file('kismet', main_pid)
                        self.logger.info(f"{name} started successfully (PID: {main_pid})")
                        print(f"{GREEN}✓ {name} started (PID: {main_pid}){RESET}")
                        return True
                else:
                    self.logger.error(f"{name} failed to start")
                    print(f"{RED}✗ {name} failed to start{RESET}")
                    return False

            else:
                # Regular Python processes
                proc = subprocess.Popen(
                    start_cmd,
                    stdout=log_handle,
                    stderr=log_handle,
                    start_new_session=True
                )

                # Track process
                self.running_processes[process_name] = proc
                self.write_pid_file(process_name, proc.pid)

                # Wait for startup
                time.sleep(process_info['startup_delay'])

                # Verify it's still running
                if proc.poll() is None:
                    self.logger.info(f"{name} started successfully (PID: {proc.pid})")
                    print(f"{GREEN}✓ {name} started (PID: {proc.pid}){RESET}")
                    return True
                else:
                    self.logger.error(f"{name} exited immediately (return code: {proc.returncode})")
                    print(f"{RED}✗ {name} failed to start (exited with code {proc.returncode}){RESET}")
                    self.remove_pid_file(process_name)
                    return False

        except Exception as e:
            self.logger.error(f"Failed to start {name}: {e}")
            print(f"{RED}✗ Failed to start {name}: {e}{RESET}")
            return False

    def stop_process(self, process_name: str, timeout: int = 30) -> bool:
        """Stop a process gracefully."""
        process_info = PROCESSES[process_name]
        name = process_info['name']

        # Check if running
        if not self.is_process_running(process_name):
            self.logger.info(f"{name} is not running")
            print(f"{YELLOW}⚠ {name} is not running{RESET}")
            self.remove_pid_file(process_name)
            return True

        self.logger.info(f"Stopping {name}...")
        print(f"{BLUE}◼ Stopping {name}...{RESET}")

        # Get PID
        pid = self.read_pid_file(process_name)
        if not pid:
            # For Kismet, find PID via pgrep
            if process_name == 'kismet':
                result = subprocess.run(
                    ['pgrep', '-x', 'kismet'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    pid = int(pids[0])

        if not pid:
            self.logger.warning(f"Could not find PID for {name}")
            return False

        try:
            # Send SIGTERM for graceful shutdown
            self.logger.debug(f"Sending SIGTERM to {name} (PID: {pid})")
            os.kill(pid, signal.SIGTERM)

            # Wait for process to exit
            start_time = time.time()
            while time.time() - start_time < timeout:
                if not self.is_process_running(process_name):
                    self.logger.info(f"{name} stopped gracefully")
                    print(f"{GREEN}✓ {name} stopped{RESET}")
                    self.remove_pid_file(process_name)

                    # Remove from tracking
                    if process_name in self.running_processes:
                        del self.running_processes[process_name]

                    return True
                time.sleep(0.5)

            # Process didn't exit, force kill
            self.logger.warning(f"{name} did not exit gracefully, sending SIGKILL")
            print(f"{YELLOW}⚠ {name} not responding, forcing shutdown...{RESET}")

            # For Kismet, kill all instances
            if process_name == 'kismet':
                subprocess.run(['sudo', 'pkill', '-9', 'kismet'], timeout=5)
            else:
                os.kill(pid, signal.SIGKILL)

            time.sleep(1)

            self.logger.info(f"{name} stopped (forced)")
            print(f"{GREEN}✓ {name} stopped (forced){RESET}")
            self.remove_pid_file(process_name)

            if process_name in self.running_processes:
                del self.running_processes[process_name]

            return True

        except ProcessLookupError:
            self.logger.info(f"{name} already stopped")
            self.remove_pid_file(process_name)
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop {name}: {e}")
            print(f"{RED}✗ Failed to stop {name}: {e}{RESET}")
            return False

    def start_all(self) -> bool:
        """Start all CYT components in correct order."""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Starting CYT System{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")

        # Start in dependency order
        start_order = ['kismet', 'cyt_monitor', 'api_server']

        all_started = True
        for process_name in start_order:
            process_info = PROCESSES[process_name]

            # Skip optional processes if not configured
            if not process_info['required']:
                # Check if API server should be started (CYT_API_KEY set)
                if process_name == 'api_server':
                    if not os.getenv('CYT_API_KEY'):
                        self.logger.info("Skipping API server (CYT_API_KEY not set)")
                        print(f"{YELLOW}⊘ Skipping API Server (CYT_API_KEY not configured){RESET}")
                        continue

            success = self.start_process(process_name)

            if not success:
                if process_info['required']:
                    all_started = False
                    print(f"\n{RED}✗ Failed to start required component: {process_info['name']}{RESET}")
                    print(f"{RED}✗ Aborting startup{RESET}\n")
                    # Stop what we've started
                    self.stop_all()
                    return False

        if all_started:
            print(f"\n{GREEN}{'='*60}{RESET}")
            print(f"{GREEN}✓ CYT System Started Successfully{RESET}")
            print(f"{GREEN}{'='*60}{RESET}\n")
            print(f"Logs: {LOG_DIR}/")
            print(f"PIDs: {PID_DIR}/")
            print(f"\nMonitor logs: tail -f {LOG_DIR}/cyt_monitor.log")
            print(f"Stop system: sudo python3 cyt_daemon.py stop\n")
            return True
        else:
            return False

    def stop_all(self) -> bool:
        """Stop all CYT components in reverse order."""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Stopping CYT System{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")

        # Stop in reverse dependency order
        stop_order = ['api_server', 'cyt_monitor', 'kismet']

        all_stopped = True
        for process_name in stop_order:
            if self.is_process_running(process_name):
                success = self.stop_process(process_name)
                if not success:
                    all_stopped = False

        if all_stopped:
            print(f"\n{GREEN}{'='*60}{RESET}")
            print(f"{GREEN}✓ CYT System Stopped{RESET}")
            print(f"{GREEN}{'='*60}{RESET}\n")
            return True
        else:
            print(f"\n{YELLOW}⚠ Some components may still be running{RESET}\n")
            return False

    def restart_all(self) -> bool:
        """Restart all CYT components."""
        print(f"\n{BLUE}Restarting CYT System...{RESET}\n")
        self.stop_all()
        time.sleep(2)
        return self.start_all()

    def status(self):
        """Show status of all components."""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}CYT System Status{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")

        for process_name, process_info in PROCESSES.items():
            name = process_info['name']
            is_running = self.is_process_running(process_name)
            pid = self.read_pid_file(process_name)

            if is_running:
                pid_str = f"(PID: {pid})" if pid else ""
                print(f"{GREEN}✓ {name:<20} RUNNING {pid_str}{RESET}")
            else:
                required_str = "(required)" if process_info['required'] else "(optional)"
                print(f"{RED}✗ {name:<20} STOPPED {required_str}{RESET}")

        print(f"\n{BLUE}{'='*60}{RESET}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='CYT Daemon - Unified system orchestration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo python3 cyt_daemon.py start     Start all CYT components
  sudo python3 cyt_daemon.py stop      Stop all CYT components
  sudo python3 cyt_daemon.py restart   Restart all CYT components
  sudo python3 cyt_daemon.py status    Show component status

Components:
  - Kismet (wireless packet capture)
  - CYT Monitor (threat detection)
  - API Server (REST API - optional)

Notes:
  - Requires sudo for Kismet management
  - Logs written to ./logs/
  - PID files in ./run/
        """
    )
    parser.add_argument(
        'action',
        choices=['start', 'stop', 'restart', 'status'],
        help='Action to perform'
    )

    args = parser.parse_args()

    # Create daemon
    daemon = CYTDaemon()

    # Execute action
    if args.action == 'start':
        success = daemon.start_all()
        sys.exit(0 if success else 1)
    elif args.action == 'stop':
        success = daemon.stop_all()
        sys.exit(0 if success else 1)
    elif args.action == 'restart':
        success = daemon.restart_all()
        sys.exit(0 if success else 1)
    elif args.action == 'status':
        daemon.status()
        sys.exit(0)


if __name__ == '__main__':
    main()
