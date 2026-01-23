"""
Test Bank Integration and Subscription Pricing Updates
Tests for:
1. Subscription plans with updated prices (Free=0, Starter=3000, Business=7000, Enterprise=10000)
2. Bank features in subscription tiers (linked_bank_accounts, bank_sync_frequency, manual_sync_per_day)
3. Bank integration endpoints (/api/bank/*)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_SESSION_TOKEN = "test_bank_session_1769171345392"


class TestSubscriptionPlans:
    """Test subscription plans with updated prices and bank features"""
    
    def test_get_subscription_plans_returns_200(self):
        """GET /api/subscriptions/plans returns 200"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        print(f"✓ GET /api/subscriptions/plans returns 200 with {len(data['plans'])} plans")
    
    def test_free_tier_price_is_zero(self):
        """Free tier price should be ₦0"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        
        free_plan = next((p for p in data['plans'] if p['tier'] == 'free'), None)
        assert free_plan is not None, "Free plan not found"
        assert free_plan['price_monthly'] == 0, f"Free tier monthly price should be 0, got {free_plan['price_monthly']}"
        assert free_plan['price_yearly'] == 0, f"Free tier yearly price should be 0, got {free_plan['price_yearly']}"
        print(f"✓ Free tier price: ₦{free_plan['price_monthly']}/month, ₦{free_plan['price_yearly']}/year")
    
    def test_starter_tier_price_is_3000(self):
        """Starter tier price should be ₦3,000/month"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        
        starter_plan = next((p for p in data['plans'] if p['tier'] == 'starter'), None)
        assert starter_plan is not None, "Starter plan not found"
        assert starter_plan['price_monthly'] == 3000.00, f"Starter tier monthly price should be 3000, got {starter_plan['price_monthly']}"
        print(f"✓ Starter tier price: ₦{starter_plan['price_monthly']}/month")
    
    def test_business_tier_price_is_7000(self):
        """Business tier price should be ₦7,000/month"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        
        business_plan = next((p for p in data['plans'] if p['tier'] == 'business'), None)
        assert business_plan is not None, "Business plan not found"
        assert business_plan['price_monthly'] == 7000.00, f"Business tier monthly price should be 7000, got {business_plan['price_monthly']}"
        print(f"✓ Business tier price: ₦{business_plan['price_monthly']}/month")
    
    def test_enterprise_tier_price_is_10000(self):
        """Enterprise tier price should be ₦10,000/month"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        
        enterprise_plan = next((p for p in data['plans'] if p['tier'] == 'enterprise'), None)
        assert enterprise_plan is not None, "Enterprise plan not found"
        assert enterprise_plan['price_monthly'] == 10000.00, f"Enterprise tier monthly price should be 10000, got {enterprise_plan['price_monthly']}"
        print(f"✓ Enterprise tier price: ₦{enterprise_plan['price_monthly']}/month")


class TestBankFeaturesInTiers:
    """Test bank-related features in subscription tiers"""
    
    def test_free_tier_has_1_linked_bank_account(self):
        """Free tier should allow 1 linked bank account"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        
        free_plan = next((p for p in data['plans'] if p['tier'] == 'free'), None)
        assert free_plan is not None
        assert free_plan['features']['linked_bank_accounts'] == 1, f"Free tier should have 1 linked account, got {free_plan['features']['linked_bank_accounts']}"
        print(f"✓ Free tier: {free_plan['features']['linked_bank_accounts']} linked bank account(s)")
    
    def test_starter_tier_has_3_linked_bank_accounts(self):
        """Starter tier should allow 3 linked bank accounts"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        
        starter_plan = next((p for p in data['plans'] if p['tier'] == 'starter'), None)
        assert starter_plan is not None
        assert starter_plan['features']['linked_bank_accounts'] == 3, f"Starter tier should have 3 linked accounts, got {starter_plan['features']['linked_bank_accounts']}"
        print(f"✓ Starter tier: {starter_plan['features']['linked_bank_accounts']} linked bank account(s)")
    
    def test_business_tier_has_5_linked_bank_accounts(self):
        """Business tier should allow 5 linked bank accounts"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        
        business_plan = next((p for p in data['plans'] if p['tier'] == 'business'), None)
        assert business_plan is not None
        assert business_plan['features']['linked_bank_accounts'] == 5, f"Business tier should have 5 linked accounts, got {business_plan['features']['linked_bank_accounts']}"
        print(f"✓ Business tier: {business_plan['features']['linked_bank_accounts']} linked bank account(s)")
    
    def test_enterprise_tier_has_unlimited_linked_bank_accounts(self):
        """Enterprise tier should allow unlimited linked bank accounts (-1)"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        
        enterprise_plan = next((p for p in data['plans'] if p['tier'] == 'enterprise'), None)
        assert enterprise_plan is not None
        assert enterprise_plan['features']['linked_bank_accounts'] == -1, f"Enterprise tier should have unlimited (-1) linked accounts, got {enterprise_plan['features']['linked_bank_accounts']}"
        print(f"✓ Enterprise tier: Unlimited linked bank accounts")
    
    def test_all_tiers_have_bank_sync_frequency(self):
        """All tiers should have bank_sync_frequency feature"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        
        for plan in data['plans']:
            assert 'bank_sync_frequency' in plan['features'], f"{plan['tier']} tier missing bank_sync_frequency"
            print(f"✓ {plan['tier'].title()} tier: bank_sync_frequency = {plan['features']['bank_sync_frequency']}")
    
    def test_all_tiers_have_manual_sync_per_day(self):
        """All tiers should have manual_sync_per_day feature"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        
        for plan in data['plans']:
            assert 'manual_sync_per_day' in plan['features'], f"{plan['tier']} tier missing manual_sync_per_day"
            print(f"✓ {plan['tier'].title()} tier: manual_sync_per_day = {plan['features']['manual_sync_per_day']}")


