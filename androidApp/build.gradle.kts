plugins { id("com.android.application") }
android {
    namespace = "io.karnama.mobile"
    compileSdk = 35
    defaultConfig {
        applicationId = "io.karnama.mobile"
        minSdk = 26
        targetSdk = 35
        versionCode = 2
        versionName = "0.2.0"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
dependencies { implementation("androidx.work:work-runtime:2.9.1") }
