# Monetrax - Financial OS for Nigerian MSMEs

## Original Problem Statement
Build Monetrax - a comprehensive financial operating system for Nigerian MSMEs with:
- Tax compliance (VAT 7.5%, Income Tax)
- Transaction tracking & bookkeeping
- NRS (Nigeria Revenue Service) readiness
- AI-powered insights
- Secure authentication (Google OAuth + MFA)
- Subscription-based pricing with Stripe integration

## Subscription Tiers (Updated Jan 20, 2026)
| Tier | Monthly | Yearly | Transactions | AI Insights | Receipt OCR | PDF Reports |
|------|---------|--------|--------------|-------------|-------------|-------------|
| Free | ₦0 | ₦0 | 50/month | ❌ | ❌ | ❌ |
| Starter | ₦5,000 | ₦50,000 | 200/month | ✅ | ✅ | ✅ |
| Business | ₦10,000 | ₦100,000 | 1,000/month | ✅ | ✅ | ✅ |
| Enterprise | ₦20,000 | ₦200,000 | Unlimited | ✅ | ✅ | ✅ |

## Tier Enforcement Features
- **Transaction Limits**: Backend enforces monthly limits, returns 403 when exceeded
- **Feature Gating**: Premium features (AI, OCR, PDF) locked for free tier
- **Usage Tracking**: Real-time usage stats with progress bars
- **Upgrade Prompts**: Modal appears when accessing premium features on free tier
- **Free Trial Prevention**: `had_paid_subscription` flag prevents free tier abuse

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
- `subscriptions` - User subscription data
- `payment_transactions` - Payment history

## What's Been Implemented

### Core Features
- ✅ Google OAuth + TOTP MFA authentication
- ✅ Nigerian tax calculations (7.5% VAT, progressive income tax)
- ✅ Transaction management with categories
- ✅ Tax readiness score (NRS-Ready)
- ✅ Tax calendar with Nigerian deadlines
- ✅ Dark/Light theme toggle

### Enhanced Features
- ✅ **Receipt OCR Scanning** - Upload receipt images, AI parses data (Gated)
- ✅ **PDF Tax Report Export** - Professional PDF reports (Gated)
- ✅ **CSV Import/Export** - Bulk transaction management
- ✅ **Interactive Charts** - Line, Bar, Pie charts
- ✅ **AI Insights** - Basic/Standard/Premium levels (Gated)

### Subscription System
- ✅ **4-Tier Model**: Free, Starter, Business, Enterprise
- ✅ **Stripe Integration**: Secure checkout sessions
- ✅ **Transaction Limits**: 50/200/1000/Unlimited per month
- ✅ **Feature Gating**: AI, OCR, PDF locked for free tier
- ✅ **Usage Banner**: Progress bar showing transactions used
- ✅ **Upgrade Modal**: Prompts when accessing premium features
- ✅ **Crown Icons**: Visual indicators on premium features
- ✅ **Free Trial Prevention**: Tracks paid subscription history

## API Endpoints

### Subscriptions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/subscriptions/plans | Get all tiers with pricing |
| GET | /api/subscriptions/current | Get subscription with usage stats |
| GET | /api/subscriptions/usage | Detailed usage (limit_exceeded flag) |
| POST | /api/subscriptions/checkout | Create Stripe checkout session |
| GET | /api/subscriptions/checkout/status/{id} | Check payment status |
| GET | /api/subscriptions/feature-check/{feature} | Check feature access |
| POST | /api/subscriptions/cancel | Cancel subscription |
| POST | /api/webhooks/stripe | Stripe webhook handler |

### Other Endpoints
- Authentication: /api/auth/session, /api/auth/me, /api/auth/logout
- MFA: /api/mfa/totp/setup, /api/mfa/totp/verify, /api/mfa/status
- Business: /api/business (POST/GET/PATCH)
- Transactions: /api/transactions (POST/GET/DELETE)
- Tax: /api/summary, /api/tax/summary, /api/tax/calendar
- Reports: /api/reports/income-statement, /api/reports/export/pdf
- AI: /api/ai/insights/v2, /api/ai/categorize
- OCR: /api/receipts/scan

## Testing Results (Jan 20, 2026)
- Backend: 100% (44 tests passed)
- Frontend: 100% (25 UI tests passed)

## Prioritized Backlog

### P0 - Critical (All Done ✅)
- ✅ Authentication (OAuth + MFA)
- ✅ Nigerian tax calculations
- ✅ Transaction management
- ✅ Receipt OCR
- ✅ PDF Export
- ✅ CSV Import/Export
- ✅ Charts & Analytics
- ✅ AI Insights
- ✅ Subscription System with Stripe
- ✅ Tier Enforcement

### P1 - High Priority (Next)
- Frontend refactoring (break down App.js)
- WhatsApp integration for transaction recording
- Email notifications for tax deadlines
- Invoice generation

### P2 - Medium Priority
- Multi-currency support
- Bank statement parsing
- Recurring transactions
- Database query optimization (pagination)

### P3 - Nice to Have
- Pidgin language support
- Mobile app (React Native)
- Multi-user business accounts (Enterprise tier)
