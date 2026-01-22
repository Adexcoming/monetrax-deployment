"""
Test Agent System - Monetrax
Tests for:
1. Promote user to agent (superadmin only)
2. Revoke agent role (superadmin only)
3. Agent dashboard
4. Agent promotional plans
5. Agent check user eligibility
6. Agent signup user
7. Agent signups list
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session tokens (will be set up in fixtures)
SUPERADMIN_SESSION = None
AGENT_SESSION = None
REGULAR_USER_SESSION = None

# Test user IDs
TEST_USER_ID = None
TEST_AGENT_ID = None


class TestSetup:
    """Setup test users and sessions"""
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_test_data(self):
        """Create test users for agent system testing"""
        global SUPERADMIN_SESSION, AGENT_SESSION, REGULAR_USER_SESSION, TEST_USER_ID, TEST_AGENT_ID
        
        # Create superadmin session using existing superadmin
        # First, let's create test users via MongoDB
        import subprocess
        
        timestamp = int(datetime.now().timestamp())
        
        # Create test regular user
        test_user_id = f"test_agent_user_{timestamp}"
        test_user_email = f"test_agent_user_{timestamp}@example.com"
        test_user_session = f"test_agent_session_{timestamp}"
        
        # Create test agent user
        test_agent_id = f"test_agent_{timestamp}"
        test_agent_email = f"test_agent_{timestamp}@example.com"
        test_agent_session = f"test_agent_session_agent_{timestamp}"
        
        # Create superadmin session
        superadmin_session = f"test_superadmin_session_{timestamp}"
        
        mongo_script = f'''
        use monetrax_db;
        
        // Create test regular user
        db.users.insertOne({{
            user_id: "{test_user_id}",
            email: "{test_user_email}",
            name: "Test Agent User",
            role: "user",
            status: "active",
            created_at: new Date()
        }});
        
        // Create session for test user
        db.user_sessions.insertOne({{
            user_id: "{test_user_id}",
            session_token: "{test_user_session}",
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            mfa_verified: true,
            created_at: new Date()
        }});
        
        // Create test agent user
        db.users.insertOne({{
            user_id: "{test_agent_id}",
            email: "{test_agent_email}",
            name: "Test Agent",
            role: "agent",
            agent_initials: "TAG",
            status: "active",
            created_at: new Date()
        }});
        
        // Create session for test agent
        db.user_sessions.insertOne({{
            user_id: "{test_agent_id}",
            session_token: "{test_agent_session}",
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            mfa_verified: true,
            created_at: new Date()
        }});
        
        // Create superadmin session (using existing superadmin user_ff38c65acecd)
        db.user_sessions.insertOne({{
            user_id: "user_ff38c65acecd",
            session_token: "{superadmin_session}",
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            mfa_verified: true,
            created_at: new Date()
        }});
        
        print("Test data created successfully");
        '''
        
        result = subprocess.run(
            ['mongosh', '--quiet', '--eval', mongo_script],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"MongoDB setup error: {result.stderr}")
        
        SUPERADMIN_SESSION = superadmin_session
        AGENT_SESSION = test_agent_session
        REGULAR_USER_SESSION = test_user_session
        TEST_USER_ID = test_user_id
        TEST_AGENT_ID = test_agent_id
        
        yield
        
        # Cleanup test data
        cleanup_script = f'''
        use monetrax_db;
        db.users.deleteMany({{user_id: /^test_agent/}});
        db.user_sessions.deleteMany({{session_token: /^test_/}});
        db.agent_signups.deleteMany({{agent_id: /^test_/}});
        print("Test data cleaned up");
        '''
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)


class TestPromoteToAgent:
    """Test /api/admin/users/{user_id}/promote-to-agent endpoint"""
    
    def test_promote_user_to_agent_success(self):
        """Superadmin can promote a regular user to agent"""
        # Create a fresh user to promote
        import subprocess
        timestamp = int(datetime.now().timestamp())
        new_user_id = f"test_promote_user_{timestamp}"
        new_user_email = f"test_promote_{timestamp}@example.com"
        
        mongo_script = f'''
        use monetrax_db;
        db.users.insertOne({{
            user_id: "{new_user_id}",
            email: "{new_user_email}",
            name: "User To Promote",
            role: "user",
            status: "active",
            created_at: new Date()
        }});
        '''
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{new_user_id}/promote-to-agent",
            params={"agent_initials": "PRM"},
            headers={"Authorization": f"Bearer {SUPERADMIN_SESSION}"}
        )
        
        print(f"Promote to agent response: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "success"
        assert "PRM" in data["agent_initials"]
        
        # Cleanup
        subprocess.run(['mongosh', '--quiet', '--eval', f'use monetrax_db; db.users.deleteOne({{user_id: "{new_user_id}"}});'], capture_output=True)
    
    def test_promote_requires_superadmin(self):
        """Non-superadmin cannot promote users to agent"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{TEST_USER_ID}/promote-to-agent",
            params={"agent_initials": "TST"},
            headers={"Authorization": f"Bearer {AGENT_SESSION}"}
        )
        
        print(f"Non-superadmin promote response: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_promote_invalid_initials_too_short(self):
        """Agent initials must be at least 2 characters"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{TEST_USER_ID}/promote-to-agent",
            params={"agent_initials": "A"},
            headers={"Authorization": f"Bearer {SUPERADMIN_SESSION}"}
        )
        
        print(f"Short initials response: {response.status_code}")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    def test_promote_invalid_initials_too_long(self):
        """Agent initials must be at most 5 characters"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{TEST_USER_ID}/promote-to-agent",
            params={"agent_initials": "TOOLONG"},
            headers={"Authorization": f"Bearer {SUPERADMIN_SESSION}"}
        )
        
        print(f"Long initials response: {response.status_code}")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    def test_promote_nonexistent_user(self):
        """Cannot promote nonexistent user"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/nonexistent_user_123/promote-to-agent",
            params={"agent_initials": "TST"},
            headers={"Authorization": f"Bearer {SUPERADMIN_SESSION}"}
        )
        
        print(f"Nonexistent user response: {response.status_code}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_promote_already_agent(self):
        """Cannot promote user who is already an agent"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{TEST_AGENT_ID}/promote-to-agent",
            params={"agent_initials": "NEW"},
            headers={"Authorization": f"Bearer {SUPERADMIN_SESSION}"}
        )
        
        print(f"Already agent response: {response.status_code}")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    def test_promote_unauthenticated(self):
        """Unauthenticated request returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{TEST_USER_ID}/promote-to-agent",
            params={"agent_initials": "TST"}
        )
        
        print(f"Unauthenticated response: {response.status_code}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestRevokeAgent:
    """Test /api/admin/users/{user_id}/revoke-agent endpoint"""
    
    def test_revoke_agent_success(self):
        """Superadmin can revoke agent role"""
        # Create a fresh agent to revoke
        import subprocess
        timestamp = int(datetime.now().timestamp())
        agent_id = f"test_revoke_agent_{timestamp}"
        
        mongo_script = f'''
        use monetrax_db;
        db.users.insertOne({{
            user_id: "{agent_id}",
            email: "test_revoke_{timestamp}@example.com",
            name: "Agent To Revoke",
            role: "agent",
            agent_initials: "RVK",
            status: "active",
            created_at: new Date()
        }});
        '''
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{agent_id}/revoke-agent",
            headers={"Authorization": f"Bearer {SUPERADMIN_SESSION}"}
        )
        
        print(f"Revoke agent response: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "success"
        
        # Cleanup
        subprocess.run(['mongosh', '--quiet', '--eval', f'use monetrax_db; db.users.deleteOne({{user_id: "{agent_id}"}});'], capture_output=True)
    
    def test_revoke_requires_superadmin(self):
        """Non-superadmin cannot revoke agent role"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{TEST_AGENT_ID}/revoke-agent",
            headers={"Authorization": f"Bearer {AGENT_SESSION}"}
        )
        
        print(f"Non-superadmin revoke response: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_revoke_non_agent(self):
        """Cannot revoke from user who is not an agent"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{TEST_USER_ID}/revoke-agent",
            headers={"Authorization": f"Bearer {SUPERADMIN_SESSION}"}
        )
        
        print(f"Non-agent revoke response: {response.status_code}")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    def test_revoke_nonexistent_user(self):
        """Cannot revoke from nonexistent user"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/nonexistent_user_123/revoke-agent",
            headers={"Authorization": f"Bearer {SUPERADMIN_SESSION}"}
        )
        
        print(f"Nonexistent user revoke response: {response.status_code}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestAgentDashboard:
    """Test /api/agent/dashboard endpoint"""
    
    def test_agent_dashboard_success(self):
        """Agent can access their dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/agent/dashboard",
            headers={"Authorization": f"Bearer {AGENT_SESSION}"}
        )
        
        print(f"Agent dashboard response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "agent_id" in data
        assert "agent_initials" in data
        assert "statistics" in data
        assert "total_signups" in data["statistics"]
        assert "promo_signups" in data["statistics"]
        assert "total_savings_given" in data["statistics"]
    
    def test_agent_dashboard_requires_agent_role(self):
        """Regular user cannot access agent dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/agent/dashboard",
            headers={"Authorization": f"Bearer {REGULAR_USER_SESSION}"}
        )
        
        print(f"Regular user dashboard response: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_agent_dashboard_unauthenticated(self):
        """Unauthenticated request returns 401"""
        response = requests.get(f"{BASE_URL}/api/agent/dashboard")
        
        print(f"Unauthenticated dashboard response: {response.status_code}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestAgentPromotionalPlans:
    """Test /api/agent/promotional-plans endpoint"""
    
    def test_promotional_plans_success(self):
        """Agent can view promotional plans"""
        response = requests.get(
            f"{BASE_URL}/api/agent/promotional-plans",
            headers={"Authorization": f"Bearer {AGENT_SESSION}"}
        )
        
        print(f"Promotional plans response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) >= 3  # starter, business, enterprise
        
        for plan in data["plans"]:
            assert "tier" in plan
            assert "name" in plan
            assert "regular_price" in plan
            assert "promo_price" in plan
            assert "savings" in plan
            assert plan["promo_price"] < plan["regular_price"]  # Promo should be cheaper
    
    def test_promotional_plans_requires_agent(self):
        """Regular user cannot view promotional plans"""
        response = requests.get(
            f"{BASE_URL}/api/agent/promotional-plans",
            headers={"Authorization": f"Bearer {REGULAR_USER_SESSION}"}
        )
        
        print(f"Regular user plans response: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"


class TestAgentCheckUser:
    """Test /api/agent/check-user/{identifier} endpoint"""
    
    def test_check_new_user_eligible(self):
        """New user (not found) is eligible for promo"""
        response = requests.get(
            f"{BASE_URL}/api/agent/check-user/newuser_test@example.com",
            headers={"Authorization": f"Bearer {AGENT_SESSION}"}
        )
        
        print(f"Check new user response: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["found"] == False
        assert data["eligible_for_promo"] == True
    
    def test_check_existing_user(self):
        """Check existing user eligibility"""
        # Use the test user email
        import subprocess
        result = subprocess.run(
            ['mongosh', '--quiet', '--eval', f'use monetrax_db; var u = db.users.findOne({{user_id: "{TEST_USER_ID}"}}); print(u ? u.email : "not_found");'],
            capture_output=True,
            text=True
        )
        test_email = result.stdout.strip()
        
        if test_email and test_email != "not_found":
            response = requests.get(
                f"{BASE_URL}/api/agent/check-user/{test_email}",
                headers={"Authorization": f"Bearer {AGENT_SESSION}"}
            )
            
            print(f"Check existing user response: {response.status_code} - {response.text}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            assert "found" in data
            assert "eligible_for_promo" in data
    
    def test_check_user_requires_agent(self):
        """Regular user cannot check user eligibility"""
        response = requests.get(
            f"{BASE_URL}/api/agent/check-user/test@example.com",
            headers={"Authorization": f"Bearer {REGULAR_USER_SESSION}"}
        )
        
        print(f"Regular user check response: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"


class TestAgentSignupUser:
    """Test /api/agent/signup-user endpoint"""
    
    def test_signup_new_user_success(self):
        """Agent can sign up a new user with promo"""
        timestamp = int(datetime.now().timestamp())
        
        response = requests.post(
            f"{BASE_URL}/api/agent/signup-user",
            json={
                "name": f"Test Signup User {timestamp}",
                "email": f"test_signup_{timestamp}@example.com",
                "tier": "starter",
                "agent_initials": "TAG"
            },
            headers={"Authorization": f"Bearer {AGENT_SESSION}"}
        )
        
        print(f"Signup user response: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "user_id" in data
        assert data["tier"] == "starter"
        assert data["promo_used"] == True
        assert data["savings"] > 0
        assert data["promo_price"] < data["regular_price"]
        
        # Cleanup
        import subprocess
        subprocess.run(['mongosh', '--quiet', '--eval', f'use monetrax_db; db.users.deleteOne({{email: "test_signup_{timestamp}@example.com"}}); db.agent_signups.deleteMany({{user_email: "test_signup_{timestamp}@example.com"}});'], capture_output=True)
    
    def test_signup_with_phone(self):
        """Agent can sign up user with phone number"""
        timestamp = int(datetime.now().timestamp())
        
        response = requests.post(
            f"{BASE_URL}/api/agent/signup-user",
            json={
                "name": f"Test Phone User {timestamp}",
                "phone": f"080{timestamp % 100000000:08d}",
                "tier": "business",
                "agent_initials": "TAG"
            },
            headers={"Authorization": f"Bearer {AGENT_SESSION}"}
        )
        
        print(f"Signup with phone response: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Cleanup
        import subprocess
        subprocess.run(['mongosh', '--quiet', '--eval', f'use monetrax_db; db.users.deleteOne({{name: "Test Phone User {timestamp}"}}); db.agent_signups.deleteMany({{user_name: "Test Phone User {timestamp}"}});'], capture_output=True)
    
    def test_signup_requires_email_or_phone(self):
        """Signup requires either email or phone"""
        response = requests.post(
            f"{BASE_URL}/api/agent/signup-user",
            json={
                "name": "Test User No Contact",
                "tier": "starter",
                "agent_initials": "TAG"
            },
            headers={"Authorization": f"Bearer {AGENT_SESSION}"}
        )
        
        print(f"No contact signup response: {response.status_code}")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    def test_signup_requires_agent_role(self):
        """Regular user cannot sign up users"""
        response = requests.post(
            f"{BASE_URL}/api/agent/signup-user",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "tier": "starter",
                "agent_initials": "TST"
            },
            headers={"Authorization": f"Bearer {REGULAR_USER_SESSION}"}
        )
        
        print(f"Regular user signup response: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"


class TestAgentSignupsList:
    """Test /api/agent/signups endpoint"""
    
    def test_signups_list_success(self):
        """Agent can view their signups list"""
        response = requests.get(
            f"{BASE_URL}/api/agent/signups",
            headers={"Authorization": f"Bearer {AGENT_SESSION}"}
        )
        
        print(f"Signups list response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "signups" in data
        assert "pagination" in data
        assert "page" in data["pagination"]
        assert "total" in data["pagination"]
    
    def test_signups_list_with_tier_filter(self):
        """Agent can filter signups by tier"""
        response = requests.get(
            f"{BASE_URL}/api/agent/signups?tier=starter",
            headers={"Authorization": f"Bearer {AGENT_SESSION}"}
        )
        
        print(f"Filtered signups response: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_signups_list_requires_agent(self):
        """Regular user cannot view signups list"""
        response = requests.get(
            f"{BASE_URL}/api/agent/signups",
            headers={"Authorization": f"Bearer {REGULAR_USER_SESSION}"}
        )
        
        print(f"Regular user signups response: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
