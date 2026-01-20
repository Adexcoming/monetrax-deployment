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
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from decimal import Decimal

import pyotp
import qrcode
import httpx
from fastapi import FastAPI, HTTPException, Request, Response, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

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


# ============== PYDANTIC MODELS ==============
class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    mfa_enabled: bool = False
    mfa_verified: bool = False


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
    
    mfa_doc = await mfa_collection.find_one({"user_id": user_doc["user_id"]}, {"_id": 0})
    user_doc["mfa_enabled"] = mfa_doc.get("totp_enabled", False) if mfa_doc else False
    user_doc["mfa_verified"] = session_doc.get("mfa_verified", False)
    
    return user_doc


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
    else:
        user_id = generate_id("user")
        await users_collection.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
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
    
    transaction_id = generate_id("txn")
    now = datetime.now(timezone.utc)
    
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
