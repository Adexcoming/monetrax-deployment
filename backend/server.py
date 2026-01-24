"""
Monetrax - Financial OS for Nigerian MSMEs
Complete backend with Tax Compliance, Transaction Management, AI Insights
"""
import os
import uuid
import secrets
import base64
import io
import re
import random
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from decimal import Decimal

import pyotp
import qrcode
import httpx
import resend
import bcrypt
from fastapi import FastAPI, HTTPException, Request, Response, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Resend
resend.api_key = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

app = FastAPI(title="Monetrax API", description="Financial OS for Nigerian MSMEs")

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
DB_NAME = os.environ.get("DB_NAME", "monetrax_db")
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Collections
users_collection = db["users"]
sessions_collection = db["user_sessions"]
mfa_collection = db["mfa_settings"]
backup_codes_collection = db["backup_codes"]
businesses_collection = db["businesses"]
transactions_collection = db["transactions"]
tax_records_collection = db["tax_records"]

# ============== NIGERIAN TAX CONSTANTS ==============
VAT_RATE = 0.075  # 7.5% VAT
TAX_FREE_THRESHOLD = 800000  # ₦800,000 tax-free threshold (2025)

# Progressive Income Tax Rates (Nigeria)
INCOME_TAX_BRACKETS = [
    (300000, 0.07),      # First ₦300,000 - 7%
    (300000, 0.11),      # Next ₦300,000 - 11%
    (500000, 0.15),      # Next ₦500,000 - 15%
    (500000, 0.19),      # Next ₦500,000 - 19%
    (1600000, 0.21),     # Next ₦1,600,000 - 21%
    (float('inf'), 0.24) # Above ₦3,200,000 - 24%
]

# Tax Categories
TAXABLE_INCOME_CATEGORIES = ["Sales", "Services", "Consulting", "Rental Income", "Commission", "Interest"]
DEDUCTIBLE_EXPENSE_CATEGORIES = ["Rent", "Utilities", "Salaries", "Equipment", "Supplies", "Transport", "Marketing"]

# ============== VAT EXEMPTION CATEGORIES (Nigerian Tax Law Compliance) ==============
VAT_EXEMPT_CATEGORIES = {
    # Food & Household Essentials
    "Basic Food": True,
    "Baby Products": True,
    "Sanitary Products": True,
    
    # Medical & Pharmaceutical
    "Medical": True,
    "Pharmaceutical": True,
    "Healthcare": True,
    "Medical Equipment": True,
    
    # Education
    "Education": True,
    "Books": True,
    "Educational Materials": True,
    "Tuition": True,
    
    # Agriculture
    "Agriculture": True,
    "Fertilizers": True,
    "Seeds": True,
    "Animal Feed": True,
    "Farm Equipment": True,
    "Livestock": True,
    
    # Energy & Petroleum
    "Fuel": True,
    "Diesel": True,
    "LPG": True,
    "Gas": True,
    "Electricity": True,
    "Clean Energy": True,
    
    # Transportation
    "Public Transport": True,
    "Bus Fare": True,
    "Ferry": True,
    "Economy Flight": True,
    
    # Real Estate & Land
    "Land Sale": True,
    "Residential Property": True,
    "Residential Rent": True,
    
    # Financial Services
    "Bank Charges": True,
    "Loan Interest": True,
    "Life Insurance": True,
    "Pension": True,
    
    # Diplomatic & Humanitarian
    "Diplomatic": True,
    "Humanitarian": True,
    "Relief Materials": True,
}

# Keywords for auto-detecting VAT-exempt transactions
VAT_EXEMPT_KEYWORDS = [
    # Food & Essentials
    "rice", "beans", "yam", "cassava", "maize", "bread", "fish", "meat", "poultry", 
    "milk", "fruit", "vegetable", "baby food", "diaper", "sanitary pad", "tampon",
    # Medical
    "drug", "medicine", "pharmaceutical", "hospital", "clinic", "medical", "doctor",
    "pharmacy", "health", "diagnostic", "wheelchair", "prosthetic",
    # Education
    "book", "textbook", "school", "tuition", "education", "university", "college",
    # Agriculture
    "fertilizer", "seed", "seedling", "tractor", "farm", "feed", "livestock", "poultry feed",
    # Energy
    "diesel", "petrol", "fuel", "lpg", "gas", "electricity", "nepa", "phcn",
    # Transport
    "bus fare", "taxi", "uber", "bolt", "ferry", "danfo", "keke",
    # Financial
    "bank charge", "interest", "insurance premium", "pension",
]

# Income Tax Exempt Categories (Company/Personal)
INCOME_TAX_EXEMPT_CATEGORIES = {
    "Pension Contribution": True,
    "Life Insurance Premium": True,
    "National Housing Fund": True,
    "Gratuity": True,
    "Reimbursement": True,
    "Charity Donation": True,
    "Agricultural Income": True,
    "Export Income": True,
    "Government Bond Interest": True,
}

# ============== MULTI-CURRENCY SUPPORT ==============
# Exchange rates relative to NGN (Nigerian Naira)
# These should be updated regularly in production
CURRENCY_RATES = {
    "NGN": {"rate": 1, "symbol": "₦", "name": "Nigerian Naira"},
    "USD": {"rate": 1550, "symbol": "$", "name": "US Dollar"},
    "GBP": {"rate": 1950, "symbol": "£", "name": "British Pound"},
    "EUR": {"rate": 1680, "symbol": "€", "name": "Euro"},
    "CAD": {"rate": 1100, "symbol": "C$", "name": "Canadian Dollar"},
    "AUD": {"rate": 1000, "symbol": "A$", "name": "Australian Dollar"},
    "GHS": {"rate": 95, "symbol": "₵", "name": "Ghanaian Cedi"},
    "KES": {"rate": 12, "symbol": "KSh", "name": "Kenyan Shilling"},
    "ZAR": {"rate": 85, "symbol": "R", "name": "South African Rand"},
    "INR": {"rate": 18.5, "symbol": "₹", "name": "Indian Rupee"},
    "AED": {"rate": 420, "symbol": "د.إ", "name": "UAE Dirham"},
    "CNY": {"rate": 215, "symbol": "¥", "name": "Chinese Yuan"},
}

def convert_currency(amount_ngn: float, target_currency: str) -> float:
    """Convert NGN amount to target currency"""
    if target_currency not in CURRENCY_RATES:
        return amount_ngn
    rate = CURRENCY_RATES[target_currency]["rate"]
    return round(amount_ngn / rate, 2)

def convert_to_ngn(amount: float, source_currency: str) -> float:
    """Convert amount from source currency to NGN"""
    if source_currency not in CURRENCY_RATES:
        return amount
    rate = CURRENCY_RATES[source_currency]["rate"]
    return round(amount * rate, 2)


# ============== PYDANTIC MODELS ==============
class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "user"
    status: str = "active"
    mfa_enabled: bool = False
    mfa_verified: bool = False


# Email/Password Auth Models
class EmailSignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2)


class EmailLoginRequest(BaseModel):
    email: EmailStr
    password: str


# Phone Auth Models
class PhoneSignupRequest(BaseModel):
    phone: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')
    name: str = Field(..., min_length=2)


class PhoneVerifyRequest(BaseModel):
    phone: str
    code: str = Field(..., min_length=6, max_length=6)


class PhoneSendOTPRequest(BaseModel):
    phone: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')


class BusinessCreate(BaseModel):
    business_name: str
    business_type: str = "Sole Proprietorship"
    industry: str = "Retail"
    tin: Optional[str] = None
    annual_turnover: Optional[float] = 0


class BusinessResponse(BaseModel):
    business_id: str
    user_id: str
    business_name: str
    business_type: str
    industry: str
    tin: Optional[str] = None
    annual_turnover: float = 0
    created_at: str


class TransactionCreate(BaseModel):
    type: str  # income or expense
    category: str
    amount: float
    description: str
    date: Optional[str] = None
    is_taxable: bool = True
    payment_method: Optional[str] = "Cash"


class TransactionResponse(BaseModel):
    transaction_id: str
    business_id: str
    type: str
    category: str
    amount: float
    description: str
    date: str
    is_taxable: bool
    vat_amount: float = 0
    payment_method: str
    created_at: str


class TaxSummary(BaseModel):
    period: str
    total_income: float
    total_expenses: float
    profit: float
    taxable_income: float
    vat_collected: float
    vat_paid: float
    net_vat: float
    income_tax: float
    total_tax_liability: float
    tax_readiness_score: int


class FinancialSummary(BaseModel):
    income: float
    expenses: float
    profit: float
    vat_collected: float
    vat_paid: float
    net_vat: float
    estimated_income_tax: float
    total_tax_due: float
    net_profit: float
    transaction_count: int
    tax_readiness_score: int


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str
    provisioning_uri: str


class TOTPVerifyRequest(BaseModel):
    code: str


class AIInsightRequest(BaseModel):
    query: str


# ============== HELPER FUNCTIONS ==============
def generate_id(prefix: str = "") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}" if prefix else uuid.uuid4().hex[:12]


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def generate_backup_codes(count: int = 10) -> list[str]:
    return [f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}" for _ in range(count)]


def calculate_vat(amount: float, is_income: bool = True) -> float:
    """Calculate VAT amount (7.5%)"""
    return round(amount * VAT_RATE, 2)


def calculate_income_tax(annual_income: float) -> float:
    """Calculate Nigerian progressive income tax"""
    if annual_income <= TAX_FREE_THRESHOLD:
        return 0
    
    taxable = annual_income - TAX_FREE_THRESHOLD
    tax = 0
    remaining = taxable
    
    for bracket_amount, rate in INCOME_TAX_BRACKETS:
        if remaining <= 0:
            break
        taxable_in_bracket = min(remaining, bracket_amount)
        tax += taxable_in_bracket * rate
        remaining -= taxable_in_bracket
    
    return round(tax, 2)


def calculate_tax_readiness(transactions: list, has_tin: bool = False) -> int:
    """Calculate tax readiness score (0-100)"""
    score = 0
    
    # Has transactions recorded (30 points)
    if len(transactions) > 0:
        score += 15
    if len(transactions) > 10:
        score += 15
    
    # Has income recorded (25 points)
    income_count = len([t for t in transactions if t.get("type") == "income"])
    if income_count > 0:
        score += 15
    if income_count > 5:
        score += 10
    
    # Has expenses recorded (20 points)
    expense_count = len([t for t in transactions if t.get("type") == "expense"])
    if expense_count > 0:
        score += 10
    if expense_count > 5:
        score += 10
    
    # Has TIN (15 points)
    if has_tin:
        score += 15
    
    # Regular recording (10 points)
    if len(transactions) > 0:
        dates = [t.get("date") for t in transactions if t.get("date")]
        if len(set(dates)) > 3:  # Multiple unique dates
            score += 10
    
    return min(score, 100)


async def get_current_user(request: Request) -> dict:
    """Extract and validate user from session token"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_doc = await sessions_collection.find_one({"session_token": session_token}, {"_id": 0})
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    user_doc = await users_collection.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Check if user is suspended
    if user_doc.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended")
    
    mfa_doc = await mfa_collection.find_one({"user_id": user_doc["user_id"]}, {"_id": 0})
    user_doc["mfa_enabled"] = mfa_doc.get("totp_enabled", False) if mfa_doc else False
    user_doc["mfa_verified"] = session_doc.get("mfa_verified", False)
    user_doc["role"] = user_doc.get("role", "user")  # Default to user role
    
    return user_doc


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require admin or superadmin role"""
    role = user.get("role", "user")
    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_superadmin(user: dict = Depends(get_current_user)) -> dict:
    """Require superadmin role"""
    role = user.get("role", "user")
    if role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return user


async def require_agent(user: dict = Depends(get_current_user)) -> dict:
    """Require agent, admin, or superadmin role"""
    role = user.get("role", "user")
    if role not in ["agent", "admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Agent access required")
    return user


async def get_user_business(user_id: str) -> Optional[dict]:
    """Get user's business"""
    return await businesses_collection.find_one({"user_id": user_id}, {"_id": 0})


# ============== ROUTES ==============

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Monetrax", "timestamp": datetime.now(timezone.utc).isoformat()}


# ============== AUTH ROUTES ==============

@app.post("/api/auth/session")
async def create_session(request: Request, response: Response):
    """Exchange session_id for session_token after Google OAuth"""
    data = await request.json()
    session_id = data.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    async with httpx.AsyncClient() as http_client:
        try:
            auth_response = await http_client.get(
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
    
    existing_user = await users_collection.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user["user_id"]
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture, "updated_at": datetime.now(timezone.utc)}}
        )
        role = existing_user.get("role", "user")
    else:
        user_id = generate_id("user")
        role = "user"  # Default role for new users
        await users_collection.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "role": role,
            "status": "active",
            "created_at": datetime.now(timezone.utc)
        })
    
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    mfa_doc = await mfa_collection.find_one({"user_id": user_id}, {"_id": 0})
    mfa_enabled = mfa_doc.get("totp_enabled", False) if mfa_doc else False
    
    await sessions_collection.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "mfa_verified": not mfa_enabled,
        "created_at": datetime.now(timezone.utc)
    })
    
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
        "role": role,
        "mfa_enabled": mfa_enabled,
        "mfa_verified": not mfa_enabled,
        "session_token": session_token
    }


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(**user)


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if session_token:
        await sessions_collection.delete_one({"session_token": session_token})
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}


# ============== EMAIL/PASSWORD AUTH ==============

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


@app.post("/api/auth/email/signup")
async def email_signup(data: EmailSignupRequest, response: Response):
    """Register a new user with email and password"""
    # Check if email already exists
    existing_user = await users_collection.find_one({"email": data.email.lower()}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered. Please login instead.")
    
    # Create user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    hashed_password = hash_password(data.password)
    
    await users_collection.insert_one({
        "user_id": user_id,
        "email": data.email.lower(),
        "name": data.name,
        "password_hash": hashed_password,
        "auth_provider": "email",
        "role": "user",
        "status": "active",
        "email_verified": False,
        "created_at": datetime.now(timezone.utc)
    })
    
    # Create session
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    await sessions_collection.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "mfa_verified": True,
        "created_at": datetime.now(timezone.utc)
    })
    
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
        "email": data.email.lower(),
        "name": data.name,
        "role": "user",
        "mfa_enabled": False,
        "mfa_verified": True,
        "session_token": session_token
    }


@app.post("/api/auth/email/login")
async def email_login(data: EmailLoginRequest, response: Response):
    """Login with email and password"""
    user = await users_collection.find_one({"email": data.email.lower()}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user registered with a different auth provider
    auth_provider = user.get("auth_provider", "google")
    if auth_provider != "email" and not user.get("password_hash"):
        raise HTTPException(
            status_code=400, 
            detail=f"This account uses {auth_provider} login. Please use '{auth_provider.title()}' to sign in."
        )
    
    if not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Your account has been suspended")
    
    # Create session
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    mfa_doc = await mfa_collection.find_one({"user_id": user["user_id"]}, {"_id": 0})
    mfa_enabled = mfa_doc.get("totp_enabled", False) if mfa_doc else False
    
    await sessions_collection.insert_one({
        "user_id": user["user_id"],
        "session_token": session_token,
        "expires_at": expires_at,
        "mfa_verified": not mfa_enabled,
        "created_at": datetime.now(timezone.utc)
    })
    
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
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "role": user.get("role", "user"),
        "mfa_enabled": mfa_enabled,
        "mfa_verified": not mfa_enabled,
        "session_token": session_token
    }


# ============== PHONE AUTH ==============

# In-memory OTP storage (in production, use Redis or database)
phone_otp_store = {}


def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


@app.post("/api/auth/phone/send-otp")
async def phone_send_otp(data: PhoneSendOTPRequest):
    """Send OTP to phone number for verification"""
    phone = data.phone.replace(" ", "").replace("-", "")
    
    # Normalize Nigerian phone numbers
    if phone.startswith("0"):
        phone = "+234" + phone[1:]
    elif not phone.startswith("+"):
        phone = "+234" + phone
    
    # Generate OTP
    otp = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Store OTP (in production, send via SMS using Twilio/Termii)
    phone_otp_store[phone] = {
        "otp": otp,
        "expires_at": expires_at,
        "attempts": 0
    }
    
    # NOTE: In production, integrate with SMS provider like Twilio or Termii
    # For now, we'll log the OTP (remove in production!)
    logger.info(f"OTP for {phone}: {otp} (Development only - remove in production)")
    
    # Check if user exists for this phone
    existing_user = await users_collection.find_one({"phone": phone}, {"_id": 0})
    
    return {
        "message": "OTP sent successfully",
        "phone": phone,
        "is_new_user": existing_user is None,
        # Remove this in production - only for testing!
        "dev_otp": otp
    }


@app.post("/api/auth/phone/verify")
async def phone_verify_otp(data: PhoneVerifyRequest, response: Response):
    """Verify OTP and login/signup user"""
    phone = data.phone.replace(" ", "").replace("-", "")
    
    # Normalize Nigerian phone numbers
    if phone.startswith("0"):
        phone = "+234" + phone[1:]
    elif not phone.startswith("+"):
        phone = "+234" + phone
    
    # Check OTP
    stored = phone_otp_store.get(phone)
    if not stored:
        raise HTTPException(status_code=400, detail="No OTP found for this number. Please request a new one.")
    
    if stored["attempts"] >= 3:
        del phone_otp_store[phone]
        raise HTTPException(status_code=400, detail="Too many attempts. Please request a new OTP.")
    
    if datetime.now(timezone.utc) > stored["expires_at"]:
        del phone_otp_store[phone]
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")
    
    if stored["otp"] != data.code:
        stored["attempts"] += 1
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # OTP is valid - remove it
    del phone_otp_store[phone]
    
    # Check if user exists
    user = await users_collection.find_one({"phone": phone}, {"_id": 0})
    
    if not user:
        # This is a new user - they need to provide their name
        # Return a token for completing registration
        temp_token = secrets.token_urlsafe(32)
        phone_otp_store[f"verified_{temp_token}"] = {
            "phone": phone,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
        return {
            "status": "needs_registration",
            "temp_token": temp_token,
            "message": "Phone verified. Please complete registration."
        }
    
    # Existing user - create session
    if user.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Your account has been suspended")
    
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    mfa_doc = await mfa_collection.find_one({"user_id": user["user_id"]}, {"_id": 0})
    mfa_enabled = mfa_doc.get("totp_enabled", False) if mfa_doc else False
    
    await sessions_collection.insert_one({
        "user_id": user["user_id"],
        "session_token": session_token,
        "expires_at": expires_at,
        "mfa_verified": not mfa_enabled,
        "created_at": datetime.now(timezone.utc)
    })
    
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
        "status": "authenticated",
        "user_id": user["user_id"],
        "email": user.get("email", ""),
        "phone": user["phone"],
        "name": user["name"],
        "picture": user.get("picture"),
        "role": user.get("role", "user"),
        "mfa_enabled": mfa_enabled,
        "mfa_verified": not mfa_enabled,
        "session_token": session_token
    }


