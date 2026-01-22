# Monetrax - Google Play Store Publishing Guide

## Complete Step-by-Step Instructions

---

## PART 1: PREPARATION

### Step 1.1: Create Google Play Developer Account
1. Go to https://play.google.com/console
2. Sign in with your Google account
3. Pay the one-time $25 USD registration fee
4. Complete account details and verification

### Step 1.2: Install Required Software

**On Windows:**
1. Download Android Studio: https://developer.android.com/studio
2. Install Android Studio (includes Java JDK)
3. During setup, ensure "Android SDK" is selected

**On Mac:**
```bash
# Install via Homebrew
brew install --cask android-studio
```

**On Linux:**
```bash
# Download and extract Android Studio
sudo snap install android-studio --classic
```

### Step 1.3: Download TWA Project Files
The TWA project files are in: `/app/twa-android/`

Download this entire folder to your local machine.

---

## PART 2: GENERATE SIGNING KEY

### Step 2.1: Create Release Keystore

Open terminal/command prompt and run:

```bash
keytool -genkey -v -keystore monetrax-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias monetrax
```

You will be prompted for:
- **Keystore password**: Create a strong password (SAVE THIS!)
- **Key password**: Can be same as keystore password
- **Your name**: Your full name
- **Organizational unit**: Your department (or leave blank)
- **Organization**: Your company name (Synexis Consulting Ltd)
- **City**: Your city
- **State/Province**: Your state
- **Country code**: NG (for Nigeria)

⚠️ **IMPORTANT**: Save the keystore file and passwords securely! You'll need them for ALL future updates.

### Step 2.2: Get SHA256 Fingerprint

```bash
keytool -list -v -keystore monetrax-release-key.jks -alias monetrax
```

Enter your keystore password when prompted.

Look for the line starting with `SHA256:` - copy the entire fingerprint.

Example:
```
SHA256: 14:6D:E9:83:C5:73:06:50:D8:EE:B9:95:2F:34:FC:64:16:A0:83:42:E6:1D:BE:A8:8A:04:96:B2:3F:CF:44:E5
```

---

## PART 3: CONFIGURE THE PROJECT

### Step 3.1: Update Digital Asset Links

1. Open `/app/frontend/public/.well-known/assetlinks.json`
2. Replace `PLACEHOLDER_SHA256_FINGERPRINT` with your actual SHA256 fingerprint
3. Deploy the updated file to your server

The file should look like:
```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "com.monetrax.app",
    "sha256_cert_fingerprints": ["14:6D:E9:83:C5:73:06:50:D8:EE:B9:95:2F:34:FC:64:16:A0:83:42:E6:1D:BE:A8:8A:04:96:B2:3F:CF:44:E5"]
  }
}]
```

### Step 3.2: Verify Asset Links File

After deploying, verify it's accessible:
```
https://monetrax-admin.preview.emergentagent.com/.well-known/assetlinks.json
```

### Step 3.3: Update TWA Configuration

1. Open `twa-android/app/src/main/res/values/strings.xml`
2. Update the `sha256_cert_fingerprints` in the `assetStatements` string

### Step 3.4: Configure Signing in build.gradle

1. Open `twa-android/app/build.gradle`
2. Uncomment and update the signing config:

```gradle
signingConfigs {
    release {
        storeFile file('path/to/monetrax-release-key.jks')
        storePassword 'your-store-password'
        keyAlias 'monetrax'
        keyPassword 'your-key-password'
    }
}

buildTypes {
    release {
        minifyEnabled true
        proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        signingConfig signingConfigs.release  // Uncomment this line
    }
}
```

---

## PART 4: ADD APP ICONS

### Step 4.1: Prepare Icons

You need these icon sizes in PNG format:
- `ic_launcher.png` - Regular icon
- `ic_launcher_round.png` - Round icon (Android 7.1+)

| Folder | Size |
|--------|------|
| mipmap-mdpi | 48x48 |
| mipmap-hdpi | 72x72 |
| mipmap-xhdpi | 96x96 |
| mipmap-xxhdpi | 144x144 |
| mipmap-xxxhdpi | 192x192 |

### Step 4.2: Use Android Studio Asset Studio

1. Open project in Android Studio
2. Right-click on `res` folder → New → Image Asset
3. Select your 512x512 icon
4. Generate all sizes automatically

Or copy icons from your PWA:
```bash
cp /app/frontend/public/icons/icon-48x48.png twa-android/app/src/main/res/mipmap-mdpi/ic_launcher.png
cp /app/frontend/public/icons/icon-72x72.png twa-android/app/src/main/res/mipmap-hdpi/ic_launcher.png
cp /app/frontend/public/icons/icon-96x96.png twa-android/app/src/main/res/mipmap-xhdpi/ic_launcher.png
cp /app/frontend/public/icons/icon-144x144.png twa-android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png
cp /app/frontend/public/icons/icon-192x192.png twa-android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png
```

---

## PART 5: BUILD THE APP

### Step 5.1: Open Project in Android Studio

1. Launch Android Studio
2. File → Open → Select `twa-android` folder
3. Wait for Gradle sync to complete (may take a few minutes)

### Step 5.2: Build App Bundle (Recommended)

1. Build → Generate Signed Bundle / APK
2. Select **"Android App Bundle"**
3. Click Next
4. Select your keystore:
   - Key store path: Browse to your .jks file
   - Key store password: Enter your password
   - Key alias: monetrax
   - Key password: Enter your key password
5. Click Next
6. Select "release" build variant
7. Click Create

The .aab file will be generated in:
`twa-android/app/release/app-release.aab`

