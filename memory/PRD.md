# Monetrax - Financial OS for Nigerian MSMEs

## Original Problem Statement
Build Monetrax (formerly Naira Ledger) - a comprehensive financial operating system for Nigerian MSMEs with:
- Tax compliance (VAT 7.5%, Income Tax)
- Transaction tracking & bookkeeping
- NRS (Nigeria Revenue Service) readiness
- AI-powered insights
- Secure authentication (Google OAuth + MFA)

## User Choices
1. Authentication: Both Google OAuth + TOTP MFA
2. AI Features: OpenAI GPT for transaction categorization & insights
3. Receipt OCR: Google Vision API integration (playbook ready)
4. GCP-ready architecture for future deployment

## Architecture

### Tech Stack
- **Frontend**: React 18 + Tailwind CSS + Lucide Icons
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: Emergent-managed Google OAuth + TOTP MFA
- **AI**: OpenAI GPT via Emergent LLM Key

### Collections
- `users` - User profiles
- `user_sessions` - Session tokens
- `mfa_settings` - TOTP secrets
- `backup_codes` - Recovery codes
- `businesses` - Business profiles
- `transactions` - Income/expense transactions
- `tax_records` - Tax filing history

## User Personas
1. **Small Business Owner** - Needs simple bookkeeping and tax tracking
2. **MSME Accountant** - Requires accurate Nigerian tax calculations
3. **Tax Consultant** - Uses platform for client compliance monitoring

## Core Requirements (Static)
- ✅ Google OAuth authentication
- ✅ TOTP MFA with backup codes
- ✅ Nigerian VAT calculation (7.5%)
- ✅ Progressive income tax calculation
- ✅ Tax readiness score (NRS-Ready)
- ✅ Transaction recording (income/expenses)
- ✅ Financial reports (Income Statement)
- ✅ Tax calendar with deadlines
- ✅ AI-powered insights
- ✅ Dark/Light theme support
- ⏳ Receipt OCR (playbook ready)
- ⏳ WhatsApp integration (future)

## What's Been Implemented (Jan 20, 2026)

### Backend (/app/backend/server.py)
- Health check API
- Authentication (Google OAuth + MFA)
- Business CRUD operations
- Transaction management with VAT
- Financial summary with tax readiness
- Tax summary with Nigerian calculations
- Tax calendar with deadlines
- Income statement reports
- AI categorization & insights
- Transaction categories

### Frontend (/app/frontend/src/App.js)
- Landing page with features
- Google OAuth login flow
- MFA verification page
- Dashboard with NRS Readiness Score
- Transactions page with filters
- Tax overview page
- Reports page (Income Statement)
- Settings page with MFA setup
- Dark/Light theme toggle
- Business setup modal
- Add transaction modal

### Nigerian Tax Features
- VAT: 7.5% on taxable transactions
- Tax-free threshold: ₦800,000
- Progressive income tax brackets
- Tax calendar (VAT filing 21st, Annual tax Mar 31)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check |
| POST | /api/auth/session | Create session from OAuth |
| GET | /api/auth/me | Get current user |
| POST | /api/auth/logout | Logout |
| POST | /api/mfa/totp/setup | Initialize TOTP |
| POST | /api/mfa/totp/verify | Verify & enable TOTP |
| POST | /api/mfa/totp/authenticate | Verify TOTP during login |
| GET | /api/mfa/status | Get MFA status |
| POST | /api/business | Create business |
| GET | /api/business | Get business |
| PATCH | /api/business | Update business |
| POST | /api/transactions | Create transaction |
| GET | /api/transactions | List transactions |
| DELETE | /api/transactions/{id} | Delete transaction |
| GET | /api/summary | Financial summary |
| GET | /api/tax/summary | Tax summary |
| GET | /api/tax/calendar | Tax deadlines |
| GET | /api/reports/income-statement | Income statement |
| POST | /api/ai/categorize | AI categorization |
| POST | /api/ai/insights | AI insights |
| GET | /api/categories | Transaction categories |

## Prioritized Backlog

### P0 - Critical (Done)
- ✅ Authentication (OAuth + MFA)
- ✅ Nigerian tax calculations
- ✅ Transaction management
- ✅ Tax readiness score
- ✅ Financial reports

### P1 - High Priority (Next)
- Receipt OCR with Google Vision API
- Export reports to PDF
- Bulk transaction import (CSV)
- Email notifications

### P2 - Medium Priority
- WhatsApp integration
- Multi-currency support
- Invoice generation
- Bank statement parsing

### P3 - Nice to Have
- Pidgin language support
- Mobile app (React Native)
- Multi-user business accounts
- API for third-party integrations

## Next Tasks
1. Implement Receipt OCR (playbook available)
2. Add PDF export for reports
3. Implement bulk CSV import
4. Add email notifications for tax deadlines

## Testing Results
- Backend: 100% public APIs passing
- Frontend: 95% tests passing
- Overall: 97% success rate
