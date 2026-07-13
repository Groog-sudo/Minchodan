package com.minchodan.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.provider.Telephony
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.modules.core.DeviceEventManagerModule

// ==========================================
// 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
// "메시지 오면 읽어주는" 편의기능의 Android 측 SMS 수신 브릿지입니다.
// ==========================================
//
// 💡 [면접 대비 주석 - 왜 매니페스트 정적 리시버가 아니라 동적 등록인가]
// Q. AndroidManifest에 <receiver>를 선언하는 대신 코드에서 registerReceiver를
//    호출한 이유가 뭡니까?
// A. "정적 리시버는 앱이 완전히 종료된 상태에서도 시스템이 깨워 실행하는데,
//    Android 8(API 26) 이후 암시적 브로드캐스트 백그라운드 제한까지 얽혀 데모
//    범위를 벗어납니다. 이번 기능은 '앱이 열려 있는 동안 수신 문자를 읽어준다'는
//    데모 스코프로 한정하고, startListening/stopListening을 JS 생명주기(화면
//    mount/unmount)에 맞춰 호출하는 동적 등록을 선택했습니다. 앱이 백그라운드나
//    종료 상태일 때는 읽어주지 않는 게 현재 알려진 한계입니다."
//
// [TH HARDCODE] RECEIVE_SMS 권한은 Google Play 정책상 "기본 문자 앱(Default SMS
// app)"이 아니면 상시 허용되지 않는 민감 권한이다. 데모/사이드로드 빌드 범위를
// 벗어나 스토어에 배포하려면 별도 정책 심사 절차가 필요하다 - 발표 시 반드시 언급.
//
// [TH HARDCODE - 공기계 테스트] SIM 없는 실기기는 실제 SMS가 오지 않으므로
// DEBUG_SMS_ACTION 브로드캐스트로 동일 이벤트 경로를 검증한다.
//   adb shell am broadcast -p com.minchodan.app -a com.minchodan.app.DEBUG_SMS \
//     --es sender "01012345678" --es body "테스트 메시지"
class SmsReaderModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    companion object {
        const val DEBUG_SMS_ACTION = "com.minchodan.app.DEBUG_SMS"
    }

    private var receiver: BroadcastReceiver? = null

    override fun getName(): String {
        return "SmsReaderModule"
    }

    private fun emitSms(sender: String, body: String) {
        if (body.isBlank()) return
        val payload = Arguments.createMap()
        payload.putString("sender", sender)
        payload.putString("body", body)
        reactApplicationContext
            .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
            .emit("onSmsReceived", payload)
    }

    @ReactMethod
    fun startListening(promise: Promise) {
        try {
            if (receiver != null) {
                promise.resolve(true)
                return
            }
            val newReceiver = object : BroadcastReceiver() {
                override fun onReceive(context: Context, intent: Intent) {
                    when (intent.action) {
                        DEBUG_SMS_ACTION -> {
                            // 공기계/에뮬 SIM 없이 TTS 경로만 검증하는 디버그 인입.
                            val sender = intent.getStringExtra("sender") ?: "디버그발신"
                            val body = intent.getStringExtra("body") ?: return
                            emitSms(sender, body)
                        }
                        Telephony.Sms.Intents.SMS_RECEIVED_ACTION -> {
                            // [TH HARDCODE] 장문 SMS는 통신사에서 여러 PDU로 분할해 보낼 수
                            // 있어, 같은 브로드캐스트 안의 조각들을 이어 붙여 본문을 만든다.
                            val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
                            if (messages.isNullOrEmpty()) return
                            val sender = messages[0].originatingAddress ?: "알 수 없음"
                            val body = messages.joinToString(separator = "") { it.messageBody ?: "" }
                            emitSms(sender, body)
                        }
                    }
                }
            }
            val filter = IntentFilter().apply {
                addAction(Telephony.Sms.Intents.SMS_RECEIVED_ACTION)
                addAction(DEBUG_SMS_ACTION)
            }
            // adb 브로드캐스트(디버그) 수신을 위해 EXPORTED 필요(API 33+).
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                reactApplicationContext.registerReceiver(
                    newReceiver,
                    filter,
                    Context.RECEIVER_EXPORTED,
                )
            } else {
                @Suppress("UnspecifiedRegisterReceiverFlag")
                reactApplicationContext.registerReceiver(newReceiver, filter)
            }
            receiver = newReceiver
            promise.resolve(true)
        } catch (e: Exception) {
            promise.reject("SMS_LISTEN_ERROR", e.message)
        }
    }

    @ReactMethod
    fun stopListening(promise: Promise) {
        try {
            receiver?.let { reactApplicationContext.unregisterReceiver(it) }
            receiver = null
            promise.resolve(true)
        } catch (e: Exception) {
            promise.reject("SMS_UNLISTEN_ERROR", e.message)
        }
    }

    /** 공기계 검증용: JS/브리지에서 직접 가짜 문자를 주입한다. */
    @ReactMethod
    fun simulateIncomingSms(sender: String, body: String, promise: Promise) {
        try {
            emitSms(sender, body)
            promise.resolve(true)
        } catch (e: Exception) {
            promise.reject("SMS_SIMULATE_ERROR", e.message)
        }
    }
}
