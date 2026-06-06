# Cloudphone Home Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Android app homepage into a glass-style cloudphone status panel while keeping detailed diagnostics available in a collapsed section.

**Architecture:** Keep the existing diagnostics collectors and Relay service unchanged. Replace the XML layout with a status-first screen and update `MainActivity` rendering helpers so the same `DiagnosticReport` drives compact status cards, copy actions, and hidden details.

**Tech Stack:** Kotlin, Android XML/View, AppCompat, Material Components, Gradle Android Plugin 8.5.0, minSdk 24.

---

## File Structure

- Modify `app/src/main/res/values/colors.xml`: add glass-panel palette and status colors.
- Modify `app/src/main/res/values/styles.xml`: add reusable glass card, metric, and compact button styles.
- Modify `app/src/main/res/values/strings.xml`: add labels for connection copy, details toggle, and status actions.
- Replace `app/src/main/res/layout/activity_main.xml`: convert the current text-heavy scroll page into a status-first layout with a collapsed diagnostics detail area.
- Modify `app/src/main/java/com/allin/cloudphone/inspector/MainActivity.kt`: bind new views, render compact status, calculate readiness score, toggle details, and add copy connection info.

## Task 1: Resource Tokens

**Files:**
- Modify: `app/src/main/res/values/colors.xml`
- Modify: `app/src/main/res/values/styles.xml`
- Modify: `app/src/main/res/values/strings.xml`

- [ ] **Step 1: Update color tokens**

Replace `app/src/main/res/values/colors.xml` with:

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="bg">#EAF4F0</color>
    <color name="bg_deep">#DDEDE8</color>
    <color name="surface">#F8FFFC</color>
    <color name="surface_glass">#CCFFFFFF</color>
    <color name="surface_glass_strong">#E9FFFFFF</color>
    <color name="glass_stroke">#B3FFFFFF</color>
    <color name="text_primary">#123033</color>
    <color name="text_secondary">#60777B</color>
    <color name="text_muted">#8BA1A4</color>
    <color name="ok">#0B8F86</color>
    <color name="warn">#B7791F</color>
    <color name="bad">#C2413A</color>
    <color name="unknown">#718096</color>
    <color name="brand">#0B8F86</color>
    <color name="brand_dark">#075E59</color>
    <color name="button_soft">#E7F3F0</color>
</resources>
```

- [ ] **Step 2: Update styles**

Keep `AppTheme` and existing styles for compatibility, then append these new styles to `app/src/main/res/values/styles.xml` before `</resources>`:

```xml
<style name="GlassPanel">
    <item name="android:layout_width">match_parent</item>
    <item name="android:layout_height">wrap_content</item>
    <item name="android:background">@drawable/bg_glass_panel</item>
    <item name="android:padding">16dp</item>
</style>

<style name="MetricPanel">
    <item name="android:layout_width">0dp</item>
    <item name="android:layout_height">92dp</item>
    <item name="android:layout_weight">1</item>
    <item name="android:background">@drawable/bg_metric_panel</item>
    <item name="android:padding">12dp</item>
</style>

<style name="CompactButton">
    <item name="android:layout_width">0dp</item>
    <item name="android:layout_height">44dp</item>
    <item name="android:layout_weight">1</item>
    <item name="android:layout_marginEnd">8dp</item>
    <item name="android:textAllCaps">false</item>
    <item name="cornerRadius">14dp</item>
</style>
```

- [ ] **Step 3: Update strings**

Append these strings to `app/src/main/res/values/strings.xml` before `</resources>`:

```xml
<string name="copy_connection">复制接入信息</string>
<string name="details_show">查看诊断详情</string>
<string name="details_hide">收起诊断详情</string>
<string name="cloudphone_taken_over">云机已接管</string>
```

- [ ] **Step 4: Create drawable backgrounds**

Create `app/src/main/res/drawable/bg_glass_panel.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android">
    <solid android:color="@color/surface_glass" />
    <stroke android:width="1dp" android:color="@color/glass_stroke" />
    <corners android:radius="24dp" />
    <padding android:left="0dp" android:top="0dp" android:right="0dp" android:bottom="0dp" />
</shape>
```

Create `app/src/main/res/drawable/bg_metric_panel.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android">
    <solid android:color="@color/surface_glass_strong" />
    <stroke android:width="1dp" android:color="@color/glass_stroke" />
    <corners android:radius="18dp" />
