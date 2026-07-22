package com.minchodan.app

import android.content.Context
import android.media.AudioManager
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.Promise

class AudioSessionBridgeModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    private val audioManager: AudioManager =
        reactContext.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    override fun getName(): String {
        return "AudioSessionBridgeModule"
    }

    @ReactMethod
    fun setVoiceProcessing(enabled: Boolean, promise: Promise) {
        try {
            if (enabled) {
                // 통화(Communication) 모드로 전환하여 기기 자체 하드웨어 AEC(에코 캔슬러) 구동 유도
                audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
                audioManager.isSpeakerphoneOn = true
            } else {
                // 일반 재생 모드로 복구
                audioManager.mode = AudioManager.MODE_NORMAL
            }
            promise.resolve(true)
        } catch (e: Exception) {
            promise.reject("AUDIO_MODE_ERROR", e.message)
        }
    }

    @ReactMethod
    fun getSessionInfo(promise: Promise) {
        try {
            val modeStr = when (audioManager.mode) {
                AudioManager.MODE_NORMAL -> "NORMAL"
                AudioManager.MODE_RINGTONE -> "RINGTONE"
                AudioManager.MODE_IN_CALL -> "IN_CALL"
                AudioManager.MODE_IN_COMMUNICATION -> "IN_COMMUNICATION"
                else -> "UNKNOWN"
            }
            promise.resolve("Android AudioManager Mode: $modeStr")
        } catch (e: Exception) {
            promise.reject("AUDIO_INFO_ERROR", e.message)
        }

    }

}
