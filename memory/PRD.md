# Monetrax - Financial OS for Nigerian MSMEs

## Original Problem Statement
Build Monetrax (formerly Naira Ledger) - a comprehensive financial operating system for Nigerian MSMEs with:
- Tax compliance (VAT 7.5%, Income Tax)
- Transaction tracking & bookkeeping
- NRS (Nigeria Revenue Service) readiness
- AI-powered insights
- Secure authentication (Google OAuth + MFA)
- Subscription-based pricing with Stripe integration

## User Choices
1. Authentication: Both Google OAuth + TOTP MFA
2. AI Features: OpenAI GPT for transaction categorization & insights
3. Receipt OCR: Google Vision API integration ✅
4. PDF Export: Implemented ✅
5. CSV Import/Export: Implemented ✅
6. Charts & Graphs: Implemented with Recharts ✅
7. AI Insight Levels: Basic/Standard/Premium ✅
8. Subscription Tiers: Free, Starter, Business, Enterprise ✅
9. Payment Processing: Stripe Integration ✅

## Architecture

### Tech Stack
- **Frontend**: React 18 + Tailwind CSS + Recharts + Lucide Icons
- **Backend**: FastAPI (Python) + ReportLab (PDF)
- **Database**: MongoDB
- **Auth**: Emergent-managed Google OAuth + TOTP MFA
- **AI**: OpenAI GPT via Emergent LLM Key
- **OCR**: Google Vision API (optional)
- **Payments**: Stripe via emergentintegrations library

### Collections
- `users` - User profiles
- `user_sessions` - Session tokens
- `mfa_settings` - TOTP secrets
- `backup_codes` - Recovery codes
- `businesses` - Business profiles
- `transactions` - Income/expense transactions
- `tax_records` - Tax filing history
- `subscriptions` - User subscription data ✅ NEW
- `payment_transactions` - Payment history ✅ NEW

## What's Been Implemented (Jan 20, 2026)

### Core Features
- ✅ Google OAuth + TOTP MFA authentication
- ✅ Nigerian tax calculations (7.5% VAT, progressive income tax)
- ✅ Transaction management with categories
- ✅ Tax readiness score (NRS-Ready)
- ✅ Tax calendar with Nigerian deadlines
- ✅ Dark/Light theme toggle

### Enhanced Features
- ✅ **Receipt OCR Scanning** - Upload receipt images, AI parses merchant/amount/date
- ✅ **PDF Tax Report Export** - Professional PDF with income statement, tax breakdown
- ✅ **CSV Import** - Bulk import transactions from CSV
- ✅ **CSV Export** - Export transactions to CSV
- ✅ **Interactive Charts**:
  - Line Chart: Revenue vs Expenses trend
  - Bar Chart: Monthly profit
  - Pie Charts: Revenue/Expense by category
- ✅ **AI Insights with Levels**:
  - Basic: Quick 2-3 sentence summary
  - Standard: Detailed analysis with recommendations
  - Premium: Full report with tax optimization, cash flow, growth opportunities

### Subscription System (NEW - Jan 20, 2026)
- ✅ **4-Tier Subscription Model**:
  - **Free**: ₦0/month - 50 transactions, CSV export only
  - **Starter**: ₦2,500/month - 200 transactions, AI insights, Receipt OCR, PDF reports
  - **Business**: ₦7,500/month - 1000 transactions, Priority support (Most Popular)
  - **Enterprise**: ₦25,000/month - Unlimited transactions, Multi-user access
- ✅ **Stripe Payment Integration** - Secure checkout sessions via emergentintegrations
- ✅ **Billing Cycle Toggle** - Monthly/Yearly with 17% yearly discount
- ✅ **Subscription Management**:
  - View current subscription status
  - Upgrade to higher tiers
  - Cancel subscription (reverts to free at period end)
- ✅ **Feature Gating** - API to check feature access based on tier
- ✅ **Payment Status Polling** - Frontend polls for payment completion
- ✅ **Webhook Support** - Handle Stripe events for subscription updates

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/session | Create session from OAuth |
| GET | /api/auth/me | Get current user |
| POST | /api/auth/logout | Logout |

### MFA
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/mfa/totp/setup | Initialize TOTP |
| POST | /api/mfa/totp/verify | Verify & enable TOTP |
| POST | /api/mfa/totp/authenticate | Verify TOTP during login |
| GET | /api/mfa/status | Get MFA status |

### Business & Transactions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/business | Create business |
| GET | /api/business | Get business |
| POST | /api/transactions | Create transaction |
| GET | /api/transactions | List transactions |
| DELETE | /api/transactions/{id} | Delete transaction |

### Tax & Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/summary | Financial summary |
| GET | /api/tax/summary | Tax summary |
| GET | /api/tax/calendar | Tax deadlines |
| GET | /api/reports/income-statement | Income statement |
| GET | /api/reports/export/pdf | Export PDF report |

### Enhanced Features
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/receipts/scan | OCR receipt scanning |
| POST | /api/transactions/import/csv | Bulk CSV import |
| GET | /api/transactions/export/csv | Export to CSV |
| GET | /api/analytics/charts | Charts data |
| POST | /api/ai/insights/v2 | AI insights with levels |
| GET | /api/categories | Transaction categories |

### Subscriptions (NEW)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/subscriptions/plans | Get all subscription tiers |
| GET | /api/subscriptions/current | Get user's current subscription |
| POST | /api/subscriptions/checkout | Create Stripe checkout session |
| GET | /api/subscriptions/checkout/status/{session_id} | Check payment status |
| GET | /api/subscriptions/feature-check/{feature} | Check feature access |
| POST | /api/subscriptions/cancel | Cancel subscription |
| POST | /api/webhooks/stripe | Stripe webhook handler |

## Testing Results
- Backend Subscription Tests: 100% (28/28 tests passed)
- Frontend UI Tests: 100% (11/11 tests passed)
- Overall: 100% success rate

## Prioritized Backlog

### P0 - Critical (All Done ✅)
- ✅ Authentication (OAuth + MFA)
- ✅ Nigerian tax calculations
- ✅ Transaction management
- ✅ Receipt OCR
- ✅ PDF Export
- ✅ CSV Import/Export
- ✅ Charts & Analytics
- ✅ AI Insights with levels
- ✅ Subscription System with Stripe

### P1 - High Priority (Next)
- WhatsApp integration for transaction recording
- Email notifications for tax deadlines
- Invoice generation
- Frontend component refactoring (break down App.js)

### P2 - Medium Priority
- Multi-currency support
- Bank statement parsing
- Recurring transactions
- Database query optimization (pagination)

### P3 - Nice to Have
- Pidgin language support
- Mobile app (React Native)
- Multi-user business accounts (Enterprise tier)

## Deployment Notes
- GCP-ready architecture
- All endpoints properly secured
- Environment variables for configuration
- Receipt OCR requires GOOGLE_VISION_API_KEY (optional)
- Stripe uses test key sk_test_emergent

## File Structure
```
/app/
├── backend/
│   ├── server.py         # FastAPI backend (including subscription system)
│   └── .env              # Backend environment variables
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.js        # Main React component (includes SubscriptionPage)
│   │   └── index.css     # Global and TailwindCSS styles
│   ├── public/
│   │   ├── logo.svg      # Main brand logo
│   │   └── logo-icon.svg # Icon version of the logo
│   ├── package.json      # Frontend dependencies
│   └── .env              # Frontend environment variables
├── tests/
│   └── test_subscription_system.py  # Subscription API tests
└── memory/
    └── PRD.md            # Product Requirements Document
```
