"""
Admin System Backend Tests for Monetrax
Tests admin endpoints with role-based access control (RBAC)

Endpoints tested:
- /api/admin/overview - Admin dashboard metrics
- /api/admin/users - User management
- /api/admin/businesses - Business management
- /api/admin/transactions - Transaction monitoring
- /api/admin/tax-rules - Tax engine configuration
- /api/admin/subscriptions - Subscription management
- /api/admin/logs - Admin audit logs
- /api/admin/settings - System settings (superadmin only)
"""

import pytest
import requests
import os
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthCheck:
    """Basic health check to ensure API is running"""
    
    def test_health_endpoint(self):
        """Test that the API health endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"


class TestAdminEndpointsUnauthenticated:
    """Test that admin endpoints return 401 for unauthenticated requests"""
    
    def test_admin_overview_requires_auth(self):
        """GET /api/admin/overview should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/overview")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    
    def test_admin_users_requires_auth(self):
        """GET /api/admin/users should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    
    def test_admin_businesses_requires_auth(self):
        """GET /api/admin/businesses should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/businesses")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    
    def test_admin_transactions_requires_auth(self):
        """GET /api/admin/transactions should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/transactions")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    
    def test_admin_tax_rules_requires_auth(self):
        """GET /api/admin/tax-rules should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/tax-rules")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    
    def test_admin_subscriptions_requires_auth(self):
        """GET /api/admin/subscriptions should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/subscriptions")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    
    def test_admin_logs_requires_auth(self):
        """GET /api/admin/logs should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/logs")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    
    def test_admin_settings_requires_auth(self):
        """GET /api/admin/settings should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/settings")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"


class TestAdminEndpointsWithRegularUser:
    """Test that admin endpoints return 403 for regular users (non-admin)"""
    
    @pytest.fixture(autouse=True)
    def setup_regular_user(self):
        """Create a regular user session for testing"""
        import subprocess
        import json
        
        # Create test user and session in MongoDB
        timestamp = int(datetime.now().timestamp() * 1000)
        self.user_id = f"test-regular-user-{timestamp}"
        self.session_token = f"test_session_regular_{timestamp}"
        self.email = f"test.regular.{timestamp}@example.com"
        
        mongo_script = f"""
        use('monetrax_db');
        db.users.insertOne({{
            user_id: '{self.user_id}',
            email: '{self.email}',
            name: 'Test Regular User',
            role: 'user',
            picture: 'https://via.placeholder.com/150',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: '{self.user_id}',
            session_token: '{self.session_token}',
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            mfa_verified: true,
            created_at: new Date()
        }});
        """
        
        result = subprocess.run(
            ['mongosh', '--quiet', '--eval', mongo_script],
            capture_output=True,
            text=True
        )
        
        yield
        
        # Cleanup
        cleanup_script = f"""
        use('monetrax_db');
        db.users.deleteOne({{ user_id: '{self.user_id}' }});
        db.user_sessions.deleteOne({{ session_token: '{self.session_token}' }});
        """
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)
    
    def test_admin_overview_forbidden_for_regular_user(self):
        """GET /api/admin/overview should return 403 for regular users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/overview", cookies=cookies)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
    
    def test_admin_users_forbidden_for_regular_user(self):
        """GET /api/admin/users should return 403 for regular users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/users", cookies=cookies)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
    
    def test_admin_businesses_forbidden_for_regular_user(self):
        """GET /api/admin/businesses should return 403 for regular users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/businesses", cookies=cookies)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
    
    def test_admin_transactions_forbidden_for_regular_user(self):
        """GET /api/admin/transactions should return 403 for regular users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/transactions", cookies=cookies)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
    
    def test_admin_settings_forbidden_for_regular_user(self):
        """GET /api/admin/settings should return 403 for regular users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/settings", cookies=cookies)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


