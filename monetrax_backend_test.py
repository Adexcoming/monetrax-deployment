#!/usr/bin/env python3
"""
Monetrax - Nigerian MSME Financial Platform Backend API Testing
Tests all backend endpoints for the Monetrax financial system
"""
import requests
import sys
import json
from datetime import datetime
import uuid

class MonettraxAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session_token = None
        self.user_id = None
        self.business_id = None
        self.transaction_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        # Add session token via Authorization header if available
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
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:300]}...")
                    return success, response_data
                except:
                    print(f"   Response: {response.text[:100]}...")
                    return success, {}
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
        """Test health check endpoint - should return service: Monetrax"""
        success, response = self.run_test(
            "Health Check (should return service: Monetrax)",
            "GET",
            "/api/health",
            200
        )
        if success and response.get("service") == "Monetrax":
            print("   ✅ Service name 'Monetrax' confirmed")
            return True
        elif success:
            print(f"   ⚠️  Service name is '{response.get('service')}', expected 'Monetrax'")
            return False
        return success

    def test_categories_endpoint(self):
        """Test categories endpoint - should return Nigerian income/expense categories"""
        success, response = self.run_test(
            "Categories API (Nigerian income/expense categories)",
            "GET",
            "/api/categories",
            200
        )
        if success:
            income_categories = response.get("income", [])
            expense_categories = response.get("expense", [])
            
            # Check for Nigerian-specific categories
            income_names = [cat.get("name") for cat in income_categories]
            expense_names = [cat.get("name") for cat in expense_categories]
            
            if "Sales" in income_names and "Transport" in expense_names:
                print("   ✅ Nigerian business categories confirmed")
                return True
            else:
                print(f"   ⚠️  Missing expected Nigerian categories")
                return False
        return success

    def test_tax_calendar_endpoint(self):
        """Test tax calendar endpoint - should return Nigerian tax deadlines"""
        success, response = self.run_test(
            "Tax Calendar API (Nigerian tax deadlines)",
            "GET",
            "/api/tax/calendar",
            200
        )
        if success:
            deadlines = response.get("deadlines", [])
            tips = response.get("tips", [])
            
            # Check for Nigerian tax deadlines
            deadline_names = [d.get("name") for d in deadlines]
            if "Monthly VAT Filing" in deadline_names and "Annual Income Tax" in deadline_names:
                print("   ✅ Nigerian tax deadlines confirmed")
                return True
            else:
                print(f"   ⚠️  Missing expected Nigerian tax deadlines")
                return False
        return success

    def create_test_user_session(self):
        """Create a test user and session in MongoDB for authenticated testing"""
        print("\n🔧 Setting up test user and session...")
        
        # Generate test IDs
        timestamp = str(int(datetime.now().timestamp()))
        self.user_id = f"user_{timestamp}"
        session_token = f"test_session_{timestamp}"
        
        # We'll use direct MongoDB insertion for testing
        # For now, let's use a mock session token and test without auth
        self.session_token = session_token
        print(f"   Test User ID: {self.user_id}")
        print(f"   Test Session Token: {self.session_token}")
        return True

    def test_business_creation(self):
        """Test business creation endpoint"""
        business_data = {
            "business_name": "Ade Fashion Store",
            "business_type": "Sole Proprietorship", 
            "industry": "Fashion",
            "tin": "12345678-0001",
            "annual_turnover": 5000000
        }
        
        success, response = self.run_test(
            "Business Creation (POST /api/business)",
            "POST",
            "/api/business",
            201,
            data=business_data
        )
        
        if success and response.get("business_id"):
            self.business_id = response.get("business_id")
            print(f"   ✅ Business created with ID: {self.business_id}")
            return True
        return success

    def test_transaction_creation(self):
        """Test transaction creation with VAT calculation"""
        transaction_data = {
            "type": "income",
            "category": "Sales", 
            "amount": 10000,
            "description": "Product sales to customer",
            "date": "2026-01-20",
            "is_taxable": True,
            "payment_method": "Cash"
        }
        
        success, response = self.run_test(
            "Transaction Creation with VAT (POST /api/transactions)",
            "POST", 
            "/api/transactions",
            201,
            data=transaction_data
        )
        
        if success:
            vat_amount = response.get("vat_amount", 0)
            expected_vat = 10000 * 0.075  # 7.5% VAT
            
            if abs(vat_amount - expected_vat) < 0.01:
                print(f"   ✅ VAT calculation correct: ₦{vat_amount} (7.5%)")
                self.transaction_id = response.get("transaction_id")
                return True
            else:
                print(f"   ⚠️  VAT calculation incorrect: got ₦{vat_amount}, expected ₦{expected_vat}")
                return False
        return success

    def test_financial_summary(self):
        """Test financial summary endpoint - should return tax_readiness_score"""
        success, response = self.run_test(
            "Financial Summary with Tax Readiness Score (GET /api/summary)",
            "GET",
            "/api/summary?period=month",
            200
        )
        
        if success:
            tax_readiness_score = response.get("tax_readiness_score")
            if tax_readiness_score is not None:
                print(f"   ✅ Tax readiness score: {tax_readiness_score}%")
                return True
            else:
                print(f"   ⚠️  Missing tax_readiness_score in response")
                return False
        return success

    def test_tax_summary(self):
        """Test tax summary endpoint - should return Nigerian tax calculations"""
        success, response = self.run_test(
            "Tax Summary with Nigerian Tax Calculations (GET /api/tax/summary)",
            "GET",
            "/api/tax/summary",
            200
        )
        
        if success:
            # Check for Nigerian tax fields
            required_fields = ["vat_collected", "vat_paid", "net_vat", "income_tax", "total_tax_liability"]
            missing_fields = [field for field in required_fields if field not in response]
            
            if not missing_fields:
                print(f"   ✅ All Nigerian tax calculation fields present")
                return True
            else:
                print(f"   ⚠️  Missing tax fields: {missing_fields}")
                return False
        return success

    def test_income_statement_report(self):
        """Test income statement report endpoint"""
        success, response = self.run_test(
            "Income Statement Report (GET /api/reports/income-statement)",
            "GET",
            "/api/reports/income-statement",
            200
        )
        
        if success:
            # Check for report structure
            required_sections = ["income", "expenses", "gross_profit", "net_profit"]
            missing_sections = [section for section in required_sections if section not in response]
            
            if not missing_sections:
                print(f"   ✅ Income statement structure complete")
                return True
            else:
                print(f"   ⚠️  Missing report sections: {missing_sections}")
                return False
        return success

    def run_all_tests(self):
        """Run all Monetrax API tests"""
        print("🚀 Starting Monetrax Nigerian MSME Financial Platform API Tests")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 70)

        # Test public endpoints first
        print("\n📋 TESTING PUBLIC ENDPOINTS")
        self.test_health_endpoint()
        self.test_categories_endpoint() 
        self.test_tax_calendar_endpoint()

        # Setup test user for authenticated endpoints
        print("\n🔐 SETTING UP AUTHENTICATION")
        self.create_test_user_session()

        # Test authenticated endpoints (these will likely fail without proper auth setup)
        print("\n💼 TESTING BUSINESS & TRANSACTION ENDPOINTS")
        print("   Note: These may fail without proper authentication setup")
        
        self.test_business_creation()
        self.test_transaction_creation()
        self.test_financial_summary()
        self.test_tax_summary()
        self.test_income_statement_report()

        # Print summary
        print("\n" + "=" * 70)
        print(f"📊 MONETRAX API TEST SUMMARY")
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
        
        # Print passed tests
        passed_tests = [t for t in self.test_results if t["success"]]
        if passed_tests:
            print(f"\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   - {test['name']}")
        
        return self.tests_passed, self.tests_run

def main():
    """Main test execution"""
    backend_url = "http://localhost:8001"
    
    print(f"🇳🇬 Testing Monetrax - Nigerian MSME Financial Platform")
    print(f"🔗 Backend URL: {backend_url}")
    
    tester = MonettraxAPITester(backend_url)
    
    try:
        passed, total = tester.run_all_tests()
        
        if passed == total:
            print(f"\n🎉 ALL TESTS PASSED! ({passed}/{total})")
            return 0
        else:
            print(f"\n⚠️  SOME TESTS FAILED ({passed}/{total})")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())