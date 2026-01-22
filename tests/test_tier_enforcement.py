"""
Monetrax Tier Enforcement Tests
Tests for updated pricing (Free=0, Starter=5000, Business=10000, Enterprise=20000)
and tier enforcement features (transaction limits, feature gating, usage stats)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://msme-agent-sys.preview.emergentagent.com')

# Test session token created via MongoDB
TEST_SESSION_TOKEN = "test_session_tier_1768932992031"


class TestUpdatedPricing:
    """Tests for GET /api/subscriptions/plans - Verify updated pricing"""
    
    def test_free_tier_pricing_is_zero(self):
        """Test Free tier has ₦0 pricing"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        free_plan = next(p for p in data["plans"] if p["tier"] == "free")
        assert free_plan["price_monthly"] == 0
        assert free_plan["price_yearly"] == 0
        print(f"✓ Free tier pricing: ₦{free_plan['price_monthly']}/month")
        
    def test_starter_tier_pricing_is_5000(self):
        """Test Starter tier has ₦5,000/month pricing"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        data = response.json()
        starter_plan = next(p for p in data["plans"] if p["tier"] == "starter")
        assert starter_plan["price_monthly"] == 5000.0
        assert starter_plan["price_yearly"] == 50000.0
        print(f"✓ Starter tier pricing: ₦{starter_plan['price_monthly']}/month")
        
    def test_business_tier_pricing_is_10000(self):
        """Test Business tier has ₦10,000/month pricing"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        data = response.json()
        business_plan = next(p for p in data["plans"] if p["tier"] == "business")
        assert business_plan["price_monthly"] == 10000.0
        assert business_plan["price_yearly"] == 100000.0
        print(f"✓ Business tier pricing: ₦{business_plan['price_monthly']}/month")
        
    def test_enterprise_tier_pricing_is_20000(self):
        """Test Enterprise tier has ₦20,000/month pricing"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        data = response.json()
        enterprise_plan = next(p for p in data["plans"] if p["tier"] == "enterprise")
        assert enterprise_plan["price_monthly"] == 20000.0
        assert enterprise_plan["price_yearly"] == 200000.0
        print(f"✓ Enterprise tier pricing: ₦{enterprise_plan['price_monthly']}/month")


class TestCurrentSubscriptionWithUsage:
    """Tests for GET /api/subscriptions/current - Includes usage stats"""
    
    def test_current_subscription_includes_usage_stats(self):
        """Test that current subscription includes transactions_this_month and transactions_limit"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/current",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check usage stats are present
        assert "usage" in data
        assert "transactions_this_month" in data["usage"]
        assert "transactions_limit" in data["usage"]
        
        print(f"✓ Usage stats: {data['usage']['transactions_this_month']}/{data['usage']['transactions_limit']} transactions")
        
    def test_free_tier_has_50_transaction_limit(self):
        """Test that free tier has 50 transactions/month limit"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/current",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        data = response.json()
        
        assert data["tier"] == "free"
        assert data["usage"]["transactions_limit"] == 50
        print(f"✓ Free tier transaction limit: {data['usage']['transactions_limit']}")


class TestUsageEndpoint:
    """Tests for GET /api/subscriptions/usage - Detailed usage with limit_exceeded flag"""
    
    def test_usage_endpoint_returns_200(self):
        """Test usage endpoint returns 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/usage",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        
    def test_usage_endpoint_includes_limit_exceeded_flag(self):
        """Test usage endpoint includes limit_exceeded flag"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/usage",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        data = response.json()
        
        assert "transactions" in data
        assert "limit_exceeded" in data["transactions"]
        assert "used" in data["transactions"]
        assert "limit" in data["transactions"]
        assert "remaining" in data["transactions"]
        assert "usage_percentage" in data["transactions"]
        
        print(f"✓ Usage data: {data['transactions']['used']}/{data['transactions']['limit']} ({data['transactions']['usage_percentage']}%)")
        print(f"✓ Limit exceeded: {data['transactions']['limit_exceeded']}")
        
    def test_usage_endpoint_includes_tier_info(self):
        """Test usage endpoint includes tier information"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/usage",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        data = response.json()
        
        assert "tier" in data
        assert "tier_name" in data
        assert data["tier"] == "free"
        assert data["tier_name"] == "Free"
        
    def test_usage_endpoint_requires_auth(self):
        """Test usage endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/usage")
        assert response.status_code == 401


class TestFeatureGating:
    """Tests for GET /api/subscriptions/feature-check/{feature} - Feature access for free tier"""
    
    def test_free_tier_no_ai_insights(self):
        """Test free tier does not have AI insights access"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/feature-check/ai_insights",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["feature"] == "ai_insights"
        assert data["has_access"] == False
        assert data["upgrade_required"] == True
        print(f"✓ AI Insights access for free tier: {data['has_access']}")
        
    def test_free_tier_no_receipt_ocr(self):
        """Test free tier does not have receipt OCR access"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/feature-check/receipt_ocr",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        data = response.json()
        
        assert data["has_access"] == False
        assert data["upgrade_required"] == True
        print(f"✓ Receipt OCR access for free tier: {data['has_access']}")
        
    def test_free_tier_no_pdf_reports(self):
        """Test free tier does not have PDF reports access"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/feature-check/pdf_reports",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        data = response.json()
        
        assert data["has_access"] == False
        assert data["upgrade_required"] == True
        print(f"✓ PDF Reports access for free tier: {data['has_access']}")
        
    def test_free_tier_has_csv_export(self):
        """Test free tier has CSV export access"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/feature-check/csv_export",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        data = response.json()
        
        assert data["has_access"] == True
        print(f"✓ CSV Export access for free tier: {data['has_access']}")


class TestTransactionLimitEnforcement:
    """Tests for POST /api/transactions - Transaction limit enforcement"""
    
    def test_transaction_creation_works_within_limit(self):
        """Test that transactions can be created within the limit"""
        response = requests.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"},
            json={
                "type": "income",
                "category": "Sales",
                "amount": 1000,
                "description": "Test transaction for tier enforcement",
                "is_taxable": True,
                "payment_method": "Cash"
            }
        )
        # Should succeed if within limit
        if response.status_code == 200:
            data = response.json()
            assert "transaction_id" in data
            print(f"✓ Transaction created successfully: {data['transaction_id']}")
        elif response.status_code == 403:
            # Limit already reached
            data = response.json()
            assert "transaction_limit_exceeded" in str(data)
            print(f"✓ Transaction limit enforced: {data}")
        else:
            # Other error
            print(f"Transaction response: {response.status_code} - {response.text}")
            assert response.status_code in [200, 403]


class TestHealthEndpoint:
    """Basic health check"""
    
    def test_health_endpoint(self):
        """Test health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Monetrax"
        print(f"✓ Health check: {data['status']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