</shape>
```

Create `app/src/main/res/drawable/bg_status_pill.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android">
    <solid android:color="#E6F7F3" />
    <corners android:radius="999dp" />
</shape>
```

Create `app/src/main/res/drawable/bg_primary_button.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android">
    <solid android:color="@color/brand" />
    <corners android:radius="16dp" />
</shape>
```

- [ ] **Step 5: Verify resource compilation**

Run:

```bash
./gradlew :app:assembleDebug
```

Expected: build passes or only pre-existing warnings appear.

## Task 2: Status-First Layout

**Files:**
- Replace: `app/src/main/res/layout/activity_main.xml`

- [ ] **Step 1: Replace the layout with a status-first screen**

Replace `activity_main.xml` with a `ScrollView` containing:

- Header row: title, online pill, subtitle.
- Hero glass panel: status label, readiness score, short explanation.
- Metric grid: Relay, Root, ADB, foreground app.
- Action buttons: copy connection, copy JSON, refresh, Relay toggle.
- Network test panel.
- Collapsed details container with existing text views.

Required view IDs:

```text
subtitleText
statusPillText
heroTitleText
heroSubtitleText
scoreText
relayMetricText
rootMetricText
adbMetricText
foregroundMetricText
copyConnectionButton
copyJsonButton
refreshButton
relayToggleButton
detailsToggleButton
detailsContainer
serverInput
networkButton
networkText
systemText
rootText
permissionText
relayText
appText
jsonText
summaryText
```

Implementation note: keep a single `ScrollView` for Android 7 compatibility. The detail section starts with `android:visibility="gone"` so the homepage is clean by default.

- [ ] **Step 2: Build after layout replacement**

Run:

```bash
./gradlew :app:assembleDebug
```

Expected: Kotlin compile fails only if `MainActivity` still references removed button IDs such as `copySummaryButton`, `settingsButton`, `startRelayButton`, or `stopRelayButton`. Those are fixed in Task 3.

## Task 3: MainActivity Rendering

**Files:**
- Modify: `app/src/main/java/com/allin/cloudphone/inspector/MainActivity.kt`

- [ ] **Step 1: Update view bindings**

Add properties:

```kotlin
private lateinit var statusPillText: TextView
private lateinit var heroTitleText: TextView
private lateinit var heroSubtitleText: TextView
private lateinit var scoreText: TextView
private lateinit var relayMetricText: TextView
private lateinit var rootMetricText: TextView
private lateinit var adbMetricText: TextView
private lateinit var foregroundMetricText: TextView
private lateinit var copyConnectionButton: Button
private lateinit var relayToggleButton: Button
private lateinit var detailsToggleButton: Button
private lateinit var detailsContainer: android.view.View
```

Remove bindings and click listeners for:

```kotlin
copySummaryButton
settingsButton
startRelayButton
stopRelayButton
```

Bind new IDs in `bindViews()`.

- [ ] **Step 2: Add compact status helpers**

Add these helper methods:

```kotlin
private fun readinessScore(report: DiagnosticReport): Int {
    var score = 40
    if (report.root.rootAvailable) score += 25
    if (RelayService.latestStatus.contains("已连接")) score += 20
    if (report.permissions.count { it.granted } >= report.permissions.size.coerceAtLeast(1) / 2) score += 10
    if (report.network?.status == "success") score += 5
    return score.coerceIn(0, 100)
}

private fun relayShortStatus(): String = when {
    RelayService.latestStatus.contains("已连接") -> "Online"
    RelayService.latestStatus.contains("重试") -> "Retrying"
    RelayService.latestStatus.contains("失败") -> "Failed"
    else -> "Unknown"
}

private fun adbShortStatus(): String = "Unknown"

