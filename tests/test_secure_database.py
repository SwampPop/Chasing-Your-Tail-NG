import unittest
import sqlite3
import time
from secure_database import SecureKismetDB


class TestSecureKismetDB(unittest.TestCase):
    """
    Test suite for the SecureKismetDB class.
    """

    def setUp(self):
        """
        Set up a temporary in-memory database for testing.
        """
        self.db_path = ":memory:"
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        # Create the necessary tables
        self.cursor.execute("""
            CREATE TABLE devices (
                devmac TEXT,
                type TEXT,
                device TEXT,
                last_time REAL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE packets (
                sourcemac TEXT,
                datasource TEXT,
                ts_sec REAL
            )
        """)

        # Add some test data
        self.now = time.time()
        self.cursor.execute("INSERT INTO devices VALUES (?, ?, ?, ?)",
                            ('AA:AA:AA:AA:AA:AA', 'Wi-Fi Client', '{}', self.now - 10))
        self.cursor.execute("INSERT INTO devices VALUES (?, ?, ?, ?)",
                            ('BB:BB:BB:BB:BB:BB', 'Wi-Fi Client', '{}', self.now - 20))
        self.cursor.execute("INSERT INTO devices VALUES (?, ?, ?, ?)",
                            ('CC:CC:CC:CC:CC:CC', 'Wi-Fi AP', '{"dot11.device": {"dot11.device.last_probed_ssid_record": {"dot11.probedssid.ssid": "test_ssid"}}}', self.now - 30))
        self.cursor.execute("INSERT INTO devices VALUES (?, ?, ?, ?)",
                            ('DD:DD:DD:DD:DD:DD', 'UAV', '{}', self.now - 40))
        self.conn.commit()

    def tearDown(self):
        """
        Close the database connection after each test.
        """
        self.conn.close()

    def test_get_devices_by_time_range(self):
        """
        Test the get_devices_by_time_range method.
        """
        with SecureKismetDB(self.db_path) as db:
            devices = db.get_devices_by_time_range(self.now - 25)
            self.assertEqual(len(devices), 2)
            macs = {d['mac'] for d in devices}
            self.assertIn('AA:AA:AA:AA:AA:AA', macs)
            self.assertIn('BB:BB:BB:BB:BB:BB', macs)

    def test_get_mac_addresses_by_time_range(self):
        """
        Test the get_mac_addresses_by_time_range method.
        """
        with SecureKismetDB(self.db_path) as db:
            macs = db.get_mac_addresses_by_time_range(self.now - 25)
            self.assertEqual(len(macs), 2)
            self.assertIn('AA:AA:AA:AA:AA:AA', macs)
            self.assertIn('BB:BB:BB:BB:BB:BB', macs)

    def test_get_probe_requests_by_time_range(self):
        """
        Test the get_probe_requests_by_time_range method.
        """
        with SecureKismetDB(self.db_path) as db:
            probes = db.get_probe_requests_by_time_range(self.now - 35)
            self.assertEqual(len(probes), 1)
            self.assertEqual(probes[0]['ssid'], 'test_ssid')

    def test_get_chase_targets_secure(self):
        """
        Test the get_chase_targets_secure method.
        """
        # Add some packet data
        self.cursor.execute("INSERT INTO packets VALUES (?, ?, ?)",
                            ('AA:AA:AA:AA:AA:AA', 'source1', self.now - 10))
        self.cursor.execute("INSERT INTO packets VALUES (?, ?, ?)",
                            ('AA:AA:AA:AA:AA:AA', 'source2', self.now - 10))
        self.conn.commit()

        with SecureKismetDB(self.db_path) as db:
            targets = db.get_chase_targets_secure(60, 2)
            self.assertEqual(len(targets), 1)
            self.assertEqual(targets[0]['devmac'], 'AA:AA:AA:AA:AA:AA')

    def test_check_watchlist_macs_secure(self):
        """
        Test the check_watchlist_macs_secure method.
        """
        with SecureKismetDB(self.db_path) as db:
            watchlist = ['AA:AA:AA:AA:AA:AA', 'EE:EE:EE:EE:EE:EE']
            seen = db.check_watchlist_macs_secure(watchlist, 60)
            self.assertEqual(len(seen), 1)
            self.assertIn('AA:AA:AA:AA:AA:AA', seen)

    def test_check_for_drones_secure(self):
        """
        Test the check_for_drones_secure method.
        """
        with SecureKismetDB(self.db_path) as db:
            drones = db.check_for_drones_secure(60)
            self.assertEqual(len(drones), 1)
            self.assertEqual(drones[0]['devmac'], 'DD:DD:DD:DD:DD:DD')


if __name__ == '__main__':
    unittest.main()