@app.post("/api/auth/phone/complete-signup")
async def phone_complete_signup(request: Request, response: Response):
    """Complete phone signup with user details"""
    data = await request.json()
    temp_token = data.get("temp_token")
    name = data.get("name", "").strip()
    
    if not temp_token or not name:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Verify temp token
    stored = phone_otp_store.get(f"verified_{temp_token}")
    if not stored:
        raise HTTPException(status_code=400, detail="Invalid or expired token. Please start again.")
    
    if datetime.now(timezone.utc) > stored["expires_at"]:
        del phone_otp_store[f"verified_{temp_token}"]
        raise HTTPException(status_code=400, detail="Token expired. Please start again.")
    
    phone = stored["phone"]
    del phone_otp_store[f"verified_{temp_token}"]
    
    # Check if user already exists
    existing = await users_collection.find_one({"phone": phone}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    
    await users_collection.insert_one({
        "user_id": user_id,
        "phone": phone,
        "name": name,
        "auth_provider": "phone",
        "role": "user",
        "status": "active",
        "phone_verified": True,
        "created_at": datetime.now(timezone.utc)
    })
    
    # Create session
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    await sessions_collection.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "mfa_verified": True,
        "created_at": datetime.now(timezone.utc)
    })
    
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
        "phone": phone,
        "name": name,
        "role": "user",
        "mfa_enabled": False,
        "mfa_verified": True,
        "session_token": session_token
    }


# ============== MFA ROUTES ==============

@app.post("/api/mfa/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    email = user["email"]
    
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=email, issuer_name="Monetrax")
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    await mfa_collection.update_one(
        {"user_id": user_id},
        {"$set": {"totp_secret_pending": secret, "totp_setup_at": datetime.now(timezone.utc)}},
        upsert=True
    )
    
    return TOTPSetupResponse(secret=secret, qr_code=f"data:image/png;base64,{qr_base64}", provisioning_uri=provisioning_uri)


@app.post("/api/mfa/totp/verify")
async def verify_totp(data: TOTPVerifyRequest, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    code = data.code.replace(" ", "").replace("-", "")
    
    mfa_doc = await mfa_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not mfa_doc:
        raise HTTPException(status_code=400, detail="TOTP setup not initiated")
    
    secret = mfa_doc.get("totp_secret") or mfa_doc.get("totp_secret_pending")
    
    if not secret:
        raise HTTPException(status_code=400, detail="No TOTP secret found")
    
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    if mfa_doc.get("totp_secret_pending") and not mfa_doc.get("totp_enabled"):
        await mfa_collection.update_one(
            {"user_id": user_id},
            {"$set": {"totp_secret": secret, "totp_enabled": True, "totp_verified_at": datetime.now(timezone.utc)}, "$unset": {"totp_secret_pending": ""}}
        )
        
        backup_codes = generate_backup_codes()
        await backup_codes_collection.update_one(
            {"user_id": user_id},
            {"$set": {"codes": [{"code": c, "used": False} for c in backup_codes], "created_at": datetime.now(timezone.utc)}},
            upsert=True
        )
        
        return {"message": "TOTP enabled successfully", "mfa_enabled": True, "backup_codes": backup_codes}
    
    return {"message": "TOTP verified", "verified": True}


@app.post("/api/mfa/totp/authenticate")
async def authenticate_totp(request: Request, data: TOTPVerifyRequest, response: Response):
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_doc = await sessions_collection.find_one({"session_token": session_token}, {"_id": 0})
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = session_doc["user_id"]
    code = data.code.replace(" ", "").replace("-", "")
    
    mfa_doc = await mfa_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not mfa_doc or not mfa_doc.get("totp_enabled"):
        raise HTTPException(status_code=400, detail="TOTP not enabled")
    
    totp = pyotp.TOTP(mfa_doc.get("totp_secret"))
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    await sessions_collection.update_one(
        {"session_token": session_token},
        {"$set": {"mfa_verified": True, "mfa_verified_at": datetime.now(timezone.utc)}}
    )
    
    user_doc = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    return {"message": "MFA authentication successful", "user": {**user_doc, "mfa_enabled": True, "mfa_verified": True}}


@app.get("/api/mfa/status")
async def get_mfa_status(user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    
    mfa_doc = await mfa_collection.find_one({"user_id": user_id}, {"_id": 0})
    backup_doc = await backup_codes_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    totp_enabled = mfa_doc.get("totp_enabled", False) if mfa_doc else False
    backup_count = len([c for c in backup_doc.get("codes", []) if not c.get("used")]) if backup_doc else 0
    
    return {"mfa_enabled": totp_enabled, "totp_enabled": totp_enabled, "backup_codes_count": backup_count}


@app.post("/api/mfa/backup-codes/verify")
async def verify_backup_code(request: Request, data: TOTPVerifyRequest, response: Response):
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_doc = await sessions_collection.find_one({"session_token": session_token}, {"_id": 0})
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = session_doc["user_id"]
    code = data.code.upper().replace(" ", "")
    
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
    
    await backup_codes_collection.update_one({"user_id": user_id}, {"$set": {"codes": codes}})
    
    await sessions_collection.update_one(
        {"session_token": session_token},
        {"$set": {"mfa_verified": True, "mfa_verified_at": datetime.now(timezone.utc)}}
    )
    
    user_doc = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    return {"message": "Backup code verified", "codes_remaining": len([c for c in codes if not c.get("used")]), "user": {**user_doc, "mfa_enabled": True, "mfa_verified": True}}


# ============== BUSINESS ROUTES ==============

@app.post("/api/business", response_model=BusinessResponse)
async def create_business(data: BusinessCreate, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    
    existing = await businesses_collection.find_one({"user_id": user_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Business already exists for this user")
    
    business_id = generate_id("biz")
    now = datetime.now(timezone.utc)
    
    business = {
        "business_id": business_id,
        "user_id": user_id,
        "business_name": data.business_name,
        "business_type": data.business_type,
        "industry": data.industry,
        "tin": data.tin,
        "annual_turnover": data.annual_turnover or 0,
        "created_at": now.isoformat()
    }
    
    await businesses_collection.insert_one(business)
    
    return BusinessResponse(**business)


@app.get("/api/business")
async def get_business(user: dict = Depends(get_current_user)):
    business = await get_user_business(user["user_id"])
    if not business:
        return None
    return BusinessResponse(**business)


@app.patch("/api/business")
async def update_business(data: BusinessCreate, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    
    result = await businesses_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "business_name": data.business_name,
            "business_type": data.business_type,
            "industry": data.industry,
            "tin": data.tin,
            "annual_turnover": data.annual_turnover,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business = await get_user_business(user_id)
    return BusinessResponse(**business)


# ============== TRANSACTION ROUTES ==============

@app.post("/api/transactions", response_model=TransactionResponse)
async def create_transaction(data: TransactionCreate, user: dict = Depends(get_current_user)):
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=400, detail="Please create a business first")
    
    # Check subscription limits
    user_id = user["user_id"]
    subscription = await subscriptions_collection.find_one({"user_id": user_id}, {"_id": 0})
    tier = subscription.get("tier", "free") if subscription else "free"
    tier_data = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])
    
    now = datetime.now(timezone.utc)
    
    # Check if paid subscription has expired
    if subscription and tier != "free":
        current_period_end = subscription.get("current_period_end")
        if current_period_end:
            if isinstance(current_period_end, str):
                period_end = datetime.fromisoformat(current_period_end.replace('Z', '+00:00'))
            else:
                period_end = current_period_end
            
            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)
            
            # Subscription has expired - user can only view, not add
            if period_end < now:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "subscription_expired",
                        "message": f"Your {tier_data['name']} subscription has expired. Please renew to add new transactions.",
                        "tier": tier,
                        "expired_at": period_end.isoformat(),
                        "can_view": True,
                        "can_add": False,
                        "renewal_required": True
                    }
                )
    
    # Get transaction limit for this tier
    tx_limit = tier_data["features"]["transactions_per_month"]
    
    # If not unlimited (-1), check transaction count
    if tx_limit != -1:
        if tier == "free":
            # FREE TIER: 50 transactions TOTAL (not monthly)
            # Check if user ever had a paid subscription (no re-trial)
            had_paid = user.get("had_paid_subscription", False)
            if not had_paid and subscription:
                had_paid = await payment_transactions_collection.find_one(
                    {"user_id": user_id, "status": "completed"},
                    {"_id": 0}
                ) is not None
            
            if had_paid:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "free_trial_expired",
                        "message": "Free tier is not available after having a paid subscription. Please upgrade to continue.",
                        "tier": tier,
                        "upgrade_required": True
                    }
                )
            
            # Count TOTAL transactions (not monthly) for free tier
            total_tx_count = await transactions_collection.count_documents({
                "business_id": business["business_id"]
            })
            
            if total_tx_count >= tx_limit:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "free_limit_exceeded",
                        "message": f"You have reached the free tier limit of {tx_limit} total transactions. Upgrade to continue tracking your finances.",
                        "current_count": total_tx_count,
                        "limit": tx_limit,
                        "tier": tier,
                        "upgrade_required": True
                    }
                )
        else:
            # PAID TIERS: Monthly transaction limit
            month_start = now.replace(day=1).strftime("%Y-%m-%d")
            
            # Count transactions this month
            monthly_tx_count = await transactions_collection.count_documents({
                "business_id": business["business_id"],
                "date": {"$gte": month_start}
            })
            
            if monthly_tx_count >= tx_limit:
                raise HTTPException(
                    status_code=403, 
                    detail={
                        "error": "monthly_limit_exceeded",
                        "message": f"You have reached your monthly limit of {tx_limit} transactions on the {tier_data['name']} plan. Your limit resets next month.",
                        "current_count": monthly_tx_count,
                        "limit": tx_limit,
                        "tier": tier,
                        "resets_at": (now.replace(day=1) + timedelta(days=32)).replace(day=1).isoformat(),
                        "upgrade_available": tier != "enterprise"
                    }
                )
    
    transaction_id = generate_id("txn")
    
    # Calculate VAT
    vat_amount = 0
    if data.is_taxable:
        vat_amount = calculate_vat(data.amount, data.type == "income")
    
    transaction = {
        "transaction_id": transaction_id,
        "business_id": business["business_id"],
        "type": data.type,
        "category": data.category,
        "amount": data.amount,
        "description": data.description,
        "date": data.date or now.strftime("%Y-%m-%d"),
        "is_taxable": data.is_taxable,
        "vat_amount": vat_amount,
        "payment_method": data.payment_method or "Cash",
        "created_at": now.isoformat()
    }
    
    await transactions_collection.insert_one(transaction)
    
    return TransactionResponse(**transaction)


