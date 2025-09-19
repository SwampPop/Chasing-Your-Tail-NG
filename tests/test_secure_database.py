import unittest
import time
from secure_database import SecureTimeWindows

class TestSecureTimeWindows(unittest.TestCase):
    """
    Test suite for the SecureTimeWindows class.
    """

    def setUp(self):
        """
        This method is called before each test. It sets up a sample
        config that we can use in our tests.
        """
        self.sample_config = {
            'timing': {
                'time_windows': {
                    'recent': 5,
                    'medium': 10,
                    'old': 15
                }
            }
        }
        self.time_manager = SecureTimeWindows(self.sample_config)

    def test_get_time_boundaries_creates_correct_keys(self):
        """
        Tests if the get_time_boundaries method returns a dictionary
        with all the expected time window keys.
        """
        # ACT: Run the method we want to test
        boundaries = self.time_manager.get_time_boundaries()
        
        # ASSERT: Check that the results are what we expect
        self.assertIn('recent_time', boundaries)
        self.assertIn('medium_time', boundaries)
        self.assertIn('old_time', boundaries)
        self.assertIn('current_time', boundaries)

    def test_get_time_boundaries_calculates_correctly(self):
        """
        Tests if the time boundaries are calculated in the correct
        relative order (e.g., 'medium' is an earlier time than 'recent').
        """
        # ACT: Run the method
        boundaries = self.time_manager.get_time_boundaries()
        
        # ASSERT: Verify the logic. The timestamp for "old" (15 mins ago)
        # must be smaller than the timestamp for "recent" (5 mins ago).
        self.assertLess(boundaries['old_time'], boundaries['medium_time'])
        self.assertLess(boundaries['medium_time'], boundaries['recent_time'])
        self.assertLess(boundaries['recent_time'], boundaries['current_time'])

    def test_filter_devices_by_ignore_list(self):
        """
        Tests the ignore list filtering logic.
        """
        # ARRANGE: Set up the data for this specific test
        devices = ['AA:AA:AA:AA:AA:AA', 'BB:BB:BB:BB:BB:BB', 'CC:CC:CC:CC:CC:CC']
        ignore_list = ['BB:BB:BB:BB:BB:BB', 'DD:DD:DD:DD:DD:DD']
        
        # ACT: Run the method
        filtered_devices = self.time_manager.filter_devices_by_ignore_list(devices, ignore_list)
        
        # ASSERT: Check the result
        self.assertEqual(len(filtered_devices), 2)
        self.assertIn('AA:AA:AA:AA:AA:AA', filtered_devices)
        self.assertIn('CC:CC:CC:CC:CC:CC', filtered_devices)
        self.assertNotIn('BB:BB:BB:BB:BB:BB', filtered_devices)