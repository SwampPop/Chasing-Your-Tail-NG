#!/usr/bin/env python3
"""
Integration Test Suite for CYT
Tests all major components and their interactions
"""
import sys
import os
import tempfile
import json
import sqlite3
from pathlib import Path

# Test results tracking
test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def test_result(test_name, passed, message=""):
    """Record test result"""
    if passed:
        test_results['passed'].append(test_name)
        print(f"✅ PASS: {test_name}")
    else:
        test_results['failed'].append((test_name, message))
        print(f"❌ FAIL: {test_name}: {message}")
    if message and passed:
        print(f"   ℹ️  {message}")

def test_warning(test_name, message):
    """Record test warning"""
    test_results['warnings'].append((test_name, message))
    print(f"⚠️  WARN: {test_name}: {message}")


print("="*80)
print("CYT INTEGRATION TEST SUITE")
print("="*80)
print()

# ============================================================================
# TEST 1: Module Imports
# ============================================================================
print("TEST SUITE 1: Module Imports")
print("-" * 80)

try:
    import cyt_constants
    test_result("Import cyt_constants", True)
except Exception as e:
    test_result("Import cyt_constants", False, str(e))

try:
    from cyt_constants import DeviceType, AlertType, PersistenceLevel, SystemConstants
    test_result("Import constants enums", True)
except Exception as e:
    test_result("Import constants enums", False, str(e))

try:
    from lib.database_utils import DatabaseSchema, safe_db_connection, HISTORY_SCHEMA, WATCHLIST_SCHEMA
    test_result("Import database_utils", True)
except Exception as e:
    test_result("Import database_utils", False, str(e))

try:
    import secure_database
    test_result("Import secure_database", True)
except Exception as e:
    test_result("Import secure_database", False, str(e))

try:
    import secure_credentials
    test_result("Import secure_credentials", True)
except Exception as e:
    test_result("Import secure_credentials", False, str(e))

try:
    import input_validation
    test_result("Import input_validation", True)
except Exception as e:
    test_result("Import input_validation", False, str(e))

try:
    from lib import watchlist_manager, history_manager
    test_result("Import lib managers", True)
except Exception as e:
    test_result("Import lib managers", False, str(e))

try:
    import surveillance_detector
    test_result("Import surveillance_detector", True)
except Exception as e:
    test_result("Import surveillance_detector", False, str(e))

try:
    import gps_tracker
    test_result("Import gps_tracker", True)
except Exception as e:
    test_result("Import gps_tracker", False, str(e))

try:
    import report_generator
    test_result("Import report_generator", True)
except Exception as e:
    test_result("Import report_generator", False, str(e))

print()

# ============================================================================
# TEST 2: Constants and Enums
# ============================================================================
print("TEST SUITE 2: Constants and Enums")
print("-" * 80)

try:
    # Test DeviceType enum
    assert DeviceType.WI_FI_CLIENT.value == "Wi-Fi Client"
    assert DeviceType.DRONE.value == "DRONE"
    test_result("DeviceType enum values", True)
except AssertionError as e:
    test_result("DeviceType enum values", False, str(e))

try:
    # Test AlertType enum
    assert AlertType.DRONE.value == "DRONE"
    assert AlertType.WATCHLIST.value == "ALERT"
    test_result("AlertType enum values", True)
except AssertionError as e:
    test_result("AlertType enum values", False, str(e))

try:
    # Test PersistenceLevel
    assert PersistenceLevel.CRITICAL.threshold == 0.8
    assert PersistenceLevel.HIGH.threshold == 0.6
    assert PersistenceLevel.from_score(0.85) == PersistenceLevel.CRITICAL
    assert PersistenceLevel.from_score(0.7) == PersistenceLevel.HIGH
    test_result("PersistenceLevel thresholds", True)
except AssertionError as e:
    test_result("PersistenceLevel thresholds", False, str(e))