@app.get("/api/transactions")
async def get_transactions(
    limit: int = 50,
    skip: int = 0,
    type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    business = await get_user_business(user["user_id"])
    if not business:
        return []
    
    query = {"business_id": business["business_id"]}
    
    if type:
        query["type"] = type
    
    if start_date:
        query["date"] = {"$gte": start_date}
    
    if end_date:
        if "date" in query:
            query["date"]["$lte"] = end_date
        else:
            query["date"] = {"$lte": end_date}
    
    cursor = transactions_collection.find(query, {"_id": 0}).sort("date", -1).skip(skip).limit(limit)
    transactions = await cursor.to_list(length=limit)
    
    return transactions


@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await transactions_collection.delete_one({
        "transaction_id": transaction_id,
        "business_id": business["business_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {"message": "Transaction deleted"}


# ============== FINANCIAL SUMMARY ROUTES ==============

@app.get("/api/summary", response_model=FinancialSummary)
async def get_financial_summary(
    period: str = "month",  # month, year, all
    user: dict = Depends(get_current_user)
):
    business = await get_user_business(user["user_id"])
    if not business:
        return FinancialSummary(
            income=0, expenses=0, profit=0, vat_collected=0, vat_paid=0,
            net_vat=0, estimated_income_tax=0, total_tax_due=0, net_profit=0,
            transaction_count=0, tax_readiness_score=0
        )
    
    # Build date filter
    now = datetime.now(timezone.utc)
    query = {"business_id": business["business_id"]}
    
    if period == "month":
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
        query["date"] = {"$gte": start_date}
    elif period == "year":
        start_date = now.replace(month=1, day=1).strftime("%Y-%m-%d")
        query["date"] = {"$gte": start_date}
    
    cursor = transactions_collection.find(query, {"_id": 0})
    transactions = await cursor.to_list(length=10000)
    
    # Calculate totals
    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    profit = income - expenses
    
    vat_collected = sum(t.get("vat_amount", 0) for t in transactions if t["type"] == "income" and t.get("is_taxable"))
    vat_paid = sum(t.get("vat_amount", 0) for t in transactions if t["type"] == "expense" and t.get("is_taxable"))
    net_vat = vat_collected - vat_paid
    
    # Estimate annual income tax
    annual_income = income * (12 if period == "month" else 1 if period == "year" else 1)
    estimated_income_tax = calculate_income_tax(annual_income)
    if period == "month":
        estimated_income_tax = estimated_income_tax / 12
    
    total_tax_due = net_vat + estimated_income_tax
    net_profit = profit - total_tax_due
    
    tax_readiness = calculate_tax_readiness(transactions, bool(business.get("tin")))
    
    return FinancialSummary(
        income=round(income, 2),
        expenses=round(expenses, 2),
        profit=round(profit, 2),
        vat_collected=round(vat_collected, 2),
        vat_paid=round(vat_paid, 2),
        net_vat=round(net_vat, 2),
        estimated_income_tax=round(estimated_income_tax, 2),
        total_tax_due=round(total_tax_due, 2),
        net_profit=round(net_profit, 2),
        transaction_count=len(transactions),
        tax_readiness_score=tax_readiness
    )


# ============== TAX ROUTES ==============

@app.get("/api/tax/summary")
async def get_tax_summary(year: int = None, user: dict = Depends(get_current_user)):
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    current_year = year or datetime.now().year
    start_date = f"{current_year}-01-01"
    end_date = f"{current_year}-12-31"
    
    cursor = transactions_collection.find({
        "business_id": business["business_id"],
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0})
    transactions = await cursor.to_list(length=10000)
    
    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    profit = income - expenses
    
    taxable_income = sum(t["amount"] for t in transactions if t["type"] == "income" and t.get("is_taxable", True))
    
    vat_collected = sum(t.get("vat_amount", 0) for t in transactions if t["type"] == "income" and t.get("is_taxable"))
    vat_paid = sum(t.get("vat_amount", 0) for t in transactions if t["type"] == "expense" and t.get("is_taxable"))
    
    income_tax = calculate_income_tax(taxable_income)
    
    return TaxSummary(
        period=f"Year {current_year}",
        total_income=round(income, 2),
        total_expenses=round(expenses, 2),
        profit=round(profit, 2),
        taxable_income=round(taxable_income, 2),
        vat_collected=round(vat_collected, 2),
        vat_paid=round(vat_paid, 2),
        net_vat=round(vat_collected - vat_paid, 2),
        income_tax=round(income_tax, 2),
        total_tax_liability=round((vat_collected - vat_paid) + income_tax, 2),
        tax_readiness_score=calculate_tax_readiness(transactions, bool(business.get("tin")))
    )


@app.get("/api/tax/calendar")
async def get_tax_calendar():
    """Get Nigerian tax deadlines"""
    current_year = datetime.now().year
    next_month = (datetime.now().month % 12) + 1
    next_year = current_year if next_month > 1 else current_year + 1
    
    return {
        "deadlines": [
            {
                "name": "Monthly VAT Filing",
                "date": f"{next_year}-{next_month:02d}-21",
                "description": "VAT returns for the previous month",
                "type": "vat"
            },
            {
                "name": "Annual Income Tax",
                "date": f"{current_year + 1}-03-31",
                "description": "Self-assessment tax filing deadline",
                "type": "income_tax"
            },
            {
                "name": "Company Income Tax",
                "date": f"{current_year + 1}-06-30",
                "description": "Corporate tax filing deadline",
                "type": "company_tax"
            }
        ],
        "tips": [
            "Keep all receipts and invoices organized",
            "Record transactions daily for accurate records",
            "Set aside VAT collected - it belongs to NRS",
            "Consult a tax professional for complex situations"
        ]
    }


# ============== REPORTS ROUTES ==============

@app.get("/api/reports/income-statement")
async def get_income_statement(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    query = {"business_id": business["business_id"]}
    
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        if "date" in query:
            query["date"]["$lte"] = end_date
        else:
            query["date"] = {"$lte": end_date}
    
    cursor = transactions_collection.find(query, {"_id": 0})
    transactions = await cursor.to_list(length=10000)
    
    # Group by category
    income_by_category = {}
    expense_by_category = {}
    
    for t in transactions:
        if t["type"] == "income":
            income_by_category[t["category"]] = income_by_category.get(t["category"], 0) + t["amount"]
        else:
            expense_by_category[t["category"]] = expense_by_category.get(t["category"], 0) + t["amount"]
    
    total_income = sum(income_by_category.values())
    total_expenses = sum(expense_by_category.values())
    gross_profit = total_income - total_expenses
    
    # Tax estimates
    vat_liability = sum(t.get("vat_amount", 0) for t in transactions if t["type"] == "income" and t.get("is_taxable"))
    income_tax = calculate_income_tax(total_income)
    
    net_profit = gross_profit - vat_liability - income_tax
    
    return {
        "business_name": business["business_name"],
        "period": f"{start_date or 'Start'} to {end_date or 'Present'}",
        "income": {
            "categories": income_by_category,
            "total": round(total_income, 2)
        },
        "expenses": {
            "categories": expense_by_category,
            "total": round(total_expenses, 2)
        },
        "gross_profit": round(gross_profit, 2),
        "tax_provisions": {
            "vat_liability": round(vat_liability, 2),
            "income_tax_estimate": round(income_tax, 2),
            "total": round(vat_liability + income_tax, 2)
        },
        "net_profit": round(net_profit, 2)
    }


# ============== AI INSIGHTS ROUTES ==============

@app.post("/api/ai/categorize")
async def ai_categorize_transaction(
    description: str = Form(...),
    amount: float = Form(...),
    user: dict = Depends(get_current_user)
):
    """Use AI to categorize a transaction"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=f"categorize_{user['user_id']}_{datetime.now().timestamp()}",
            system_message="""You are a Nigerian business financial assistant. Categorize transactions for MSMEs.
            
Available categories for INCOME: Sales, Services, Consulting, Rental Income, Commission, Interest, Other Income
Available categories for EXPENSE: Rent, Utilities, Salaries, Equipment, Supplies, Transport, Marketing, Food, Communication, Professional Fees, Insurance, Maintenance, Other Expense

Respond with ONLY a JSON object like: {"type": "income" or "expense", "category": "category_name", "is_taxable": true/false}"""
        ).with_model("openai", "gpt-4o-mini")
        
        message = UserMessage(text=f"Categorize this transaction: '{description}' for ₦{amount:,.2f}")
        response = await chat.send_message(message)
        
        # Parse response
        import json
        try:
            # Clean response and parse JSON
            response_text = response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            result = json.loads(response_text)
            return result
        except:
            return {"type": "expense", "category": "Other Expense", "is_taxable": True}
    
    except Exception as e:
        # Fallback categorization
        description_lower = description.lower()
        
        income_keywords = ["sale", "sold", "received", "payment from", "income", "revenue"]
        if any(kw in description_lower for kw in income_keywords):
            return {"type": "income", "category": "Sales", "is_taxable": True}
        
        return {"type": "expense", "category": "Other Expense", "is_taxable": True}


@app.post("/api/ai/insights")
async def get_ai_insights(data: AIInsightRequest, user: dict = Depends(get_current_user)):
    """Get AI-powered business insights"""
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get recent transactions
    cursor = transactions_collection.find(
        {"business_id": business["business_id"]},
        {"_id": 0}
    ).sort("date", -1).limit(100)
    transactions = await cursor.to_list(length=100)
    
    # Calculate summary
    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=f"insights_{user['user_id']}_{datetime.now().timestamp()}",
            system_message="""You are a friendly Nigerian business financial advisor for MSMEs. 
Speak in a warm, supportive tone. Use Naira (₦) for currency.
Provide practical, actionable advice specific to Nigerian small businesses.
Consider Nigerian tax laws (7.5% VAT, progressive income tax, NRS compliance).
Keep responses concise but helpful."""
        ).with_model("openai", "gpt-4o-mini")
        
        context = f"""Business: {business['business_name']} ({business['industry']})
Recent Performance: ₦{income:,.0f} income, ₦{expenses:,.0f} expenses
Profit: ₦{income - expenses:,.0f}
Transaction count: {len(transactions)}

User question: {data.query}"""
        
        message = UserMessage(text=context)
        response = await chat.send_message(message)
        
        return {"insight": response, "context": {"income": income, "expenses": expenses, "profit": income - expenses}}
    
    except Exception as e:
        # Fallback insights
        profit = income - expenses
        profit_margin = (profit / income * 100) if income > 0 else 0
        
        insight = f"Your business {business['business_name']} "
        if profit > 0:
            insight += f"is profitable with ₦{profit:,.0f} profit ({profit_margin:.1f}% margin). "
        else:
            insight += f"has a loss of ₦{abs(profit):,.0f}. Consider reviewing expenses. "
        
        insight += "Keep recording transactions for better insights!"
        
        return {"insight": insight, "context": {"income": income, "expenses": expenses, "profit": profit}}


# ============== CATEGORIES ==============

@app.get("/api/categories")
async def get_categories():
    """Get available transaction categories"""
    return {
        "income": [
            {"name": "Sales", "icon": "shopping-bag", "taxable": True},
            {"name": "Services", "icon": "briefcase", "taxable": True},
            {"name": "Consulting", "icon": "users", "taxable": True},
            {"name": "Rental Income", "icon": "home", "taxable": True},
            {"name": "Commission", "icon": "percent", "taxable": True},
            {"name": "Interest", "icon": "trending-up", "taxable": True},
            {"name": "Other Income", "icon": "plus-circle", "taxable": True}
        ],
        "expense": [
            {"name": "Rent", "icon": "home", "taxable": False},
            {"name": "Utilities", "icon": "zap", "taxable": True},
            {"name": "Salaries", "icon": "users", "taxable": False},
            {"name": "Equipment", "icon": "tool", "taxable": True},
            {"name": "Supplies", "icon": "package", "taxable": True},
            {"name": "Transport", "icon": "truck", "taxable": True},
            {"name": "Marketing", "icon": "megaphone", "taxable": True},
            {"name": "Food", "icon": "coffee", "taxable": False},
            {"name": "Communication", "icon": "phone", "taxable": True},
            {"name": "Professional Fees", "icon": "file-text", "taxable": True},
            {"name": "Insurance", "icon": "shield", "taxable": False},
            {"name": "Maintenance", "icon": "wrench", "taxable": True},
            {"name": "Other Expense", "icon": "minus-circle", "taxable": True}
        ]
    }


# ============== RECEIPT OCR ROUTES ==============

@app.post("/api/receipts/scan")
async def scan_receipt(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Scan a receipt image using Google Vision API OCR"""
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=400, detail="Please create a business first")
    
    # Read file
    contents = await file.read()
    
    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image (JPEG, PNG, or WebP)")
    
    # Check for Google Vision API key
    google_vision_key = os.environ.get("GOOGLE_VISION_API_KEY")
    
    if google_vision_key:
        # Use Google Vision API
        try:
            import httpx
            
            # Encode image to base64
            image_base64 = base64.b64encode(contents).decode('utf-8')
            
            # Call Google Vision API
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    f"https://vision.googleapis.com/v1/images:annotate?key={google_vision_key}",
                    json={
                        "requests": [{
                            "image": {"content": image_base64},
                            "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]
                        }]
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise Exception("Vision API request failed")
                
                result = response.json()
                text_annotations = result.get("responses", [{}])[0].get("fullTextAnnotation", {})
                extracted_text = text_annotations.get("text", "")
        except Exception as e:
            # Fallback to AI-based extraction
            extracted_text = None
    else:
        extracted_text = None
    
    # Use AI to parse receipt data (works with or without Vision API)
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        if extracted_text:
            prompt = f"""Parse this receipt text and extract:
1. Merchant/Store name
2. Total amount (in Naira ₦)
3. Date (if visible)
4. Individual items with prices

Receipt text:
{extracted_text}

Return ONLY a JSON object like:
{{"merchant": "Store Name", "total": 5000, "date": "2026-01-20", "items": [{{"description": "Item 1", "amount": 2500}}, {{"description": "Item 2", "amount": 2500}}], "category_suggestion": "Supplies"}}"""
        else:
            # Without OCR, ask user to describe
            return {
                "success": False,
                "message": "Receipt OCR requires Google Vision API key. Please enter transaction details manually.",
                "ocr_available": False
            }
        
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=f"receipt_{user['user_id']}_{datetime.now().timestamp()}",
            system_message="You are a receipt parser. Extract structured data from receipt text. Always respond with valid JSON only."
        ).with_model("openai", "gpt-4o-mini")
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        # Parse AI response
        import json
        try:
            response_text = response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            parsed = json.loads(response_text)
            
            return {
                "success": True,
                "ocr_available": True,
                "extracted_text": extracted_text[:500] if extracted_text else None,
                "parsed_data": {
                    "merchant": parsed.get("merchant", "Unknown"),
                    "total": parsed.get("total", 0),
                    "date": parsed.get("date"),
                    "items": parsed.get("items", []),
                    "category_suggestion": parsed.get("category_suggestion", "Other Expense")
                }
            }
        except:
            return {
                "success": True,
                "ocr_available": True,
                "extracted_text": extracted_text[:500] if extracted_text else None,
                "parsed_data": None,
                "message": "Could not parse receipt. Please enter details manually."
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing receipt: {str(e)}",
            "ocr_available": bool(google_vision_key)
        }


# ============== PDF EXPORT ROUTES ==============

@app.get("/api/reports/export/pdf")
async def export_tax_report_pdf(
    report_type: str = "income-statement",
    year: int = None,
    user: dict = Depends(get_current_user)
):
    """Generate PDF tax report"""
    from fastapi.responses import StreamingResponse
    
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    current_year = year or datetime.now().year
    
    # Get transactions
    cursor = transactions_collection.find({
        "business_id": business["business_id"],
        "date": {"$gte": f"{current_year}-01-01", "$lte": f"{current_year}-12-31"}
    }, {"_id": 0})
    transactions = await cursor.to_list(length=10000)
    
    # Calculate totals
    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    profit = income - expenses
    
    vat_collected = sum(t.get("vat_amount", 0) for t in transactions if t["type"] == "income" and t.get("is_taxable"))
    vat_paid = sum(t.get("vat_amount", 0) for t in transactions if t["type"] == "expense" and t.get("is_taxable"))
    net_vat = vat_collected - vat_paid
    income_tax = calculate_income_tax(income)
    
    # Group by category
    income_by_cat = {}
    expense_by_cat = {}
    for t in transactions:
        if t["type"] == "income":
            income_by_cat[t["category"]] = income_by_cat.get(t["category"], 0) + t["amount"]
        else:
            expense_by_cat[t["category"]] = expense_by_cat.get(t["category"], 0) + t["amount"]
    
    # Generate PDF
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import inch
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=20, textColor=colors.HexColor('#10b981'))
        story.append(Paragraph(f"MONETRAX - Tax Report {current_year}", title_style))
        story.append(Paragraph(f"<b>{business['business_name']}</b>", styles['Heading2']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Summary Table
        summary_data = [
            ['Description', 'Amount (₦)'],
            ['Total Revenue', f"{income:,.2f}"],
            ['Total Expenses', f"{expenses:,.2f}"],
            ['Gross Profit', f"{profit:,.2f}"],
            ['', ''],
            ['VAT Collected (7.5%)', f"{vat_collected:,.2f}"],
            ['VAT Paid (Credit)', f"({vat_paid:,.2f})"],
            ['Net VAT Due', f"{net_vat:,.2f}"],
            ['', ''],
            ['Estimated Income Tax', f"{income_tax:,.2f}"],
            ['Total Tax Liability', f"{net_vat + income_tax:,.2f}"],
            ['', ''],
            ['Net Profit After Tax', f"{profit - net_vat - income_tax:,.2f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[3.5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecfdf5')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 30))
        
        # Income Breakdown
        if income_by_cat:
            story.append(Paragraph("Revenue by Category", styles['Heading3']))
            income_data = [['Category', 'Amount (₦)']] + [[cat, f"{amt:,.2f}"] for cat, amt in income_by_cat.items()]
            income_table = Table(income_data, colWidths=[3.5*inch, 2*inch])
            income_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(income_table)
            story.append(Spacer(1, 20))
        
        # Expense Breakdown
        if expense_by_cat:
            story.append(Paragraph("Expenses by Category", styles['Heading3']))
            expense_data = [['Category', 'Amount (₦)']] + [[cat, f"{amt:,.2f}"] for cat, amt in expense_by_cat.items()]
            expense_table = Table(expense_data, colWidths=[3.5*inch, 2*inch])
            expense_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef4444')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(expense_table)
        
        # Footer
        story.append(Spacer(1, 40))
        story.append(Paragraph("This report is generated by Monetrax for tax compliance purposes.", styles['Normal']))
        story.append(Paragraph(f"TIN: {business.get('tin', 'Not registered')}", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=monetrax_tax_report_{current_year}.pdf"}
        )
        
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation not available. Please install reportlab.")


# ============== CSV IMPORT/EXPORT ROUTES ==============

@app.post("/api/transactions/import/csv")
async def import_transactions_csv(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Import transactions from CSV file"""
    import csv
    
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=400, detail="Please create a business first")
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")
    
    contents = await file.read()
    decoded = contents.decode('utf-8')
    
    # Parse CSV
    reader = csv.DictReader(io.StringIO(decoded))
    
    imported = 0
    errors = []
    transactions_to_insert = []
    
    for row_num, row in enumerate(reader, start=2):
        try:
            # Expected columns: date, type, category, amount, description, is_taxable
            tx_type = row.get('type', '').lower().strip()
            if tx_type not in ['income', 'expense']:
                errors.append(f"Row {row_num}: Invalid type '{tx_type}'")
                continue
            
            amount = float(row.get('amount', 0))
            if amount <= 0:
                errors.append(f"Row {row_num}: Invalid amount")
                continue
            
            # Calculate VAT
            is_taxable = row.get('is_taxable', 'true').lower() in ['true', 'yes', '1']
            vat_amount = calculate_vat(amount) if is_taxable else 0
            
            transaction = {
                "transaction_id": generate_id("txn"),
                "business_id": business["business_id"],
                "type": tx_type,
                "category": row.get('category', 'Other Income' if tx_type == 'income' else 'Other Expense'),
                "amount": amount,
                "description": row.get('description', ''),
                "date": row.get('date', datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                "is_taxable": is_taxable,
                "vat_amount": vat_amount,
                "payment_method": row.get('payment_method', 'Cash'),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "imported": True
            }
            
            transactions_to_insert.append(transaction)
            imported += 1
            
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    # Bulk insert
    if transactions_to_insert:
        await transactions_collection.insert_many(transactions_to_insert)
    
    return {
        "success": True,
        "imported": imported,
        "errors": errors[:10],  # Return first 10 errors
        "total_errors": len(errors)
    }


@app.get("/api/transactions/export/csv")
async def export_transactions_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Export transactions to CSV file"""
    from fastapi.responses import StreamingResponse
    import csv
    
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    query = {"business_id": business["business_id"]}
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        if "date" in query:
            query["date"]["$lte"] = end_date
        else:
            query["date"] = {"$lte": end_date}
    
    cursor = transactions_collection.find(query, {"_id": 0}).sort("date", -1)
    transactions = await cursor.to_list(length=10000)
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['date', 'type', 'category', 'amount', 'vat_amount', 'description', 'payment_method', 'is_taxable'])
    
    # Data
    for tx in transactions:
        writer.writerow([
            tx.get('date', ''),
            tx.get('type', ''),
            tx.get('category', ''),
            tx.get('amount', 0),
            tx.get('vat_amount', 0),
            tx.get('description', ''),
            tx.get('payment_method', ''),
            tx.get('is_taxable', True)
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=monetrax_transactions_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


# ============== ANALYTICS & CHARTS DATA ==============

@app.get("/api/analytics/charts")
async def get_charts_data(
    period: str = "6months",  # 6months, year, all
    user: dict = Depends(get_current_user)
):
    """Get data for charts and graphs"""
    business = await get_user_business(user["user_id"])
    if not business:
        return {"monthly_data": [], "category_breakdown": {"income": {}, "expense": {}}}
    
    now = datetime.now(timezone.utc)
    
    # Determine date range
    if period == "6months":
        months_back = 6
    elif period == "year":
        months_back = 12
    else:
        months_back = 24
    
    # Get all transactions in range
    start_date = (now - timedelta(days=months_back * 30)).strftime("%Y-%m-%d")
    
    cursor = transactions_collection.find({
        "business_id": business["business_id"],
        "date": {"$gte": start_date}
    }, {"_id": 0})
    transactions = await cursor.to_list(length=10000)
    
    # Monthly aggregation
    monthly_data = {}
    for tx in transactions:
        month_key = tx["date"][:7]  # YYYY-MM
        if month_key not in monthly_data:
            monthly_data[month_key] = {"month": month_key, "income": 0, "expense": 0, "profit": 0, "vat": 0}
        
        if tx["type"] == "income":
            monthly_data[month_key]["income"] += tx["amount"]
            monthly_data[month_key]["vat"] += tx.get("vat_amount", 0)
        else:
            monthly_data[month_key]["expense"] += tx["amount"]
        
        monthly_data[month_key]["profit"] = monthly_data[month_key]["income"] - monthly_data[month_key]["expense"]
    
    # Sort by month
    monthly_list = sorted(monthly_data.values(), key=lambda x: x["month"])
    
    # Category breakdown
    income_by_cat = {}
    expense_by_cat = {}
    for tx in transactions:
        if tx["type"] == "income":
            income_by_cat[tx["category"]] = income_by_cat.get(tx["category"], 0) + tx["amount"]
        else:
            expense_by_cat[tx["category"]] = expense_by_cat.get(tx["category"], 0) + tx["amount"]
    
    # Daily trend (last 30 days)
    thirty_days_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    daily_data = {}
    for tx in transactions:
        if tx["date"] >= thirty_days_ago:
            day_key = tx["date"]
            if day_key not in daily_data:
                daily_data[day_key] = {"date": day_key, "income": 0, "expense": 0}
            if tx["type"] == "income":
                daily_data[day_key]["income"] += tx["amount"]
            else:
                daily_data[day_key]["expense"] += tx["amount"]
    
    daily_list = sorted(daily_data.values(), key=lambda x: x["date"])
    
    return {
        "monthly_data": monthly_list,
        "daily_data": daily_list,
        "category_breakdown": {
            "income": income_by_cat,
            "expense": expense_by_cat
        },
        "totals": {
            "income": sum(m["income"] for m in monthly_list),
            "expense": sum(m["expense"] for m in monthly_list),
            "profit": sum(m["profit"] for m in monthly_list),
            "vat": sum(m["vat"] for m in monthly_list)
        }
    }


# ============== ENHANCED AI INSIGHTS WITH LEVELS ==============

class AIInsightRequestV2(BaseModel):
    query: str
    level: str = "basic"  # basic, standard, premium
    include_charts: bool = True


@app.post("/api/ai/insights/v2")
async def get_ai_insights_v2(data: AIInsightRequestV2, user: dict = Depends(get_current_user)):
    """Enhanced AI insights with levels and chart recommendations"""
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get transactions based on level
    limit = {"basic": 50, "standard": 100, "premium": 500}.get(data.level, 50)
    
    cursor = transactions_collection.find(
        {"business_id": business["business_id"]},
        {"_id": 0}
    ).sort("date", -1).limit(limit)
    transactions = await cursor.to_list(length=limit)
    
    # Calculate comprehensive metrics
    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    profit = income - expenses
    
    # Category analysis
    income_by_cat = {}
    expense_by_cat = {}
    for t in transactions:
        if t["type"] == "income":
            income_by_cat[t["category"]] = income_by_cat.get(t["category"], 0) + t["amount"]
        else:
            expense_by_cat[t["category"]] = expense_by_cat.get(t["category"], 0) + t["amount"]
    
    # Monthly trend
    monthly_trend = {}
    for t in transactions:
        month = t["date"][:7]
        if month not in monthly_trend:
            monthly_trend[month] = {"income": 0, "expense": 0}
        if t["type"] == "income":
            monthly_trend[month]["income"] += t["amount"]
        else:
            monthly_trend[month]["expense"] += t["amount"]
    
    # Top categories
    top_income_cat = max(income_by_cat.items(), key=lambda x: x[1])[0] if income_by_cat else "N/A"
    top_expense_cat = max(expense_by_cat.items(), key=lambda x: x[1])[0] if expense_by_cat else "N/A"
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        # Build context based on level
        level_prompts = {
            "basic": "Provide a brief 2-3 sentence insight.",
            "standard": "Provide detailed analysis with 3-5 actionable recommendations.",
            "premium": """Provide comprehensive analysis including:
1. Financial health assessment
2. Tax optimization strategies
3. Cash flow recommendations
4. Growth opportunities
5. Risk factors to watch
6. Specific action items with timelines"""
        }
        
        system_message = f"""You are an expert Nigerian business financial advisor for MSMEs.
Use Naira (₦) for all amounts. Consider Nigerian tax laws (7.5% VAT, progressive income tax).
{level_prompts.get(data.level, level_prompts['basic'])}
Be specific and actionable. Reference the actual numbers provided."""
        
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=f"insights_v2_{user['user_id']}_{datetime.now().timestamp()}",
            system_message=system_message
        ).with_model("openai", "gpt-4o-mini")
        
        context = f"""Business: {business['business_name']} ({business['industry']})
TIN Registered: {'Yes' if business.get('tin') else 'No'}

Financial Summary (Last {len(transactions)} transactions):
- Total Income: ₦{income:,.0f}
- Total Expenses: ₦{expenses:,.0f}
- Net Profit: ₦{profit:,.0f}
- Profit Margin: {(profit/income*100) if income > 0 else 0:.1f}%

Top Revenue Source: {top_income_cat} (₦{income_by_cat.get(top_income_cat, 0):,.0f})
Top Expense Category: {top_expense_cat} (₦{expense_by_cat.get(top_expense_cat, 0):,.0f})

Monthly Trend: {list(monthly_trend.items())[-3:] if monthly_trend else 'No data'}

User Question: {data.query}"""
        
        message = UserMessage(text=context)
        response = await chat.send_message(message)
        
        # Generate chart recommendations based on data
        chart_recommendations = []
        if data.include_charts:
            if len(monthly_trend) >= 3:
                chart_recommendations.append({
                    "type": "line",
                    "title": "Revenue vs Expenses Trend",
                    "description": "Track your monthly financial performance"
                })
            if income_by_cat:
                chart_recommendations.append({
                    "type": "pie",
                    "title": "Revenue by Category",
                    "description": "See where your money comes from"
                })
            if expense_by_cat:
                chart_recommendations.append({
                    "type": "bar",
                    "title": "Expense Breakdown",
                    "description": "Understand your spending patterns"
                })
            if profit != 0:
                chart_recommendations.append({
                    "type": "gauge",
                    "title": "Profit Margin",
                    "description": "Your current profitability rate"
                })
        
        return {
            "insight": response,
            "level": data.level,
            "metrics": {
                "income": income,
                "expenses": expenses,
                "profit": profit,
                "profit_margin": round((profit/income*100) if income > 0 else 0, 1),
                "transaction_count": len(transactions),
                "vat_collected": sum(t.get("vat_amount", 0) for t in transactions if t["type"] == "income"),
                "estimated_tax": calculate_income_tax(income)
            },
            "category_data": {
                "income": income_by_cat,
                "expense": expense_by_cat
            },
            "monthly_trend": [{"month": k, **v} for k, v in sorted(monthly_trend.items())],
            "chart_recommendations": chart_recommendations,
            "top_insights": {
                "best_revenue_source": top_income_cat,
                "highest_expense": top_expense_cat,
                "months_analyzed": len(monthly_trend)
            }
        }
    
    except Exception as e:
        # Fallback response
        return {
            "insight": f"Based on your data, your business has ₦{income:,.0f} income and ₦{expenses:,.0f} expenses, resulting in ₦{profit:,.0f} profit.",
            "level": data.level,
            "metrics": {
                "income": income,
                "expenses": expenses,
                "profit": profit
            },
            "error": str(e)
        }


# ============== SUBSCRIPTION SYSTEM ==============

# Subscription tier configurations
SUBSCRIPTION_TIERS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "features": {
            "transactions_per_month": 50,
            "ai_insights": False,
            "receipt_ocr": False,
            "pdf_reports": False,
            "csv_export": True,
            "priority_support": False,
            "multi_user": False,
            "custom_categories": False,
            "linked_bank_accounts": 1,
            "bank_sync_frequency": "daily",
            "manual_sync_per_day": 3
        },
        "description": "Perfect for getting started",
        "highlight": False
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 3000.00,
        "price_yearly": 30000.00,
        "features": {
            "transactions_per_month": 200,
            "ai_insights": True,
            "receipt_ocr": False,
            "pdf_reports": False,
            "csv_export": True,
            "priority_support": False,
            "multi_user": False,
            "custom_categories": False,
            "linked_bank_accounts": 3,
            "bank_sync_frequency": "daily",
            "manual_sync_per_day": 10
        },
        "description": "Great for small businesses",
        "highlight": False
    },
    "business": {
        "name": "Business",
        "price_monthly": 7000.00,
        "price_yearly": 70000.00,
        "features": {
            "transactions_per_month": 1000,
            "ai_insights": True,
            "receipt_ocr": True,
            "pdf_reports": True,
            "csv_export": True,
            "priority_support": True,
            "multi_user": False,
            "custom_categories": True,
            "linked_bank_accounts": 5,
            "bank_sync_frequency": "realtime",
            "manual_sync_per_day": -1  # Unlimited
        },
        "description": "Most popular for growing businesses",
        "highlight": True
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 10000.00,
        "price_yearly": 100000.00,
        "features": {
            "transactions_per_month": -1,  # Unlimited
            "ai_insights": True,
            "receipt_ocr": True,
            "pdf_reports": True,
            "csv_export": True,
            "priority_support": True,
            "multi_user": True,
            "custom_categories": True,
            "linked_bank_accounts": -1,  # Unlimited
            "bank_sync_frequency": "realtime",
            "manual_sync_per_day": -1  # Unlimited
        },
        "description": "For large organizations",
        "highlight": False
    }
}

# Agent Promotional Pricing (one-time discount per user)
AGENT_PROMOTIONAL_PRICING = {
    "starter": {
        "promo_price_monthly": 2000.00,  # ₦2,000 instead of ₦3,000
        "regular_price_monthly": 3000.00,
        "savings": 1000.00
    },
    "business": {
        "promo_price_monthly": 5000.00,  # ₦5,000 instead of ₦7,000
        "regular_price_monthly": 7000.00,
        "savings": 2000.00
    },
    "enterprise": {
        "promo_price_monthly": 8000.00,  # ₦8,000 instead of ₦10,000
        "regular_price_monthly": 10000.00,
        "savings": 2000.00
    }
}

# Subscription collection
subscriptions_collection = db["subscriptions"]
payment_transactions_collection = db["payment_transactions"]
agent_signups_collection = db["agent_signups"]


class SubscriptionPlan(BaseModel):
    tier: str
    name: str
    price_monthly: float
    price_yearly: float
    features: dict
    description: str
    highlight: bool


class CreateCheckoutRequest(BaseModel):
    tier: str
    billing_cycle: str = "monthly"  # monthly or yearly
    origin_url: str


class SubscriptionResponse(BaseModel):
    subscription_id: str
    user_id: str
    tier: str
    status: str
    billing_cycle: str
    current_period_start: str
    current_period_end: str
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None


@app.get("/api/subscriptions/plans")
async def get_subscription_plans():
    """Get all available subscription plans"""
    plans = []
    for tier_id, tier_data in SUBSCRIPTION_TIERS.items():
        plans.append({
            "tier": tier_id,
            **tier_data
        })
    return {"plans": plans}


@app.get("/api/subscriptions/current")
async def get_current_subscription(user: dict = Depends(get_current_user)):
    """Get user's current subscription with usage stats"""
    subscription = await subscriptions_collection.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    # Get business for usage calculation
    business = await get_user_business(user["user_id"])
    
    # Calculate monthly usage
    usage = {"transactions_this_month": 0, "transactions_limit": 50}
    if business:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1).strftime("%Y-%m-%d")
        monthly_tx_count = await transactions_collection.count_documents({
            "business_id": business["business_id"],
            "date": {"$gte": month_start}
        })
        usage["transactions_this_month"] = monthly_tx_count
    
    now = datetime.now(timezone.utc)
    
    if not subscription:
        # Check if user ever had a paid subscription (prevent free tier re-trial)
        had_paid_subscription = await payment_transactions_collection.find_one(
            {"user_id": user["user_id"], "status": "completed"},
            {"_id": 0}
        )
        
        tier_data = SUBSCRIPTION_TIERS["free"]
        usage["transactions_limit"] = tier_data["features"]["transactions_per_month"]
        
        return {
            "subscription_id": None,
            "user_id": user["user_id"],
            "tier": "free",
            "tier_name": "Free",
            "status": "active",
            "billing_cycle": None,
            "features": tier_data["features"],
            "current_period_start": now.isoformat(),
            "current_period_end": None,
            "renewal_date": None,
            "days_remaining": None,
            "is_expiring_soon": False,
            "can_upgrade": True,
            "had_paid_subscription": bool(had_paid_subscription),
            "usage": usage
        }
    
    tier_data = SUBSCRIPTION_TIERS.get(subscription["tier"], SUBSCRIPTION_TIERS["free"])
    usage["transactions_limit"] = tier_data["features"]["transactions_per_month"]
    
    # Calculate renewal/expiry info
    current_period_end = subscription.get("current_period_end")
    renewal_date = None
    days_remaining = None
    is_expiring_soon = False
    
    if current_period_end:
        if isinstance(current_period_end, str):
            period_end = datetime.fromisoformat(current_period_end.replace('Z', '+00:00'))
        else:
            period_end = current_period_end
        
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
        
        renewal_date = period_end.isoformat()
        days_remaining = (period_end - now).days
        is_expiring_soon = days_remaining <= 7 and days_remaining >= 0
    
    return {
        **subscription,
        "tier_name": tier_data["name"],
        "features": tier_data["features"],
        "renewal_date": renewal_date,
        "days_remaining": days_remaining,
        "is_expiring_soon": is_expiring_soon,
        "can_upgrade": subscription["tier"] != "enterprise",
        "had_paid_subscription": True,
        "usage": usage
    }


@app.post("/api/subscriptions/checkout")
async def create_checkout_session(
    request: Request,
    data: CreateCheckoutRequest,
    user: dict = Depends(get_current_user)
):
    """Create a Stripe checkout session for subscription"""
    from emergentintegrations.payments.stripe.checkout import (
        StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse
    )
    
    tier = data.tier.lower()
    if tier not in SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail="Invalid subscription tier")
    
    if tier == "free":
        raise HTTPException(status_code=400, detail="Free tier doesn't require payment")
    
    tier_data = SUBSCRIPTION_TIERS[tier]
    
    # Get price based on billing cycle
    if data.billing_cycle == "yearly":
        amount = tier_data["price_yearly"]
    else:
        amount = tier_data["price_monthly"]
    
    # Convert NGN to USD (approximate rate for Stripe - adjust as needed)
    # Using 1 USD = 1500 NGN for example
    ngn_to_usd_rate = 1500
    amount_usd = round(amount / ngn_to_usd_rate, 2)
    
    # Ensure minimum amount for Stripe
    if amount_usd < 0.50:
        amount_usd = 0.50
    
    stripe_api_key = os.environ.get("STRIPE_API_KEY")
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Payment service not configured")
    
    # Setup webhook URL
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhooks/stripe"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    # Create success and cancel URLs
    success_url = f"{data.origin_url}/subscription?session_id={{CHECKOUT_SESSION_ID}}&status=success"
    cancel_url = f"{data.origin_url}/subscription?status=cancelled"
    
    # Create pending payment transaction
    payment_id = generate_id("pay")
    await payment_transactions_collection.insert_one({
        "payment_id": payment_id,
        "user_id": user["user_id"],
        "tier": tier,
        "billing_cycle": data.billing_cycle,
        "amount_ngn": amount,
        "amount_usd": amount_usd,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Create checkout session
    checkout_request = CheckoutSessionRequest(
        amount=amount_usd,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["user_id"],
            "tier": tier,
            "billing_cycle": data.billing_cycle,
            "payment_id": payment_id,
            "amount_ngn": str(amount)
        }
    )
    
    try:
        session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Update payment transaction with session ID
        await payment_transactions_collection.update_one(
            {"payment_id": payment_id},
            {"$set": {"stripe_session_id": session.session_id}}
        )
        
        return {
            "checkout_url": session.url,
            "session_id": session.session_id,
            "payment_id": payment_id
        }
    except Exception as e:
        # Mark payment as failed
        await payment_transactions_collection.update_one(
            {"payment_id": payment_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")


@app.get("/api/subscriptions/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, user: dict = Depends(get_current_user)):
    """Check the status of a checkout session and update subscription if paid"""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    
    stripe_api_key = os.environ.get("STRIPE_API_KEY")
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Payment service not configured")
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key)
    
    try:
        status = await stripe_checkout.get_checkout_status(session_id)
        
        # Find the payment transaction
        payment_tx = await payment_transactions_collection.find_one(
            {"stripe_session_id": session_id, "user_id": user["user_id"]},
            {"_id": 0}
        )
        
        if not payment_tx:
            return {"status": status.status, "payment_status": status.payment_status}
        
        # If payment is complete and not already processed
        if status.payment_status == "paid" and payment_tx.get("status") != "completed":
            tier = status.metadata.get("tier") or payment_tx.get("tier")
            billing_cycle = status.metadata.get("billing_cycle") or payment_tx.get("billing_cycle", "monthly")
            
            # Calculate subscription period
            now = datetime.now(timezone.utc)
            if billing_cycle == "yearly":
                period_end = now + timedelta(days=365)
            else:
                period_end = now + timedelta(days=30)
            
            subscription_id = generate_id("sub")
            
            # Update or create subscription
            await subscriptions_collection.update_one(
                {"user_id": user["user_id"]},
                {"$set": {
                    "subscription_id": subscription_id,
                    "user_id": user["user_id"],
                    "tier": tier,
                    "status": "active",
                    "billing_cycle": billing_cycle,
                    "current_period_start": now.isoformat(),
                    "current_period_end": period_end.isoformat(),
                    "stripe_session_id": session_id,
                    "updated_at": now.isoformat()
                }},
                upsert=True
            )
            
            # Update payment transaction
            await payment_transactions_collection.update_one(
                {"stripe_session_id": session_id},
                {"$set": {
                    "status": "completed",
                    "completed_at": now.isoformat()
                }}
            )
            
            tier_data = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])
            
            # Send receipt email (fire and forget - don't block response)
            amount_ngn = tier_data["price_yearly"] if billing_cycle == "yearly" else tier_data["price_monthly"]
            html_content = get_subscription_receipt_html(
                user_name=user.get("name", "Valued Customer"),
                tier_name=tier_data["name"],
                amount=amount_ngn,
                billing_cycle=billing_cycle,
                next_billing_date=period_end.strftime("%B %d, %Y")
            )
            
            # Send email asynchronously
            asyncio.create_task(send_email(
                to_email=user["email"],
                subject=f"Payment Confirmation - {tier_data['name']} Plan | Monetrax",
                html_content=html_content,
                email_type="subscription_receipt"
            ))
            
            return {
                "status": "complete",
                "payment_status": "paid",
                "email_sent": True,
                "subscription": {
                    "subscription_id": subscription_id,
                    "tier": tier,
                    "tier_name": tier_data["name"],
                    "status": "active",
                    "billing_cycle": billing_cycle,
                    "features": tier_data["features"],
                    "current_period_start": now.isoformat(),
                    "current_period_end": period_end.isoformat()
                }
            }
        
        return {
            "status": status.status,
            "payment_status": status.payment_status,
            "amount_total": status.amount_total,
            "currency": status.currency
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check status: {str(e)}")


@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events with signature verification"""
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        
        # Verify webhook signature if secret is configured
        if webhook_secret and sig_header:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"Webhook signature verification failed: {e}")
                raise HTTPException(status_code=400, detail="Invalid signature")
        else:
            # Fallback for development/testing without signature verification
            import json
            event = json.loads(payload)
        
        event_type = event.get("type") if isinstance(event, dict) else event["type"]
        data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event["data"]["object"]
        
        logger.info(f"Received Stripe webhook: {event_type}")
        
        if event_type == "checkout.session.completed":
            session_id = data.get("id")
            metadata = data.get("metadata", {})
            
            user_id = metadata.get("user_id")
            tier = metadata.get("tier")
            billing_cycle = metadata.get("billing_cycle", "monthly")
            payment_id = metadata.get("payment_id")
            
            if user_id and tier:
                now = datetime.now(timezone.utc)
                if billing_cycle == "yearly":
                    period_end = now + timedelta(days=365)
                else:
                    period_end = now + timedelta(days=30)
                
                subscription_id = generate_id("sub")
                
                await subscriptions_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "subscription_id": subscription_id,
                        "user_id": user_id,
                        "tier": tier,
                        "status": "active",
                        "billing_cycle": billing_cycle,
                        "current_period_start": now.isoformat(),
                        "current_period_end": period_end.isoformat(),
                        "stripe_session_id": session_id,
                        "updated_at": now.isoformat()
                    }},
                    upsert=True
                )
                
                # Mark user as having had a paid subscription
                await users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"had_paid_subscription": True}}
                )
                
                if payment_id:
                    await payment_transactions_collection.update_one(
                        {"payment_id": payment_id},
                        {"$set": {"status": "completed", "completed_at": now.isoformat()}}
                    )
                
                logger.info(f"Subscription activated for user {user_id}: {tier} ({billing_cycle})")
        
        elif event_type == "customer.subscription.updated":
            # Handle subscription updates (e.g., plan changes)
            stripe_sub_id = data.get("id")
            status = data.get("status")
            logger.info(f"Subscription updated: {stripe_sub_id} -> {status}")
        
        elif event_type == "customer.subscription.deleted":
            # Handle subscription cancellation
            stripe_sub_id = data.get("id")
            logger.info(f"Subscription deleted: {stripe_sub_id}")
        
        return {"received": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"received": True, "error": str(e)}


@app.post("/api/subscriptions/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    """Cancel user's subscription (downgrades to free at period end)"""
    subscription = await subscriptions_collection.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    if subscription.get("tier") == "free":
        raise HTTPException(status_code=400, detail="You are already on the free tier")
    
    await subscriptions_collection.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "status": "cancelling",
            "cancel_at_period_end": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Subscription will be cancelled at the end of the current billing period",
        "current_period_end": subscription.get("current_period_end")
    }


@app.get("/api/subscriptions/usage")
async def get_subscription_usage(user: dict = Depends(get_current_user)):
    """Get detailed usage statistics for current subscription"""
    subscription = await subscriptions_collection.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    tier = subscription.get("tier", "free") if subscription else "free"
    tier_data = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])
    
    business = await get_user_business(user["user_id"])
    
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    
    # Calculate usage
    transactions_this_month = 0
    total_transactions = 0
    
    if business:
        transactions_this_month = await transactions_collection.count_documents({
            "business_id": business["business_id"],
            "date": {"$gte": month_start}
        })
        total_transactions = await transactions_collection.count_documents({
            "business_id": business["business_id"]
        })
    
    tx_limit = tier_data["features"]["transactions_per_month"]
    
    # Check if user ever had paid subscription
    had_paid = await payment_transactions_collection.find_one(
        {"user_id": user["user_id"], "status": "completed"},
        {"_id": 0}
    )
    
    # Determine the relevant transaction count based on tier
    # Free tier: TOTAL transactions count
    # Paid tiers: MONTHLY transactions count
    if tier == "free":
        relevant_count = total_transactions
        count_type = "total"
    else:
        relevant_count = transactions_this_month
        count_type = "monthly"
    
    # Check if limit exceeded
    limit_exceeded = tx_limit != -1 and relevant_count >= tx_limit
    
    # Calculate percentage used
    usage_percentage = 0
    if tx_limit > 0:
        usage_percentage = min(100, round((relevant_count / tx_limit) * 100))
    elif tx_limit == -1:
        usage_percentage = 0  # Unlimited
    
    # Check subscription expiry for paid tiers
    subscription_expired = False
    expires_at = None
    if subscription and tier != "free":
        current_period_end = subscription.get("current_period_end")
        if current_period_end:
            if isinstance(current_period_end, str):
                period_end = datetime.fromisoformat(current_period_end.replace('Z', '+00:00'))
            else:
                period_end = current_period_end
            
            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)
            
            subscription_expired = period_end < now
            expires_at = period_end.isoformat()
    
    # Can add transactions?
    can_add_transactions = True
    block_reason = None
    
    if subscription_expired:
        can_add_transactions = False
        block_reason = "subscription_expired"
    elif tier == "free" and bool(had_paid):
        can_add_transactions = False
        block_reason = "free_trial_not_available"
    elif limit_exceeded:
        can_add_transactions = False
        block_reason = "limit_exceeded"
    
    return {
        "tier": tier,
        "tier_name": tier_data["name"],
        "transactions": {
            "used": relevant_count,
            "limit": tx_limit,
            "unlimited": tx_limit == -1,
            "remaining": max(0, tx_limit - relevant_count) if tx_limit != -1 else -1,
            "usage_percentage": usage_percentage,
            "limit_exceeded": limit_exceeded,
            "count_type": count_type  # "total" for free, "monthly" for paid
        },
        "transactions_this_month": transactions_this_month,
        "total_transactions": total_transactions,
        "features": tier_data["features"],
        "had_paid_subscription": bool(had_paid),
        "subscription_expired": subscription_expired,
        "expires_at": expires_at,
        "can_add_transactions": can_add_transactions,
        "block_reason": block_reason,
        "month_start": month_start,
        "can_upgrade": tier != "enterprise"
    }


# Feature access helper
async def check_feature_access(user_id: str, feature: str) -> bool:
    """Check if user has access to a specific feature based on their subscription"""
    subscription = await subscriptions_collection.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    tier = subscription.get("tier", "free") if subscription else "free"
    tier_data = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])
    
    return tier_data["features"].get(feature, False)


async def get_user_tier(user_id: str) -> str:
    """Get user's subscription tier"""
    subscription = await subscriptions_collection.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    return subscription.get("tier", "free") if subscription else "free"


# Update existing endpoints to check feature access

@app.get("/api/subscriptions/feature-check/{feature}")
async def check_feature(feature: str, user: dict = Depends(get_current_user)):
    """Check if user has access to a specific feature"""
    has_access = await check_feature_access(user["user_id"], feature)
    tier = await get_user_tier(user["user_id"])
    
    return {
        "feature": feature,
        "has_access": has_access,
        "current_tier": tier,
        "upgrade_required": not has_access and feature in SUBSCRIPTION_TIERS["starter"]["features"]
    }


# ============== EMAIL SYSTEM ==============

# Email preferences collection
email_preferences_collection = db["email_preferences"]
email_logs_collection = db["email_logs"]


class EmailPreferences(BaseModel):
    tax_deadline_reminders: bool = True
    subscription_updates: bool = True
    weekly_summary: bool = False


async def send_email(to_email: str, subject: str, html_content: str, email_type: str = "general"):
    """Send email using Resend API"""
    if not resend.api_key or resend.api_key == "re_demo_key":
        logger.warning(f"Resend API key not configured. Email to {to_email} not sent.")
        return {"status": "skipped", "reason": "API key not configured"}
    
    params = {
        "from": SENDER_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }
    
    try:
        email_result = await asyncio.to_thread(resend.Emails.send, params)
        
        # Log the email
        await email_logs_collection.insert_one({
            "email_id": email_result.get("id"),
            "to_email": to_email,
            "subject": subject,
            "email_type": email_type,
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {"status": "success", "email_id": email_result.get("id")}
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        
        await email_logs_collection.insert_one({
            "to_email": to_email,
            "subject": subject,
            "email_type": email_type,
            "status": "failed",
            "error": str(e),
            "attempted_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {"status": "failed", "error": str(e)}


def get_subscription_receipt_html(user_name: str, tier_name: str, amount: float, billing_cycle: str, next_billing_date: str):
    """Generate HTML template for subscription receipt"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Payment Confirmation - Monetrax</title>
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #001F4F 0%, #003366 100%); padding: 32px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px;">
                    <span style="color: white;">MONE</span><span style="color: #22C55E;">TRAX</span>
                </h1>
                <p style="color: #94a3b8; margin-top: 8px; font-size: 14px;">Payment Confirmation</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 32px;">
                <div style="text-align: center; margin-bottom: 32px;">
                    <div style="width: 64px; height: 64px; background: #dcfce7; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                        <span style="font-size: 32px;">✓</span>
                    </div>
                    <h2 style="color: #1f2937; margin: 0 0 8px 0;">Payment Successful!</h2>
                    <p style="color: #6b7280; margin: 0;">Thank you for your subscription, {user_name}!</p>
                </div>
                
                <!-- Receipt Details -->
                <div style="background: #f8fafc; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                    <h3 style="color: #1f2937; margin: 0 0 16px 0; font-size: 16px;">Subscription Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Plan</td>
                            <td style="padding: 8px 0; color: #1f2937; text-align: right; font-weight: 600;">{tier_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Billing Cycle</td>
                            <td style="padding: 8px 0; color: #1f2937; text-align: right;">{billing_cycle.capitalize()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Amount Paid</td>
                            <td style="padding: 8px 0; color: #22C55E; text-align: right; font-weight: 600;">₦{amount:,.0f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Next Billing Date</td>
                            <td style="padding: 8px 0; color: #1f2937; text-align: right;">{next_billing_date}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- Features Unlocked -->
                <div style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                    <h3 style="color: #166534; margin: 0 0 12px 0; font-size: 16px;">🎉 Features Now Unlocked</h3>
                    <ul style="color: #166534; margin: 0; padding-left: 20px; line-height: 1.8;">
                        <li>AI-powered financial insights</li>
                        <li>Receipt OCR scanning</li>
                        <li>PDF tax report exports</li>
                        <li>Custom transaction categories</li>
                    </ul>
                </div>
                
                <!-- CTA -->
                <div style="text-align: center;">
                    <a href="https://monetrax.com/dashboard" style="display: inline-block; background: #22C55E; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600;">Go to Dashboard</a>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; margin: 0 0 8px 0; font-size: 14px;">Need help? Contact us at support@monetrax.com</p>
                <p style="color: #9ca3af; margin: 0; font-size: 12px;">© 2026 Monetrax. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """


def get_tax_deadline_reminder_html(user_name: str, deadlines: list):
    """Generate HTML template for tax deadline reminder"""
    deadline_rows = ""
    for d in deadlines:
        days_left = d.get("days_until", 0)
        urgency_color = "#ef4444" if days_left <= 7 else "#f59e0b" if days_left <= 14 else "#22C55E"
        deadline_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{d.get('name', '')}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{d.get('date', '')}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">
                <span style="background: {urgency_color}20; color: {urgency_color}; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                    {days_left} days left
                </span>
            </td>
        </tr>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Tax Deadline Reminder - Monetrax</title>
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #001F4F 0%, #003366 100%); padding: 32px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px;">
                    <span style="color: white;">MONE</span><span style="color: #22C55E;">TRAX</span>
                </h1>
                <p style="color: #94a3b8; margin-top: 8px; font-size: 14px;">Tax Deadline Reminder</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 32px;">
                <div style="text-align: center; margin-bottom: 32px;">
                    <div style="width: 64px; height: 64px; background: #fef3c7; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                        <span style="font-size: 32px;">📅</span>
                    </div>
                    <h2 style="color: #1f2937; margin: 0 0 8px 0;">Upcoming Tax Deadlines</h2>
                    <p style="color: #6b7280; margin: 0;">Hi {user_name}, here are your upcoming tax obligations:</p>
                </div>
                
                <!-- Deadlines Table -->
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
                    <thead>
                        <tr style="background: #f8fafc;">
                            <th style="padding: 12px; text-align: left; color: #6b7280; font-weight: 600; border-bottom: 2px solid #e5e7eb;">Tax Type</th>
                            <th style="padding: 12px; text-align: left; color: #6b7280; font-weight: 600; border-bottom: 2px solid #e5e7eb;">Due Date</th>
                            <th style="padding: 12px; text-align: right; color: #6b7280; font-weight: 600; border-bottom: 2px solid #e5e7eb;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {deadline_rows}
                    </tbody>
                </table>
                
                <!-- Tips -->
                <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                    <h3 style="color: #92400e; margin: 0 0 12px 0; font-size: 16px;">💡 Tips for Filing</h3>
                    <ul style="color: #92400e; margin: 0; padding-left: 20px; line-height: 1.8;">
                        <li>Ensure all transactions are recorded and categorized</li>
                        <li>Review your PDF tax report before filing</li>
                        <li>Keep receipts and documentation for 6 years</li>
                    </ul>
                </div>
                
                <!-- CTA -->
                <div style="text-align: center;">
                    <a href="https://monetrax.com/tax" style="display: inline-block; background: #22C55E; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600;">View Tax Dashboard</a>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; margin: 0 0 8px 0; font-size: 14px;">Need help? Contact us at support@monetrax.com</p>
                <p style="color: #9ca3af; margin: 0; font-size: 12px;">© 2026 Monetrax. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """


@app.post("/api/email/send-upgrade-receipt")
async def send_upgrade_receipt(user: dict = Depends(get_current_user)):
    """Send subscription upgrade receipt email"""
    subscription = await subscriptions_collection.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not subscription or subscription.get("tier") == "free":
        raise HTTPException(status_code=400, detail="No active paid subscription found")
    
    tier_data = SUBSCRIPTION_TIERS.get(subscription["tier"], SUBSCRIPTION_TIERS["free"])
    
    # Calculate amount based on billing cycle
    billing_cycle = subscription.get("billing_cycle", "monthly")
    amount = tier_data["price_yearly"] if billing_cycle == "yearly" else tier_data["price_monthly"]
    
    # Format next billing date
    next_billing = subscription.get("current_period_end", "")
    if next_billing:
        try:
            next_billing = datetime.fromisoformat(next_billing.replace("Z", "+00:00")).strftime("%B %d, %Y")
        except:
            next_billing = "N/A"
    
    html_content = get_subscription_receipt_html(
        user_name=user.get("name", "Valued Customer"),
        tier_name=tier_data["name"],
        amount=amount,
        billing_cycle=billing_cycle,
        next_billing_date=next_billing
    )
    
    result = await send_email(
        to_email=user["email"],
        subject=f"Payment Confirmation - {tier_data['name']} Plan | Monetrax",
        html_content=html_content,
        email_type="subscription_receipt"
    )
    
    return result


@app.get("/api/email/preferences")
async def get_email_preferences(user: dict = Depends(get_current_user)):
    """Get user's email notification preferences"""
    prefs = await email_preferences_collection.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not prefs:
        return {
            "user_id": user["user_id"],
            "tax_deadline_reminders": True,
            "subscription_updates": True,
            "weekly_summary": False
        }
    
    return prefs


@app.put("/api/email/preferences")
async def update_email_preferences(
    preferences: EmailPreferences,
    user: dict = Depends(get_current_user)
):
    """Update user's email notification preferences"""
    await email_preferences_collection.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "user_id": user["user_id"],
            "tax_deadline_reminders": preferences.tax_deadline_reminders,
            "subscription_updates": preferences.subscription_updates,
            "weekly_summary": preferences.weekly_summary,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"status": "success", "message": "Email preferences updated"}


@app.post("/api/email/send-tax-reminder")
async def send_tax_deadline_reminder(user: dict = Depends(get_current_user)):
    """Send tax deadline reminder email to user"""
    # Check if user has opted in for tax reminders
    prefs = await email_preferences_collection.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if prefs and not prefs.get("tax_deadline_reminders", True):
        return {"status": "skipped", "reason": "User opted out of tax reminders"}
    
    # Get upcoming tax deadlines
    today = datetime.now(timezone.utc)
    current_year = today.year
    
    # Nigerian tax deadlines
    all_deadlines = [
        {"name": "Monthly VAT Return", "date": f"{current_year}-{today.month:02d}-21", "days_until": 0},
        {"name": "WHT Remittance", "date": f"{current_year}-{today.month:02d}-21", "days_until": 0},
        {"name": "Annual Tax Return", "date": f"{current_year}-03-31", "days_until": 0},
        {"name": "Q1 PAYE", "date": f"{current_year}-04-10", "days_until": 0},
    ]
    
    # Calculate days until each deadline and filter upcoming ones
    upcoming_deadlines = []
    for d in all_deadlines:
        try:
            deadline_date = datetime.strptime(d["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_until = (deadline_date - today).days
            if 0 <= days_until <= 30:
                d["days_until"] = days_until
                d["date"] = deadline_date.strftime("%B %d, %Y")
                upcoming_deadlines.append(d)
        except:
            pass
    
    if not upcoming_deadlines:
        return {"status": "skipped", "reason": "No upcoming deadlines within 30 days"}
    
    # Sort by urgency
    upcoming_deadlines.sort(key=lambda x: x["days_until"])
    
    html_content = get_tax_deadline_reminder_html(
        user_name=user.get("name", "Valued Customer"),
        deadlines=upcoming_deadlines
    )
    
    result = await send_email(
        to_email=user["email"],
        subject="🗓️ Upcoming Tax Deadlines - Don't Miss These! | Monetrax",
        html_content=html_content,
        email_type="tax_reminder"
    )
    
    return result


@app.post("/api/email/test")
async def send_test_email(user: dict = Depends(get_current_user)):
    """Send a test email to verify email configuration"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1 style="color: #22C55E;">Test Email from Monetrax</h1>
        <p>Hi {user.get('name', 'there')},</p>
        <p>This is a test email to verify your email notifications are working correctly.</p>
        <p>If you received this, your email configuration is set up properly! 🎉</p>
        <p>Best regards,<br>The Monetrax Team</p>
    </body>
    </html>
    """
    
    result = await send_email(
        to_email=user["email"],
        subject="Test Email - Monetrax",
        html_content=html_content,
        email_type="test"
    )
    
    return result


# ============== AGENT SYSTEM ==============

# Agent Pydantic Models
class AgentUserSignup(BaseModel):
    name: str = Field(..., min_length=2)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    tier: str = Field(..., pattern='^(starter|business|enterprise)$')
    agent_initials: str = Field(..., min_length=2, max_length=5)
    business_name: Optional[str] = None
    business_type: Optional[str] = None


class AgentSignupResponse(BaseModel):
    user_id: str
    email: Optional[str]
    phone: Optional[str]
    name: str
    tier: str
    promo_price: float
    regular_price: float
    savings: float
    agent_tag: str
    promo_used: bool
    temp_password: Optional[str] = None


@app.get("/api/agent/dashboard")
async def agent_dashboard(agent: dict = Depends(require_agent)):
    """Get agent dashboard with their signup statistics"""
    agent_id = agent["user_id"]
    agent_initials = agent.get("agent_initials", "")
    
    # Get all signups by this agent
    signups = await agent_signups_collection.find(
        {"agent_id": agent_id},
        {"_id": 0}
    ).to_list(length=1000)
    
    # Calculate statistics
    total_signups = len(signups)
    total_promo_used = sum(1 for s in signups if s.get("promo_applied"))
    total_savings_given = sum(s.get("savings", 0) for s in signups)
    
    # Signups by tier
    by_tier = {"starter": 0, "business": 0, "enterprise": 0}
    for signup in signups:
        tier = signup.get("tier")
        if tier in by_tier:
            by_tier[tier] += 1
    
    # Recent signups
    recent_signups = sorted(signups, key=lambda x: x.get("created_at", ""), reverse=True)[:10]
    
    return {
        "agent_id": agent_id,
        "agent_name": agent.get("name"),
        "agent_initials": agent_initials,
        "statistics": {
            "total_signups": total_signups,
            "promo_signups": total_promo_used,
            "total_savings_given": total_savings_given,
            "by_tier": by_tier
        },
        "promotional_pricing": AGENT_PROMOTIONAL_PRICING,
        "recent_signups": recent_signups
    }


@app.get("/api/agent/promotional-plans")
async def get_promotional_plans(agent: dict = Depends(require_agent)):
    """Get available promotional plans for agents"""
    plans = []
    for tier_key in ["starter", "business", "enterprise"]:
        tier_data = SUBSCRIPTION_TIERS[tier_key]
        promo_data = AGENT_PROMOTIONAL_PRICING[tier_key]
        
        plans.append({
            "tier": tier_key,
            "name": tier_data["name"],
            "regular_price": promo_data["regular_price_monthly"],
            "promo_price": promo_data["promo_price_monthly"],
            "savings": promo_data["savings"],
            "features": tier_data["features"],
            "description": tier_data["description"]
        })
    
    return {"plans": plans}


@app.post("/api/agent/signup-user", response_model=AgentSignupResponse)
async def agent_signup_user(data: AgentUserSignup, agent: dict = Depends(require_agent)):
    """Agent signs up a new user with promotional pricing"""
    
    # Validate that either email or phone is provided
    if not data.email and not data.phone:
        raise HTTPException(status_code=400, detail="Either email or phone is required")
    
    # Check if user already exists
    query = {}
    if data.email:
        query["email"] = data.email.lower()
    if data.phone:
        phone = data.phone.replace(" ", "").replace("-", "")
        if phone.startswith("0"):
            phone = "+234" + phone[1:]
        elif not phone.startswith("+"):
            phone = "+234" + phone
        query["phone"] = phone
    
    existing_user = await users_collection.find_one(
        {"$or": [{"email": query.get("email")}, {"phone": query.get("phone")}]} if query.get("email") and query.get("phone") 
        else query,
        {"_id": 0}
    )
    
    if existing_user:
        # Check if user already used promotional discount
        if existing_user.get("promo_discount_used"):
            raise HTTPException(
                status_code=400, 
                detail="This user has already used their promotional discount. They can subscribe at regular prices."
            )
        
        # Update existing user with promo eligibility
        user_id = existing_user["user_id"]
    else:
        # Create new user
        user_id = generate_id("user")
        temp_password = secrets.token_urlsafe(8)
        hashed_password = hash_password(temp_password)
        
        now = datetime.now(timezone.utc)
        
        new_user = {
            "user_id": user_id,
            "name": data.name,
            "auth_provider": "agent",
            "role": "user",
            "status": "active",
            "agent_tag": data.agent_initials.upper(),
            "signed_up_by_agent": agent["user_id"],
            "promo_discount_used": False,
            "promo_eligible": True,
            "created_at": now.isoformat()
        }
        
        if data.email:
            new_user["email"] = data.email.lower()
            new_user["password_hash"] = hashed_password
        
        if data.phone:
            phone = data.phone.replace(" ", "").replace("-", "")
            if phone.startswith("0"):
                phone = "+234" + phone[1:]
            elif not phone.startswith("+"):
                phone = "+234" + phone
            new_user["phone"] = phone
        
        await users_collection.insert_one(new_user)
    
    # Get promotional pricing
    promo_data = AGENT_PROMOTIONAL_PRICING[data.tier]
    tier_data = SUBSCRIPTION_TIERS[data.tier]
    
    now = datetime.now(timezone.utc)
    
    # Create subscription with promotional pricing
    subscription_id = generate_id("sub")
    period_end = now + timedelta(days=30)
    
    await subscriptions_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "subscription_id": subscription_id,
            "user_id": user_id,
            "tier": data.tier,
            "status": "pending_payment",
            "billing_cycle": "monthly",
            "is_promotional": True,
            "promo_price": promo_data["promo_price_monthly"],
            "regular_price": promo_data["regular_price_monthly"],
            "agent_id": agent["user_id"],
            "agent_tag": data.agent_initials.upper(),
            "current_period_start": now.isoformat(),
            "current_period_end": period_end.isoformat(),
            "created_at": now.isoformat()
        }},
        upsert=True
    )
    
    # Mark user as having used promo
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "promo_discount_used": True,
            "promo_tier": data.tier,
            "agent_tag": data.agent_initials.upper()
        }}
    )
    
    # Log the signup
    await agent_signups_collection.insert_one({
        "signup_id": generate_id("ags"),
        "agent_id": agent["user_id"],
        "agent_tag": data.agent_initials.upper(),
        "user_id": user_id,
        "user_name": data.name,
        "user_email": data.email.lower() if data.email else None,
        "user_phone": query.get("phone"),
        "tier": data.tier,
        "promo_price": promo_data["promo_price_monthly"],
        "regular_price": promo_data["regular_price_monthly"],
        "savings": promo_data["savings"],
        "promo_applied": True,
        "business_name": data.business_name,
        "business_type": data.business_type,
        "created_at": now.isoformat()
    })
    
    # Create business if provided
    if data.business_name:
        business_id = generate_id("biz")
        await businesses_collection.insert_one({
            "business_id": business_id,
            "user_id": user_id,
            "name": data.business_name,
            "type": data.business_type or "General",
            "created_at": now.isoformat()
        })
    
    return AgentSignupResponse(
        user_id=user_id,
        email=data.email,
        phone=query.get("phone") if data.phone else None,
        name=data.name,
        tier=data.tier,
        promo_price=promo_data["promo_price_monthly"],
        regular_price=promo_data["regular_price_monthly"],
        savings=promo_data["savings"],
        agent_tag=data.agent_initials.upper(),
        promo_used=True,
        temp_password=temp_password if not existing_user else None
    )