### Step 5.3: Alternative - Build APK

For testing on devices before publishing:
1. Build → Generate Signed Bundle / APK
2. Select **"APK"**
3. Follow same signing steps
4. APK will be in `twa-android/app/release/app-release.apk`

---

## PART 6: PUBLISH TO GOOGLE PLAY

### Step 6.1: Create App Listing

1. Go to https://play.google.com/console
2. Click "Create app"
3. Fill in:
   - **App name**: Monetrax
   - **Default language**: English (United Kingdom)
   - **App or game**: App
   - **Free or paid**: Free (with in-app purchases for subscriptions)
4. Accept declarations and create app

### Step 6.2: Complete Store Listing

**Main store listing:**

| Field | Value |
|-------|-------|
| App name | Monetrax |
| Short description | Tax compliance & bookkeeping for Nigerian MSMEs |
| Full description | See below |

**Full Description:**
```
Monetrax - Your Personal Tax Assistant & Business Coach

Simplify bookkeeping and tax compliance for your Nigerian business. Monetrax helps MSMEs track transactions, calculate VAT, and stay NRS-ready with AI-powered insights.

KEY FEATURES:

📊 Smart Transaction Tracking
• Record income and expenses effortlessly
• Categorize transactions automatically
• Import transactions via CSV or scan receipts

💰 Automatic Tax Calculations
• Real-time VAT calculations
• Income tax estimates based on Nigerian tax brackets
• NRS (National Revenue Service) readiness score

🤖 AI-Powered Insights
• Get personalized financial advice
• Identify cost-saving opportunities
• Understand your business trends

📱 Works Offline
• Record transactions without internet
• Data syncs automatically when online
• Access your data anytime, anywhere

📈 Professional Reports
• Generate PDF tax reports
• Export data to CSV
• Share reports with your accountant

🔒 Secure & Private
• Bank-level encryption
• Your data stays private
• Regular security updates

SUBSCRIPTION PLANS:
• Free: 50 transactions, CSV export
• Starter: ₦5,000/month - 200 transactions, AI insights
• Business: ₦10,000/month - 1,000 transactions, Receipt OCR, PDF reports
• Enterprise: ₦20,000/month - Unlimited transactions, all features

Built specifically for Nigerian MSMEs. Start for free today!
```

### Step 6.3: Add Graphics

**Required:**
- **App icon**: 512x512 PNG (use your existing icon-512x512.png)
- **Feature graphic**: 1024x500 PNG
- **Screenshots**: Minimum 2 phone screenshots (1080x1920 or similar)

**Tips for screenshots:**
1. Open your app on a phone or emulator
2. Take screenshots of key screens:
   - Dashboard with NRS score
   - Transaction list
   - Add transaction form
   - Reports/insights page
   - Subscription plans

### Step 6.4: Set Up App Content

1. **Privacy policy**: Required - create a privacy policy page on your website
2. **App category**: Finance
3. **Content rating**: Complete the questionnaire (likely "Everyone")
4. **Target audience**: 18+ (financial app)

### Step 6.5: Upload App Bundle

1. Go to Release → Production
2. Click "Create new release"
3. Upload your `app-release.aab` file
4. Add release notes:
   ```
   Initial release of Monetrax - Financial OS for Nigerian MSMEs
   
   Features:
   - Transaction tracking
   - Tax calculations (VAT & Income Tax)
   - NRS readiness score
   - AI-powered insights
   - Receipt scanning
   - PDF reports
   - CSV export
   ```
5. Click "Review release"
6. Click "Start rollout to Production"

### Step 6.6: Wait for Review

- Google typically reviews apps within 1-7 days
- You'll receive an email when approved
- Check for any policy issues in the console

---

## PART 7: POST-LAUNCH

### Step 7.1: Monitor Performance

- Check Play Console dashboard for:
  - Downloads
  - Ratings & reviews
  - Crash reports
  - ANR (App Not Responding) reports

### Step 7.2: Respond to Reviews

- Reply to user reviews promptly
- Address issues and thank positive reviewers

### Step 7.3: Update Your App

**For web changes:**
- No app update needed! TWA automatically loads latest web content

**For app wrapper changes:**
1. Update version in `build.gradle`:
   ```gradle
   versionCode 2
   versionName "1.1.0"
   ```
2. Build new .aab file
3. Upload to Play Console
4. Create new release

---

## TROUBLESHOOTING

### App shows Chrome browser instead of full-screen
- Verify Digital Asset Links file is accessible
- Check SHA256 fingerprint matches exactly
- Clear Chrome cache on test device
- Wait up to 24 hours for Chrome to cache the asset links

### "App not installed" error
- Ensure APK is properly signed
- Check minimum SDK version compatibility
- Enable "Install from unknown sources" for testing

### Blank white screen
- Check internet connectivity
- Verify your website URL is correct in strings.xml
- Check browser console for errors

### Play Store rejection
- Review rejection email carefully
- Common issues:
  - Missing privacy policy
  - Incomplete store listing
  - Deceptive behavior flags
- Fix issues and resubmit

---

## QUICK REFERENCE

| Item | Value |
|------|-------|
| Package name | com.monetrax.app |
| Min SDK | 21 (Android 5.0) |
| Target SDK | 34 (Android 14) |
| Web URL | https://monetrax-admin.preview.emergentagent.com |
| Asset Links | /.well-known/assetlinks.json |

---

## NEED HELP?

- TWA Documentation: https://developer.chrome.com/docs/android/trusted-web-activity/
- Play Console Help: https://support.google.com/googleplay/android-developer/
- Android Studio: https://developer.android.com/studio/intro

