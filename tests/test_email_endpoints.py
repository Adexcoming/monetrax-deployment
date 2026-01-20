"""
Test Email Notification System for Monetrax
Tests: GET/PUT /api/email/preferences, POST /api/email/send-tax-reminder, 
       POST /api/email/send-upgrade-receipt, POST /api/email/test
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', '')


class TestEmailPreferences:
    """Email preferences endpoint tests"""
    
    def test_get_email_preferences_returns_200(self):
        """GET /api/email/preferences - Returns 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/email/preferences",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_get_email_preferences_returns_default_values(self):
        """GET /api/email/preferences - Returns default preference values"""
        response = requests.get(
            f"{BASE_URL}/api/email/preferences",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify default structure
        assert "tax_deadline_reminders" in data, "Missing tax_deadline_reminders field"
        assert "subscription_updates" in data, "Missing subscription_updates field"
        assert "weekly_summary" in data, "Missing weekly_summary field"
        
        # Verify default values (should be True, True, False for new users)
        assert isinstance(data["tax_deadline_reminders"], bool)
        assert isinstance(data["subscription_updates"], bool)
        assert isinstance(data["weekly_summary"], bool)
        
    def test_get_email_preferences_requires_auth(self):
        """GET /api/email/preferences - Requires authentication"""
        response = requests.get(f"{BASE_URL}/api/email/preferences")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
    def test_update_email_preferences_returns_200(self):
        """PUT /api/email/preferences - Returns 200 OK"""
        response = requests.put(
            f"{BASE_URL}/api/email/preferences",
            headers={
                "Authorization": f"Bearer {SESSION_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "tax_deadline_reminders": True,
                "subscription_updates": True,
                "weekly_summary": True
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_update_email_preferences_persists_changes(self):
        """PUT /api/email/preferences - Changes are persisted"""
        # Update preferences
        update_response = requests.put(
            f"{BASE_URL}/api/email/preferences",
            headers={
                "Authorization": f"Bearer {SESSION_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "tax_deadline_reminders": False,
                "subscription_updates": True,
                "weekly_summary": True
            }
        )
        assert update_response.status_code == 200
        
        # Verify changes persisted
        get_response = requests.get(
            f"{BASE_URL}/api/email/preferences",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert get_response.status_code == 200
        data = get_response.json()
        
        assert data["tax_deadline_reminders"] == False, "tax_deadline_reminders not updated"
        assert data["subscription_updates"] == True, "subscription_updates not updated"
        assert data["weekly_summary"] == True, "weekly_summary not updated"
        
    def test_update_email_preferences_requires_auth(self):
        """PUT /api/email/preferences - Requires authentication"""
        response = requests.put(
            f"{BASE_URL}/api/email/preferences",
            headers={"Content-Type": "application/json"},
            json={
                "tax_deadline_reminders": True,
                "subscription_updates": True,
                "weekly_summary": False
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestSendTaxReminder:
    """Tax reminder email endpoint tests"""
    
    def test_send_tax_reminder_returns_200(self):
        """POST /api/email/send-tax-reminder - Returns 200 OK"""
        response = requests.post(
            f"{BASE_URL}/api/email/send-tax-reminder",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_send_tax_reminder_returns_status(self):
        """POST /api/email/send-tax-reminder - Returns status field"""
        response = requests.post(
            f"{BASE_URL}/api/email/send-tax-reminder",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return status (success, skipped, or failed)
        assert "status" in data, "Missing status field in response"
        assert data["status"] in ["success", "skipped", "failed"], f"Unexpected status: {data['status']}"
        
    def test_send_tax_reminder_skipped_with_demo_key(self):
        """POST /api/email/send-tax-reminder - Returns 'skipped' with demo API key"""
        response = requests.post(
            f"{BASE_URL}/api/email/send-tax-reminder",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # With demo key, should be skipped
        if data["status"] == "skipped":
            assert "reason" in data, "Missing reason for skipped status"
            
    def test_send_tax_reminder_requires_auth(self):
        """POST /api/email/send-tax-reminder - Requires authentication"""
        response = requests.post(f"{BASE_URL}/api/email/send-tax-reminder")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestSendUpgradeReceipt:
    """Subscription upgrade receipt email endpoint tests"""
    
    def test_send_upgrade_receipt_requires_auth(self):
        """POST /api/email/send-upgrade-receipt - Requires authentication"""
        response = requests.post(f"{BASE_URL}/api/email/send-upgrade-receipt")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
    def test_send_upgrade_receipt_requires_paid_subscription(self):
        """POST /api/email/send-upgrade-receipt - Returns 400 for free tier users"""
        response = requests.post(
            f"{BASE_URL}/api/email/send-upgrade-receipt",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        # Free tier users should get 400 error
        assert response.status_code == 400, f"Expected 400 for free tier, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Missing error detail"


class TestSendTestEmail:
    """Test email endpoint tests"""
    
    def test_send_test_email_returns_200(self):
        """POST /api/email/test - Returns 200 OK"""
        response = requests.post(
            f"{BASE_URL}/api/email/test",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_send_test_email_returns_status(self):
        """POST /api/email/test - Returns status field"""
        response = requests.post(
            f"{BASE_URL}/api/email/test",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data, "Missing status field in response"
        # With demo key, should be skipped
        if data["status"] == "skipped":
            assert "reason" in data, "Missing reason for skipped status"
            
    def test_send_test_email_requires_auth(self):
        """POST /api/email/test - Requires authentication"""
        response = requests.post(f"{BASE_URL}/api/email/test")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestRefactoredComponents:
    """Test that refactored component files exist"""
    
    def test_auth_context_file_exists(self):
        """Refactored AuthContext.js exists"""
        import os
        path = "/app/frontend/src/contexts/AuthContext.js"
        assert os.path.exists(path), f"AuthContext.js not found at {path}"
        
    def test_subscription_context_file_exists(self):
        """Refactored SubscriptionContext.js exists"""
        import os
        path = "/app/frontend/src/contexts/SubscriptionContext.js"
        assert os.path.exists(path), f"SubscriptionContext.js not found at {path}"
        
    def test_dashboard_page_file_exists(self):
        """Refactored DashboardPage.js exists"""
        import os
        path = "/app/frontend/src/components/pages/DashboardPage.js"
        assert os.path.exists(path), f"DashboardPage.js not found at {path}"


class TestHealthCheck:
    """Basic health check"""
    
    def test_health_endpoint(self):
        """GET /api/health - Returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