@app.get("/api/agent/signups")
async def get_agent_signups(
    agent: dict = Depends(require_agent),
    page: int = 1,
    limit: int = 20,
    tier: Optional[str] = None
):
    """Get list of users signed up by this agent"""
    agent_id = agent["user_id"]
    
    query = {"agent_id": agent_id}
    if tier:
        query["tier"] = tier
    
    skip = (page - 1) * limit
    
    signups = await agent_signups_collection.find(
        query, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    total = await agent_signups_collection.count_documents(query)
    
    return {
        "signups": signups,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@app.get("/api/agent/check-user/{identifier}")
async def agent_check_user_eligibility(identifier: str, agent: dict = Depends(require_agent)):
    """Check if a user is eligible for promotional pricing"""
    # Try to find by email or phone
    user = await users_collection.find_one(
        {"$or": [
            {"email": identifier.lower()},
            {"phone": identifier},
            {"phone": "+234" + identifier[1:] if identifier.startswith("0") else identifier}
        ]},
        {"_id": 0}
    )
    
    if not user:
        return {
            "found": False,
            "eligible_for_promo": True,
            "message": "New user - eligible for promotional discount"
        }
    
    promo_used = user.get("promo_discount_used", False)
    
    return {
        "found": True,
        "user_id": user.get("user_id"),
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "current_tier": user.get("subscription_tier", "free"),
        "eligible_for_promo": not promo_used,
        "promo_used": promo_used,
        "agent_tag": user.get("agent_tag"),
        "message": "Already used promotional discount" if promo_used else "Eligible for promotional discount"
    }


# ============== ADMIN SYSTEM ==============

# Admin collections
admin_logs_collection = db["admin_logs"]
tax_rules_collection = db["tax_rules"]
system_settings_collection = db["system_settings"]


class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None


class CreateAgentRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2)
    agent_initials: str = Field(..., min_length=2, max_length=5)
    phone: Optional[str] = None


class TaxRuleUpdate(BaseModel):
    vat_rate: Optional[float] = None
    tax_free_threshold: Optional[float] = None
    income_tax_brackets: Optional[List[dict]] = None


async def log_admin_action(admin_id: str, action: str, target_type: str, target_id: str, details: dict = None):
    """Log admin actions for audit trail"""
    await admin_logs_collection.insert_one({
        "log_id": generate_id("log"),
        "admin_id": admin_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip_address": None  # Can be added from request
    })


@app.post("/api/admin/create-agent")
async def create_agent_account(data: CreateAgentRequest, admin: dict = Depends(require_superadmin)):
    """Create a new agent account (superadmin only)"""
    # Check if email already exists
    existing = await users_collection.find_one({"email": data.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create agent user
    user_id = generate_id("user")
    temp_password = secrets.token_urlsafe(10)
    hashed_password = hash_password(temp_password)
    
    now = datetime.now(timezone.utc)
    
    await users_collection.insert_one({
        "user_id": user_id,
        "email": data.email.lower(),
        "name": data.name,
        "phone": data.phone,
        "password_hash": hashed_password,
        "auth_provider": "email",
        "role": "agent",
        "agent_initials": data.agent_initials.upper(),
        "status": "active",
        "created_at": now.isoformat(),
        "created_by": admin["user_id"]
    })
    
    await log_admin_action(admin["user_id"], "create_agent", "user", user_id, {
        "email": data.email,
        "name": data.name,
        "agent_initials": data.agent_initials.upper()
    })
    
    return {
        "status": "success",
        "message": "Agent account created successfully",
        "agent": {
            "user_id": user_id,
            "email": data.email.lower(),
            "name": data.name,
            "agent_initials": data.agent_initials.upper(),
            "temp_password": temp_password
        },
        "instructions": "Please share the temporary password with the agent. They should change it after first login."
    }


@app.get("/api/admin/agents")
async def list_agents(admin: dict = Depends(require_admin)):
    """List all agent accounts"""
    agents = await users_collection.find(
        {"role": "agent"},
        {"_id": 0, "password_hash": 0}
    ).to_list(length=100)
    
    # Get signup stats for each agent
    for agent in agents:
        agent_id = agent["user_id"]
        total_signups = await agent_signups_collection.count_documents({"agent_id": agent_id})
        total_promo = await agent_signups_collection.count_documents({"agent_id": agent_id, "promo_applied": True})
        agent["stats"] = {
            "total_signups": total_signups,
            "promo_signups": total_promo
        }
    
    return {"agents": agents}


# ============== ADMIN OVERVIEW ==============

@app.get("/api/admin/overview")
async def admin_overview(admin: dict = Depends(require_admin)):
    """Get admin dashboard overview metrics"""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Total users
    total_users = await users_collection.count_documents({})
    active_users = await users_collection.count_documents({"status": {"$ne": "suspended"}})
    new_users_this_month = await users_collection.count_documents({
        "created_at": {"$gte": month_start}
    })
    
    # Total businesses
    total_businesses = await businesses_collection.count_documents({})
    
    # Total transactions
    total_transactions = await transactions_collection.count_documents({})
    transactions_this_month = await transactions_collection.count_documents({
        "date": {"$gte": month_start.strftime("%Y-%m-%d")}
    })
    
    # Calculate MRR (Monthly Recurring Revenue)
    active_subscriptions = await subscriptions_collection.find(
        {"status": "active", "tier": {"$ne": "free"}},
        {"_id": 0, "tier": 1, "billing_cycle": 1}
    ).to_list(length=10000)
    
    mrr = 0
    for sub in active_subscriptions:
        tier = sub.get("tier", "free")
        tier_data = SUBSCRIPTION_TIERS.get(tier, {})
        if sub.get("billing_cycle") == "yearly":
            mrr += tier_data.get("price_yearly", 0) / 12
        else:
            mrr += tier_data.get("price_monthly", 0)
    
    # Subscription breakdown
    sub_breakdown = {
        "free": await subscriptions_collection.count_documents({"tier": "free"}),
        "starter": await subscriptions_collection.count_documents({"tier": "starter"}),
        "business": await subscriptions_collection.count_documents({"tier": "business"}),
        "enterprise": await subscriptions_collection.count_documents({"tier": "enterprise"})
    }
    
    # Free users (no subscription record = free tier)
    users_with_sub = await subscriptions_collection.distinct("user_id")
    sub_breakdown["free"] = total_users - len(users_with_sub) + sub_breakdown.get("free", 0)
    
    # System health
    system_health = {
        "database": "healthy",
        "api": "healthy",
        "email_service": "healthy" if resend.api_key and resend.api_key != "re_demo_key" else "not_configured",
        "payment_service": "healthy" if os.environ.get("STRIPE_API_KEY") else "not_configured"
    }
    
    # Recent errors (last 24h)
    yesterday = now - timedelta(days=1)
    error_logs = await admin_logs_collection.count_documents({
        "action": "error",
        "timestamp": {"$gte": yesterday.isoformat()}
    })
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "suspended": total_users - active_users,
            "new_this_month": new_users_this_month
        },
        "businesses": {
            "total": total_businesses
        },
        "transactions": {
            "total": total_transactions,
            "this_month": transactions_this_month
        },
        "revenue": {
            "mrr": round(mrr, 2),
            "currency": "NGN"
        },
        "subscriptions": sub_breakdown,
        "system_health": system_health,
        "error_count_24h": error_logs
    }


# ============== ADMIN USERS ==============

@app.get("/api/admin/users")
async def admin_list_users(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """List all users with pagination and filters"""
    query = {}
    
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
            {"user_id": {"$regex": search, "$options": "i"}}
        ]
    
    if role:
        query["role"] = role
    
    if status:
        query["status"] = status
    
    skip = (page - 1) * limit
    
    total = await users_collection.count_documents(query)
    users = await users_collection.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    # Enrich with subscription and business data
    enriched_users = []
    for user in users:
        subscription = await subscriptions_collection.find_one({"user_id": user["user_id"]}, {"_id": 0})
        business = await businesses_collection.find_one({"user_id": user["user_id"]}, {"_id": 0})
        
        enriched_users.append({
            **user,
            "subscription_tier": subscription.get("tier", "free") if subscription else "free",
            "has_business": business is not None,
            "business_name": business.get("business_name") if business else None
        })
    
    return {
        "users": enriched_users,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@app.get("/api/admin/users/{user_id}")
async def admin_get_user(user_id: str, admin: dict = Depends(require_admin)):
    """Get detailed user information"""
    user = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get related data
    subscription = await subscriptions_collection.find_one({"user_id": user_id}, {"_id": 0})
    business = await businesses_collection.find_one({"user_id": user_id}, {"_id": 0})
    mfa = await mfa_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    # Transaction stats
    tx_count = await transactions_collection.count_documents({"business_id": business["business_id"]} if business else {})
    
    # Payment history
    payments = await payment_transactions_collection.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(length=10)
    
    return {
        "user": user,
        "subscription": subscription,
        "business": business,
        "mfa_enabled": mfa.get("totp_enabled", False) if mfa else False,
        "transaction_count": tx_count,
        "payment_history": payments
    }


@app.patch("/api/admin/users/{user_id}")
async def admin_update_user(user_id: str, update: AdminUserUpdate, admin: dict = Depends(require_admin)):
    """Update user role or status"""
    user = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {}
    
    if update.role is not None:
        # Only superadmin can change roles
        if admin.get("role") != "superadmin" and update.role in ["admin", "superadmin"]:
            raise HTTPException(status_code=403, detail="Only superadmin can assign admin roles")
        
        if update.role not in ["user", "agent", "admin", "superadmin"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        update_data["role"] = update.role
    
    if update.status is not None:
        if update.status not in ["active", "suspended"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        update_data["status"] = update.status
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await users_collection.update_one({"user_id": user_id}, {"$set": update_data})
    
    # Log the action
    await log_admin_action(
        admin_id=admin["user_id"],
        action="user_update",
        target_type="user",
        target_id=user_id,
        details={"changes": update_data}
    )
    
    return {"status": "success", "message": "User updated", "updates": update_data}


@app.post("/api/admin/users/{user_id}/suspend")
async def admin_suspend_user(user_id: str, admin: dict = Depends(require_admin)):
    """Suspend a user account"""
    user = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("role") in ["admin", "superadmin"] and admin.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Cannot suspend admin users")
    
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"status": "suspended", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Invalidate all sessions
    await sessions_collection.delete_many({"user_id": user_id})
    
    await log_admin_action(admin["user_id"], "user_suspend", "user", user_id)
    
    return {"status": "success", "message": "User suspended"}


@app.post("/api/admin/users/{user_id}/activate")
async def admin_activate_user(user_id: str, admin: dict = Depends(require_admin)):
    """Activate a suspended user account"""
    user = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"status": "active", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    await log_admin_action(admin["user_id"], "user_activate", "user", user_id)
    
    return {"status": "success", "message": "User activated"}


@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin: dict = Depends(require_superadmin)):
    """Delete a user account permanently (superadmin only)"""
    user = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if user_id == admin["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Prevent deleting other superadmins
    if user.get("role") == "superadmin":
        raise HTTPException(status_code=403, detail="Cannot delete superadmin accounts")
    
    # Delete user's business
    business = await businesses_collection.find_one({"user_id": user_id}, {"_id": 0})
    if business:
        # Delete all transactions for this business
        await transactions_collection.delete_many({"business_id": business["business_id"]})
        await businesses_collection.delete_one({"user_id": user_id})
    
    # Delete user sessions
    await sessions_collection.delete_many({"user_id": user_id})
    
    # Delete MFA data
    await mfa_collection.delete_one({"user_id": user_id})
    await backup_codes_collection.delete_one({"user_id": user_id})
    
    # Delete subscription data
    await subscriptions_collection.delete_one({"user_id": user_id})
    
    # Delete the user
    await users_collection.delete_one({"user_id": user_id})
    
    await log_admin_action(admin["user_id"], "user_delete", "user", user_id, {"email": user.get("email")})
    
    return {"status": "success", "message": f"User {user.get('email')} deleted permanently"}


@app.post("/api/admin/users/{user_id}/change-tier")
async def admin_change_user_tier(user_id: str, tier: str, admin: dict = Depends(require_superadmin)):
    """Change a user's subscription tier (superadmin only)"""
    valid_tiers = ["free", "starter", "business", "enterprise"]
    
    if tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}")
    
    user = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update or create subscription
    subscription = await subscriptions_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    now = datetime.now(timezone.utc)
    
    if subscription:
        old_tier = subscription.get("tier", "free")
        await subscriptions_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "tier": tier,
                "updated_at": now.isoformat(),
                "admin_override": True,
                "admin_override_by": admin["user_id"],
                "admin_override_at": now.isoformat()
            }}
        )
    else:
        old_tier = "free"
        await subscriptions_collection.insert_one({
            "subscription_id": f"sub_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "tier": tier,
            "status": "active",
            "billing_cycle": "admin_override",
            "admin_override": True,
            "admin_override_by": admin["user_id"],
            "admin_override_at": now.isoformat(),
            "created_at": now.isoformat()
        })
    
    await log_admin_action(admin["user_id"], "tier_change", "user", user_id, {"old_tier": old_tier, "new_tier": tier})
    
    return {"status": "success", "message": f"User tier changed from {old_tier} to {tier}"}


