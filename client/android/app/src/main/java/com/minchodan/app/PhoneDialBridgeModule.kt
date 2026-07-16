package com.minchodan.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import androidx.core.content.ContextCompat
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

class PhoneDialBridgeModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String {
        return "PhoneDialBridgeModule"
    }

    @ReactMethod
    fun placeCall(phoneNumber: String, contactName: String?, promise: Promise) {
        val cleaned = phoneNumber.replace(Regex("[^0-9+]"), "")
        if (cleaned.isEmpty()) {
            promise.reject("invalid_number", "전화번호가 비어 있습니다")
            return
        }
        val activity = currentActivity
        if (activity == null) {
            promise.reject("no_activity", "Activity not available")
            return
        }
        if (ContextCompat.checkSelfPermission(
                reactApplicationContext,
                Manifest.permission.CALL_PHONE
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            promise.reject("permission_denied", "CALL_PHONE not granted")
            return
        }
        try {
            val intent = Intent(Intent.ACTION_CALL, Uri.parse("tel:$cleaned"))
            activity.startActivity(intent)
            promise.resolve(
                mapOf(
                    "mode" to "action_call",
                    "phoneNumber" to cleaned
                )
            )
        } catch (e: Exception) {
            promise.reject("dial_failed", e.message)
        }
    }
}
