package com.minchodan.app

import android.content.Context
import android.os.Build
import android.os.PowerManager
import android.util.Log
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

/**
 * 💡 [면접 대비 주석] ADPF(Adaptive Performance Framework) 발열 헤드룸 브릿지 (2026-07-29).
 *
 * 핸드오프 §5.8에서 "프레임이 끊긴다"는 신고를 추적한 결과 코드 회귀가 아니라 기기 발열
 * 스로틀링이었다(cpu7 3.0GHz -> 0.81GHz, 카메라 세션 30fps -> 중앙 12.6fps). 그런데 §5.7에서
 * 추론 지연을 캡처 컨트롤러의 입력에서 떼어내면서(blocksCapture=false), 캡처 경로 자체가
 * 느려질 때 물러설 장치가 함께 사라졌다. 이전에는 추론 지연이 거친 대리 지표 역할을 했다.
 *
 * 실사용은 장시간 보행이라 스로틀링이 재현될 조건이므로, 대리 지표 대신 발열을 직접 읽는다.
 *
 * 두 가지를 함께 노출한다.
 *  - headroom: PowerManager.getThermalHeadroom(forecastSeconds). 1.0이 스로틀링 임계이며
 *    그 이상이면 이미 성능이 깎이고 있다는 뜻이다. 예보값이라 임계 도달 "전에" 물러설 수 있다.
 *  - status: PowerManager.getCurrentThermalStatus(). §5.8 실측에서 이 값은 스로틀링 중에도
 *    0(NONE)으로 보고됐으므로 단독 판단 근거로 쓰지 않는다. 진단 로그용으로만 함께 넘긴다.
 *
 * API 요구사항: getThermalHeadroom은 Android 11(API 30)+, getCurrentThermalStatus는
 * Android 10(API 29)+. 미지원 단말·미지원 SoC에서는 각각 null로 내려 JS가 발열 제어를
 * 통째로 비활성화하게 한다(기능 저하 없이 기존 동작 유지).
 */
class ThermalBridgeModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    private val powerManager: PowerManager? =
        reactContext.getSystemService(Context.POWER_SERVICE) as? PowerManager

    override fun getName(): String {
        return "ThermalBridgeModule"
    }

    /**
     * @param forecastSeconds 몇 초 뒤를 예보할지. 0이면 현재값.
     *        플랫폼이 호출 간격을 최소 10초로 제한하며, 그보다 자주 부르면 직전 값을 그대로
     *        돌려주므로 JS 폴링 주기도 10초 이상으로 맞춰야 한다.
     */
    @ReactMethod
    fun getThermalState(forecastSeconds: Int, promise: Promise) {
        val result = Arguments.createMap()
        val pm = powerManager
        if (pm == null) {
            result.putNull("headroom")
            result.putNull("status")
            result.putString("reason", "POWER_SERVICE 미제공")
            promise.resolve(result)
            return
        }

        // 헤드룸(API 30+). 지원하지 않는 SoC/커널에서는 NaN이 온다.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            try {
                val headroom = pm.getThermalHeadroom(forecastSeconds.coerceAtLeast(0))
                if (headroom.isNaN() || headroom.isInfinite()) {
                    result.putNull("headroom")
                    result.putString("reason", "헤드룸 미지원(NaN)")
                } else {
                    result.putDouble("headroom", headroom.toDouble())
                }
            } catch (e: Throwable) {
                Log.w(TAG, "getThermalHeadroom 실패: ${e.message}")
                result.putNull("headroom")
                result.putString("reason", "헤드룸 조회 예외: ${e.message}")
            }
        } else {
            result.putNull("headroom")
            result.putString("reason", "API ${Build.VERSION.SDK_INT} < 30")
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            try {
                result.putInt("status", pm.currentThermalStatus)
            } catch (e: Throwable) {
                result.putNull("status")
            }
        } else {
            result.putNull("status")
        }

        promise.resolve(result)
    }

    companion object {
        private const val TAG = "ThermalBridge"
    }
}