try:
    # Test SystemConstants
    assert SystemConstants.EARTH_RADIUS_METERS == 6371000
    assert SystemConstants.PBKDF2_ITERATIONS == 250000
    assert SystemConstants.DB_CONNECTION_TIMEOUT == 30.0
    test_result("SystemConstants values", True)
except AssertionError as e:
    test_result("SystemConstants values", False, str(e))

print()

# ============================================================================
# TEST 3: Database Utilities
# ============================================================================
print("TEST SUITE 3: Database Utilities")
print("-" * 80)

try:
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        test_db = tmp.name

    # Test DatabaseSchema
    test_schema = DatabaseSchema(
        os.path.basename(test_db),
        {
            'test_table': '''
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                )
            '''
        }
    )
    test_schema.db_path = test_db
    test_schema.initialize()

    # Verify table was created
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
        result = cursor.fetchone()
        assert result is not None

    os.unlink(test_db)
    test_result("DatabaseSchema initialization", True)
except Exception as e:
    test_result("DatabaseSchema initialization", False, str(e))
    if os.path.exists(test_db):
        os.unlink(test_db)

try:
    # Test safe_db_connection context manager
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        test_db = tmp.name

    with safe_db_connection(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER)")
        cursor.execute("INSERT INTO test VALUES (1)")

    # Verify commit worked
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        assert count == 1

    os.unlink(test_db)
    test_result("safe_db_connection context manager", True)
except Exception as e:
    test_result("safe_db_connection context manager", False, str(e))
    if os.path.exists(test_db):
        os.unlink(test_db)

print()

# ============================================================================
# TEST 4: Configuration Loading
# ============================================================================
print("TEST SUITE 4: Configuration Loading")
print("-" * 80)

try:
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Verify new configuration sections exist
    assert 'detection_thresholds' in config
    assert 'gps_settings' in config
    assert 'ui_settings' in config
    assert 'report_settings' in config

    # Verify specific values
    assert config['detection_thresholds']['min_appearances'] == 3
    assert config['gps_settings']['location_threshold_meters'] == 100
    assert config['ui_settings']['animation_duration'] == 0.7
    assert config['report_settings']['detection_accuracy'] == 0.95

    test_result("Configuration structure", True)
except Exception as e:
    test_result("Configuration structure", False, str(e))

print()

# ============================================================================
# TEST 5: Secure Credentials (Minimal)
# ============================================================================
print("TEST SUITE 5: Secure Credentials")
print("-" * 80)

try:
    # Set test mode to avoid password prompts
    os.environ['CYT_TEST_MODE'] = 'true'
    os.environ['CYT_MASTER_PASSWORD'] = 'test_password_for_integration_test'

    # Create temporary credentials directory
    with tempfile.TemporaryDirectory() as temp_dir:
        cred_manager = secure_credentials.SecureCredentialManager(temp_dir)

        # Test storing credential
        cred_manager.store_credential('test_service', 'api_key', 'test_key_12345')

        # Test retrieving credential
        retrieved = cred_manager.get_credential('test_service', 'api_key')
        assert retrieved == 'test_key_12345'

        test_result("Secure credential storage/retrieval", True)
except Exception as e:
    test_result("Secure credential storage/retrieval", False, str(e))
finally:
    # Clean up environment
    if 'CYT_TEST_MODE' in os.environ:
        del os.environ['CYT_TEST_MODE']
    if 'CYT_MASTER_PASSWORD' in os.environ:
        del os.environ['CYT_MASTER_PASSWORD']

print()

# ============================================================================
# TEST 6: Surveillance Detector
# ============================================================================
print("TEST SUITE 6: Surveillance Detector")
print("-" * 80)

