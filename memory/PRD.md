# Monetrax - Financial OS for Nigerian MSMEs

## Original Problem Statement
Build Monetrax - a comprehensive financial operating system for Nigerian MSMEs with:
- Tax compliance (VAT 7.5%, Income Tax)
- Transaction tracking & bookkeeping
- NRS (Nigeria Revenue Service) readiness
- AI-powered insights
- Secure authentication (Google OAuth + MFA)
- Subscription-based pricing with Stripe integration
- Email notifications for tax deadlines
- **Progressive Web App (PWA) for mobile access**

## Progressive Web App (PWA) - NEW
Monetrax is now available as a PWA that can be installed on both Android and iOS devices!

### Installation Instructions

**Android (Chrome):**
1. Visit https://msme-agent-sys.preview.emergentagent.com
2. Tap the "Install Monetrax" banner at the bottom
3. Or tap ⋮ menu → "Add to Home Screen"
4. The app icon will appear on your home screen

**iOS (Safari):**
1. Visit https://msme-agent-sys.preview.emergentagent.com
2. Tap the Share button (box with arrow)
3. Scroll down and tap "Add to Home Screen"
4. Tap "Add" in the top right
5. The app icon will appear on your home screen

### PWA Features
- ✅ **Installable**: Add to home screen on any device
- ✅ **Offline Support**: Access cached data when offline
- ✅ **Fast Loading**: Service worker caches assets
- ✅ **Push Notifications**: Get tax deadline reminders (requires permission)
- ✅ **Native Feel**: Runs in standalone mode without browser UI
- ✅ **App Shortcuts**: Quick access to Add Transaction, Dashboard, Tax
- ✅ **iOS Splash Screens**: Beautiful loading screens on all iPhones/iPads

### PWA Technical Details
- **Service Worker**: Caches static assets, network-first for API calls
- **Manifest**: Full app metadata with 8 icon sizes
- **Icons**: 72x72 to 512x512 pixels, maskable
- **Splash Screens**: 10 iOS sizes for all devices
- **Theme Color**: #001F4F (dark) / #ffffff (light)

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
- **PWA**: Service Worker + Web App Manifest

### File Structure
```
/app/
├── backend/
│   ├── server.py         # FastAPI backend
│   └── .env              # Environment variables
├── frontend/
│   ├── public/
│   │   ├── manifest.json      # PWA manifest
│   │   ├── service-worker.js  # Offline caching
│   │   ├── offline.html       # Offline fallback
│   │   ├── icons/             # App icons (72-512px)
│   │   ├── splash/            # iOS splash screens
│   │   ├── logo.svg
│   │   └── logo-icon.svg
│   ├── src/
│   │   ├── App.js        # Main app + PWA components
│   │   ├── index.css     # Styles + PWA CSS
│   │   ├── contexts/     # Refactored contexts
│   │   └── components/   # Refactored components
│   └── package.json
└── memory/
    └── PRD.md
```

## What's Been Implemented

### Core Features
- ✅ Google OAuth + TOTP MFA authentication
- ✅ Nigerian tax calculations (7.5% VAT, progressive income tax)
- ✅ Transaction management with categories
- ✅ Tax readiness score (NRS-Ready)
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
- ✅ Upgrade Modals & Prompts

### Email Notifications
- ✅ Tax Deadline Reminders
- ✅ Subscription Receipts
- ✅ Email Preferences

### Progressive Web App (NEW)
- ✅ Web App Manifest
- ✅ Service Worker with offline caching
- ✅ Offline fallback page
- ✅ App icons (all sizes)
- ✅ iOS splash screens
- ✅ Install prompt component
- ✅ Network status indicator
- ✅ Mobile-responsive design
- ✅ Safe area support for notched devices

### Admin System (Jan 21, 2026)
- ✅ Role-based access control (user, agent, admin, superadmin)
- ✅ Admin Dashboard at /admin route
- ✅ User Management (list, search, suspend, activate)
- ✅ Business Management (list, search, view details)
- ✅ Transaction Monitoring (list, filter, flag/unflag)
- ✅ Tax Engine Configuration (view/edit tax rules)
- ✅ Subscription Management (list, filter by tier)
- ✅ Admin Logs (audit trail of admin actions)
- ✅ System Settings (superadmin only)
- ✅ Migration script to set superadmin: `/app/backend/migrations/set_superadmin.py`

### Agent System (NEW - Jan 22, 2026)
- ✅ Agent role with unique initials
- ✅ Agent Portal at /agent route with Dashboard, Sign Up User, and My Signups tabs
- ✅ Superadmin can promote users to agent via Admin Panel
- ✅ Superadmin can revoke agent status
- ✅ Agents can sign up new users with promotional discounts
- ✅ Users are tagged with agent initials for tracking
- ✅ Promotional pricing: Starter (₦2,000), Business (₦5,000), Enterprise (₦8,000)
- ✅ Agent dashboard shows statistics (total signups, promo signups, total savings)
- ✅ Check user eligibility for promotional pricing
- ✅ Paginated signups list with tier filter

### Mono Bank Integration (NEW - Jan 23, 2026)
- ✅ Bank integration foundation with Mono API
- ✅ Support for 20+ Nigerian banks (Access, GTBank, First Bank, UBA, etc.)
- ✅ Bank account linking flow (awaiting Mono API keys)
- ✅ Real-time transaction sync via webhooks
- ✅ Daily scheduled sync for lower tiers
- ✅ Manual sync with tier-based limits
- ✅ Auto-categorization of bank transactions
- ✅ Import bank transactions to Monetrax
- ✅ Bulk transaction import
- ✅ Tier-based limits:
  - Free: 1 account, daily sync, 3 manual syncs/day
  - Starter: 3 accounts, daily sync, 10 manual syncs/day
  - Business: 5 accounts, real-time sync, unlimited manual syncs
  - Enterprise: Unlimited accounts, real-time sync, unlimited manual syncs
- ✅ Frontend: /bank route with BankAccounts component
- ✅ "Coming Soon" state when Mono keys not configured

### Updated Subscription Pricing (Jan 23, 2026)
- ✅ Free: ₦0/month
- ✅ Starter: ₦3,000/month (was ₦5,000)
- ✅ Business: ₦7,000/month (was ₦10,000)
- ✅ Enterprise: ₦10,000/month (was ₦20,000)

## Testing Results (Jan 23, 2026)
- Backend: 100% passed (20/20 bank integration tests)
- Frontend: 100% passed (Bank Accounts UI, navigation, pricing display)
- Bank Integration: Foundation complete (awaiting Mono API keys)
- Agent System: 100% passed (25/25 tests)
- Admin System: Fully tested with RBAC verification
- PWA: 100% passed

## Prioritized Backlog

### P0 - Critical (All Done ✅)
- ✅ Core financial features
- ✅ Subscription System
- ✅ Email Notifications
- ✅ PWA Implementation
- ✅ Admin System with RBAC
- ✅ Agent System with promotional pricing

### P1 - High Priority (Next)
- Mono API key configuration (user to provide MONO_SECRET_KEY, MONO_PUBLIC_KEY, MONO_WEBHOOK_SECRET)
- Frontend component refactoring (App.js is 3000+ lines)
- Agent Commission System (track and calculate agent commissions)
- Email notifications for tax deadlines (scheduled cron job)
- Push notification integration for tax reminders

### P2 - Medium Priority
- Multi-currency support
- Bank statement parsing (PDF upload)
- Recurring transactions
- WhatsApp integration for transaction recording

### P3 - Nice to Have
- Native mobile apps (React Native)
- Multi-user business accounts
