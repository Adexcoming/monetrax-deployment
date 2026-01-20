# Monetrax - Financial OS for Nigerian MSMEs

## Original Problem Statement
Build Monetrax - a comprehensive financial operating system for Nigerian MSMEs with:
- Tax compliance (VAT 7.5%, Income Tax)
- Transaction tracking & bookkeeping
- NRS (Nigeria Revenue Service) readiness
- AI-powered insights
- Secure authentication (Google OAuth + MFA)
- Subscription-based pricing with Stripe integration
- Email notifications for tax deadlines and billing

## Subscription Tiers
| Tier | Monthly | Yearly | Transactions | AI Insights | Receipt OCR | PDF Reports |
|------|---------|--------|--------------|-------------|-------------|-------------|
| Free | ₦0 | ₦0 | 50/month | ❌ | ❌ | ❌ |
| Starter | ₦5,000 | ₦50,000 | 200/month | ✅ | ✅ | ✅ |
| Business | ₦10,000 | ₦100,000 | 1,000/month | ✅ | ✅ | ✅ |
| Enterprise | ₦20,000 | ₦200,000 | Unlimited | ✅ | ✅ | ✅ |

## Architecture

### Tech Stack
- **Frontend**: React 18 + Tailwind CSS + Recharts + Lucide Icons
- **Backend**: FastAPI (Python) + ReportLab (PDF)
- **Database**: MongoDB
- **Auth**: Emergent-managed Google OAuth + TOTP MFA
- **AI**: OpenAI GPT via Emergent LLM Key
- **OCR**: Google Vision API (optional)
- **Payments**: Stripe via emergentintegrations library
- **Email**: Resend API

### Refactored Frontend Structure
```
/app/frontend/src/
├── contexts/
│   ├── AuthContext.js       # Authentication state & API helper
│   ├── ThemeContext.js      # Light/dark theme management
│   ├── SubscriptionContext.js # Subscription state & upgrade modal
│   └── index.js             # Export all contexts
├── components/
│   ├── layout/
│   │   ├── DashboardLayout.js  # Sidebar navigation layout
│   │   └── index.js
│   └── pages/
│       ├── DashboardPage.js    # Dashboard with summary cards
│       ├── SettingsPage.js     # Settings with email prefs
│       └── index.js
└── App.js                   # Main app with routing
```

### Database Collections
- `users` - User profiles
- `user_sessions` - Session tokens
- `mfa_settings` - TOTP secrets
- `backup_codes` - Recovery codes
- `businesses` - Business profiles
- `transactions` - Income/expense transactions
- `tax_records` - Tax filing history
- `subscriptions` - User subscription data
- `payment_transactions` - Payment history
- `email_preferences` - User email notification settings
- `email_logs` - Email send history

## What's Been Implemented (Jan 20, 2026)

### Core Features
- ✅ Google OAuth + TOTP MFA authentication
- ✅ Nigerian tax calculations (7.5% VAT, progressive income tax)
- ✅ Transaction management with categories
- ✅ Tax readiness score (NRS-Ready)
- ✅ Tax calendar with Nigerian deadlines
- ✅ Dark/Light theme toggle

### Enhanced Features
- ✅ Receipt OCR Scanning (Gated)
- ✅ PDF Tax Report Export (Gated)
- ✅ CSV Import/Export
- ✅ Interactive Charts
- ✅ AI Insights (Gated)

### Subscription System
- ✅ 4-Tier Model with Stripe
- ✅ Transaction Limits enforcement
- ✅ Feature Gating
- ✅ Usage Banner & Upgrade Modals
- ✅ Free Trial Prevention

### Email Notification System (NEW)
- ✅ **Email Preferences API**: GET/PUT /api/email/preferences
- ✅ **Tax Deadline Reminders**: Professional HTML emails with upcoming deadlines
- ✅ **Subscription Receipts**: Automatic email on successful upgrade
- ✅ **Test Email**: /api/email/test for configuration verification
- ✅ **Frontend Settings**: Toggle switches for notifications
- ✅ **Email Logs**: Tracking sent emails in database

### Frontend Refactoring (NEW)
- ✅ Created `/contexts/` directory with AuthContext, ThemeContext, SubscriptionContext
- ✅ Created `/components/pages/` with DashboardPage, SettingsPage
- ✅ Created `/components/layout/` with DashboardLayout
- ✅ Settings page now includes Email Notifications section

## API Endpoints

### Email System (NEW)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/email/preferences | Get user email preferences |
| PUT | /api/email/preferences | Update email preferences |
| POST | /api/email/send-tax-reminder | Send tax deadline reminder |
| POST | /api/email/send-upgrade-receipt | Send subscription receipt |
| POST | /api/email/test | Send test email |

### Subscriptions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/subscriptions/plans | Get all tiers |
| GET | /api/subscriptions/current | Get subscription with usage |
| GET | /api/subscriptions/usage | Detailed usage stats |
| POST | /api/subscriptions/checkout | Create Stripe checkout |
| GET | /api/subscriptions/checkout/status/{id} | Check payment & send receipt |
| POST | /api/subscriptions/cancel | Cancel subscription |

## Testing Results (Jan 20, 2026)
- Backend Email Tests: 100% (19/19 passed)
- Frontend UI Tests: 100% (13/13 passed)
- Total: 100% success rate

## Configuration Required

### Backend .env
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=monetrax_db
JWT_SECRET=your-secret
EMERGENT_LLM_KEY=sk-emergent-xxx
STRIPE_API_KEY=sk_test_xxx
RESEND_API_KEY=re_xxx  # Get from resend.com
SENDER_EMAIL=your-verified@domain.com
```

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
- ✅ Email Notifications
- ✅ Frontend Refactoring (started)

### P1 - High Priority (Next)
- Complete frontend refactoring (migrate remaining pages)
- WhatsApp integration for transaction recording
- Scheduled email reminders (cron job)
- Invoice generation

### P2 - Medium Priority
- Multi-currency support
- Bank statement parsing
- Recurring transactions
- Database query optimization

### P3 - Nice to Have
- Pidgin language support
- Mobile app (React Native)
- Multi-user business accounts
