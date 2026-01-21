"""
Migration script to promote a user to superadmin role.
Run this once to set up the initial superadmin.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "monetrax_db")

async def promote_to_superadmin(email: str):
    """Promote a user to superadmin role"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    users = db["users"]
    
    # Find the user
    user = await users.find_one({"email": email})
    
    if not user:
        print(f"❌ User with email '{email}' not found.")
        print("   Please ensure the user has logged in at least once.")
        return False
    
    current_role = user.get("role", "user")
    
    if current_role == "superadmin":
        print(f"✓ User '{email}' is already a superadmin.")
        return True
    
    # Update to superadmin
    result = await users.update_one(
        {"email": email},
        {"$set": {
            "role": "superadmin",
            "status": "active",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count > 0:
        print(f"✅ Successfully promoted '{email}' to superadmin!")
        print(f"   Previous role: {current_role}")
        print(f"   New role: superadmin")
        print(f"\n   The user can now access /admin")
        return True
    else:
        print(f"❌ Failed to update user '{email}'")
        return False

async def list_admins():
    """List all users with admin or superadmin roles"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    users = db["users"]
    
    admins = await users.find(
        {"role": {"$in": ["admin", "superadmin"]}},
        {"_id": 0, "email": 1, "name": 1, "role": 1}
    ).to_list(length=100)
    
    if not admins:
        print("No admins found in the system.")
        return
    
    print("\n📋 Current Admins:")
    print("-" * 50)
    for admin in admins:
        print(f"  {admin.get('role', 'user'):12} | {admin.get('email')} ({admin.get('name', 'N/A')})")
    print("-" * 50)

if __name__ == "__main__":
    import sys
    
    # Default email to promote
    TARGET_EMAIL = "eleba@hotmail.co.uk"
    
    if len(sys.argv) > 1:
        TARGET_EMAIL = sys.argv[1]
    
    print(f"\n🔐 Monetrax Admin Migration Script")
    print(f"=" * 50)
    print(f"Target email: {TARGET_EMAIL}\n")
    
    # Run the migration
    asyncio.run(promote_to_superadmin(TARGET_EMAIL))
    
    # List all admins
    asyncio.run(list_admins())
    
    print(f"\n✓ Migration complete.")