@app.post("/api/admin/users/{user_id}/promote-to-agent")
async def admin_promote_to_agent(user_id: str, agent_initials: str, admin: dict = Depends(require_superadmin)):
    """Promote a user to agent role (superadmin only)"""
    # Validate agent initials
    agent_initials = agent_initials.strip().upper()
    if len(agent_initials) < 2 or len(agent_initials) > 5:
        raise HTTPException(status_code=400, detail="Agent initials must be 2-5 characters")
    
    user = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_role = user.get("role", "user")
    
    if old_role in ["admin", "superadmin"]:
        raise HTTPException(status_code=400, detail="Cannot demote admin/superadmin to agent")
    
    if old_role == "agent":
        raise HTTPException(status_code=400, detail="User is already an agent")
    
    # Check if agent initials are already in use
    existing_agent = await users_collection.find_one({
        "agent_initials": agent_initials,
        "user_id": {"$ne": user_id}
    }, {"_id": 0})
    
    if existing_agent:
        raise HTTPException(status_code=400, detail=f"Agent initials '{agent_initials}' are already in use by another agent")
    
    # Update user to agent role
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "role": "agent",
            "agent_initials": agent_initials,
            "promoted_to_agent_at": datetime.now(timezone.utc).isoformat(),
            "promoted_by": admin["user_id"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await log_admin_action(admin["user_id"], "promote_to_agent", "user", user_id, {
        "old_role": old_role,
        "new_role": "agent",
        "agent_initials": agent_initials
    })
    
    return {
        "status": "success",
        "message": f"User {user.get('email')} promoted to agent with initials '{agent_initials}'",
        "agent_initials": agent_initials
    }


@app.post("/api/admin/users/{user_id}/revoke-agent")
async def admin_revoke_agent(user_id: str, admin: dict = Depends(require_superadmin)):
    """Revoke agent role from a user (superadmin only)"""
    user = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("role") != "agent":
        raise HTTPException(status_code=400, detail="User is not an agent")
    
    # Update user back to regular user role
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "role": "user",
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        "$unset": {
            "agent_initials": "",
            "promoted_to_agent_at": "",
            "promoted_by": ""
        }}
    )
    
    await log_admin_action(admin["user_id"], "revoke_agent", "user", user_id, {
        "old_agent_initials": user.get("agent_initials")
    })
    
    return {"status": "success", "message": f"Agent role revoked from {user.get('email')}"}


