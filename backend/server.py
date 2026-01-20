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
            "custom_categories": False
        },
        "description": "Perfect for getting started",
        "highlight": False
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 5000.00,
        "price_yearly": 50000.00,
        "features": {
            "transactions_per_month": 200,
            "ai_insights": True,
            "receipt_ocr": True,
            "pdf_reports": True,
            "csv_export": True,
            "priority_support": False,
            "multi_user": False,
            "custom_categories": True
        },
        "description": "Great for small businesses",
        "highlight": False
    },
    "business": {
        "name": "Business",
        "price_monthly": 10000.00,
        "price_yearly": 100000.00,
        "features": {
            "transactions_per_month": 1000,
            "ai_insights": True,
            "receipt_ocr": True,
            "pdf_reports": True,
            "csv_export": True,
            "priority_support": True,
            "multi_user": False,
            "custom_categories": True
        },
        "description": "Most popular for growing businesses",
        "highlight": True
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 20000.00,
        "price_yearly": 200000.00,
        "features": {
            "transactions_per_month": -1,  # Unlimited
            "ai_insights": True,
            "receipt_ocr": True,
            "pdf_reports": True,
            "csv_export": True,
            "priority_support": True,
            "multi_user": True,
            "custom_categories": True
        },
        "description": "For large organizations",
        "highlight": False
    }
}

# Subscription collection
subscriptions_collection = db["subscriptions"]
payment_transactions_collection = db["payment_transactions"]


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
    """Get user's current subscription"""
    subscription = await subscriptions_collection.find_one(
        {"user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not subscription:
        # Return free tier by default
        now = datetime.now(timezone.utc)
        return {
            "subscription_id": None,
            "user_id": user["user_id"],
            "tier": "free",
            "tier_name": "Free",
            "status": "active",
            "billing_cycle": None,
            "features": SUBSCRIPTION_TIERS["free"]["features"],
            "current_period_start": now.isoformat(),
            "current_period_end": None,
            "can_upgrade": True
        }
    
    tier_data = SUBSCRIPTION_TIERS.get(subscription["tier"], SUBSCRIPTION_TIERS["free"])
    
    return {
        **subscription,
        "tier_name": tier_data["name"],
        "features": tier_data["features"],
        "can_upgrade": subscription["tier"] != "enterprise"
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
            
            return {
                "status": "complete",
                "payment_status": "paid",
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
    """Handle Stripe webhook events"""
    try:
        payload = await request.body()
        # For simplicity, we process without signature verification in test mode
        # In production, add signature verification
        
        import json
        event = json.loads(payload)
        
        event_type = event.get("type")
        data = event.get("data", {}).get("object", {})
        
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
                
                if payment_id:
                    await payment_transactions_collection.update_one(
                        {"payment_id": payment_id},
                        {"$set": {"status": "completed", "completed_at": now.isoformat()}}
                    )
        
        return {"received": True}
    except Exception as e:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
