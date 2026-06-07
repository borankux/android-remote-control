plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

fun publicConfigValue(name: String, fallback: String): String =
    providers.gradleProperty(name)
        .orElse(providers.environmentVariable(name))
        .orElse(fallback)
        .get()

fun buildConfigString(value: String): String =
    "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

android {
    namespace = "com.allin.cloudphone.inspector"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.allin.cloudphone.inspector"
        minSdk = 24
        targetSdk = 36
        versionCode = 9
        versionName = "0.8.2"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField(
            "String",
            "RELAY_URL",
            buildConfigString(publicConfigValue("CLOUDPHONE_RELAY_URL", "wss://relay.example.com/cloudphone-relay/ws/device"))
        )
        buildConfigField(
            "String",
            "RELAY_TOKEN",
            buildConfigString(publicConfigValue("CLOUDPHONE_RELAY_TOKEN", ""))
        )
        buildConfigField(
            "String",
            "UPDATE_HOST",
            buildConfigString(publicConfigValue("CLOUDPHONE_UPDATE_HOST", "relay.example.com"))
        )
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        buildConfig = true
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    testImplementation("junit:junit:4.13.2")
}
