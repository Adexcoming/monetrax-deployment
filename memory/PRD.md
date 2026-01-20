# MFA Authentication App - PRD

## Original Problem Statement
Build an MFA Authentication app with:
1. Emergent-managed Google OAuth login
2. TOTP (Time-based One-Time Password) - Google Authenticator support
3. Backup codes for emergency recovery
4. Modern dark theme UI

## Architecture

### Tech Stack
- **Frontend**: React 18 + Tailwind CSS + Lucide Icons
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: Emergent-managed Google OAuth

### Core Features
1. **Google OAuth Login** - Seamless login via Emergent Auth
2. **TOTP MFA** - 6-digit codes from authenticator apps (30-second window)
3. **Backup Codes** - 10 single-use recovery codes (XXXX-XXXX format)
4. **Session Management** - 7-day sessions with secure httpOnly cookies

## User Personas
1. **Security-conscious user** - Wants extra protection for their account
2. **Tech-savvy user** - Familiar with authenticator apps
3. **Regular user** - Needs simple recovery options (backup codes)

## Core Requirements (Static)
- ✅ Google OAuth integration
- ✅ TOTP setup with QR code
- ✅ TOTP verification during login
- ✅ Backup codes generation
- ✅ Backup code verification
- ✅ MFA status dashboard
- ✅ Session management

## What's Been Implemented (Jan 20, 2026)

### Backend (/app/backend/server.py)
- Health check endpoint
- Session creation/validation
- User authentication
- TOTP setup & verification
- Backup codes management
- MFA status API

### Frontend (/app/frontend/src/App.js)
- Landing page with Google login
- Auth callback handling
- MFA verification page
- Dashboard with security settings
- MFA setup modal with QR code
- Backup codes modal

### Security Features
- Secure session cookies (httpOnly, secure, sameSite)
- TOTP with 1-window tolerance
- Single-use backup codes
- Session expiry validation

## Prioritized Backlog

### P0 - Critical (Done)
- ✅ Google OAuth login
- ✅ TOTP MFA setup & verification
- ✅ Backup codes

### P1 - High Priority (Next)
- Device trust / remember device feature
- Session activity log
- Email notifications for MFA changes

### P2 - Medium Priority
- SMS verification (requires Twilio)
- Security key / WebAuthn support
- Account recovery flow

### P3 - Nice to Have
- Dark/light theme toggle
- Export security settings
- Admin dashboard

## Next Tasks
1. Add device trust feature (remember this device for 30 days)
2. Implement session activity logging
3. Add email notifications when MFA is enabled/disabled
4. Consider SMS as additional MFA method

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
| GET | /api/mfa/backup-codes | Get backup codes count |
| POST | /api/mfa/backup-codes/regenerate | Generate new codes |
| POST | /api/mfa/backup-codes/verify | Verify backup code |
| GET | /api/mfa/status | Get MFA status |
| POST | /api/mfa/disable | Disable MFA |

## Database Collections
- `users` - User profiles
- `user_sessions` - Session tokens
- `mfa_settings` - TOTP secrets
- `backup_codes` - Recovery codes
