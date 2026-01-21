"""
Test Superadmin Features - Delete User and Change Tier
Tests for:
1. DELETE /api/admin/users/{user_id} - superadmin can delete non-superadmin users
2. DELETE /api/admin/users/{user_id} - returns 403 for non-superadmin trying to delete
3. DELETE /api/admin/users/{user_id} - cannot delete own account
4. DELETE /api/admin/users/{user_id} - cannot delete other superadmin accounts
5. POST /api/admin/users/{user_id}/change-tier - superadmin can change user tier
6. POST /api/admin/users/{user_id}/change-tier - returns 403 for non-superadmin
7. POST /api/admin/users/{user_id}/change-tier - validates tier values
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session tokens - will be set up in fixtures
SUPERADMIN_SESSION = None
ADMIN_SESSION = None
TEST_USER_DELETE_ID = None
TEST_USER_TIER_ID = None


class TestSuperadminDeleteUser:
    """Tests for DELETE /api/admin/users/{user_id} endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self, superadmin_session, admin_session, test_users):
        """Setup test data"""
        global SUPERADMIN_SESSION, ADMIN_SESSION, TEST_USER_DELETE_ID, TEST_USER_TIER_ID
        SUPERADMIN_SESSION = superadmin_session
        ADMIN_SESSION = admin_session
        TEST_USER_DELETE_ID = test_users['delete_user_id']
        TEST_USER_TIER_ID = test_users['tier_user_id']
    
    def test_superadmin_can_delete_regular_user(self, superadmin_session, create_deletable_user):
        """Superadmin should be able to delete a regular user"""
        user_id = create_deletable_user
        
        response = requests.delete(
            f"{BASE_URL}/api/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {superadmin_session}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "success"
        assert "deleted" in data.get("message", "").lower()
        
        # Verify user is actually deleted
        verify_response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {superadmin_session}"},
            params={"search": user_id}
        )
        assert verify_response.status_code == 200
        users = verify_response.json().get("users", [])
        user_ids = [u.get("user_id") for u in users]
        assert user_id not in user_ids, "User should be deleted"
    
    def test_non_superadmin_cannot_delete_user(self, admin_session, test_users):
        """Admin (non-superadmin) should get 403 when trying to delete a user"""
        user_id = test_users['tier_user_id']
        
        response = requests.delete(
            f"{BASE_URL}/api/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_session}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "superadmin" in data.get("detail", "").lower()
    
    def test_cannot_delete_own_account(self, superadmin_session, superadmin_user_id):
        """Superadmin should not be able to delete their own account"""
        response = requests.delete(
            f"{BASE_URL}/api/admin/users/{superadmin_user_id}",
            headers={"Authorization": f"Bearer {superadmin_session}"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "own account" in data.get("detail", "").lower() or "cannot delete" in data.get("detail", "").lower()
    
    def test_cannot_delete_other_superadmin(self, superadmin_session, create_another_superadmin):
        """Superadmin should not be able to delete another superadmin"""
        other_superadmin_id = create_another_superadmin
        
        response = requests.delete(
            f"{BASE_URL}/api/admin/users/{other_superadmin_id}",
            headers={"Authorization": f"Bearer {superadmin_session}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "superadmin" in data.get("detail", "").lower()
    
    def test_delete_nonexistent_user(self, superadmin_session):
        """Deleting a non-existent user should return 404"""
        response = requests.delete(
            f"{BASE_URL}/api/admin/users/nonexistent_user_12345",
            headers={"Authorization": f"Bearer {superadmin_session}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    
    def test_unauthenticated_delete_returns_401(self):
        """Unauthenticated request should return 401"""
        response = requests.delete(
            f"{BASE_URL}/api/admin/users/some_user_id"
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"


class TestSuperadminChangeTier:
    """Tests for POST /api/admin/users/{user_id}/change-tier endpoint"""
    
    def test_superadmin_can_change_tier_to_starter(self, superadmin_session, test_users):
        """Superadmin should be able to change user tier to starter"""
        user_id = test_users['tier_user_id']
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/change-tier",
            headers={"Authorization": f"Bearer {superadmin_session}"},
            params={"tier": "starter"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "success"
        assert "starter" in data.get("message", "").lower()
    
    def test_superadmin_can_change_tier_to_business(self, superadmin_session, test_users):
        """Superadmin should be able to change user tier to business"""
        user_id = test_users['tier_user_id']
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/change-tier",
            headers={"Authorization": f"Bearer {superadmin_session}"},
            params={"tier": "business"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "success"
        assert "business" in data.get("message", "").lower()
    
    def test_superadmin_can_change_tier_to_enterprise(self, superadmin_session, test_users):
        """Superadmin should be able to change user tier to enterprise"""
        user_id = test_users['tier_user_id']
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/change-tier",
            headers={"Authorization": f"Bearer {superadmin_session}"},
            params={"tier": "enterprise"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "success"
        assert "enterprise" in data.get("message", "").lower()
    
    def test_superadmin_can_change_tier_to_free(self, superadmin_session, test_users):
        """Superadmin should be able to change user tier back to free"""
        user_id = test_users['tier_user_id']
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/change-tier",
            headers={"Authorization": f"Bearer {superadmin_session}"},
            params={"tier": "free"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "success"
        assert "free" in data.get("message", "").lower()
    
    def test_non_superadmin_cannot_change_tier(self, admin_session, test_users):
        """Admin (non-superadmin) should get 403 when trying to change tier"""
        user_id = test_users['tier_user_id']
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/change-tier",
            headers={"Authorization": f"Bearer {admin_session}"},
            params={"tier": "business"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "superadmin" in data.get("detail", "").lower()
    
    def test_invalid_tier_returns_400(self, superadmin_session, test_users):
        """Invalid tier value should return 400"""
        user_id = test_users['tier_user_id']
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/change-tier",
            headers={"Authorization": f"Bearer {superadmin_session}"},
            params={"tier": "invalid_tier"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "invalid" in data.get("detail", "").lower() or "must be" in data.get("detail", "").lower()
    
    def test_change_tier_nonexistent_user(self, superadmin_session):
        """Changing tier for non-existent user should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/nonexistent_user_12345/change-tier",
            headers={"Authorization": f"Bearer {superadmin_session}"},
            params={"tier": "business"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    
    def test_unauthenticated_change_tier_returns_401(self):
        """Unauthenticated request should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/some_user_id/change-tier",
            params={"tier": "business"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    
    def test_tier_change_persists_in_database(self, superadmin_session, test_users):
        """Verify tier change is persisted by fetching user list"""
        user_id = test_users['tier_user_id']
        
        # Change to enterprise
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{user_id}/change-tier",
            headers={"Authorization": f"Bearer {superadmin_session}"},
            params={"tier": "enterprise"}
        )
        assert response.status_code == 200
        
        # Verify by fetching users
        users_response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {superadmin_session}"},
            params={"search": "test_tier_user"}
        )
        assert users_response.status_code == 200
        users = users_response.json().get("users", [])
        
        # Find our test user
        test_user = next((u for u in users if u.get("user_id") == user_id), None)
        assert test_user is not None, "Test user should be found"
        assert test_user.get("subscription_tier") == "enterprise", f"Expected enterprise, got {test_user.get('subscription_tier')}"


# ============== FIXTURES ==============

@pytest.fixture(scope="module")
def superadmin_session():
    """Get or create superadmin session"""
    import subprocess
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', '''
        use('monetrax_db');
        const superadmin = db.users.findOne({email: 'morayoadewunmi@gmail.com'});
        if (!superadmin) {
            print('ERROR: Superadmin not found');
            quit(1);
        }
        
        // Create or get session
        let session = db.user_sessions.findOne({
            user_id: superadmin.user_id,
            expires_at: {$gt: new Date()}
        });
        
        if (!session) {
            const token = 'test_superadmin_' + Date.now();
            db.user_sessions.insertOne({
                user_id: superadmin.user_id,
                session_token: token,
                expires_at: new Date(Date.now() + 7*24*60*60*1000),
                mfa_verified: true,
                created_at: new Date()
            });
            print(token);
        } else {
            print(session.session_token);
        }
        '''
    ], capture_output=True, text=True)
    
    token = result.stdout.strip().split('\n')[-1]
    assert token and not token.startswith('ERROR'), f"Failed to get superadmin session: {result.stderr}"
    return token


@pytest.fixture(scope="module")
def superadmin_user_id():
    """Get superadmin user ID"""
    import subprocess
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', '''
        use('monetrax_db');
        const superadmin = db.users.findOne({email: 'morayoadewunmi@gmail.com'});
        print(superadmin.user_id);
        '''
    ], capture_output=True, text=True)
    
    return result.stdout.strip().split('\n')[-1]


@pytest.fixture(scope="module")
def admin_session():
    """Create admin (non-superadmin) session"""
    import subprocess
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', '''
        use('monetrax_db');
        
        // Create or get admin user
        let admin = db.users.findOne({email: 'test_admin_iter10@example.com'});
        if (!admin) {
            const userId = 'test_admin_iter10_' + Date.now();
            db.users.insertOne({
                user_id: userId,
                email: 'test_admin_iter10@example.com',
                name: 'Test Admin Iter10',
                role: 'admin',
                status: 'active',
                created_at: new Date()
            });
            admin = {user_id: userId};
        }
        
        // Create session
        const token = 'test_admin_session_' + Date.now();
        db.user_sessions.deleteMany({user_id: admin.user_id});
        db.user_sessions.insertOne({
            user_id: admin.user_id,
            session_token: token,
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            mfa_verified: true,
            created_at: new Date()
        });
        print(token);
        '''
    ], capture_output=True, text=True)
    
    token = result.stdout.strip().split('\n')[-1]
    return token


@pytest.fixture(scope="module")
def test_users():
    """Create test users for delete and tier change tests"""
    import subprocess
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', '''
        use('monetrax_db');
        
        // Clean up old test users
        db.users.deleteMany({email: /test_delete_iter10|test_tier_iter10/});
        
        // Create user for tier tests
        const tierUserId = 'test_tier_iter10_' + Date.now();
        db.users.insertOne({
            user_id: tierUserId,
            email: 'test_tier_iter10@example.com',
            name: 'Test Tier User Iter10',
            role: 'user',
            status: 'active',
            created_at: new Date()
        });
        
        // Create user for delete tests (will be created fresh each time)
        const deleteUserId = 'test_delete_iter10_' + Date.now();
        db.users.insertOne({
            user_id: deleteUserId,
            email: 'test_delete_iter10@example.com',
            name: 'Test Delete User Iter10',
            role: 'user',
            status: 'active',
            created_at: new Date()
        });
        
        print(JSON.stringify({delete_user_id: deleteUserId, tier_user_id: tierUserId}));
        '''
    ], capture_output=True, text=True)
    
    import json
    output = result.stdout.strip().split('\n')[-1]
    return json.loads(output)


@pytest.fixture
def create_deletable_user():
    """Create a fresh user for deletion test"""
    import subprocess
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', '''
        use('monetrax_db');
        const userId = 'deletable_user_' + Date.now();
        db.users.insertOne({
            user_id: userId,
            email: 'deletable_' + Date.now() + '@example.com',
            name: 'Deletable User',
            role: 'user',
            status: 'active',
            created_at: new Date()
        });
        print(userId);
        '''
    ], capture_output=True, text=True)
    
    return result.stdout.strip().split('\n')[-1]


@pytest.fixture
def create_another_superadmin():
    """Create another superadmin for testing"""
    import subprocess
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', '''
        use('monetrax_db');
        
        // Clean up old test superadmin
        db.users.deleteMany({email: 'test_superadmin2_iter10@example.com'});
        
        const userId = 'test_superadmin2_iter10_' + Date.now();
        db.users.insertOne({
            user_id: userId,
            email: 'test_superadmin2_iter10@example.com',
            name: 'Test Superadmin 2',
            role: 'superadmin',
            status: 'active',
            created_at: new Date()
        });
        print(userId);
        '''
    ], capture_output=True, text=True)
    
    user_id = result.stdout.strip().split('\n')[-1]
    yield user_id
    
    # Cleanup
    subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
        use('monetrax_db');
        db.users.deleteOne({{user_id: '{user_id}'}});
        '''
    ], capture_output=True, text=True)


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup(request):
    """Cleanup test data after all tests"""
    yield
    import subprocess
    subprocess.run([
        'mongosh', '--quiet', '--eval', '''
        use('monetrax_db');
        db.users.deleteMany({email: /test_.*iter10|deletable_/});
        db.user_sessions.deleteMany({session_token: /test_.*iter10|test_admin_session/});
        db.subscriptions.deleteMany({user_id: /test_.*iter10/});
        '''
    ], capture_output=True, text=True)
