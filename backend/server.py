"""
MFA Authentication Server with Google OAuth + TOTP + Backup Codes
"""
import os
import uuid
import secrets
import base64
import io
from datetime import datetime, timezone, timedelta
from typing import Optional

import pyotp
import qrcode
import httpx
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="MFA Auth API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "mfa_auth_db")
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Collections
users_collection = db["users"]
sessions_collection = db["user_sessions"]
mfa_collection = db["mfa_settings"]
backup_codes_collection = db["backup_codes"]


# Pydantic Models
class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    mfa_enabled: bool = False
    mfa_verified: bool = False


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str
    provisioning_uri: str


class TOTPVerifyRequest(BaseModel):
    code: str


class BackupCodesResponse(BaseModel):
    codes: list[str]
    created_at: str


class MFAStatusResponse(BaseModel):
    mfa_enabled: bool
    totp_enabled: bool
    backup_codes_count: int
    last_verified: Optional[str] = None


# Helper Functions
def generate_user_id() -> str:
    return f"user_{uuid.uuid4().hex[:12]}"


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate backup codes in format XXXX-XXXX"""
    codes = []
    for _ in range(count):
        code = f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
        codes.append(code)
    return codes


async def get_current_user(request: Request) -> dict:
    """Extract and validate user from session token"""
    # Try cookie first
    session_token = request.cookies.get("session_token")
    
    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session
    session_doc = await sessions_collection.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry with timezone awareness
    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user
    user_doc = await users_collection.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Check MFA status
    mfa_doc = await mfa_collection.find_one(
        {"user_id": user_doc["user_id"]},
        {"_id": 0}
    )
    
    user_doc["mfa_enabled"] = mfa_doc.get("totp_enabled", False) if mfa_doc else False
    user_doc["mfa_verified"] = session_doc.get("mfa_verified", False)
    
    return user_doc


# Routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/auth/session")
async def create_session(request: Request, response: Response):
    """Exchange session_id for session_token after Google OAuth"""
    data = await request.json()
    session_id = data.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    # Fetch user data from Emergent Auth
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id},
                timeout=10.0
            )
            
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session_id")
            
            user_data = auth_response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Auth service error: {str(e)}")
    
    email = user_data.get("email")
    name = user_data.get("name")
    picture = user_data.get("picture")
    
    # Check if user exists
    existing_user = await users_collection.find_one(
        {"email": email},
        {"_id": 0}
    )
    
    if existing_user:
        user_id = existing_user["user_id"]
        # Update user info if changed
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture, "updated_at": datetime.now(timezone.utc)}}
        )
    else:
        # Create new user
        user_id = generate_user_id()
        await users_collection.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "created_at": datetime.now(timezone.utc)
        })
    
    # Create session
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    # Check if user has MFA enabled
    mfa_doc = await mfa_collection.find_one({"user_id": user_id}, {"_id": 0})
    mfa_enabled = mfa_doc.get("totp_enabled", False) if mfa_doc else False
    
    await sessions_collection.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "mfa_verified": not mfa_enabled,  # If no MFA, mark as verified
        "created_at": datetime.now(timezone.utc)
    })
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    return {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "mfa_enabled": mfa_enabled,
        "mfa_verified": not mfa_enabled,
        "session_token": session_token
    }


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(**user)


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    """Logout and clear session"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await sessions_collection.delete_one({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}


# MFA - TOTP Routes
@app.post("/api/mfa/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(user: dict = Depends(get_current_user)):
    """Initialize TOTP setup - returns QR code and secret"""
    user_id = user["user_id"]
    email = user["email"]
    
    # Generate new TOTP secret
    secret = pyotp.random_base32()
    
    # Create provisioning URI for authenticator apps
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=email, issuer_name="MFA Auth App")
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # Store pending TOTP setup (not enabled yet)
    await mfa_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "totp_secret_pending": secret,
                "totp_setup_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )
    
    return TOTPSetupResponse(
        secret=secret,
        qr_code=f"data:image/png;base64,{qr_base64}",
        provisioning_uri=provisioning_uri
    )


@app.post("/api/mfa/totp/verify")
async def verify_totp(data: TOTPVerifyRequest, user: dict = Depends(get_current_user)):
    """Verify TOTP code and enable MFA"""
    user_id = user["user_id"]
    code = data.code.replace(" ", "").replace("-", "")
    
    # Get MFA settings
    mfa_doc = await mfa_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not mfa_doc:
        raise HTTPException(status_code=400, detail="TOTP setup not initiated")
    
    # Check if verifying pending setup or existing TOTP
    secret = mfa_doc.get("totp_secret") or mfa_doc.get("totp_secret_pending")
    
    if not secret:
        raise HTTPException(status_code=400, detail="No TOTP secret found")
    
    # Verify code
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    # If this is initial setup, enable TOTP
    if mfa_doc.get("totp_secret_pending") and not mfa_doc.get("totp_enabled"):
        await mfa_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "totp_secret": secret,
                    "totp_enabled": True,
                    "totp_verified_at": datetime.now(timezone.utc)
                },
                "$unset": {"totp_secret_pending": ""}
            }
        )
        
        # Generate backup codes automatically
        backup_codes = generate_backup_codes()
        await backup_codes_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "codes": [{"code": c, "used": False} for c in backup_codes],
                    "created_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        return {
            "message": "TOTP enabled successfully",
            "mfa_enabled": True,
            "backup_codes": backup_codes
        }
    
    # Regular TOTP verification for login
    return {"message": "TOTP verified", "verified": True}