private fun foregroundShortStatus(): String = "Unknown"
```

Implementation note: ADB and foreground can start as `Unknown` because existing homepage report does not currently include snapshot output. Do not add new Root commands in this UI-only task.

- [ ] **Step 3: Render hero and metric cards**

In `render(report)`, update:

```kotlin
val score = readinessScore(report)
scoreText.text = score.toString()
statusPillText.text = relayShortStatus()
heroTitleText.text = when {
    !RelayService.latestStatus.contains("已连接") -> "Relay 未连接"
    report.root.rootAvailable -> "云机已接管"
    else -> "需要处理 Root"
}
heroSubtitleText.text = "${report.deviceModel} · Android ${report.androidVersion} · ${report.generatedAt}"
relayMetricText.text = relayShortStatus()
rootMetricText.text = if (report.root.rootAvailable) "Ready" else "Unavailable"
adbMetricText.text = adbShortStatus()
foregroundMetricText.text = foregroundShortStatus()
subtitleText.text = "App ${report.appVersion} · SDK ${report.sdkInt}"
summaryText.text = TextSummaryFormatter.format(report)
```

Keep existing detail text rendering for `systemText`, `rootText`, `permissionText`, `networkText`, `appText`, and `jsonText`.

- [ ] **Step 4: Add connection info copy**

Add:

```kotlin
private fun copyConnectionInfo() {
    val report = latestReport
    val text = buildString {
        appendLine("Relay URL: ${RelayConfig.baseUrl}")
        appendLine("Device ID: ${RelayDeviceId.raw(this@MainActivity)}")
        appendLine("Token header: x-relay-token")
        appendLine("App version: ${report?.appVersion ?: BuildConfig.VERSION_NAME}")
        appendLine("CLI:")
        appendLine("export CLOUDPHONE_RELAY_URL='https://showprogress.cn/cloudphone-relay'")
        appendLine("export CLOUDPHONE_RELAY_TOKEN='<relay-token>'")
        appendLine("export CLOUDPHONE_DEVICE_ID='${RelayDeviceId.raw(this@MainActivity)}'")
        appendLine("node tools/cloudphone-api-client.mjs devices")
    }.trim()
    copy("云机接入信息", text)
}
```

Wire `copyConnectionButton.setOnClickListener { copyConnectionInfo() }`.

- [ ] **Step 5: Add details toggle and Relay toggle**

Add:

```kotlin
private fun toggleDetails() {
    val show = detailsContainer.visibility != android.view.View.VISIBLE
    detailsContainer.visibility = if (show) android.view.View.VISIBLE else android.view.View.GONE
    detailsToggleButton.text = getString(if (show) R.string.details_hide else R.string.details_show)
}

private fun toggleRelay() {
    if (RelayService.latestStatus.contains("已连接")) {
        RelayService.stop(this)
    } else {
        RelayService.start(this)
    }
    renderRelayStatus()
    latestReport?.let { render(it) }
}
```

Wire:

```kotlin
detailsToggleButton.setOnClickListener { toggleDetails() }
relayToggleButton.setOnClickListener { toggleRelay() }
```

- [ ] **Step 6: Build after Kotlin update**

Run:

```bash
./gradlew :app:assembleDebug
```

Expected: build passes.

## Task 4: Polish and Package

**Files:**
- Inspect: `app/build/outputs/apk/debug/app-debug.apk`

- [ ] **Step 1: Check resource colors and one-hue risk**

Run:

```bash
rg -n "#[0-9A-Fa-f]{6}|@color/" app/src/main/res/values app/src/main/res/layout app/src/main/res/drawable
```

Expected: palette includes teal, amber, red, gray, and neutral colors; it is not dominated only by teal variants.

- [ ] **Step 2: Build APK**

Run:

```bash
./gradlew :app:assembleDebug
```

Expected: `app/build/outputs/apk/debug/app-debug.apk` exists.

- [ ] **Step 3: Upload APK for manual install**

Run:

```bash
scp app/build/outputs/apk/debug/app-debug.apk pb:/var/www/download/cloudphone-inspector-glass-home-debug.apk
```

Expected public URL:

```text
https://showprogress.cn/download/cloudphone-inspector-glass-home-debug.apk
```

- [ ] **Step 4: Verify URL**

Run:

```bash
curl -I https://showprogress.cn/download/cloudphone-inspector-glass-home-debug.apk
```

Expected: HTTP 200.

## Self-Review

Spec coverage:

- Homepage no longer displays long diagnostic text by default: Task 2 and Task 3.
- Relay, Root, ADB, device status visible on homepage: Task 2 and Task 3.
- Copy JSON retained: Task 2 and Task 3.
- Copy connection information added: Task 3.
- Details available: Task 2 and Task 3.
- Android 7+ compatible XML/View implementation: all tasks avoid Compose and high-version APIs.
- APK build and URL delivery: Task 4.

Placeholder scan: no incomplete placeholder markers are present.

Type consistency: new view IDs listed in Task 2 match the properties and bindings required in Task 3.
