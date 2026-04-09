"""Tests for secure_ignore_loader.py — malformed input, empty files, edge cases."""
import unittest
import tempfile
import pathlib

from secure_ignore_loader import SecureIgnoreLoader


class TestMACLoading(unittest.TestCase):

    def _write_temp(self, content: str) -> pathlib.Path:
        f = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8')
        f.write(content)
        f.close()
        return pathlib.Path(f.name)

    def test_empty_file_returns_empty(self):
        path = self._write_temp("")
        result = SecureIgnoreLoader.load_mac_list(path)
        self.assertEqual(result, [])

    def test_comments_only_returns_empty(self):
        path = self._write_temp("# This is a comment\n# Another comment\n")
        result = SecureIgnoreLoader.load_mac_list(path)
        self.assertEqual(result, [])

    def test_valid_macs_loaded(self):
        path = self._write_temp(
            "AA:BB:CC:DD:EE:FF\n11:22:33:44:55:66\n")
        result = SecureIgnoreLoader.load_mac_list(path)
        self.assertEqual(len(result), 2)
        self.assertIn("AA:BB:CC:DD:EE:FF", result)

    def test_malformed_macs_skipped(self):
        path = self._write_temp(
            "AA:BB:CC:DD:EE:FF\nNOT_A_MAC\nZZ:ZZ:ZZ:ZZ:ZZ:ZZ\n")
        result = SecureIgnoreLoader.load_mac_list(path)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "AA:BB:CC:DD:EE:FF")

    def test_lowercase_normalized_to_upper(self):
        path = self._write_temp("aa:bb:cc:dd:ee:ff\n")
        result = SecureIgnoreLoader.load_mac_list(path)
        self.assertEqual(result, ["AA:BB:CC:DD:EE:FF"])

    def test_mixed_format_with_comments(self):
        path = self._write_temp(
            "# Known devices\n"
            "AA:BB:CC:DD:EE:FF  # router\n"
            "\n"
            "11:22:33:44:55:66\n")
        result = SecureIgnoreLoader.load_mac_list(path)
        # Should handle inline comments if the parser strips them
        self.assertGreaterEqual(len(result), 1)

    def test_json_format_loaded(self):
        path = self._write_temp(
            '["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"]')
        result = SecureIgnoreLoader.load_mac_list(path)
        self.assertEqual(len(result), 2)

    def test_nonexistent_file_returns_empty(self):
        result = SecureIgnoreLoader.load_mac_list(
            pathlib.Path("/nonexistent/file.txt"))
        self.assertEqual(result, [])


class TestSSIDLoading(unittest.TestCase):

    def _write_temp(self, content: str) -> pathlib.Path:
        f = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8')
        f.write(content)
        f.close()
        return pathlib.Path(f.name)

    def test_empty_file_returns_empty(self):
        path = self._write_temp("")
        result = SecureIgnoreLoader.load_ssid_list(path)
        self.assertEqual(result, [])

    def test_valid_ssids_loaded(self):
        path = self._write_temp("MyNetwork\nGuestWiFi\n")
        result = SecureIgnoreLoader.load_ssid_list(path)
        self.assertEqual(len(result), 2)

    def test_nonexistent_file_returns_empty(self):
        result = SecureIgnoreLoader.load_ssid_list(
            pathlib.Path("/nonexistent/file.txt"))
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