@app.post("/api/mfa/totp/authenticate")
async def authenticate_totp(request: Request, data: TOTPVerifyRequest, response: Response):
    """Authenticate with TOTP during login"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get session
    session_doc = await sessions_collection.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = session_doc["user_id"]
    code = data.code.replace(" ", "").replace("-", "")
    
    # Get MFA settings
    mfa_doc = await mfa_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not mfa_doc or not mfa_doc.get("totp_enabled"):
        raise HTTPException(status_code=400, detail="TOTP not enabled")
    
    secret = mfa_doc.get("totp_secret")
    
    # Verify TOTP code
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    # Mark session as MFA verified
    await sessions_collection.update_one(
        {"session_token": session_token},
        {"$set": {"mfa_verified": True, "mfa_verified_at": datetime.now(timezone.utc)}}
    )
    
    # Get user data
    user_doc = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    return {
        "message": "MFA authentication successful",
        "user": {
            **user_doc,
            "mfa_enabled": True,
            "mfa_verified": True
        }
    }


# Backup Codes Routes
@app.get("/api/mfa/backup-codes")
async def get_backup_codes(user: dict = Depends(get_current_user)):
    """Get remaining backup codes count"""
    user_id = user["user_id"]
    
    backup_doc = await backup_codes_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not backup_doc:
        return {"codes_remaining": 0, "has_backup_codes": False}
    
    remaining = len([c for c in backup_doc.get("codes", []) if not c.get("used")])
    
    return {
        "codes_remaining": remaining,
        "has_backup_codes": remaining > 0,
        "created_at": backup_doc.get("created_at", "").isoformat() if backup_doc.get("created_at") else None
    }


@app.post("/api/mfa/backup-codes/regenerate")
async def regenerate_backup_codes(user: dict = Depends(get_current_user)):
    """Regenerate all backup codes (invalidates old ones)"""
    user_id = user["user_id"]
    
    backup_codes = generate_backup_codes()
    
    await backup_codes_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "codes": [{"code": c, "used": False} for c in backup_codes],
                "created_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )
    
    return {
        "message": "Backup codes regenerated",
        "codes": backup_codes
    }


@app.post("/api/mfa/backup-codes/verify")
async def verify_backup_code(request: Request, data: TOTPVerifyRequest, response: Response):
    """Verify backup code during login"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get session
    session_doc = await sessions_collection.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = session_doc["user_id"]
    code = data.code.upper().replace(" ", "")
    
    # Get backup codes
    backup_doc = await backup_codes_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not backup_doc:
        raise HTTPException(status_code=400, detail="No backup codes found")
    
    codes = backup_doc.get("codes", [])
    code_found = False
    
    for i, c in enumerate(codes):
        if c["code"] == code and not c["used"]:
            codes[i]["used"] = True
            codes[i]["used_at"] = datetime.now(timezone.utc).isoformat()
            code_found = True
            break
    
    if not code_found:
        raise HTTPException(status_code=400, detail="Invalid or already used backup code")
    
    # Update codes
    await backup_codes_collection.update_one(
        {"user_id": user_id},
        {"$set": {"codes": codes}}
    )
    
    # Mark session as MFA verified
    await sessions_collection.update_one(
        {"session_token": session_token},
        {"$set": {"mfa_verified": True, "mfa_verified_at": datetime.now(timezone.utc)}}
    )
    
    # Get user data
    user_doc = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    remaining = len([c for c in codes if not c.get("used")])
    
    return {
        "message": "Backup code verified",
        "codes_remaining": remaining,
        "user": {
            **user_doc,
            "mfa_enabled": True,
            "mfa_verified": True
        }
    }


# MFA Status
@app.get("/api/mfa/status", response_model=MFAStatusResponse)
async def get_mfa_status(user: dict = Depends(get_current_user)):
    """Get complete MFA status for user"""
    user_id = user["user_id"]
    
    mfa_doc = await mfa_collection.find_one({"user_id": user_id}, {"_id": 0})
    backup_doc = await backup_codes_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    totp_enabled = mfa_doc.get("totp_enabled", False) if mfa_doc else False
    backup_count = len([c for c in backup_doc.get("codes", []) if not c.get("used")]) if backup_doc else 0
    
    last_verified = None
    if mfa_doc and mfa_doc.get("totp_verified_at"):
        lv = mfa_doc["totp_verified_at"]
        last_verified = lv.isoformat() if hasattr(lv, 'isoformat') else str(lv)
    
    return MFAStatusResponse(
        mfa_enabled=totp_enabled,
        totp_enabled=totp_enabled,
        backup_codes_count=backup_count,
        last_verified=last_verified
    )


@app.post("/api/mfa/disable")
async def disable_mfa(data: TOTPVerifyRequest, user: dict = Depends(get_current_user)):
    """Disable MFA (requires current TOTP code)"""
    user_id = user["user_id"]
    code = data.code.replace(" ", "").replace("-", "")
    
    mfa_doc = await mfa_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not mfa_doc or not mfa_doc.get("totp_enabled"):
        raise HTTPException(status_code=400, detail="MFA not enabled")
    
    # Verify code before disabling
    totp = pyotp.TOTP(mfa_doc["totp_secret"])
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    # Disable MFA
    await mfa_collection.delete_one({"user_id": user_id})
    await backup_codes_collection.delete_one({"user_id": user_id})
    
    return {"message": "MFA disabled successfully", "mfa_enabled": False}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
