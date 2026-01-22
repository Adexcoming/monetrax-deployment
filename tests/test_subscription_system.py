"""
Monetrax Subscription System Tests
Tests for 4-tier subscription model with Stripe integration
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://msme-agent-sys.preview.emergentagent.com')

# Test session token created via MongoDB
TEST_SESSION_TOKEN = "test_session_1768931670935"


class TestSubscriptionPlans:
    """Tests for GET /api/subscriptions/plans - Returns all 4 subscription tiers"""
    
    def test_get_subscription_plans_returns_200(self):
        """Test that plans endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        
    def test_get_subscription_plans_returns_4_tiers(self):
        """Test that exactly 4 subscription tiers are returned"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) == 4
        
    def test_subscription_tiers_have_correct_names(self):
        """Test that all 4 tiers have correct names: Free, Starter, Business, Enterprise"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        data = response.json()
        tier_names = [plan["name"] for plan in data["plans"]]
        assert "Free" in tier_names
        assert "Starter" in tier_names
        assert "Business" in tier_names
        assert "Enterprise" in tier_names
        
    def test_free_tier_has_zero_price(self):
        """Test that Free tier has ₦0 pricing"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        data = response.json()
        free_plan = next(p for p in data["plans"] if p["tier"] == "free")
        assert free_plan["price_monthly"] == 0
        assert free_plan["price_yearly"] == 0
        
    def test_starter_tier_pricing(self):
        """Test Starter tier pricing: ₦2,500/month"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        data = response.json()
        starter_plan = next(p for p in data["plans"] if p["tier"] == "starter")
        assert starter_plan["price_monthly"] == 2500.0
        assert starter_plan["price_yearly"] == 25000.0
        
    def test_business_tier_pricing(self):
        """Test Business tier pricing: ₦7,500/month"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        data = response.json()
        business_plan = next(p for p in data["plans"] if p["tier"] == "business")
        assert business_plan["price_monthly"] == 7500.0
        assert business_plan["price_yearly"] == 75000.0
        assert business_plan["highlight"] == True  # Business is highlighted as most popular
        
    def test_enterprise_tier_pricing(self):
        """Test Enterprise tier pricing: ₦25,000/month"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        data = response.json()
        enterprise_plan = next(p for p in data["plans"] if p["tier"] == "enterprise")
        assert enterprise_plan["price_monthly"] == 25000.0
        assert enterprise_plan["price_yearly"] == 250000.0
        
    def test_yearly_pricing_has_discount(self):
        """Test that yearly pricing has ~17% discount (10 months for price of 12)"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        data = response.json()
        for plan in data["plans"]:
            if plan["price_monthly"] > 0:
                # Yearly should be 10x monthly (17% discount)
                expected_yearly = plan["price_monthly"] * 10
                assert plan["price_yearly"] == expected_yearly
                
    def test_plans_have_features(self):
        """Test that all plans have feature definitions"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        data = response.json()
        required_features = ["transactions_per_month", "ai_insights", "receipt_ocr", 
                           "pdf_reports", "csv_export", "priority_support", 
                           "multi_user", "custom_categories"]
        for plan in data["plans"]:
            assert "features" in plan
            for feature in required_features:
                assert feature in plan["features"]


class TestCurrentSubscription:
    """Tests for GET /api/subscriptions/current - Returns user's current subscription"""
    
    def test_current_subscription_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/current")
        assert response.status_code == 401
        
    def test_current_subscription_returns_free_by_default(self):
        """Test that new users default to free tier"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/current",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "free"
        assert data["tier_name"] == "Free"
        assert data["status"] == "active"
        
    def test_current_subscription_includes_features(self):
        """Test that current subscription includes feature access info"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/current",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        data = response.json()
        assert "features" in data
        assert "can_upgrade" in data
        assert data["can_upgrade"] == True  # Free tier can upgrade