class TestAdminEndpointsWithAdminUser:
    """Test that admin endpoints work correctly for admin users"""
    
    @pytest.fixture(autouse=True)
    def setup_admin_user(self):
        """Create an admin user session for testing"""
        import subprocess
        
        timestamp = int(datetime.now().timestamp() * 1000)
        self.user_id = f"test-admin-user-{timestamp}"
        self.session_token = f"test_session_admin_{timestamp}"
        self.email = f"test.admin.{timestamp}@example.com"
        
        mongo_script = f"""
        use('monetrax_db');
        db.users.insertOne({{
            user_id: '{self.user_id}',
            email: '{self.email}',
            name: 'Test Admin User',
            role: 'admin',
            picture: 'https://via.placeholder.com/150',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: '{self.user_id}',
            session_token: '{self.session_token}',
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            mfa_verified: true,
            created_at: new Date()
        }});
        """
        
        result = subprocess.run(
            ['mongosh', '--quiet', '--eval', mongo_script],
            capture_output=True,
            text=True
        )
        
        yield
        
        # Cleanup
        cleanup_script = f"""
        use('monetrax_db');
        db.users.deleteOne({{ user_id: '{self.user_id}' }});
        db.user_sessions.deleteOne({{ session_token: '{self.session_token}' }});
        """
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)
    
    def test_admin_overview_accessible_for_admin(self):
        """GET /api/admin/overview should return 200 for admin users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/overview", cookies=cookies)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Validate response structure
        data = response.json()
        assert 'users' in data, "Response should contain 'users' key"
        assert 'businesses' in data, "Response should contain 'businesses' key"
        assert 'transactions' in data, "Response should contain 'transactions' key"
        assert 'revenue' in data, "Response should contain 'revenue' key"
        assert 'subscriptions' in data, "Response should contain 'subscriptions' key"
        assert 'system_health' in data, "Response should contain 'system_health' key"
    
    def test_admin_users_accessible_for_admin(self):
        """GET /api/admin/users should return 200 for admin users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/users", cookies=cookies)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Validate response structure
        data = response.json()
        assert 'users' in data, "Response should contain 'users' key"
        assert 'pagination' in data, "Response should contain 'pagination' key"
        assert isinstance(data['users'], list), "'users' should be a list"
    
    def test_admin_businesses_accessible_for_admin(self):
        """GET /api/admin/businesses should return 200 for admin users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/businesses", cookies=cookies)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Validate response structure
        data = response.json()
        assert 'businesses' in data, "Response should contain 'businesses' key"
        assert 'pagination' in data, "Response should contain 'pagination' key"
    
    def test_admin_transactions_accessible_for_admin(self):
        """GET /api/admin/transactions should return 200 for admin users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/transactions", cookies=cookies)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Validate response structure
        data = response.json()
        assert 'transactions' in data, "Response should contain 'transactions' key"
        assert 'totals' in data, "Response should contain 'totals' key"
        assert 'pagination' in data, "Response should contain 'pagination' key"
    
    def test_admin_tax_rules_accessible_for_admin(self):
        """GET /api/admin/tax-rules should return 200 for admin users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/tax-rules", cookies=cookies)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Validate response structure
        data = response.json()
        assert 'vat_rate' in data, "Response should contain 'vat_rate' key"
        assert 'tax_free_threshold' in data, "Response should contain 'tax_free_threshold' key"
    
    def test_admin_subscriptions_accessible_for_admin(self):
        """GET /api/admin/subscriptions should return 200 for admin users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/subscriptions", cookies=cookies)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Validate response structure
        data = response.json()
        assert 'subscriptions' in data, "Response should contain 'subscriptions' key"
        assert 'pagination' in data, "Response should contain 'pagination' key"
    
    def test_admin_logs_accessible_for_admin(self):
        """GET /api/admin/logs should return 200 for admin users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/logs", cookies=cookies)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Validate response structure
        data = response.json()
        assert 'logs' in data, "Response should contain 'logs' key"
        assert 'pagination' in data, "Response should contain 'pagination' key"
    
    def test_admin_settings_forbidden_for_admin(self):
        """GET /api/admin/settings should return 403 for admin (requires superadmin)"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/settings", cookies=cookies)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