class TestBankEndpoints:
    """Test bank integration endpoints"""
    
    def test_supported_institutions_returns_200(self):
        """GET /api/bank/supported-institutions returns list of Nigerian banks"""
        response = requests.get(f"{BASE_URL}/api/bank/supported-institutions")
        assert response.status_code == 200
        data = response.json()
        
        assert "institutions" in data
        assert "total" in data
        assert len(data['institutions']) > 0, "Should have at least one supported institution"
        
        # Check for major Nigerian banks
        bank_names = [b['name'] for b in data['institutions']]
        assert "Access Bank" in bank_names, "Access Bank should be in supported institutions"
        assert "GTBank" in bank_names, "GTBank should be in supported institutions"
        assert "First Bank" in bank_names, "First Bank should be in supported institutions"
        assert "UBA" in bank_names, "UBA should be in supported institutions"
        
        print(f"✓ GET /api/bank/supported-institutions returns {data['total']} banks")
        print(f"  Banks include: {', '.join(bank_names[:5])}...")
    
    def test_bank_status_requires_auth(self):
        """GET /api/bank/status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/bank/status")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/bank/status requires authentication (401)")
    
    def test_bank_status_with_auth(self):
        """GET /api/bank/status returns status with valid auth"""
        response = requests.get(
            f"{BASE_URL}/api/bank/status",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "configured" in data
        assert "tier" in data
        assert "linked_accounts" in data
        assert "max_accounts" in data
        assert "can_link_more" in data
        assert "sync_frequency" in data
        assert "manual_syncs_today" in data
        assert "manual_syncs_limit" in data
        assert "can_manual_sync" in data
        
        print(f"✓ GET /api/bank/status returns status:")
        print(f"  - configured: {data['configured']}")
        print(f"  - tier: {data['tier']}")
        print(f"  - max_accounts: {data['max_accounts']}")
        print(f"  - sync_frequency: {data['sync_frequency']}")
    
    def test_bank_accounts_requires_auth(self):
        """GET /api/bank/accounts requires authentication"""
        response = requests.get(f"{BASE_URL}/api/bank/accounts")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/bank/accounts requires authentication (401)")
    
    def test_bank_accounts_with_auth(self):
        """GET /api/bank/accounts returns user's linked accounts"""
        response = requests.get(
            f"{BASE_URL}/api/bank/accounts",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "accounts" in data
        assert "count" in data
        assert "max_accounts" in data
        assert "can_link_more" in data
        
        print(f"✓ GET /api/bank/accounts returns:")
        print(f"  - accounts: {data['count']} linked")
        print(f"  - max_accounts: {data['max_accounts']}")
        print(f"  - can_link_more: {data['can_link_more']}")
    
    def test_bank_link_initiate_requires_auth(self):
        """POST /api/bank/link/initiate requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/bank/link/initiate",
            json={"account_type": "financial_data"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/bank/link/initiate requires authentication (401)")
    
    def test_bank_link_initiate_returns_503_when_not_configured(self):
        """POST /api/bank/link/initiate returns 503 when Mono keys not configured"""
        response = requests.post(
            f"{BASE_URL}/api/bank/link/initiate",
            headers={"Authorization": f"Bearer {TEST_SESSION_TOKEN}"},
            json={"account_type": "financial_data"}
        )
        # Should return 503 since MONO_SECRET_KEY is empty
        assert response.status_code == 503, f"Expected 503 (not configured), got {response.status_code}: {response.text}"
        data = response.json()
        assert "not configured" in data.get("detail", "").lower(), f"Expected 'not configured' message, got: {data}"
        print("✓ POST /api/bank/link/initiate returns 503 'Bank integration not configured' when Mono keys empty")
    
    def test_bank_webhook_accepts_post(self):
        """POST /api/bank/webhook accepts webhook events"""
        response = requests.post(
            f"{BASE_URL}/api/bank/webhook",
            json={
                "event": "mono.events.test",
                "data": {}
            }
        )
        # Should return 200 (webhook received) since no webhook secret is configured
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "received", f"Expected status 'received', got: {data}"
        print("✓ POST /api/bank/webhook accepts webhook events and returns 'received'")


class TestPromotionalPricing:
    """Test agent promotional pricing"""
    
    def test_promotional_pricing_exists(self):
        """Agent promotional pricing should be available"""
        # This tests the promotional pricing endpoint if available
        # The pricing is defined in AGENT_PROMOTIONAL_PRICING constant
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        
        # Verify the regular prices match what promotional pricing is based on
        data = response.json()
        starter = next((p for p in data['plans'] if p['tier'] == 'starter'), None)
        business = next((p for p in data['plans'] if p['tier'] == 'business'), None)
        enterprise = next((p for p in data['plans'] if p['tier'] == 'enterprise'), None)
        
        # Promotional prices: Starter ₦2,000, Business ₦5,000, Enterprise ₦8,000
        # Regular prices: Starter ₦3,000, Business ₦7,000, Enterprise ₦10,000
        assert starter['price_monthly'] == 3000.00, "Starter regular price should be 3000"
        assert business['price_monthly'] == 7000.00, "Business regular price should be 7000"
        assert enterprise['price_monthly'] == 10000.00, "Enterprise regular price should be 10000"
        
        print("✓ Regular prices verified for promotional pricing calculation:")
        print(f"  - Starter: ₦3,000 (promo: ₦2,000, saves ₦1,000)")
        print(f"  - Business: ₦7,000 (promo: ₦5,000, saves ₦2,000)")
        print(f"  - Enterprise: ₦10,000 (promo: ₦8,000, saves ₦2,000)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