# ============== ADMIN BUSINESSES ==============

@app.get("/api/admin/businesses")
async def admin_list_businesses(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    industry: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """List all businesses"""
    query = {}
    
    if search:
        query["$or"] = [
            {"business_name": {"$regex": search, "$options": "i"}},
            {"business_id": {"$regex": search, "$options": "i"}}
        ]
    
    if industry:
        query["industry"] = industry
    
    skip = (page - 1) * limit
    
    total = await businesses_collection.count_documents(query)
    businesses = await businesses_collection.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    # Enrich with user and transaction data
    enriched = []
    for biz in businesses:
        user = await users_collection.find_one({"user_id": biz["user_id"]}, {"_id": 0, "email": 1, "name": 1})
        tx_count = await transactions_collection.count_documents({"business_id": biz["business_id"]})
        
        # Calculate tax readiness
        transactions = await transactions_collection.find({"business_id": biz["business_id"]}, {"_id": 0}).to_list(length=1000)
        tax_readiness = calculate_tax_readiness(transactions, bool(biz.get("tin")))
        
        enriched.append({
            **biz,
            "owner_email": user.get("email") if user else None,
            "owner_name": user.get("name") if user else None,
            "transaction_count": tx_count,
            "tax_readiness_score": tax_readiness
        })
    
    return {
        "businesses": enriched,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@app.get("/api/admin/businesses/{business_id}")
async def admin_get_business(business_id: str, admin: dict = Depends(require_admin)):
    """Get detailed business information"""
    business = await businesses_collection.find_one({"business_id": business_id}, {"_id": 0})
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    user = await users_collection.find_one({"user_id": business["user_id"]}, {"_id": 0})
    subscription = await subscriptions_collection.find_one({"user_id": business["user_id"]}, {"_id": 0})
    
    # Financial summary
    transactions = await transactions_collection.find({"business_id": business_id}, {"_id": 0}).to_list(length=10000)
    
    income = sum(t["amount"] for t in transactions if t.get("type") == "income")
    expenses = sum(t["amount"] for t in transactions if t.get("type") == "expense")
    
    tax_readiness = calculate_tax_readiness(transactions, bool(business.get("tin")))
    
    return {
        "business": business,
        "owner": user,
        "subscription": subscription,
        "financial_summary": {
            "total_income": income,
            "total_expenses": expenses,
            "net_profit": income - expenses,
            "transaction_count": len(transactions)
        },
        "tax_readiness_score": tax_readiness,
        "compliance_status": "compliant" if tax_readiness >= 70 else "needs_attention" if tax_readiness >= 40 else "at_risk"
    }


# ============== ADMIN TRANSACTIONS ==============

@app.get("/api/admin/transactions")
async def admin_list_transactions(
    page: int = 1,
    limit: int = 50,
    type: Optional[str] = None,
    category: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    flagged: Optional[bool] = None,
    admin: dict = Depends(require_admin)
):
    """List all transactions globally with filters"""
    query = {}
    
    if type:
        query["type"] = type
    
    if category:
        query["category"] = category
    
    if min_amount is not None:
        query["amount"] = {"$gte": min_amount}
    
    if max_amount is not None:
        if "amount" in query:
            query["amount"]["$lte"] = max_amount
        else:
            query["amount"] = {"$lte": max_amount}
    
    if flagged is not None:
        query["flagged"] = flagged
    
    skip = (page - 1) * limit
    
    total = await transactions_collection.count_documents(query)
    transactions = await transactions_collection.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    # Enrich with business names
    enriched = []
    for tx in transactions:
        business = await businesses_collection.find_one({"business_id": tx.get("business_id")}, {"_id": 0, "business_name": 1})
        enriched.append({
            **tx,
            "business_name": business.get("business_name") if business else "Unknown"
        })
    
    # Calculate totals
    total_income = sum(t["amount"] for t in enriched if t.get("type") == "income")
    total_expense = sum(t["amount"] for t in enriched if t.get("type") == "expense")
    
    return {
        "transactions": enriched,
        "totals": {
            "income": total_income,
            "expense": total_expense
        },
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@app.post("/api/admin/transactions/{transaction_id}/flag")
async def admin_flag_transaction(transaction_id: str, reason: str = "", admin: dict = Depends(require_admin)):
    """Flag a transaction as suspicious"""
    tx = await transactions_collection.find_one({"transaction_id": transaction_id}, {"_id": 0})
    
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    await transactions_collection.update_one(
        {"transaction_id": transaction_id},
        {"$set": {
            "flagged": True,
            "flag_reason": reason,
            "flagged_by": admin["user_id"],
            "flagged_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await log_admin_action(admin["user_id"], "transaction_flag", "transaction", transaction_id, {"reason": reason})
    
    return {"status": "success", "message": "Transaction flagged"}


@app.post("/api/admin/transactions/{transaction_id}/unflag")
async def admin_unflag_transaction(transaction_id: str, admin: dict = Depends(require_admin)):
    """Remove flag from a transaction"""
    tx = await transactions_collection.find_one({"transaction_id": transaction_id}, {"_id": 0})
    
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    await transactions_collection.update_one(
        {"transaction_id": transaction_id},
        {"$unset": {"flagged": "", "flag_reason": "", "flagged_by": "", "flagged_at": ""}}
    )
    
    await log_admin_action(admin["user_id"], "transaction_unflag", "transaction", transaction_id)
    
    return {"status": "success", "message": "Transaction unflagged"}


# ============== ADMIN TAX ENGINE ==============

@app.get("/api/admin/tax-rules")
async def admin_get_tax_rules(admin: dict = Depends(require_admin)):
    """Get current tax rules configuration"""
    rules = await tax_rules_collection.find_one({"active": True}, {"_id": 0})
    
    if not rules:
        # Return defaults (use "unlimited" string instead of float('inf') for JSON serialization)
        rules = {
            "vat_rate": VAT_RATE,
            "tax_free_threshold": TAX_FREE_THRESHOLD,
            "income_tax_brackets": [
                {"amount": 300000, "rate": 0.07},
                {"amount": 300000, "rate": 0.11},
                {"amount": 500000, "rate": 0.15},
                {"amount": 500000, "rate": 0.19},
                {"amount": 1600000, "rate": 0.21},
                {"amount": "unlimited", "rate": 0.24}
            ],
            "effective_date": "2025-01-01",
            "active": True
        }
    
    return rules


@app.put("/api/admin/tax-rules")
async def admin_update_tax_rules(update: TaxRuleUpdate, admin: dict = Depends(require_superadmin)):
    """Update tax rules (superadmin only)"""
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": admin["user_id"]}
    
    if update.vat_rate is not None:
        if not 0 <= update.vat_rate <= 1:
            raise HTTPException(status_code=400, detail="VAT rate must be between 0 and 1")
        update_data["vat_rate"] = update.vat_rate
    
    if update.tax_free_threshold is not None:
        if update.tax_free_threshold < 0:
            raise HTTPException(status_code=400, detail="Tax free threshold must be positive")
        update_data["tax_free_threshold"] = update.tax_free_threshold
    
    if update.income_tax_brackets is not None:
        update_data["income_tax_brackets"] = update.income_tax_brackets
    
    # Deactivate old rules and create new
    await tax_rules_collection.update_many({"active": True}, {"$set": {"active": False}})
    
    current_rules = await tax_rules_collection.find_one({"active": False}, {"_id": 0})
    new_rules = {**(current_rules or {}), **update_data, "active": True, "effective_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
    new_rules.pop("_id", None)
    
    await tax_rules_collection.insert_one(new_rules)
    
    await log_admin_action(admin["user_id"], "tax_rules_update", "system", "tax_rules", update_data)
    
    return {"status": "success", "message": "Tax rules updated", "rules": new_rules}


# ============== ADMIN SUBSCRIPTIONS ==============

@app.get("/api/admin/subscriptions")
async def admin_list_subscriptions(
    page: int = 1,
    limit: int = 20,
    tier: Optional[str] = None,
    status: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """List all subscriptions"""
    query = {}
    
    if tier:
        query["tier"] = tier
    
    if status:
        query["status"] = status
    
    skip = (page - 1) * limit
    
    total = await subscriptions_collection.count_documents(query)
    subscriptions = await subscriptions_collection.find(query, {"_id": 0}).sort("updated_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    # Enrich with user data
    enriched = []
    for sub in subscriptions:
        user = await users_collection.find_one({"user_id": sub["user_id"]}, {"_id": 0, "email": 1, "name": 1})
        tier_data = SUBSCRIPTION_TIERS.get(sub.get("tier", "free"), {})
        enriched.append({
            **sub,
            "user_email": user.get("email") if user else None,
            "user_name": user.get("name") if user else None,
            "tier_name": tier_data.get("name", "Free"),
            "price_monthly": tier_data.get("price_monthly", 0)
        })
    
    return {
        "subscriptions": enriched,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@app.post("/api/admin/subscriptions/{user_id}/override")
async def admin_override_subscription(
    user_id: str,
    tier: str,
    duration_days: int = 30,
    admin: dict = Depends(require_superadmin)
):
    """Override a user's subscription (superadmin only)"""
    user = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if tier not in SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=duration_days)
    
    await subscriptions_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "subscription_id": generate_id("sub"),
            "user_id": user_id,
            "tier": tier,
            "status": "active",
            "billing_cycle": "manual_override",
            "current_period_start": now.isoformat(),
            "current_period_end": period_end.isoformat(),
            "override_by": admin["user_id"],
            "updated_at": now.isoformat()
        }},
        upsert=True
    )
    
    await log_admin_action(admin["user_id"], "subscription_override", "subscription", user_id, {"tier": tier, "duration_days": duration_days})
    
    return {"status": "success", "message": f"Subscription overridden to {tier} for {duration_days} days"}


# ============== ADMIN LOGS ==============

@app.get("/api/admin/logs")
async def admin_get_logs(
    page: int = 1,
    limit: int = 50,
    action: Optional[str] = None,
    admin_id: Optional[str] = None,
    target_type: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Get admin action logs"""
    query = {}
    
    if action:
        query["action"] = action
    
    if admin_id:
        query["admin_id"] = admin_id
    
    if target_type:
        query["target_type"] = target_type
    
    skip = (page - 1) * limit
    
    total = await admin_logs_collection.count_documents(query)
    logs = await admin_logs_collection.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit).to_list(length=limit)
    
    # Enrich with admin names
    enriched = []
    for log in logs:
        admin_user = await users_collection.find_one({"user_id": log.get("admin_id")}, {"_id": 0, "name": 1, "email": 1})
        enriched.append({
            **log,
            "admin_name": admin_user.get("name") if admin_user else "Unknown",
            "admin_email": admin_user.get("email") if admin_user else None
        })
    
    return {
        "logs": enriched,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@app.get("/api/admin/logs/errors")
async def admin_get_error_logs(
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """Get system error logs"""
    query = {"action": "error"}
    
    skip = (page - 1) * limit
    
    total = await admin_logs_collection.count_documents(query)
    logs = await admin_logs_collection.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return {
        "logs": logs,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@app.get("/api/admin/logs/api-calls")
async def admin_get_api_logs(
    page: int = 1,
    limit: int = 100,
    admin: dict = Depends(require_admin)
):
    """Get recent API call statistics"""
    # This would typically come from a logging middleware
    # For now, return email logs as example
    email_logs = await email_logs_collection.find({}, {"_id": 0}).sort("sent_at", -1).limit(limit).to_list(length=limit)
    
    return {
        "email_logs": email_logs,
        "total_email_sent": await email_logs_collection.count_documents({"status": "sent"}),
        "total_email_failed": await email_logs_collection.count_documents({"status": "failed"})
    }


# ============== ADMIN SYSTEM SETTINGS ==============

@app.get("/api/admin/settings")
async def admin_get_settings(admin: dict = Depends(require_superadmin)):
    """Get system settings (superadmin only)"""
    settings = await system_settings_collection.find_one({"type": "global"}, {"_id": 0})
    
    if not settings:
        settings = {
            "type": "global",
            "maintenance_mode": False,
            "registration_enabled": True,
            "email_notifications_enabled": True,
            "max_transactions_per_month_free": 50
        }
    
    return settings


@app.put("/api/admin/settings")
async def admin_update_settings(settings: dict, admin: dict = Depends(require_superadmin)):
    """Update system settings (superadmin only)"""
    settings["updated_at"] = datetime.now(timezone.utc).isoformat()
    settings["updated_by"] = admin["user_id"]
    settings["type"] = "global"
    
    await system_settings_collection.update_one(
        {"type": "global"},
        {"$set": settings},
        upsert=True
    )
    
    await log_admin_action(admin["user_id"], "settings_update", "system", "settings", settings)
    
    return {"status": "success", "message": "Settings updated"}


# ============== MONO BANK INTEGRATION ==============
# Collection for linked bank accounts
linked_accounts_collection = db["linked_bank_accounts"]
bank_transactions_collection = db["bank_transactions"]
bank_sync_logs_collection = db["bank_sync_logs"]

# Mono API Configuration
MONO_SECRET_KEY = os.environ.get("MONO_SECRET_KEY", "")
MONO_PUBLIC_KEY = os.environ.get("MONO_PUBLIC_KEY", "")
MONO_WEBHOOK_SECRET = os.environ.get("MONO_WEBHOOK_SECRET", "")
MONO_API_BASE = "https://api.withmono.com"


class LinkBankRequest(BaseModel):
    """Request to initiate bank account linking"""
    account_type: str = "financial_data"  # financial_data or payments


class LinkedAccountResponse(BaseModel):
    account_id: str
    institution_name: str
    institution_logo: Optional[str] = None
    account_name: str
    account_number: str
    account_type: str
    balance: float
    currency: str
    last_synced: Optional[str] = None
    status: str


class BankTransactionResponse(BaseModel):
    transaction_id: str
    account_id: str
    type: str  # debit or credit
    amount: float
    narration: str
    date: str
    balance: Optional[float] = None
    category: Optional[str] = None
    imported: bool = False


async def get_user_tier_limits(user_id: str) -> dict:
    """Get bank linking limits based on user's subscription tier"""
    subscription = await subscriptions_collection.find_one({"user_id": user_id}, {"_id": 0})
    tier = subscription.get("tier", "free") if subscription else "free"
    tier_data = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])
    
    return {
        "tier": tier,
        "linked_bank_accounts": tier_data["features"].get("linked_bank_accounts", 1),
        "bank_sync_frequency": tier_data["features"].get("bank_sync_frequency", "daily"),
        "manual_sync_per_day": tier_data["features"].get("manual_sync_per_day", 3)
    }


async def check_mono_configured():
    """Check if Mono API is configured"""
    if not MONO_SECRET_KEY:
        raise HTTPException(
            status_code=503, 
            detail="Bank integration not configured. Please contact support."
        )


@app.get("/api/bank/status")
async def get_bank_integration_status(user: dict = Depends(get_current_user)):
    """Get bank integration status and tier limits"""
    limits = await get_user_tier_limits(user["user_id"])
    
    # Count linked accounts
    linked_count = await linked_accounts_collection.count_documents({
        "user_id": user["user_id"],
        "status": {"$ne": "disconnected"}
    })
    
    # Check today's manual syncs
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_syncs = await bank_sync_logs_collection.count_documents({
        "user_id": user["user_id"],
        "sync_type": "manual",
        "created_at": {"$gte": today_start.isoformat()}
    })
    
    return {
        "configured": bool(MONO_SECRET_KEY),
        "tier": limits["tier"],
        "linked_accounts": linked_count,
        "max_accounts": limits["linked_bank_accounts"],
        "can_link_more": limits["linked_bank_accounts"] == -1 or linked_count < limits["linked_bank_accounts"],
        "sync_frequency": limits["bank_sync_frequency"],
        "manual_syncs_today": today_syncs,
        "manual_syncs_limit": limits["manual_sync_per_day"],
        "can_manual_sync": limits["manual_sync_per_day"] == -1 or today_syncs < limits["manual_sync_per_day"]
    }


@app.post("/api/bank/link/initiate")
async def initiate_bank_linking(data: LinkBankRequest, user: dict = Depends(get_current_user)):
    """Initiate bank account linking via Mono Connect"""
    await check_mono_configured()
    
    limits = await get_user_tier_limits(user["user_id"])
    linked_count = await linked_accounts_collection.count_documents({
        "user_id": user["user_id"],
        "status": {"$ne": "disconnected"}
    })
    
    # Check limits
    max_accounts = limits["linked_bank_accounts"]
    if max_accounts != -1 and linked_count >= max_accounts:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_limit_reached",
                "message": f"You can only link {max_accounts} bank account(s) on the {limits['tier'].title()} plan. Upgrade to link more.",
                "current": linked_count,
                "limit": max_accounts,
                "upgrade_required": True
            }
        )
    
    # Create Mono Connect session
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MONO_API_BASE}/v2/accounts/initiate",
                headers={
                    "mono-sec-key": MONO_SECRET_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "customer": {
                        "name": user.get("name", ""),
                        "email": user.get("email", "")
                    },
                    "meta": {
                        "user_id": user["user_id"]
                    },
                    "scope": data.account_type,
                    "redirect_url": os.environ.get("REACT_APP_BACKEND_URL", "") + "/bank/callback"
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Mono initiate error: {response.text}")
                raise HTTPException(status_code=502, detail="Failed to initiate bank linking")
            
            result = response.json()
            
            return {
                "mono_url": result.get("mono_url"),
                "session_id": result.get("id"),
                "public_key": MONO_PUBLIC_KEY,
                "instructions": "Use the Mono Connect widget with this public key to link your bank account."
            }
    
    except httpx.RequestError as e:
        logger.error(f"Mono API error: {str(e)}")
        raise HTTPException(status_code=502, detail="Bank service temporarily unavailable")


@app.post("/api/bank/link/exchange")
async def exchange_bank_token(request: Request, user: dict = Depends(get_current_user)):
    """Exchange Mono Connect code for account ID"""
    await check_mono_configured()
    
    data = await request.json()
    code = data.get("code")
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")
    
    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for account ID
            response = await client.post(
                f"{MONO_API_BASE}/account/auth",
                headers={
                    "mono-sec-key": MONO_SECRET_KEY,
                    "Content-Type": "application/json"
                },
                json={"code": code},
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Mono exchange error: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to link bank account")
            
            result = response.json()
            account_id = result.get("id")
            
            if not account_id:
                raise HTTPException(status_code=400, detail="Invalid response from bank service")
            
            # Get account details
            account_response = await client.get(
                f"{MONO_API_BASE}/accounts/{account_id}",
                headers={"mono-sec-key": MONO_SECRET_KEY},
                timeout=30.0
            )
            
            account_data = account_response.json() if account_response.status_code == 200 else {}
            account_info = account_data.get("account", {})
            institution = account_data.get("meta", {}).get("institution", {})
            
            # Save linked account
            linked_account = {
                "linked_account_id": f"link_{uuid.uuid4().hex[:12]}",
                "user_id": user["user_id"],
                "mono_account_id": account_id,
                "institution_name": institution.get("name", "Unknown Bank"),
                "institution_code": institution.get("bank_code", ""),
                "institution_logo": institution.get("icon", ""),
                "account_name": account_info.get("name", ""),
                "account_number": account_info.get("accountNumber", "")[-4:] if account_info.get("accountNumber") else "****",
                "account_type": account_info.get("type", "savings"),
                "balance": float(account_info.get("balance", 0)) / 100,  # Convert from kobo
                "currency": account_info.get("currency", "NGN"),
                "status": "active",
                "data_status": account_data.get("meta", {}).get("data_status", "PROCESSING"),
                "last_synced": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await linked_accounts_collection.insert_one(linked_account)
            
            # Log the link action
            await bank_sync_logs_collection.insert_one({
                "log_id": f"sync_{uuid.uuid4().hex[:12]}",
                "user_id": user["user_id"],
                "account_id": linked_account["linked_account_id"],
                "sync_type": "initial_link",
                "status": "success",
                "transactions_synced": 0,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            return {
                "success": True,
                "message": "Bank account linked successfully",
                "account": {
                    "account_id": linked_account["linked_account_id"],
                    "institution_name": linked_account["institution_name"],
                    "account_name": linked_account["account_name"],
                    "account_number": f"****{linked_account['account_number']}",
                    "balance": linked_account["balance"],
                    "status": linked_account["status"]
                }
            }
    
    except httpx.RequestError as e:
        logger.error(f"Mono API error: {str(e)}")
        raise HTTPException(status_code=502, detail="Bank service temporarily unavailable")


@app.get("/api/bank/accounts")
async def get_linked_accounts(user: dict = Depends(get_current_user)):
    """Get all linked bank accounts for the user"""
    accounts = await linked_accounts_collection.find(
        {"user_id": user["user_id"], "status": {"$ne": "disconnected"}},
        {"_id": 0}
    ).to_list(length=50)
    
    limits = await get_user_tier_limits(user["user_id"])
    
    return {
        "accounts": accounts,
        "count": len(accounts),
        "max_accounts": limits["linked_bank_accounts"],
        "can_link_more": limits["linked_bank_accounts"] == -1 or len(accounts) < limits["linked_bank_accounts"]
    }


@app.get("/api/bank/accounts/{account_id}")
async def get_linked_account(account_id: str, user: dict = Depends(get_current_user)):
    """Get details of a specific linked account"""
    account = await linked_accounts_collection.find_one(
        {"linked_account_id": account_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not account:
        raise HTTPException(status_code=404, detail="Linked account not found")
    
    # Get transaction count
    tx_count = await bank_transactions_collection.count_documents({
        "linked_account_id": account_id
    })
    
    # Get last sync log
    last_sync = await bank_sync_logs_collection.find_one(
        {"account_id": account_id},
        {"_id": 0},
        sort=[("created_at", -1)]
    )
    
    return {
        **account,
        "transaction_count": tx_count,
        "last_sync": last_sync
    }


@app.post("/api/bank/accounts/{account_id}/sync")
async def sync_bank_account(account_id: str, user: dict = Depends(get_current_user)):
    """Manually sync transactions from a linked bank account"""
    await check_mono_configured()
    
    account = await linked_accounts_collection.find_one(
        {"linked_account_id": account_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not account:
        raise HTTPException(status_code=404, detail="Linked account not found")
    
    # Check manual sync limits
    limits = await get_user_tier_limits(user["user_id"])
    if limits["manual_sync_per_day"] != -1:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_syncs = await bank_sync_logs_collection.count_documents({
            "user_id": user["user_id"],
            "sync_type": "manual",
            "created_at": {"$gte": today_start.isoformat()}
        })
        
        if today_syncs >= limits["manual_sync_per_day"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "sync_limit_reached",
                    "message": f"You've reached your daily limit of {limits['manual_sync_per_day']} manual syncs. Upgrade for more.",
                    "syncs_today": today_syncs,
                    "limit": limits["manual_sync_per_day"],
                    "upgrade_required": True
                }
            )
    
    try:
        async with httpx.AsyncClient() as client:
            # Trigger data refresh
            refresh_response = await client.post(
                f"{MONO_API_BASE}/accounts/{account['mono_account_id']}/sync",
                headers={"mono-sec-key": MONO_SECRET_KEY},
                timeout=30.0
            )
            
            # Get latest transactions (last 30 days)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            
            tx_response = await client.get(
                f"{MONO_API_BASE}/accounts/{account['mono_account_id']}/transactions",
                headers={"mono-sec-key": MONO_SECRET_KEY},
                params={
                    "start": start_date.strftime("%d-%m-%Y"),
                    "end": end_date.strftime("%d-%m-%Y"),
                    "paginate": "false"
                },
                timeout=60.0
            )
            
            transactions_synced = 0
            if tx_response.status_code == 200:
                tx_data = tx_response.json()
                transactions = tx_data.get("data", [])
                
                for tx in transactions:
                    # Check if transaction already exists
                    existing = await bank_transactions_collection.find_one({
                        "mono_transaction_id": tx.get("_id")
                    })
                    
                    if not existing:
                        # Save new transaction
                        bank_tx = {
                            "bank_transaction_id": f"btx_{uuid.uuid4().hex[:12]}",
                            "linked_account_id": account_id,
                            "user_id": user["user_id"],
                            "mono_transaction_id": tx.get("_id"),
                            "type": tx.get("type", "debit"),  # debit or credit
                            "amount": abs(float(tx.get("amount", 0))) / 100,  # Convert from kobo
                            "narration": tx.get("narration", ""),
                            "date": tx.get("date", ""),
                            "balance": float(tx.get("balance", 0)) / 100 if tx.get("balance") else None,
                            "category": auto_categorize_bank_transaction(tx.get("narration", ""), tx.get("type")),
                            "imported_to_monetrax": False,
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                        await bank_transactions_collection.insert_one(bank_tx)
                        transactions_synced += 1
            
            # Update account balance
            balance_response = await client.get(
                f"{MONO_API_BASE}/accounts/{account['mono_account_id']}",
                headers={"mono-sec-key": MONO_SECRET_KEY},
                timeout=30.0
            )
            
            if balance_response.status_code == 200:
                balance_data = balance_response.json()
                new_balance = float(balance_data.get("account", {}).get("balance", 0)) / 100
                
                await linked_accounts_collection.update_one(
                    {"linked_account_id": account_id},
                    {"$set": {
                        "balance": new_balance,
                        "last_synced": datetime.now(timezone.utc).isoformat()
                    }}
                )
            
            # Log sync
            await bank_sync_logs_collection.insert_one({
                "log_id": f"sync_{uuid.uuid4().hex[:12]}",
                "user_id": user["user_id"],
                "account_id": account_id,
                "sync_type": "manual",
                "status": "success",
                "transactions_synced": transactions_synced,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            return {
                "success": True,
                "message": f"Synced {transactions_synced} new transactions",
                "transactions_synced": transactions_synced,
                "last_synced": datetime.now(timezone.utc).isoformat()
            }
    
    except httpx.RequestError as e:
        logger.error(f"Mono sync error: {str(e)}")
        
        # Log failed sync
        await bank_sync_logs_collection.insert_one({
            "log_id": f"sync_{uuid.uuid4().hex[:12]}",
            "user_id": user["user_id"],
            "account_id": account_id,
            "sync_type": "manual",
            "status": "failed",
            "error": str(e),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        raise HTTPException(status_code=502, detail="Failed to sync with bank")


def auto_categorize_bank_transaction(narration: str, tx_type: str) -> str:
    """Auto-categorize bank transaction based on narration"""
    narration_lower = narration.lower()
    
    # Income categories (for credits)
    if tx_type == "credit":
        if any(kw in narration_lower for kw in ["salary", "wage", "payroll"]):
            return "Salary"
        elif any(kw in narration_lower for kw in ["transfer from", "inward", "credit"]):
            return "Transfer In"
        elif any(kw in narration_lower for kw in ["interest", "dividend"]):
            return "Interest"
        elif any(kw in narration_lower for kw in ["refund", "reversal"]):
            return "Refund"
        else:
            return "Other Income"
    
    # Expense categories (for debits)
    if any(kw in narration_lower for kw in ["airtime", "mtn", "glo", "airtel", "9mobile", "recharge"]):
        return "Communication"
    elif any(kw in narration_lower for kw in ["electricity", "nepa", "phcn", "ekedc", "ikedc", "power"]):
        return "Utilities"
    elif any(kw in narration_lower for kw in ["dstv", "gotv", "startimes", "netflix", "spotify"]):
        return "Entertainment"
    elif any(kw in narration_lower for kw in ["uber", "bolt", "taxi", "transport", "fuel", "petrol", "diesel"]):
        return "Transport"
    elif any(kw in narration_lower for kw in ["restaurant", "food", "eatery", "chicken", "pizza"]):
        return "Food"
    elif any(kw in narration_lower for kw in ["school", "tuition", "education", "course"]):
        return "Education"
    elif any(kw in narration_lower for kw in ["hospital", "clinic", "pharmacy", "medical", "health"]):
        return "Healthcare"
    elif any(kw in narration_lower for kw in ["rent", "housing", "accommodation"]):
        return "Rent"
    elif any(kw in narration_lower for kw in ["transfer to", "outward", "payment"]):
        return "Transfer Out"
    elif any(kw in narration_lower for kw in ["atm", "withdrawal", "cash"]):
        return "Cash Withdrawal"
    elif any(kw in narration_lower for kw in ["pos", "card", "purchase"]):
        return "Purchase"
    else:
        return "Other Expense"


@app.get("/api/bank/accounts/{account_id}/transactions")
async def get_bank_transactions(
    account_id: str,
    limit: int = 50,
    skip: int = 0,
    imported: Optional[bool] = None,
    tx_type: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get transactions from a linked bank account"""
    account = await linked_accounts_collection.find_one(
        {"linked_account_id": account_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not account:
        raise HTTPException(status_code=404, detail="Linked account not found")
    
    query = {"linked_account_id": account_id}
    
    if imported is not None:
        query["imported_to_monetrax"] = imported
    
    if tx_type:
        query["type"] = tx_type
    
    transactions = await bank_transactions_collection.find(
        query, {"_id": 0}
    ).sort("date", -1).skip(skip).limit(limit).to_list(length=limit)
    
    total = await bank_transactions_collection.count_documents(query)
    
    return {
        "transactions": transactions,
        "pagination": {
            "total": total,
            "limit": limit,
            "skip": skip,
            "has_more": (skip + limit) < total
        }
    }


@app.post("/api/bank/transactions/{transaction_id}/import")
async def import_bank_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    """Import a bank transaction into Monetrax as a regular transaction"""
    bank_tx = await bank_transactions_collection.find_one(
        {"bank_transaction_id": transaction_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not bank_tx:
        raise HTTPException(status_code=404, detail="Bank transaction not found")
    
    if bank_tx.get("imported_to_monetrax"):
        raise HTTPException(status_code=400, detail="Transaction already imported")
    
    # Get user's business
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=400, detail="Please create a business first")
    
    # Map bank transaction to Monetrax transaction
    tx_type = "income" if bank_tx["type"] == "credit" else "expense"
    
    # Map category to Monetrax categories
    category_mapping = {
        # Income
        "Salary": "Other Income",
        "Transfer In": "Other Income",
        "Interest": "Interest",
        "Refund": "Other Income",
        "Other Income": "Other Income",
        # Expense
        "Communication": "Communication",
        "Utilities": "Utilities",
        "Entertainment": "Other Expense",
        "Transport": "Transport",
        "Food": "Food",
        "Education": "Other Expense",
        "Healthcare": "Other Expense",
        "Rent": "Rent",
        "Transfer Out": "Other Expense",
        "Cash Withdrawal": "Other Expense",
        "Purchase": "Supplies",
        "Other Expense": "Other Expense"
    }
    
    category = category_mapping.get(bank_tx.get("category", ""), "Other Expense" if tx_type == "expense" else "Other Income")
    
    # Create Monetrax transaction
    monetrax_tx_id = f"txn_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Calculate VAT for taxable transactions
    is_taxable = tx_type == "income" and category in ["Sales", "Services", "Consulting"]
    vat_amount = calculate_vat(bank_tx["amount"]) if is_taxable else 0
    
    monetrax_tx = {
        "transaction_id": monetrax_tx_id,
        "business_id": business["business_id"],
        "type": tx_type,
        "category": category,
        "amount": bank_tx["amount"],
        "description": bank_tx["narration"],
        "date": bank_tx["date"][:10] if bank_tx.get("date") else now.strftime("%Y-%m-%d"),
        "is_taxable": is_taxable,
        "vat_amount": vat_amount,
        "payment_method": "Bank Transfer",
        "source": "bank_import",
        "bank_transaction_id": transaction_id,
        "created_at": now.isoformat()
    }
    
    await transactions_collection.insert_one(monetrax_tx)
    
    # Mark bank transaction as imported
    await bank_transactions_collection.update_one(
        {"bank_transaction_id": transaction_id},
        {"$set": {
            "imported_to_monetrax": True,
            "monetrax_transaction_id": monetrax_tx_id,
            "imported_at": now.isoformat()
        }}
    )
    
    return {
        "success": True,
        "message": "Transaction imported successfully",
        "monetrax_transaction_id": monetrax_tx_id,
        "transaction": monetrax_tx
    }


@app.post("/api/bank/transactions/import-bulk")
async def import_bulk_bank_transactions(request: Request, user: dict = Depends(get_current_user)):
    """Import multiple bank transactions at once"""
    data = await request.json()
    transaction_ids = data.get("transaction_ids", [])
    
    if not transaction_ids:
        raise HTTPException(status_code=400, detail="No transactions specified")
    
    if len(transaction_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 transactions per import")
    
    business = await get_user_business(user["user_id"])
    if not business:
        raise HTTPException(status_code=400, detail="Please create a business first")
    
    imported_count = 0
    errors = []
    
    for tx_id in transaction_ids:
        try:
            bank_tx = await bank_transactions_collection.find_one(
                {"bank_transaction_id": tx_id, "user_id": user["user_id"], "imported_to_monetrax": False},
                {"_id": 0}
            )
            
            if not bank_tx:
                continue
            
            tx_type = "income" if bank_tx["type"] == "credit" else "expense"
            category_mapping = {
                "Salary": "Other Income", "Transfer In": "Other Income", "Interest": "Interest",
                "Refund": "Other Income", "Other Income": "Other Income",
                "Communication": "Communication", "Utilities": "Utilities", "Transport": "Transport",
                "Food": "Food", "Rent": "Rent", "Purchase": "Supplies",
                "Entertainment": "Other Expense", "Education": "Other Expense", "Healthcare": "Other Expense",
                "Transfer Out": "Other Expense", "Cash Withdrawal": "Other Expense", "Other Expense": "Other Expense"
            }
            category = category_mapping.get(bank_tx.get("category", ""), "Other Expense" if tx_type == "expense" else "Other Income")
            
            monetrax_tx_id = f"txn_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)
            is_taxable = tx_type == "income" and category in ["Sales", "Services", "Consulting"]
            
            monetrax_tx = {
                "transaction_id": monetrax_tx_id,
                "business_id": business["business_id"],
                "type": tx_type,
                "category": category,
                "amount": bank_tx["amount"],
                "description": bank_tx["narration"],
                "date": bank_tx["date"][:10] if bank_tx.get("date") else now.strftime("%Y-%m-%d"),
                "is_taxable": is_taxable,
                "vat_amount": calculate_vat(bank_tx["amount"]) if is_taxable else 0,
                "payment_method": "Bank Transfer",
                "source": "bank_import",
                "bank_transaction_id": tx_id,
                "created_at": now.isoformat()
            }
            
            await transactions_collection.insert_one(monetrax_tx)
            await bank_transactions_collection.update_one(
                {"bank_transaction_id": tx_id},
                {"$set": {"imported_to_monetrax": True, "monetrax_transaction_id": monetrax_tx_id, "imported_at": now.isoformat()}}
            )
            imported_count += 1
        
        except Exception as e:
            errors.append({"transaction_id": tx_id, "error": str(e)})
    
    return {
        "success": True,
        "imported_count": imported_count,
        "total_requested": len(transaction_ids),
        "errors": errors if errors else None
    }


@app.delete("/api/bank/accounts/{account_id}")
async def unlink_bank_account(account_id: str, user: dict = Depends(get_current_user)):
    """Unlink a bank account"""
    account = await linked_accounts_collection.find_one(
        {"linked_account_id": account_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not account:
        raise HTTPException(status_code=404, detail="Linked account not found")
    
    # Mark as disconnected (keep data for history)
    await linked_accounts_collection.update_one(
        {"linked_account_id": account_id},
        {"$set": {
            "status": "disconnected",
            "disconnected_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Try to unlink from Mono (optional - might fail if already disconnected)
    if MONO_SECRET_KEY and account.get("mono_account_id"):
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{MONO_API_BASE}/accounts/{account['mono_account_id']}/unlink",
                    headers={"mono-sec-key": MONO_SECRET_KEY},
                    timeout=10.0
                )
        except:
            pass  # Ignore errors during unlink
    
    return {"success": True, "message": "Bank account unlinked"}


@app.post("/api/bank/webhook")
async def mono_webhook(request: Request):
    """Handle Mono webhook events for real-time updates"""
    # Verify webhook signature if secret is configured
    if MONO_WEBHOOK_SECRET:
        signature = request.headers.get("mono-webhook-secret", "")
        if signature != MONO_WEBHOOK_SECRET:
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    try:
        payload = await request.json()
        event_type = payload.get("event")
        data = payload.get("data", {})
        
        logger.info(f"Mono webhook received: {event_type}")
        
        if event_type == "mono.events.account_updated":
            # Account data has been refreshed
            mono_account_id = data.get("account", {}).get("_id")
            data_status = data.get("meta", {}).get("data_status")
            
            if mono_account_id and data_status == "AVAILABLE":
                # Find the linked account
                account = await linked_accounts_collection.find_one(
                    {"mono_account_id": mono_account_id},
                    {"_id": 0}
                )
                
                if account:
                    # Auto-sync if user has real-time sync enabled
                    limits = await get_user_tier_limits(account["user_id"])
                    
                    if limits["bank_sync_frequency"] == "realtime":
                        # Trigger background sync
                        asyncio.create_task(background_sync_account(account))
        
        elif event_type == "mono.events.account_connected":
            logger.info(f"New account connected: {data}")
        
        elif event_type == "mono.events.account_reauthorization_required":
            # User needs to re-authenticate
            mono_account_id = data.get("account", {}).get("_id")
            
            if mono_account_id:
                await linked_accounts_collection.update_one(
                    {"mono_account_id": mono_account_id},
                    {"$set": {
                        "status": "reauth_required",
                        "reauth_required_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return {"status": "error", "message": str(e)}


async def background_sync_account(account: dict):
    """Background task to sync account transactions"""
    try:
        if not MONO_SECRET_KEY:
            return
        
        async with httpx.AsyncClient() as client:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=7)  # Last 7 days for real-time sync
            
            tx_response = await client.get(
                f"{MONO_API_BASE}/accounts/{account['mono_account_id']}/transactions",
                headers={"mono-sec-key": MONO_SECRET_KEY},
                params={
                    "start": start_date.strftime("%d-%m-%Y"),
                    "end": end_date.strftime("%d-%m-%Y"),
                    "paginate": "false"
                },
                timeout=60.0
            )
            
            if tx_response.status_code == 200:
                tx_data = tx_response.json()
                transactions = tx_data.get("data", [])
                transactions_synced = 0
                
                for tx in transactions:
                    existing = await bank_transactions_collection.find_one({
                        "mono_transaction_id": tx.get("_id")
                    })
                    
                    if not existing:
                        bank_tx = {
                            "bank_transaction_id": f"btx_{uuid.uuid4().hex[:12]}",
                            "linked_account_id": account["linked_account_id"],
                            "user_id": account["user_id"],
                            "mono_transaction_id": tx.get("_id"),
                            "type": tx.get("type", "debit"),
                            "amount": abs(float(tx.get("amount", 0))) / 100,
                            "narration": tx.get("narration", ""),
                            "date": tx.get("date", ""),
                            "balance": float(tx.get("balance", 0)) / 100 if tx.get("balance") else None,
                            "category": auto_categorize_bank_transaction(tx.get("narration", ""), tx.get("type")),
                            "imported_to_monetrax": False,
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                        await bank_transactions_collection.insert_one(bank_tx)
                        transactions_synced += 1
                
                # Update last synced
                await linked_accounts_collection.update_one(
                    {"linked_account_id": account["linked_account_id"]},
                    {"$set": {"last_synced": datetime.now(timezone.utc).isoformat()}}
                )
                
                # Log sync
                await bank_sync_logs_collection.insert_one({
                    "log_id": f"sync_{uuid.uuid4().hex[:12]}",
                    "user_id": account["user_id"],
                    "account_id": account["linked_account_id"],
                    "sync_type": "realtime_webhook",
                    "status": "success",
                    "transactions_synced": transactions_synced,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                
                logger.info(f"Background sync completed for {account['linked_account_id']}: {transactions_synced} new transactions")
    
    except Exception as e:
        logger.error(f"Background sync error: {str(e)}")


@app.get("/api/bank/supported-institutions")
async def get_supported_institutions():
    """Get list of supported Nigerian banks"""
    # Static list of major Nigerian banks supported by Mono
    institutions = [
        {"name": "Access Bank", "code": "044", "icon": "https://mono.co/banks/access.png"},
        {"name": "First Bank", "code": "011", "icon": "https://mono.co/banks/firstbank.png"},
        {"name": "GTBank", "code": "058", "icon": "https://mono.co/banks/gtbank.png"},
        {"name": "UBA", "code": "033", "icon": "https://mono.co/banks/uba.png"},
        {"name": "Zenith Bank", "code": "057", "icon": "https://mono.co/banks/zenith.png"},
        {"name": "Union Bank", "code": "032", "icon": "https://mono.co/banks/union.png"},
        {"name": "Stanbic IBTC", "code": "221", "icon": "https://mono.co/banks/stanbic.png"},
        {"name": "Sterling Bank", "code": "232", "icon": "https://mono.co/banks/sterling.png"},
        {"name": "Fidelity Bank", "code": "070", "icon": "https://mono.co/banks/fidelity.png"},
        {"name": "Polaris Bank", "code": "076", "icon": "https://mono.co/banks/polaris.png"},
        {"name": "Wema Bank", "code": "035", "icon": "https://mono.co/banks/wema.png"},
        {"name": "Ecobank", "code": "050", "icon": "https://mono.co/banks/ecobank.png"},
        {"name": "FCMB", "code": "214", "icon": "https://mono.co/banks/fcmb.png"},
        {"name": "Keystone Bank", "code": "082", "icon": "https://mono.co/banks/keystone.png"},
        {"name": "Unity Bank", "code": "215", "icon": "https://mono.co/banks/unity.png"},
        {"name": "Kuda Bank", "code": "50211", "icon": "https://mono.co/banks/kuda.png"},
        {"name": "OPay", "code": "999992", "icon": "https://mono.co/banks/opay.png"},
        {"name": "PalmPay", "code": "999991", "icon": "https://mono.co/banks/palmpay.png"},
        {"name": "Moniepoint", "code": "50515", "icon": "https://mono.co/banks/moniepoint.png"},
        {"name": "Carbon", "code": "565", "icon": "https://mono.co/banks/carbon.png"}
    ]
    
    return {
        "institutions": institutions,
        "total": len(institutions),
        "note": "Connect your bank account to automatically sync transactions into Monetrax"
    }


# ============== ADMIN SEED (for initial setup) ==============

@app.post("/api/admin/seed-superadmin")
async def seed_superadmin(email: str, secret_key: str):
    """One-time endpoint to create first superadmin. Requires secret key."""
    # Security: Only works if no superadmins exist and correct secret is provided
    existing_superadmin = await users_collection.find_one({"role": "superadmin"})
    
    if existing_superadmin:
        raise HTTPException(status_code=400, detail="Superadmin already exists")
    
    # Check secret key (should match JWT_SECRET or a dedicated admin seed key)
    expected_secret = os.environ.get("JWT_SECRET", "")
    if secret_key != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid secret key")
    
    # Find user by email and promote to superadmin
    user = await users_collection.find_one({"email": email})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please login first to create account.")
    
    await users_collection.update_one(
        {"email": email},
        {"$set": {"role": "superadmin", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"status": "success", "message": f"User {email} promoted to superadmin"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