class TestAdminEndpointsWithSuperadmin:
    """Test that superadmin-only endpoints work correctly for superadmin users"""
    
    @pytest.fixture(autouse=True)
    def setup_superadmin_user(self):
        """Create a superadmin user session for testing"""
        import subprocess
        
        timestamp = int(datetime.now().timestamp() * 1000)
        self.user_id = f"test-superadmin-user-{timestamp}"
        self.session_token = f"test_session_superadmin_{timestamp}"
        self.email = f"test.superadmin.{timestamp}@example.com"
        
        mongo_script = f"""
        use('monetrax_db');
        db.users.insertOne({{
            user_id: '{self.user_id}',
            email: '{self.email}',
            name: 'Test Superadmin User',
            role: 'superadmin',
            picture: 'https://via.placeholder.com/150',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: '{self.user_id}',
            session_token: '{self.session_token}',
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            mfa_verified: true,
            created_at: new Date()
        }});
        """
        
        result = subprocess.run(
            ['mongosh', '--quiet', '--eval', mongo_script],
            capture_output=True,
            text=True
        )
        
        yield
        
        # Cleanup
        cleanup_script = f"""
        use('monetrax_db');
        db.users.deleteOne({{ user_id: '{self.user_id}' }});
        db.user_sessions.deleteOne({{ session_token: '{self.session_token}' }});
        """
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)
    
    def test_admin_settings_accessible_for_superadmin(self):
        """GET /api/admin/settings should return 200 for superadmin users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/settings", cookies=cookies)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Validate response structure
        data = response.json()
        assert 'maintenance_mode' in data or 'type' in data, "Response should contain settings data"
    
    def test_admin_overview_accessible_for_superadmin(self):
        """GET /api/admin/overview should return 200 for superadmin users"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/overview", cookies=cookies)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


class TestAdminUsersPagination:
    """Test pagination and filtering for admin users endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup_admin_user(self):
        """Create an admin user session for testing"""
        import subprocess
        
        timestamp = int(datetime.now().timestamp() * 1000)
        self.user_id = f"test-admin-pagination-{timestamp}"
        self.session_token = f"test_session_pagination_{timestamp}"
        self.email = f"test.pagination.{timestamp}@example.com"
        
        mongo_script = f"""
        use('monetrax_db');
        db.users.insertOne({{
            user_id: '{self.user_id}',
            email: '{self.email}',
            name: 'Test Admin Pagination',
            role: 'admin',
            picture: 'https://via.placeholder.com/150',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: '{self.user_id}',
            session_token: '{self.session_token}',
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            mfa_verified: true,
            created_at: new Date()
        }});
        """
        
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        yield
        
        # Cleanup
        cleanup_script = f"""
        use('monetrax_db');
        db.users.deleteOne({{ user_id: '{self.user_id}' }});
        db.user_sessions.deleteOne({{ session_token: '{self.session_token}' }});
        """
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)
    
    def test_admin_users_pagination_params(self):
        """Test pagination parameters work correctly"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/users?page=1&limit=5", cookies=cookies)
        assert response.status_code == 200
        
        data = response.json()
        assert data['pagination']['page'] == 1
        assert data['pagination']['limit'] == 5
    
    def test_admin_users_search_filter(self):
        """Test search filter works correctly"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/users?search=test", cookies=cookies)
        assert response.status_code == 200
        
        data = response.json()
        assert 'users' in data
    
    def test_admin_transactions_type_filter(self):
        """Test transaction type filter works correctly"""
        cookies = {'session_token': self.session_token}
        response = requests.get(f"{BASE_URL}/api/admin/transactions?type=income", cookies=cookies)
        assert response.status_code == 200
        
        data = response.json()
        assert 'transactions' in data
        assert 'totals' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
