#!/usr/bin/env python3
"""
Migration script to set a user as superadmin.
Usage: python set_superadmin.py <email>
Example: python set_superadmin.py eleba@hotmail.co.uk
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "monetrax_db")


async def set_superadmin(email: str):
    """Set a user as superadmin by email."""
    print(f"\n{'='*50}")
    print("Monetrax - Set Superadmin Migration")
    print(f"{'='*50}\n")
    
    # Connect to MongoDB
    print(f"Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    users_collection = db["users"]
    
    try:
        # Find the user by email
        print(f"Looking for user with email: {email}")
        user = await users_collection.find_one({"email": email}, {"_id": 0})
        
        if not user:
            print(f"\n❌ Error: User with email '{email}' not found.")
            print("Please make sure the user has logged in at least once.")
            return False
        
        print(f"✓ Found user: {user.get('name', 'Unknown')} ({user.get('user_id')})")
        print(f"  Current role: {user.get('role', 'user')}")
        
        # Update the user's role to superadmin
        result = await users_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "role": "superadmin",
                    "role_updated_at": datetime.now(timezone.utc).isoformat(),
                    "role_updated_by": "migration_script"
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"\n✅ Success! User '{user.get('name')}' is now a superadmin.")
            print(f"   Email: {email}")
            print(f"   User ID: {user.get('user_id')}")
        else:
            # Check if already superadmin
            if user.get('role') == 'superadmin':
                print(f"\nℹ️  User '{user.get('name')}' is already a superadmin.")
            else:
                print(f"\n⚠️  No changes made. Please check the database.")
        
        # Verify the change
        updated_user = await users_collection.find_one({"email": email}, {"_id": 0})
        print(f"\n   Verified role: {updated_user.get('role')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False
    finally:
        client.close()
        print(f"\n{'='*50}\n")


def main():
    if len(sys.argv) < 2:
        # Default to the specified email if no argument provided
        email = "eleba@hotmail.co.uk"
        print(f"No email provided, using default: {email}")
    else:
        email = sys.argv[1]
    
    # Run the async function
    success = asyncio.run(set_superadmin(email))
    
    if success:
        print("Migration completed successfully!")
        print("\nNext steps:")
        print("  1. Log out and log back in to refresh your session")
        print("  2. Navigate to /admin to access the admin panel")
    else:
        print("Migration failed. Please check the error above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
