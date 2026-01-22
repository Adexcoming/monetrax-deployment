# Monetrax TWA (Trusted Web Activity) - Android App

This folder contains the TWA project to publish Monetrax on Google Play Store.

## Prerequisites

1. **Android Studio** - Download from https://developer.android.com/studio
2. **Java JDK 11+** - Usually comes with Android Studio
3. **Google Play Developer Account** - $25 one-time fee at https://play.google.com/console

## Quick Start

### Option 1: Using Bubblewrap (Recommended - Easiest)

Bubblewrap is Google's official tool for creating TWA apps.

```bash
# Install Bubblewrap globally
npm install -g @anthropic/anthropic @nicolo-ribaudo/bubblewrap

# Initialize project (run from this directory)
bubblewrap init --manifest https://YOUR_PRODUCTION_URL/manifest.json

# Build the APK
bubblewrap build

# The APK will be generated in the app-release-signed.apk
```

### Option 2: Using Android Studio (Manual)

1. Open Android Studio
2. File → Open → Select this `twa-android` folder
3. Wait for Gradle sync to complete
4. Build → Generate Signed Bundle / APK
5. Follow the signing wizard

## Project Structure

```
twa-android/
├── app/
│   ├── src/main/
│   │   ├── AndroidManifest.xml    # App configuration
│   │   ├── res/
│   │   │   ├── values/
│   │   │   │   ├── strings.xml    # App strings & URL config
│   │   │   │   └── colors.xml     # Theme colors
│   │   │   ├── mipmap-*/          # App icons
│   │   │   └── drawable/          # Splash screen
│   │   └── java/.../
│   │       └── LauncherActivity.java
│   └── build.gradle
├── build.gradle                    # Project build config
├── settings.gradle
└── gradle.properties
```

## Configuration

### 1. Update Your Production URL

Edit `app/src/main/res/values/strings.xml`:
```xml
<string name="host_url">your-production-domain.com</string>
```

### 2. Digital Asset Links (REQUIRED)

For the TWA to work properly, you must host a Digital Asset Links file.

Create `/.well-known/assetlinks.json` on your server with:
```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "com.monetrax.app",
    "sha256_cert_fingerprints": ["YOUR_SHA256_FINGERPRINT"]
  }
}]
```

To get your SHA256 fingerprint:
```bash
keytool -list -v -keystore your-keystore.jks -alias your-alias
```

### 3. Generate Signing Key

```bash
keytool -genkey -v -keystore monetrax-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias monetrax
```

**IMPORTANT**: Keep your keystore file and passwords safe! You'll need them for all future updates.

## Building for Release

### Generate Signed APK

1. Build → Generate Signed Bundle / APK
2. Select "APK"
3. Choose your keystore
4. Select "release" build variant
5. APK will be in `app/release/app-release.apk`

### Generate App Bundle (Recommended for Play Store)

1. Build → Generate Signed Bundle / APK
2. Select "Android App Bundle"
3. Choose your keystore
4. AAB will be in `app/release/app-release.aab`

## Publishing to Google Play Store

### 1. Create App in Play Console
- Go to https://play.google.com/console
- Create a new app
- Fill in app details

### 2. Store Listing Requirements
- **App Name**: Monetrax - Financial OS
- **Short Description** (80 chars): Tax compliance & bookkeeping for Nigerian businesses
- **Full Description**: See `store_listing.txt`
- **App Icon**: 512x512 PNG (use `/icons/icon-512x512.png`)
- **Feature Graphic**: 1024x500 PNG
- **Screenshots**: At least 2 phone screenshots
- **Privacy Policy URL**: Required

### 3. Upload App Bundle
- Go to Release → Production
- Create new release
- Upload the .aab file
- Complete rollout

## Troubleshooting

### White screen / Chrome browser opens
- Verify Digital Asset Links file is accessible
- Check SHA256 fingerprint matches your signing key
- Ensure HTTPS is working

### App won't install
- Check minimum SDK version (21)
- Verify APK is signed

### Updates not showing
- TWA automatically shows latest web content
- No app store update needed for web changes

## Support

For issues with the TWA wrapper, check:
- https://developer.chrome.com/docs/android/trusted-web-activity/
- https://github.com/nicolo-nicolo-nicolo/nicolo-nicolo-nicolo