class TestCheckoutSession:
    """Tests for POST /api/subscriptions/checkout - Creates Stripe checkout session"""
    
    def test_checkout_requires_auth(self):
        """Test that checkout requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/checkout",
            json={"tier": "starter", "billing_cycle": "monthly", "origin_url": "https://test.com"}
        )
        assert response.status_code == 401
        
    def test_checkout_creates_session_for_starter(self):
        """Test creating checkout session for Starter tier"""
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/checkout",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"},
            json={"tier": "starter", "billing_cycle": "monthly", "origin_url": "https://msme-agent-sys.preview.emergentagent.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "checkout_url" in data
        assert "session_id" in data
        assert "payment_id" in data
        assert data["checkout_url"].startswith("https://checkout.stripe.com")
        
    def test_checkout_creates_session_for_business(self):
        """Test creating checkout session for Business tier"""
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/checkout",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"},
            json={"tier": "business", "billing_cycle": "monthly", "origin_url": "https://msme-agent-sys.preview.emergentagent.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "checkout_url" in data
        
    def test_checkout_creates_session_for_enterprise(self):
        """Test creating checkout session for Enterprise tier"""
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/checkout",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"},
            json={"tier": "enterprise", "billing_cycle": "yearly", "origin_url": "https://msme-agent-sys.preview.emergentagent.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "checkout_url" in data
        
    def test_checkout_rejects_free_tier(self):
        """Test that free tier cannot create checkout session"""
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/checkout",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"},
            json={"tier": "free", "billing_cycle": "monthly", "origin_url": "https://test.com"}
        )
        assert response.status_code == 400
        assert "Free tier doesn't require payment" in response.json()["detail"]
        
    def test_checkout_rejects_invalid_tier(self):
        """Test that invalid tier is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/checkout",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"},
            json={"tier": "invalid_tier", "billing_cycle": "monthly", "origin_url": "https://test.com"}
        )
        assert response.status_code == 400


class TestCheckoutStatus:
    """Tests for GET /api/subscriptions/checkout/status/{session_id}"""
    
    def test_checkout_status_requires_auth(self):
        """Test that status check requires authentication"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/checkout/status/test_session")
        assert response.status_code == 401
        
    def test_checkout_status_returns_payment_info(self):
        """Test that status endpoint returns payment information"""
        # First create a checkout session
        checkout_response = requests.post(
            f"{BASE_URL}/api/subscriptions/checkout",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"},
            json={"tier": "starter", "billing_cycle": "monthly", "origin_url": "https://msme-agent-sys.preview.emergentagent.com"}
        )
        session_id = checkout_response.json()["session_id"]
        
        # Check status
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/checkout/status/{session_id}",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "payment_status" in data


class TestFeatureCheck:
    """Tests for GET /api/subscriptions/feature-check/{feature}"""
    
    def test_feature_check_requires_auth(self):
        """Test that feature check requires authentication"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/feature-check/ai_insights")
        assert response.status_code == 401
        
    def test_free_tier_has_csv_export(self):
        """Test that free tier has CSV export access"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/feature-check/csv_export",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["feature"] == "csv_export"
        assert data["has_access"] == True
        assert data["current_tier"] == "free"
        
    def test_free_tier_no_ai_insights(self):
        """Test that free tier does not have AI insights access"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/feature-check/ai_insights",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["feature"] == "ai_insights"
        assert data["has_access"] == False
        assert data["upgrade_required"] == True
        
    def test_free_tier_no_receipt_ocr(self):
        """Test that free tier does not have receipt OCR access"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/feature-check/receipt_ocr",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        data = response.json()
        assert data["has_access"] == False
        
    def test_free_tier_no_pdf_reports(self):
        """Test that free tier does not have PDF reports access"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/feature-check/pdf_reports",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        data = response.json()
        assert data["has_access"] == False


class TestCancelSubscription:
    """Tests for POST /api/subscriptions/cancel"""
    
    def test_cancel_requires_auth(self):
        """Test that cancel requires authentication"""
        response = requests.post(f"{BASE_URL}/api/subscriptions/cancel")
        assert response.status_code == 401
        
    def test_cancel_fails_for_free_tier(self):
        """Test that cancelling free tier returns appropriate error"""
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/cancel",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        # Should return 404 (no active subscription) or 400 (already on free tier)
        assert response.status_code in [400, 404]


class TestHealthAndIntegration:
    """Basic health and integration tests"""
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Monetrax"
        assert data["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
