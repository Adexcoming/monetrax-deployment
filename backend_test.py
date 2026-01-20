#!/usr/bin/env python3
"""
MFA Authentication Backend API Testing
Tests all backend endpoints for the MFA authentication system
"""
import requests
import sys
import json
from datetime import datetime

class MFAAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session_token = "test_session_1768912578567"  # From MongoDB setup
        self.user_id = "test-user-1768912578567"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        # Add session token via Authorization header
        if self.session_token:
            test_headers['Authorization'] = f'Bearer {self.session_token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")

            self.test_results.append({
                "name": name,
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success,
                "response": response.text[:500] if not success else "OK"
            })

            return success, response.json() if success and response.text else {}

        except requests.exceptions.RequestException as e:
            print(f"❌ FAILED - Network Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status,
                "actual_status": "ERROR",
                "success": False,
                "response": str(e)
            })
            return False, {}

    def test_health_endpoint(self):
        """Test health check endpoint"""
        return self.run_test(
            "Health Check",
            "GET",
            "/api/health",
            200
        )

    def test_auth_me(self):
        """Test current user endpoint"""
        return self.run_test(
            "Get Current User (/api/auth/me)",
            "GET",
            "/api/auth/me",
            200
        )

    def test_mfa_status(self):
        """Test MFA status endpoint"""
        return self.run_test(
            "MFA Status",
            "GET",
            "/api/mfa/status",
            200
        )

    def test_totp_setup(self):
        """Test TOTP setup endpoint"""
        return self.run_test(
            "TOTP Setup",
            "POST",
            "/api/mfa/totp/setup",
            200
        )

    def test_totp_verify(self):
        """Test TOTP verification with invalid code"""
        return self.run_test(
            "TOTP Verify (Invalid Code)",
            "POST",
            "/api/mfa/totp/verify",
            400,  # Should fail with invalid code
            data={"code": "123456"}
        )

    def test_backup_codes_get(self):
        """Test get backup codes endpoint"""
        return self.run_test(
            "Get Backup Codes",
            "GET",
            "/api/mfa/backup-codes",
            200
        )

    def test_backup_codes_regenerate(self):
        """Test regenerate backup codes endpoint"""
        return self.run_test(
            "Regenerate Backup Codes",
            "POST",
            "/api/mfa/backup-codes/regenerate",
            200
        )

    def test_auth_logout(self):
        """Test logout endpoint"""
        return self.run_test(
            "Logout",
            "POST",
            "/api/auth/logout",
            200
        )

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting MFA Authentication API Tests")
        print(f"📍 Base URL: {self.base_url}")
        print(f"🔑 Session Token: {self.session_token}")
        print("=" * 60)

        # Test basic endpoints
        self.test_health_endpoint()
        
        # Test authentication endpoints
        self.test_auth_me()
        
        # Test MFA endpoints
        self.test_mfa_status()
        self.test_totp_setup()
        self.test_totp_verify()
        
        # Test backup codes
        self.test_backup_codes_get()
        self.test_backup_codes_regenerate()
        
        # Test logout (do this last as it invalidates session)
        # self.test_auth_logout()  # Commented out to keep session valid

        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"   Total Tests: {self.tests_run}")
        print(f"   Passed: {self.tests_passed}")
        print(f"   Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Print failed tests
        failed_tests = [t for t in self.test_results if not t["success"]]
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['name']}: {test['actual_status']} (expected {test['expected_status']})")
                if test['response'] and test['response'] != 'OK':
                    print(f"     Error: {test['response'][:100]}...")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    # Check if REACT_APP_BACKEND_URL is set
    import os
    backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
    
    if not backend_url or backend_url == '':
        print("⚠️  WARNING: REACT_APP_BACKEND_URL is not set, using localhost:8001")
        backend_url = 'http://localhost:8001'
    
    tester = MFAAPITester(backend_url)
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())