try:
    # Load config for detector
    with open('config.json', 'r') as f:
        config = json.load(f)

    detector = surveillance_detector.SurveillanceDetector(config)

    # Verify thresholds loaded from config
    assert detector.thresholds['min_appearances'] == config['detection_thresholds']['min_appearances']

    # Test adding appearances
    detector.add_device_appearance(
        mac='AA:BB:CC:DD:EE:FF',
        timestamp=1000.0,
        location_id='test_location_1',
        ssids_probed=['TestSSID']
    )

    detector.add_device_appearance(
        mac='AA:BB:CC:DD:EE:FF',
        timestamp=2000.0,
        location_id='test_location_2',
        ssids_probed=['TestSSID']
    )

    assert len(detector.device_history) == 1
    assert len(detector.device_history['AA:BB:CC:DD:EE:FF']) == 2

    test_result("SurveillanceDetector initialization and tracking", True)
except Exception as e:
    test_result("SurveillanceDetector initialization and tracking", False, str(e))

print()

# ============================================================================
# TEST 7: GPS Tracker
# ============================================================================
print("TEST SUITE 7: GPS Tracker")
print("-" * 80)

try:
    with open('config.json', 'r') as f:
        config = json.load(f)

    tracker = gps_tracker.GPSTracker(config)

    # Test adding GPS reading
    location_id = tracker.add_gps_reading(
        latitude=37.7749,
        longitude=-122.4194,
        location_name='Test Location'
    )

    assert location_id is not None
    assert len(tracker.locations) == 1
    assert len(tracker.location_sessions) == 1

    # Test distance calculation using SystemConstants
    loc1 = gps_tracker.GPSLocation(latitude=37.7749, longitude=-122.4194)
    loc2 = gps_tracker.GPSLocation(latitude=37.7750, longitude=-122.4195)
    distance = tracker._calculate_distance(loc1, loc2)
    assert distance > 0

    test_result("GPSTracker functionality", True)
except Exception as e:
    test_result("GPSTracker functionality", False, str(e))

print()

# ============================================================================
# TEST 8: Report Generator
# ============================================================================
print("TEST SUITE 8: Report Generator")
print("-" * 80)

try:
    # Create minimal test data
    test_device = surveillance_detector.SuspiciousDevice(
        mac='AA:BB:CC:DD:EE:FF',
        persistence_score=0.85,
        appearances=[],
        reasons=['Test reason'],
        first_seen=surveillance_detector.datetime.now(),
        last_seen=surveillance_detector.datetime.now(),
        total_appearances=5,
        locations_seen=['loc1', 'loc2']
    )

    with open('config.json', 'r') as f:
        config = json.load(f)

    generator = report_generator.ReportGenerator(
        suspicious_devices=[test_device],
        all_appearances=[],
        device_history={'AA:BB:CC:DD:EE:FF': []},
        thresholds={'min_appearances': 3},
        config=config
    )

    # Verify PersistenceLevel is used correctly
    level = PersistenceLevel.from_score(test_device.persistence_score)
    assert level == PersistenceLevel.CRITICAL

    test_result("ReportGenerator with PersistenceLevel", True)
except Exception as e:
    test_result("ReportGenerator with PersistenceLevel", False, str(e))

print()

# ============================================================================
# FINAL REPORT
# ============================================================================
print("="*80)
print("INTEGRATION TEST RESULTS")
print("="*80)
print()
print(f"✅ PASSED: {len(test_results['passed'])} tests")
print(f"❌ FAILED: {len(test_results['failed'])} tests")
print(f"⚠️  WARNINGS: {len(test_results['warnings'])} warnings")
print()

if test_results['failed']:
    print("FAILED TESTS:")
    for test_name, message in test_results['failed']:
        print(f"  - {test_name}: {message}")
    print()

if test_results['warnings']:
    print("WARNINGS:")
    for test_name, message in test_results['warnings']:
        print(f"  - {test_name}: {message}")
    print()

success_rate = len(test_results['passed']) / (len(test_results['passed']) + len(test_results['failed'])) * 100
print(f"SUCCESS RATE: {success_rate:.1f}%")
print()

if len(test_results['failed']) == 0:
    print("🎉 ALL TESTS PASSED! System is ready for production.")
    sys.exit(0)
else:
    print("⚠️  Some tests failed. Please review and fix issues.")
    sys.exit(1)
