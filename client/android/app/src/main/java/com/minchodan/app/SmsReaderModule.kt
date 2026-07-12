package com.minchodan.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
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
// [미검증] SMS 브로드캐스트 수신 자체는 아직 실측으로 검증되지 않았다. Android
// 에뮬레이터는 가짜 모뎀으로 SMS 수신을 완전히 시뮬레이션할 수 있으므로(Extended
// Controls > Phone > SMS, 또는 `adb emu sms send <번호> "<본문>"`) 실기기 SIM 없이도
// 검증 가능하다 - 테스트 후 이 주석을 갱신할 것.
class SmsReaderModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    private var receiver: BroadcastReceiver? = null

    override fun getName(): String {
        return "SmsReaderModule"
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
                    // [TH HARDCODE] 장문 SMS는 통신사에서 여러 PDU로 분할해 보낼 수
                    // 있어, 같은 브로드캐스트 안의 조각들을 이어 붙여 본문을 만든다.
                    val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
                    if (messages.isNullOrEmpty()) return
                    val sender = messages[0].originatingAddress ?: "알 수 없음"
                    val body = messages.joinToString(separator = "") { it.messageBody ?: "" }
                    if (body.isBlank()) return

                    val payload = Arguments.createMap()
                    payload.putString("sender", sender)
                    payload.putString("body", body)

                    reactApplicationContext
                        .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
                        .emit("onSmsReceived", payload)
                }
            }
            reactApplicationContext.registerReceiver(
                newReceiver,
                IntentFilter(Telephony.Sms.Intents.SMS_RECEIVED_ACTION),
            )
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
}
