#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "requests",
# ]
# ///
"""
Test deployed antenna_web.py on shoeph.one

This suite tests the live deployment to verify:
- All routes are accessible
- Authentication works correctly
- Read-only pages are open
- Write operations require auth
- Flask app is running properly
"""

import sys
import requests
from requests.auth import HTTPBasicAuth

# Configuration
BASE_URL = "https://shoeph.one/hf"
USERNAME = "ak6mj"
PASSWORD = "HF73DX2026!"

# Disable SSL warnings for testing (shoeph.one has valid cert)
requests.packages.urllib3.disable_warnings()


class TestDeployment:
    """Test suite for deployed antenna_web.py"""

    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False  # Don't verify SSL (self-signed/test cert)
        self.auth = HTTPBasicAuth(USERNAME, PASSWORD)
        self.failures = []
        self.successes = []

    def test_health_check(self):
        """Test /health endpoint (should be open)"""
        print("\n[TEST] Health check endpoint...")
        try:
            r = self.session.get(f"{BASE_URL}/health", timeout=10)
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            assert 'status' in data, "Missing 'status' in response"
            assert data['status'] == 'ok', f"Status is {data['status']}, expected 'ok'"
            assert 'service' in data, "Missing 'service' in response"
            print(f"  ✅ Health check OK: {data}")
            self.successes.append("health_check")
            return True
        except Exception as e:
            print(f"  ❌ Health check FAILED: {e}")
            self.failures.append(("health_check", str(e)))
            return False

    def test_dashboard_open(self):
        """Test dashboard is accessible without auth"""
        print("\n[TEST] Dashboard (no auth)...")
        try:
            r = self.session.get(f"{BASE_URL}/", timeout=10)
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            assert 'Antenna' in r.text, "Dashboard doesn't contain 'Antenna'"
            print(f"  ✅ Dashboard accessible without auth")
            self.successes.append("dashboard_open")
            return True
        except Exception as e:
            print(f"  ❌ Dashboard FAILED: {e}")
            self.failures.append(("dashboard_open", str(e)))
            return False

    def test_antennas_list_open(self):
        """Test antennas list is accessible without auth"""
        print("\n[TEST] Antennas list (no auth)...")
        try:
            r = self.session.get(f"{BASE_URL}/antennas", timeout=10)
            # Should work even if empty
            assert r.status_code in [200, 404], f"Expected 200 or 404, got {r.status_code}"
            print(f"  ✅ Antennas list accessible (status: {r.status_code})")
            self.successes.append("antennas_list_open")
            return True
        except Exception as e:
            print(f"  ❌ Antennas list FAILED: {e}")
            self.failures.append(("antennas_list_open", str(e)))
            return False

    def test_experiment_requires_auth(self):
        """Test experiment page requires authentication"""
        print("\n[TEST] Experiment page requires auth...")
        try:
            # Without auth - should get 401
            r = self.session.get(f"{BASE_URL}/experiment", timeout=10)
            assert r.status_code == 401, f"Expected 401 without auth, got {r.status_code}"
            print(f"  ✅ Experiment page requires auth (401 received)")

            # With auth - should work
            r = self.session.get(f"{BASE_URL}/experiment", auth=self.auth, timeout=10)
            assert r.status_code == 200, f"Expected 200 with auth, got {r.status_code}"
            print(f"  ✅ Experiment page accessible with auth")
            self.successes.append("experiment_requires_auth")
            return True
        except Exception as e:
            print(f"  ❌ Experiment auth test FAILED: {e}")
            self.failures.append(("experiment_requires_auth", str(e)))
            return False

    def test_static_files(self):
        """Test static files (CSS/JS) are accessible"""
        print("\n[TEST] Static files...")
        try:
            r = self.session.get(f"{BASE_URL}/static/style.css", timeout=10)
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            assert 'css' in r.headers.get('content-type', '').lower(), "Not CSS content-type"
            print(f"  ✅ Static CSS accessible")
            self.successes.append("static_files")
            return True
        except Exception as e:
            print(f"  ❌ Static files FAILED: {e}")
            self.failures.append(("static_files", str(e)))
            return False

    def test_api_antennas_list(self):
        """Test API endpoint for antennas"""
        print("\n[TEST] API antennas list...")
        try:
            r = self.session.get(f"{BASE_URL}/api/antennas", timeout=10)
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            assert isinstance(data, (list, dict)), "Response should be list or dict"
            print(f"  ✅ API antennas list works: {len(data) if isinstance(data, list) else 'dict'}")
            self.successes.append("api_antennas_list")
            return True
        except Exception as e:
            print(f"  ❌ API antennas FAILED: {e}")
            self.failures.append(("api_antennas_list", str(e)))
            return False

    def test_create_antenna_requires_auth(self):
        """Test creating antenna requires auth"""
        print("\n[TEST] Create antenna requires auth...")
        try:
            data = {
                'label': 'test',
                'description': 'Test antenna'
            }

            # Without auth - should fail
            r = self.session.post(f"{BASE_URL}/api/antennas",
                                 json=data, timeout=10)
            assert r.status_code == 401, f"Expected 401 without auth, got {r.status_code}"
            print(f"  ✅ Creating antenna blocked without auth (401)")

            self.successes.append("create_antenna_requires_auth")
            return True
        except Exception as e:
            print(f"  ❌ Create antenna auth test FAILED: {e}")
            self.failures.append(("create_antenna_requires_auth", str(e)))
            return False

    def test_service_running(self):
        """Test that the service responds at all"""
        print("\n[TEST] Service is running...")
        try:
            r = self.session.get(BASE_URL, timeout=10)
            assert r.status_code in [200, 301, 302, 401], f"Service not responding, got {r.status_code}"
            print(f"  ✅ Service is running (status: {r.status_code})")
            self.successes.append("service_running")
            return True
        except requests.exceptions.Timeout:
            print(f"  ❌ Service TIMEOUT")
            self.failures.append(("service_running", "Timeout"))
            return False
        except Exception as e:
            print(f"  ❌ Service FAILED: {e}")
            self.failures.append(("service_running", str(e)))
            return False

    def run_all_tests(self):
        """Run all tests and report results"""
        print("=" * 70)
        print(f"Testing deployment at {BASE_URL}")
        print("=" * 70)

        tests = [
            self.test_service_running,
            self.test_health_check,
            self.test_dashboard_open,
            self.test_antennas_list_open,
            self.test_static_files,
            self.test_api_antennas_list,
            self.test_experiment_requires_auth,
            self.test_create_antenna_requires_auth,
        ]

        for test in tests:
            test()

        print("\n" + "=" * 70)
        print(f"RESULTS: {len(self.successes)} passed, {len(self.failures)} failed")
        print("=" * 70)

        if self.failures:
            print("\n❌ FAILURES:")
            for test_name, error in self.failures:
                print(f"  - {test_name}: {error}")
            return False
        else:
            print("\n✅ ALL TESTS PASSED!")
            return True


def main():
    """Run deployment tests"""
    tester = TestDeployment()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
