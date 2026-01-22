# Monetrax - ProGuard Rules

# Keep AndroidBrowserHelper classes
-keep class com.google.androidbrowserhelper.** { *; }
-keep class androidx.browser.** { *; }

# Keep custom tabs classes
-keep class android.support.customtabs.** { *; }

# Don't warn about missing classes
-dontwarn com.google.androidbrowserhelper.**
-dontwarn androidx.browser.**
